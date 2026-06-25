import express from "express";
import http from "http";

import { ZMQReceive } from "./zmqReceive";
import { WsServer } from "./wsServer";

const PORT = Number(process.env.PORT) || 3000;

async function main(): Promise<void> {
    const app = express();

    // 在 health 路由上暴露一个允许检查当前 wsServer 运行状况的调用
    app.get("/health", (_req, res) => {
        res.json({ status: "ok", clients: wsServer.getClientCount() });
    });

    const server = http.createServer(app);

    // WebSocket 服务器，转发视频流
    const wsServer = new WsServer(server);

    // ZMQ 接收器
    const zmqReceiver = ZMQReceive.getInstance();
    zmqReceiver.onFrame((frame) => {
        wsServer.broadcastStreamFrame({
            streamId: frame.streamId,
            timestamp: frame.timestamp,
            jpeg: frame.jpeg
        });
    });

    server.listen(PORT, () => {
        console.log(`[App] HTTP/WS 服务已启动，端口 ${PORT}`);
    });

    // 启动 ZMQ 接收
    await zmqReceiver.start();

    // 退出
    const shutdown = async (signal: string) => {
        console.log(`[App] 收到 ${signal}，正在关闭...`);
        await zmqReceiver.stop();
        await wsServer.close();
        server.close();
        process.exit(0);
    };

    process.on("SIGINT", () => void shutdown("SIGINT"));
    process.on("SIGTERM", () => void shutdown("SIGTERM"));
}

main().catch((err) => {
    console.error("[App] 启动失败:", err);
    process.exit(1);
});
