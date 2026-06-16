# output.py
# 负责接收 JPEG 帧，将其写入视频文件，采用循环录像
# 通过缓存帧并动态计算实际 fps，确保视频时长与录制时长一致
# 使用 ffmpeg 管道直接写入 JPEG，避免 Python 侧解码开销

import multiprocessing

import cv2
import numpy as np

import subprocess
import time
import os
from datetime import datetime
import json

from tools.logger import add_log


def flush_buffer(logging_queue : multiprocessing.Queue, frame_buffer : list, segment_index : int, output_dir : str):
    """
    将缓冲区中的 JPEG 帧通过 ffmpeg 管道写入视频文件。
    出于实际运算视频得到帧数不固定，根据实际帧数和录制时长动态计算 fps。
    """
    if len(frame_buffer) == 0:
        return

    # 用第一帧和最后一帧的时间戳计算实际录制时长
    first_timestamp = frame_buffer[0][0]
    last_timestamp = frame_buffer[-1][0]
    actual_duration = last_timestamp - first_timestamp
    if actual_duration < 0.1:
        actual_duration = 0.1

    # FPS = 帧数 / 实际时长
    frame_count = len(frame_buffer)
    actual_fps = frame_count / actual_duration

    add_log(logging_queue, "INFO",
            f"[Output] 视频片段 {segment_index} 统计: {frame_count} 帧, "
            f"时长 {actual_duration:.1f}秒, 实际 fps: {actual_fps:.1f}")

    # 获取分辨率
    first_original_jpeg = frame_buffer[0][1]
    first_original_frame = cv2.imdecode(np.frombuffer(first_original_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)

    if first_original_frame is None:
        add_log(logging_queue, "ERROR", "[Output] 首帧解码失败，录制片段失败")
        frame_buffer.clear()
        return

    frame_height, frame_width = first_original_frame.shape[:2]
    time_str = datetime.fromtimestamp(first_timestamp).strftime("%Y%m%d_%H%M%S")

    original_path = os.path.join(output_dir, f"{time_str}_original.mp4")
    annotated_path = os.path.join(output_dir, f"{time_str}_annotated.mp4")

    # 启动 FFMPEG 进程
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",                                    # 覆盖输出文件
        "-f", "image2pipe",                      # 输入格式：管道图像流
        "-vcodec", "mjpeg",                      # 输入编码：JPEG
        "-r", str(round(actual_fps, 2)),         # 输入帧率
        "-i", "-",                               # 从 stdin 读取
        "-c:v", "libx264",                       # 输出编码：H.264
        "-pix_fmt", "yuv420p",                   # 像素格式（兼容性好）
        "-crf", "23",                            # 质量（18-28，越小越清晰）
        "-preset", "fast",                       # 编码速度
        "-movflags", "+faststart",               # moov atom 前置，支持流式播放
        "-loglevel", "error",                    # 只输出错误
    ]

    original_proc = subprocess.Popen(
        ffmpeg_cmd + [original_path],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    annotated_proc = subprocess.Popen(
        ffmpeg_cmd + [annotated_path],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    original_stdin = original_proc.stdin
    annotated_stdin = annotated_proc.stdin

    if original_stdin is None or annotated_stdin is None:
        add_log(logging_queue, "ERROR", "[Output] FFMPEG 管道创建失败")
        frame_buffer.clear()
        return

    # JPEG bytes 写入管道
    write_error_count = 0
    for timestamp, original_jpeg, annotated_jpeg in frame_buffer:
        try:
            original_stdin.write(original_jpeg)
        except Exception:
            write_error_count += 1

        try:
            annotated_stdin.write(annotated_jpeg)
        except Exception:
            pass

    # 关闭管道并等待 ffmpeg 完成编码
    original_stdin.close()
    annotated_stdin.close()

    original_ret = original_proc.wait()
    annotated_ret = annotated_proc.wait()

    if original_ret != 0 and original_proc.stderr is not None:
        stderr = original_proc.stderr.read().decode("utf-8", errors="replace")
        add_log(logging_queue, "ERROR", f"[Output] ffmpeg(original) 失败: {stderr[:200]}")

    if annotated_ret != 0 and annotated_proc.stderr is not None:
        stderr = annotated_proc.stderr.read().decode("utf-8", errors="replace")
        add_log(logging_queue, "ERROR", f"[Output] ffmpeg(annotated) 失败: {stderr[:200]}")

    add_log(logging_queue, "INFO",
            f"[Output] 视频片段 {segment_index} 已保存: {time_str}, "
            f"分辨率 {frame_width}x{frame_height}, fps {actual_fps:.1f}")

    if write_error_count > 0:
        add_log(logging_queue, "WARNING", f"[Output] 本片段有 {write_error_count} 帧写入失败")

    frame_buffer.clear()


def output_process(logging_queue : multiprocessing.Queue, output_queue : multiprocessing.Queue):
    # 读取录像配置
    config_path = "./config/output.config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    output_dir = config.get("output_dir", "./output/videos")
    cycle_video_duration = config.get("cycle_video_duration", 60)  # 每个视频片段时长（秒）

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 帧缓冲区：缓存一个片段的所有 JPEG 数据，到切片时再写入
    frame_buffer = []

    # 当前片段信息
    segment_index = 0
    segment_start_time = 0

    try:
        add_log(logging_queue, "INFO", "[Output] 录像服务已启动，等待首帧...")

        while True:
            # 从队列获取帧数据（阻塞等待）
            try:
                frame_data = output_queue.get(timeout=1)
            except Exception:
                # 队列为空，检查是否需要因超时而切片
                if len(frame_buffer) > 0:
                    elapsed = time.time() - segment_start_time
                    if elapsed >= cycle_video_duration:
                        add_log(logging_queue, "INFO", f"[Output] 视频片段 {segment_index} 达到 {cycle_video_duration}秒，开始写入")
                        flush_buffer(logging_queue, frame_buffer, segment_index, output_dir)
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

            # 新片段开始
            if len(frame_buffer) == 0:
                segment_index += 1
                segment_start_time = timestamp
                add_log(logging_queue, "INFO", f"[Output] 开始录制视频片段 {segment_index}")

            # 缓存帧（不解码，保持 JPEG 格式以节省内存）
            frame_buffer.append((timestamp, original_jpeg, annotated_jpeg))

            # 检查是否到达切片时间
            elapsed = timestamp - segment_start_time
            if elapsed >= cycle_video_duration:
                add_log(logging_queue, "INFO", f"[Output] 视频片段 {segment_index} 达到 {cycle_video_duration}秒，开始写入")
                flush_buffer(logging_queue, frame_buffer, segment_index, output_dir)

    except Exception as e:
        add_log(logging_queue, "ERROR", f"[Output] 进程异常: {e}")

    finally:
        # 写入缓冲区中剩余的帧（不足一个完整片段的也会保存）
        if len(frame_buffer) > 0:
            add_log(logging_queue, "INFO", f"[Output] 写入剩余 {len(frame_buffer)} 帧")
            flush_buffer(logging_queue, frame_buffer, segment_index, output_dir)
        add_log(logging_queue, "INFO", "[Output] 进程已退出，资源已释放")