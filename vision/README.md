# 开发者笔记
> Written by half-tree

## 部署过程 6.16

### NVIDIA 板卡上连接摄像头

首先，必须开启摄像头，出于某些原因，eno1 以太网口无法自动获取自己的 IP 地址，必须手动设置一个 IP 地址
```sh
sudo ip addr add 192.168.1.100/24 dev eno1
```
设置成功后，`eno1` 将作为 NVIDIA 的内网网关，注意，设置地址需要在内网网段且不与摄像头相同，此处设置为 192.168.1.100

然后，通过 `ipconfig` 检验 `eno1` 设备是否 UP
```sh
eno1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.100  netmask 255.255.255.0  broadcast 0.0.0.0
```
确认 `eno1` 有内网地址后，即可用 `nmap` 扫描摄像头的 IP 地址
```sh
nvidia@nvidia-desktop:~/rov-image-service/vision$ nmap -p 554 192.168.1.0/24 --open
Starting Nmap 7.80 ( https://nmap.org ) at 2026-06-16 13:06 CST
Nmap scan report for 192.168.1.168
Host is up (0.0017s latency).

PORT    STATE SERVICE
554/tcp open  rtsp

Nmap done: 256 IP addresses (2 hosts up) scanned in 6.90 seconds
```
此处可以成功扫描到与 NVIDIA 并网的摄像头 IP 地址为 `192.168.1.168`，且 554 端口开放，说明摄像头正常连接。

### 配置 Python 环境
在本项目中，不考虑使用 venv 等虚拟环境工具，直接在系统 Python 环境中安装依赖包。这是因为 NVIDIA 官方的 OpenCV 包只能安装在系统路径中，无法安装在虚拟环境中。

```sh
sudo apt install python3-opencv
```
安装 NVIDIA 官方的 OpenCV 包，这将包含 cv2, pytorch, 符合版本的 numpy 等等

```sh
pip install -r requirements.txt
```
安装除了上述系统包外，项目中还需要的 Python 包，如 ultralytics 等等，详情见 `requirements.txt` 文件

安装完成后，直接从系统 Python 环境中执行任务。

### 启动项目
```sh
cd /path/to/rov-image-service/vision
python src/main.py
```


## 目前已知的问题
1. 保存 4K 视频所需的时间非常长，这将导致 Output 模块具有录像延迟
```sh
[2026-06-16 13:52:12][USV_Client][INFO] [Output] 开始录制视频片段 1
[2026-06-16 13:53:12][USV_Client][INFO] [Output] 视频片段 1 达到 60秒，开始写入
[2026-06-16 13:53:12][USV_Client][INFO] [Output] 视频片段 1 统计: 379 帧, 时长 60.2秒, 实际 fps: 6.3
[2026-06-16 13:54:59][USV_Client][INFO] [Output] 视频片段 1 已保存: 20260616_135212, 分辨率 3840x2160, fps 6.3
[2026-06-16 13:54:59][USV_Client][INFO] [Output] 开始录制视频片段 2
[2026-06-16 13:55:54][USV_Client][INFO] [Output] 视频片段 2 达到 60秒，开始写入
[2026-06-16 13:55:54][USV_Client][INFO] [Output] 视频片段 2 统计: 375 帧, 时长 60.0秒, 实际 fps: 6.2
[2026-06-16 13:57:29][USV_Client][INFO] [Output] 视频片段 2 已保存: 20260616_135454, 分辨率 3840x2160, fps 6.2
[2026-06-16 13:57:29][USV_Client][INFO] [Output] 开始录制视频片段 3
[2026-06-16 13:58:24][USV_Client][INFO] [Output] 视频片段 3 达到 60秒，开始写入
[2026-06-16 13:58:24][USV_Client][INFO] [Output] 视频片段 3 统计: 378 帧, 时长 60.1秒, 实际 fps: 6.3
[2026-06-16 13:59:59][USV_Client][INFO] [Output] 视频片段 3 已保存: 20260616_135724, 分辨率 3840x2160, fps 6.3
[2026-06-16 13:59:59][USV_Client][INFO] [Output] 开始录制视频片段 4
```

2. SharedMemory 出于未知原因，没有被正常释放
```sh
/usr/lib/python3.10/multiprocessing/resource_tracker.py:224: UserWarning: resource_tracker: There appear to be 1 leaked shared_memory objects to clean up at shutdown
  warnings.warn('resource_tracker: There appear to be %d '
/usr/lib/python3.10/multiprocessing/resource_tracker.py:237: UserWarning: resource_tracker: '/psm_8cc2c2a8': [Errno 2] No such file or directory: '/psm_8cc2c2a8'
  warnings.warn('resource_tracker: %r: %s' % (name, e))
^C再见！朋友！
```

## 还没测试的部分

ZeroMQ 的广播还没使用