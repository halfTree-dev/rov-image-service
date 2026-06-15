# zmq_send.py
# 负责接收 JPEG 帧，通过 ZeroMQ PUB 发布到指定端口

import multiprocessing

import zmq

import json
import time

from tools.logger import add_log


def zmq_send_process(logging_queue : multiprocessing.Queue, zmq_queue : multiprocessing.Queue):
    # 读取 ZeroMQ 配置
    config_path = "./config/zmqsend.config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    zmq_endpoint = config.get("zmq_address", "tcp://*:5555")
    zmq_topic = config.get("zmq_topic", "rov_image")

    context = None
    socket = None

    try:
        # 创建 ZeroMQ PUB 套接字
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind(zmq_endpoint)

        add_log(logging_queue, "INFO", f"[ZMQ] PUB 套接字已绑定到 {zmq_endpoint}")

        while True:
            # 从队列获取帧数据（阻塞等待）
            try:
                frame_data = zmq_queue.get(timeout=1)
            except Exception:
                continue

            # 检查退出信号（收到 None 表示退出）
            if frame_data is None:
                add_log(logging_queue, "INFO", "[ZMQ] 收到退出信号")
                break

            timestamp = frame_data.get("timestamp", time.time())
            original_jpeg = frame_data.get("original")
            annotated_jpeg = frame_data.get("annotated")

            if original_jpeg is None or annotated_jpeg is None:
                continue

            # 使用 multipart 消息发布：[topic, timestamp, original, annotated]
            socket.send_multipart([
                zmq_topic.encode('utf-8'),
                str(timestamp).encode('utf-8'),
                original_jpeg,
                annotated_jpeg
            ])

    except Exception as e:
        add_log(logging_queue, "ERROR", f"[ZMQ] 进程异常: {e}")

    finally:
        if socket is not None:
            try:
                socket.close(linger=0)
            except Exception:
                pass
        if context is not None:
            try:
                context.term()
            except Exception:
                pass
        add_log(logging_queue, "INFO", "[ZMQ] 进程已退出，资源已释放")