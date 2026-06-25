import { Subscriber } from "zeromq";

import * as fs from "fs";
import * as path from "path";

// ZMQReceive 配置结构
export interface ZmqReceiveConfig {
    zmqAddress: string;
    zmqTopic: string;
}

// 单流帧的 WS 传输载荷结构
export interface StreamFrame {
    // 流名
    streamId: string;
    // 时间戳（秒）
    timestamp: number;
    // JPEG 二进制数据
    jpeg: Buffer;
}

// 帧回调类型
export type FrameCallback = (frame: StreamFrame) => void;

// 读取配置文件
function loadConfig(): ZmqReceiveConfig {
    const configPath = path.resolve(__dirname, "../zmqreceive.config.json");
    const raw = fs.readFileSync(configPath, "utf-8");
    const parsed = JSON.parse(raw) as ZmqReceiveConfig;

    if (!parsed.zmqAddress || !parsed.zmqTopic) {
        throw new Error("zmqreceive.config.json 缺少 zmqAddress 或 zmqTopic");
    }

    return parsed;
}

// ZeroMQ SUB 接收器
// 与 Python 脚本对接，负责 connect 到 vision 端 PUB，解析 multipart 消息，按流分发回调
export class ZMQReceive {
    // ZeroMQ 接收器单例
    private static instance: ZMQReceive | null = null;

    private socket: Subscriber | null = null;
    private readonly config: ZmqReceiveConfig;
    private readonly frameCallbacks: Set<FrameCallback> = new Set();
    private running: boolean = false;

    private constructor(config: ZmqReceiveConfig) {
        this.config = config;
    }

    // 获取单例
    public static getInstance(): ZMQReceive {
        if (!ZMQReceive.instance) {
            ZMQReceive.instance = new ZMQReceive(loadConfig());
        }
        return ZMQReceive.instance;
    }

    // 注册帧回调，每收到一个流都会触发一次回调
    public onFrame(callback: FrameCallback): () => void {
        this.frameCallbacks.add(callback);
        return () => {
            this.frameCallbacks.delete(callback);
        };
    }

    // 启动接收循环
    public async start(): Promise<void> {
        if (this.running) {
            return;
        }

        const socket = new Subscriber();
        socket.connect(this.config.zmqAddress);
        // 订阅指定 topic（前缀过滤），空字符串表示订阅全部
        socket.subscribe(this.config.zmqTopic);

        this.socket = socket;
        this.running = true;

        console.log(`[ZMQReceive] SUB 已 connect 到 ${this.config.zmqAddress}, topic=${this.config.zmqTopic}`);

        // 异步接收循环
        this.receiveLoop().catch((err) => {
            console.error("[ZMQReceive] 接收循环异常:", err);
        });
    }

    // 停止接收并关闭 socket
    public async stop(): Promise<void> {
        this.running = false;
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        console.log("[ZMQReceive] 已停止");
    }

    // 接收与分发循环
    private async receiveLoop(): Promise<void> {
        if (!this.socket) {
            return;
        }

        const socket = this.socket;

        while (this.running) {
            let parts: Buffer[];
            try {
                // receive 返回 multipart 各帧
                const result = await socket.receive();
                parts = result.map((p) => Buffer.from(p));
            } catch (err) {
                if (!this.running) {
                    break;
                }
                console.error("[ZMQReceive] receive 出错:", err);
                continue;
            }

            try {
                this.handleMultipart(parts);
            } catch (err) {
                console.error("[ZMQReceive] 解析帧出错:", err);
            }
        }
    }

    // 解析 multipart 帧并按流分发回调
    // 帧序：[topic, namelist(json), timestamp, jpeg0, jpeg1, ...]
    private handleMultipart(parts: Buffer[]): void {
        if (parts.length < 4) {
            // 至少需要 topic + namelist + timestamp + 一个 jpeg
            return;
        }

        const namelistFrame = parts[1];
        const timestampFrame = parts[2];

        // namelist 为 json.dumps 后的字节串，需 JSON.parse
        const namelist = JSON.parse(namelistFrame.toString("utf-8")) as string[];
        const timestamp = Number(timestampFrame.toString("utf-8"));

        // 余下的帧按 namelist 顺序对应各流的 JPEG
        const jpegFrames = parts.slice(3);

        const count = Math.min(namelist.length, jpegFrames.length);
        for (let i = 0; i < count; i++) {
            const frame: StreamFrame = {
                streamId: namelist[i],
                timestamp,
                jpeg: jpegFrames[i]
            };

            for (const callback of this.frameCallbacks) {
                try {
                    callback(frame);
                } catch (err) {
                    console.error("[ZMQReceive] 帧回调异常:", err);
                }
            }
        }
    }
}
