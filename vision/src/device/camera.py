# camera.py
# 负责读取摄像头数据，并传递摄像头数据到后续进程

import multiprocessing
from multiprocessing import shared_memory

import cv2
import numpy as np

import json
import time

from tools.logger import add_log

def camera_process(logging_queue : multiprocessing.Queue, global_dictionary : dict):
    # 读取配置
    config_path = "./config/camera.config.json"
    global_dictionary["camera_config"] = {}
    with open(config_path, "r") as f:
        config = json.load(f)
        global_dictionary["camera_config"] = config
    camera_rtsp_url = global_dictionary["camera_config"].get("camera_rtsp_url", "")
    camera_max_capture_error = global_dictionary["camera_config"].get("camera_max_capture_error", 30)

    try:
        capture = None
        shared_memory_handler = None

        # 开启读取
        capture = cv2.VideoCapture(camera_rtsp_url, cv2.CAP_FFMPEG)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture_error_counter = 0

        # 首次读取，并初始化基本信息
        camera_start_properly = False
        while not camera_start_properly:
            global_dictionary["camera_status"] = {}
            ret, frame = capture.read()
            if ret and frame is not None and len(frame.shape) == 3 and frame.shape[2] == 3:
                global_dictionary["camera_status"]["frame_width"] = frame.shape[1]
                global_dictionary["camera_status"]["frame_height"] = frame.shape[0]
                add_log(logging_queue, "INFO", f"[Camera] 摄像头连接成功，分辨率: {frame.shape[1]}x{frame.shape[0]}")
                camera_start_properly = True
            else:
                # 连续读取失败会触发重新连接机制
                add_log(logging_queue, "WARNING", "[Camera] 摄像头连接失败，无法读取有效帧，尝试重新连接")
                capture.release()
                time.sleep(1)
                capture = cv2.VideoCapture(camera_rtsp_url, cv2.CAP_FFMPEG)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                time.sleep(1)

        # 创建 SharedMemory
        """
        SharedMemory 是一种进程间通信方案，允许多个进程共享一块内存区域。此处开辟的区域用于存储摄像头帧数据。
        此处开辟的 frame_size 大小等于 frame 的像素数量（宽 x 高 x 3）乘以每个像素的字节数（uint8 是 1 字节），足够存储一帧图像数据。
        """
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        frame_shape = (frame_height, frame_width, 3)
        frame_dtype = np.uint8
        frame_size = int(np.prod(frame_shape)) * np.dtype(frame_dtype).itemsize
        shared_memory_handler = shared_memory.SharedMemory(create=True, size=frame_size)

        global_dictionary["camera_frame_shm_name"] = shared_memory_handler.name
        global_dictionary["camera_frame_shape"] = frame_shape
        global_dictionary["camera_frame_dtype"] = str(frame_dtype)
        global_dictionary["camera_frame_counter"] = 0
        global_dictionary["camera_ready"] = False
        add_log(logging_queue, "INFO", f"[Camera] 供给摄像头的 SharedMemory 已创建: {shared_memory_handler.name}, 大小: {frame_size} bytes")

        # 写入首帧
        """
        要写入刚才的共享内存，首先需要创建一个 NumPy 数组视图，指向共享内存的缓冲区。这个数组的形状和数据类型必须与我们之前定义的 frame_shape 和 frame_dtype 一致。
        通过 np.copyto() 函数将摄像头读取到的帧写入共享内存中。这个函数会将 frame 中的数据复制到适才的 shared_memory_buffer 中。
        """
        shared_memory_buffer = np.ndarray(frame_shape, dtype=frame_dtype, buffer=shared_memory_handler.buf)
        np.copyto(shared_memory_buffer, frame)
        global_dictionary["camera_frame_counter"] = 1
        global_dictionary["camera_ready"] = True

        # 阻塞读帧并写入 SharedMemory
        # 此处读取的速率与摄像头本身的帧率相等，因为 capture.read() 是阻塞调用，只有当新帧可用时才会返回。
        add_log(logging_queue, "INFO", "[Camera] 开始推送视频流")
        while not global_dictionary.get("camera_stop", False):
            ret, frame = capture.read()
            if not ret:
                # 连续读取失败会触发重新连接机制
                capture_error_counter += 1
                if capture_error_counter >= camera_max_capture_error:
                    add_log(logging_queue, "WARNING", "[Camera] 读取摄像头连续失败")
                    capture.release()
                    time.sleep(1)
                    capture = cv2.VideoCapture(camera_rtsp_url, cv2.CAP_FFMPEG)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    capture_error_counter = 0
                continue

            capture_error_counter = 0
            if frame is not None and len(frame.shape) == 3 and frame.shape[2] == 3:
                # 写入 SharedMemory，递增计数器通知消费者有新帧
                np.copyto(shared_memory_buffer, frame)
                global_dictionary["camera_frame_counter"] = global_dictionary.get("camera_frame_counter", 0) + 1

    except Exception as e:
        add_log(logging_queue, "ERROR", f"[Camera] 摄像头进程异常: {e}")

    finally:
        # 释放资源
        global_dictionary["camera_ready"] = False
        if capture is not None:
            try:
                capture.release()
            except Exception:
                pass
        if shared_memory_handler is not None:
            try:
                shared_memory_handler.close()
                shared_memory_handler.unlink()
            except Exception:
                pass
        add_log(logging_queue, "INFO", "[Camera] 摄像头进程已退出，资源已释放")