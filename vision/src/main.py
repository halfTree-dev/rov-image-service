# main.py
# Written by half-tree

# 该文件作为入口文件，负责启动以下服务
# 1. 启动读取摄像头的线程
# 2. 启动 yolo 模型线程，并将读取到的图像输入模型进行处理
# 3. 启动将结果储存到本地数据库的线程
# 4. 启动将结果发布到 ZeroMQ 的线程，以供 Node.JS 服务器使用

import multiprocessing
import time
import sys
import os

from device.camera import camera_process
from service.model import model_process
from service.output import output_process
from service.zmqsend import zmq_send_process
from tools.logger import logger_process

if __name__ == "__main__":
    os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "8"

    with multiprocessing.Manager() as manager:
        logging_queue = multiprocessing.Queue()
        global_dictionary = manager.dict()

        processes = []

        # 创建用于进程间传递 JPEG 数据的队列
        output_queue = multiprocessing.Queue(maxsize=30)
        zmq_queue = multiprocessing.Queue(maxsize=30)

        process_list = [
            ("Camera", multiprocessing.Process(target=camera_process, args=(logging_queue, global_dictionary), daemon=True)),
            ("Logger", multiprocessing.Process(target=logger_process, args=(logging_queue,), daemon=True)),
            ("Model", multiprocessing.Process(target=model_process, args=(logging_queue, global_dictionary, output_queue, zmq_queue), daemon=True)),
            ("Output", multiprocessing.Process(target=output_process, args=(logging_queue, output_queue), daemon=True)),
            ("ZMQ", multiprocessing.Process(target=zmq_send_process, args=(logging_queue, zmq_queue), daemon=True))
        ]

        for name, process in process_list:
            process.start()
            processes.append((name, process))
            print(f"视觉处理服务启动子进程: {name}，PID: {process.pid}")

        try:
            while True:
                # 睡大觉
                time.sleep(1)

        except KeyboardInterrupt:
            print("KeyboardInterrupt: 终止视觉处理服务")

            # 设置退出标志，通知各进程退出
            global_dictionary["camera_stop"] = True
            output_queue.put(None)
            zmq_queue.put(None)

            for name, process in processes:
                # process.join(timeout=20) 将会阻塞当前线程，直到子进程退出或超时，这是为了资源能够正常释放
                process.join(timeout=20)

                if process.is_alive():
                    # 如果子进程仍然在运行，说明它没有正常退出，可能是因为某些资源没有正确释放或者存在死循环等问题
                    # 在这种情况下，强制终止子进程
                    process.terminate()
                    process.join(timeout=1)

                print(f"已终止进程: {name}，PID: {process.pid}")
        finally:
            print("再见！朋友！")
            sys.exit(0)