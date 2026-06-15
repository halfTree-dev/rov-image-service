# output.py
# 负责接收 JPEG 帧，将其写入视频文件，采用循环录像

import multiprocessing

import cv2
import numpy as np

import time
import os
from datetime import datetime
import json

from tools.logger import add_log


def output_process(logging_queue : multiprocessing.Queue, output_queue : multiprocessing.Queue):
    # 读取录像配置
    config_path = "./config/output.config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    output_dir = config.get("output_dir", "./output/videos")
    video_fps = config.get("video_fps", 15)
    segment_duration = config.get("cycle_video_duration", 60)  # 每个视频片段时长（秒）

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 视频写入器和当前片段信息
    original_writer = None
    annotated_writer = None
    segment_start_time = 0
    segment_index = 0
    frame_width = 0
    frame_height = 0

    try:
        add_log(logging_queue, "INFO", "[Output] 录像服务已启动，等待首帧...")

        while True:
            # 从队列获取帧数据（阻塞等待）
            try:
                frame_data = output_queue.get(timeout=1)
            except Exception:
                # 队列为空，检查是否需要因超时而切片
                if original_writer is not None and annotated_writer is not None:
                    elapsed = time.time() - segment_start_time
                    if elapsed >= segment_duration:
                        add_log(logging_queue, "INFO", f"[Output] 视频片段 {segment_index} 录制完成（超时切片）")
                        original_writer.release()
                        annotated_writer.release()
                        original_writer = None
                        annotated_writer = None
                continue

            # 检查退出信号（收到 None 表示退出）
            if frame_data is None:
                add_log(logging_queue, "INFO", "[Output] 收到退出信号")
                break

            timestamp = frame_data.get("timestamp", time.time())
            original_jpeg = frame_data.get("original")
            annotated_jpeg = frame_data.get("annotated")

            if original_jpeg is None or annotated_jpeg is None:
                continue

            # 解码 JPEG 为 numpy 数组以获取尺寸并写入视频
            original_frame = cv2.imdecode(np.frombuffer(original_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            annotated_frame = cv2.imdecode(np.frombuffer(annotated_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)

            if original_frame is None or annotated_frame is None:
                continue

            # 首帧时初始化视频写入器
            if original_writer is None or annotated_writer is None:
                frame_height, frame_width = original_frame.shape[:2]
                segment_index += 1
                segment_start_time = timestamp
                time_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")

                original_path = os.path.join(output_dir, f"{time_str}_original.mp4")
                annotated_path = os.path.join(output_dir, f"{time_str}_annotated.mp4")

                fourcc = cv2.VideoWriter.fourcc(*'mp4v')
                original_writer = cv2.VideoWriter(original_path, fourcc, video_fps, (frame_width, frame_height))
                annotated_writer = cv2.VideoWriter(annotated_path, fourcc, video_fps, (frame_width, frame_height))

                add_log(logging_queue, "INFO", f"[Output] 开始录制视频片段 {segment_index}: {time_str}")

            # 写入帧
            original_writer.write(original_frame)
            annotated_writer.write(annotated_frame)

            # 检查是否到达切片时间
            elapsed = timestamp - segment_start_time
            if elapsed >= segment_duration:
                add_log(logging_queue, "INFO", f"[Output] 视频片段 {segment_index} 录制完成（{segment_duration}秒）")
                original_writer.release()
                annotated_writer.release()
                original_writer = None
                annotated_writer = None

    except Exception as e:
        add_log(logging_queue, "ERROR", f"[Output] 进程异常: {e}")

    finally:
        # 释放当前视频写入器（不足 1 分钟的片段也会保存）
        if original_writer is not None:
            try:
                original_writer.release()
            except Exception:
                pass
        if annotated_writer is not None:
            try:
                annotated_writer.release()
            except Exception:
                pass
        add_log(logging_queue, "INFO", "[Output] 进程已退出，资源已释放")