# model.py
# 负责从 SharedMemory 获取摄像头帧，运行 YOLO 模型，并将结果编码为 JPEG 发送到后续进程

import multiprocessing
from multiprocessing import shared_memory

import cv2
import numpy as np

import json
import time

from tools.logger import add_log


def put_jpeg_to_queue(queue : multiprocessing.Queue, data : dict):
    # 将 JPEG 数据放入队列，若队列已满则丢弃最旧的数据。
    if queue.full():
        try:
            queue.get_nowait()
        except Exception:
            pass
    queue.put(data)


def model_process(logging_queue : multiprocessing.Queue, global_dictionary : dict,
                  output_queue : multiprocessing.Queue, zmq_queue : multiprocessing.Queue):
    # 读取模型配置
    config_path = "./config/model.config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    model_weight = config.get("model_weight", "yolov8s.pt")
    model_device = config.get("model_device", 0)
    model_imgsz = config.get("model_imgsz", 640)
    model_conf = config.get("model_conf", 0.25)
    jpeg_quality = config.get("jpeg_quality", 80)

    shared_memory_handler = None

    try:
        # 等待摄像头就绪
        add_log(logging_queue, "INFO", "[Model] 等待摄像头就绪...")
        while not global_dictionary.get("camera_ready", False):
            if global_dictionary.get("camera_stop", False):
                add_log(logging_queue, "WARNING", "[Model] 摄像头未就绪即收到退出信号")
                return
            time.sleep(0.1)

        # 附加到 SharedMemory
        shared_memory_name = global_dictionary["camera_frame_shm_name"]
        frame_shape = tuple(global_dictionary["camera_frame_shape"])
        frame_dtype = np.dtype(global_dictionary["camera_frame_dtype"])
        shared_memory_handler = shared_memory.SharedMemory(name=shared_memory_name)
        shared_memory_buffer = np.ndarray(frame_shape, dtype=frame_dtype, buffer=shared_memory_handler.buf)

        add_log(logging_queue, "INFO", f"[Model] 已附加到 SharedMemory: {shared_memory_name}")

        # 加载 YOLO 模型
        from ultralytics import YOLO
        add_log(logging_queue, "INFO", f"[Model] 正在加载 YOLO 模型: {model_weight}")
        model = YOLO(model_weight)
        add_log(logging_queue, "INFO", "[Model] YOLO 模型加载完成")

        # JPEG 编码参数
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]

        last_counter = global_dictionary.get("camera_frame_counter", 0)

        add_log(logging_queue, "INFO", "[Model] 开始推理循环")

        # 检查计数器变化，获取新帧并推理
        while not global_dictionary.get("camera_stop", False):
            current_counter = global_dictionary.get("camera_frame_counter", 0)
            if current_counter == last_counter:
                time.sleep(0.001)
                continue

            last_counter = current_counter

            # 从 SharedMemory 拷贝最新帧
            frame = shared_memory_buffer.copy()

            # 运行 YOLO 模型
            results = model(source=frame, device=model_device, imgsz=model_imgsz, conf=model_conf, verbose=False)

            # 获取带标注的检测结果图像
            annotated_frame = results[0].plot()

            # 编码为 JPEG
            original_jpeg = cv2.imencode('.jpg', frame, encode_param)[1].tobytes()
            annotated_jpeg = cv2.imencode('.jpg', annotated_frame, encode_param)[1].tobytes()

            # 打包数据
            frame_data = {
                "timestamp": time.time(),
                "original": original_jpeg,
                "annotated": annotated_jpeg
            }
            # 发送到 output 和 zmq 两个队列，用于视频输出和网络传输
            put_jpeg_to_queue(output_queue, frame_data)
            put_jpeg_to_queue(zmq_queue, frame_data)

    except Exception as e:
        add_log(logging_queue, "ERROR", f"[Model] 进程异常: {e}")

    finally:
        if shared_memory_handler is not None:
            try:
                shared_memory_handler.close()
            except Exception:
                pass
        add_log(logging_queue, "INFO", "[Model] 进程已退出，资源已释放")