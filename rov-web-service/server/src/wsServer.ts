import { Server } from "http";
import { WebSocketServer, WebSocket } from "ws";

// 单流帧的 WS 传输载荷结构
export interface WsStreamFrame {
    // 流名
    streamId: string;
    // 时间戳（秒）
    timestamp: number;
    // JPEG 二进制数据
    jpeg: Buffer;
}

// 单个客户端发送缓冲超过该阈值时丢弃新帧，避免慢客户端导致内存无限增长
const MAX_SEND_BUFFER_BYTES = 2 * 1024 * 1024; // 2 MB

export class WsServer {
    private wss: WebSocketServer;

    constructor(server: Server) {
        this.wss = new WebSocketServer({ server, path: "/ws/video" });

        this.wss.on("connection", (ws: WebSocket) => {
            console.log("[WsServer] 客户端已连接，当前连接数:", this.wss.clients.size);

            ws.on("close", () => {
                console.log("[WsServer] 客户端断开，当前连接数:", this.wss.clients.size);
            });

            ws.on("error", (err: Error) => {
                console.error("[WsServer] 连接错误:", err.message);
            });
        });
    }

    // 将单个流帧打包为 WS 二进制消息

    // 每一帧的二进制消息格式为
    // [4 字节大端 headerLength][headerLength 字节 UTF-8 JSON 头][JPEG body]

    // 其中 header 的格式如下
    // JSON 头结构：{ streamId: string, timestamp: number }
    private static packFrame(frame: WsStreamFrame): Buffer {
        const headerJson = Buffer.from(
            JSON.stringify({ streamId: frame.streamId, timestamp: frame.timestamp }),
            "utf-8"
        );

        const headerLength = headerJson.length;
        // headerLength 用 4 字节大端无符号整型
        const prefix = Buffer.alloc(4);
        prefix.writeUInt32BE(headerLength, 0);

        return Buffer.concat([prefix, headerJson, frame.jpeg]);
    }

    // 向所有连接广播一条流帧
    public broadcastStreamFrame(frame: WsStreamFrame): void {
        const payload = WsServer.packFrame(frame);

        for (const client of this.wss.clients) {
            if (client.readyState !== WebSocket.OPEN) {
                continue;
            }
            if (client.bufferedAmount >= MAX_SEND_BUFFER_BYTES) {
                // 客户端消费不过来，丢弃本帧以保护服务端内存
                continue;
            }
            client.send(payload);
        }
    }

    // 当前连接数
    public getClientCount(): number {
        return this.wss.clients.size;
    }

    // 关闭 WS 服务器
    public close(): Promise<void> {
        return new Promise((resolve) => {
            for (const client of this.wss.clients) {
                client.terminate();
            }
            this.wss.close(() => {
                resolve();
            });
        });
    }
}
