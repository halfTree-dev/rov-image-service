# test_rtsp.py
import cv2
import time

print(f"OpenCV 版本: {cv2.__version__}")

# 测试 1：用 FFMPEG 后端
rtsp_url = "rtsp://admin:123456@192.168.1.168:554/stream1?transport=tcp&tcp_nodelay=1&pixel_format=yuv420p"
cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"FFMPEG 成功! 分辨率: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("FFMPEG 打开成功但读取失败")
    cap.release()
else:
    print("FFMPEG 打开失败")

# 测试 2：用 GStreamer 后端
gst_pipeline = (
    f"rtspsrc location={rtsp_url} latency=0 protocols=tcp "
    "! rtph264depay "
    "! h264parse "
    "! nvv4l2decoder "
    "! nvvidconv "
    "! video/x-raw, format=BGRx "
    "! videoconvert "
    "! video/x-raw, format=BGR "
    "! appsink drop=true sync=false"
)
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"GStreamer 成功! 分辨率: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("GStreamer 打开成功但读取失败")
    cap.release()
else:
    print("GStreamer 打开失败")

# 测试 3：用 GStreamer 软件解码（如果硬件解码器有问题）
gst_pipeline_soft = (
    f"rtspsrc location={rtsp_url} latency=0 protocols=tcp "
    "! rtph264depay "
    "! h264parse "
    "! avdec_h264 "
    "! videoconvert "
    "! video/x-raw, format=BGR "
    "! appsink drop=true sync=false"
)
cap = cv2.VideoCapture(gst_pipeline_soft, cv2.CAP_GSTREAMER)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"GStreamer(软解) 成功! 分辨率: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("GStreamer(软解) 打开成功但读取失败")
    cap.release()
else:
    print("GStreamer(软解) 打开失败")

print("\n测试完成")
