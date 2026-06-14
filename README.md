# ROV Image Service
该服务将部署在 ROV 上，读取 ROV 连接的摄像头，将摄像头图像通过 yolo 模型进行目标检测，并将视频流保存，同时通过 Web 服务将视频流展示给用户上位机。

## 实现框架

1. 构造 Python 进程，运行读取摄像头、yolo 模型进行目标检测、视频流保存和将数据传递到 ZeroMQ 的多个线程。

2. ZeroMQ 是一个高性能异步消息库，用于将数据在不同进程之间传递。

3. NodeJS 构建的 Web 服务采用 Server (Express) - Client (Vue.js) 架构，Server 端通过 ZeroMQ 接收数据并将数据传递给 Client 端，Client 端通过 WebSocket 将视频流展示给用户上位机。

4. 配置其它网络部分相关协议和守护进程，使得工控机上该服务可以自启动。

## TODO

[] 完成 vision.py，调用摄像头并跑通目标识别
[] 学习 ZeroMQ