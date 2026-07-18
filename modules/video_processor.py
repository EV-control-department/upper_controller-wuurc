"""
视频处理模块
用于处理视频流和图像处理
"""

import os
import shutil
import subprocess
import sys
import threading

import cv2
import numpy as np

# Windows 专用常量，Linux 上不需要
if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
    subprocess.CREATE_NO_WINDOW = 0


class VideoThread(threading.Thread):
    """视频处理线程，处理视频流和图像处理"""

    def __init__(self, rtsp_url, base_width, base_height, buffer_size=5, output_folder="captures", backend="ffmpeg"):
        """
        初始化视频处理线程
        
        参数:
            rtsp_url: RTSP视频流URL
            base_width: 视频宽度
            base_height: 视频高度
            buffer_size: 缓冲区大小
            output_folder: 截图保存文件夹
            backend: 拉流后端 (ffmpeg / gstreamer)
        """
        super().__init__()
        self.rtsp_url = rtsp_url
        self.base_width = base_width
        self.base_height = base_height
        self.buffer_size = buffer_size
        self.output_folder = output_folder
        self.backend = backend
        self.running = True
        self.frame_queue = []
        self.max_queue_size = 10  # 队列大小
        self.video_connected = None
        self.lock = threading.Lock()  # 用于同步对队列的访问
        self.capture_count = 0  # 用于生成照片编号
        self.process = None
        self.proc_log = []  # 存储后端进程日志
        self.stderr_thread = None  # 后端错误输出处理线程

        # 确保输出文件夹存在
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 初始化拉流进程
        if self.backend == "gstreamer":
            self._init_gst_process()
        else:
            self._init_ffmpeg_process()

    # ─── FFmpeg 后端 ─────────────────────────────────

    def _find_executable(self, name):
        """查找可执行文件路径（优先打包目录）"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            candidate = os.path.join(base_dir, '_internal', name + '.exe')
            if os.path.exists(candidate):
                return candidate
        path = shutil.which(name)
        if path:
            return path
        return name

    def _init_ffmpeg_process(self):
        """初始化FFmpeg进程"""
        ffmpeg_exe = self._find_executable('ffmpeg')

        command = [
            ffmpeg_exe,
            '-rtsp_transport', 'tcp',  # 强制使用TCP传输
            '-fflags', 'nobuffer',  # 禁用缓冲区
            '-flags', 'low_delay',  # 低延迟标志
            '-i', self.rtsp_url,  # 输入URL
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-an', '-sn',  # 禁用音频和字幕
            '-probesize', '32',  # 减少探测大小
            '-analyzeduration', '0',  # 立即开始解码
            '-'
        ]

        self.process = subprocess.Popen(command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        bufsize=self.base_width * self.base_height * 3 * self.buffer_size,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

        self._start_stderr_thread()

    # ─── GStreamer 后端 ──────────────────────────────

    def _init_gst_process(self):
        """初始化GStreamer进程"""
        gst_exe = self._find_executable('gst-launch-1.0')

        command = [
            gst_exe,
            '-e',  # 优雅退出
            'rtspsrc', f'location={self.rtsp_url}',
            'latency=0',
            '!', 'rtph264depay',
            '!', 'avdec_h264',
            '!', 'videoconvert',
            '!', 'video/x-raw,format=BGR',
            '!', 'fdsink', 'fd=1',  # 输出到 stdout
        ]

        self.process = subprocess.Popen(command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        bufsize=self.base_width * self.base_height * 3 * self.buffer_size)

        self._start_stderr_thread()

    # ─── 通用 ────────────────────────────────────────

    def _start_stderr_thread(self):
        """启动stderr读取线程"""
        self.stderr_thread = threading.Thread(target=self._read_stderr)
        self.stderr_thread.daemon = True
        self.stderr_thread.start()

    def _read_stderr(self):
        """读取后端进程的stderr输出并打印"""
        tag = self.backend.upper()
        while self.running and self.process:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                line_text = line.decode('utf-8', errors='replace').strip()
                if line_text:
                    print(f"{tag}: {line_text}")
                    with self.lock:
                        self.proc_log.append(line_text)
                        if len(self.proc_log) > 100:
                            self.proc_log = self.proc_log[-100:]
            except Exception as e:
                print(f"读取{tag}日志时出错: {e}")
                break

    def run(self):
        """线程主循环"""
        tag = self.backend.upper()
        if not hasattr(self, 'process') or self.process is None:
            print(f"{tag}进程未初始化")
            return

        frame_size = self.base_width * self.base_height * 3
        while self.running:
            try:
                raw_frame = self.process.stdout.read(frame_size)
                if len(raw_frame) == frame_size:
                    frame = np.frombuffer(raw_frame, np.uint8).reshape((self.base_height, self.base_width, 3))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    with self.lock:
                        while len(self.frame_queue) >= self.max_queue_size:
                            self.frame_queue.pop(0)
                        self.frame_queue.append(frame_rgb)

                    self.video_connected = True

            except Exception as e:
                print(f"视频读取错误 ({tag}): {e}")
                self.video_connected = False

    def stop(self):
        """设置线程停止标志"""
        self.running = False  # 设置线程停止标志

        # 等待stderr线程结束
        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=1)

    def stop_force(self):
        """强制停止线程"""
        self.running = False  # 强制停止
        self.join(timeout=3)  # 加入超时限制，防止无限等待

        # 等待stderr线程结束
        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=1)

        # 终止FFmpeg进程
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=1)  # 等待进程终止

    def get_latest_frame(self, show_undistorted=False):
        """
        获取最新的帧
        
        参数:
            show_undistorted: 是否显示去畸变后的图像
            
        返回:
            最新的视频帧，如果队列为空返回None
        """
        try:
            if self.frame_queue:
                with self.lock:  # 使用锁来确保线程安全
                    if len(self.frame_queue) > 0:  # 再次检查队列是否为空
                        latest_frame = self.frame_queue[-1]
                    else:
                        return None

                if show_undistorted:
                    undistorted_frame = undistort_frame(latest_frame, self.base_width, self.base_height)
                    return undistorted_frame
                else:
                    return latest_frame
            return None
        except Exception as e:
            print(f"获取视频帧时出错: {str(e)}")
            return None

    def save_frame(self, frame):
        """
        保存当前帧
        
        参数:
            frame: 要保存的帧
        """
        self.capture_count += 1
        # 使用项目内的assets目录保存图像
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        filename = os.path.join(assets_dir, f"capture_{self.capture_count:04d}.jpg")
        cv2.imwrite(filename, frame)  # 保存图像为 JPEG 文件
        print(f"保存照片: {filename}")

    def get_ffmpeg_logs(self, max_lines=10):
        """
        获取FFmpeg日志
        
        参数:
            max_lines: 返回的最大日志行数
            
        返回:
            最近的FFmpeg日志行列表
        """
        with self.lock:
            # 返回最近的日志行
            return self.ffmpeg_log[-max_lines:] if self.ffmpeg_log else []


# 相机标定参数
camera_matrix = np.array([[605.571998544127, 0, 641.654856317165],  # 内参矩阵，fx, 0, cx
                          [0, 603.160880757148, 343.186661021091],  # 内参矩阵，0, fy, cy
                          [0, 0, 1]], dtype=np.float32)  # 内参矩阵，0, 0, 1

distortion_coefficients = np.array([-0.326257291325774, 0.0854715353372504, 0, 0])  # 畸变系数


def undistort_frame(frame, video_base_width, video_base_height):
    """
    对图像进行去畸变处理
    
    参数:
        frame: 输入图像
        video_base_width: 视频宽度
        video_base_height: 视频高度
        
    返回:
        去畸变后的图像
    """
    # 检查 frame 是否为有效图像
    if frame is None:
        raise ValueError("传递给 undistort_frame 的帧是 None，无法进行去畸变处理")

    # 计算去畸变的映射矩阵
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, distortion_coefficients,
                                                           (video_base_width, video_base_height), 1,
                                                           (video_base_width, video_base_height))

    # 去畸变
    undistorted_frame = cv2.undistort(frame, camera_matrix, distortion_coefficients, None, new_camera_matrix)

    # 裁剪去畸变后图像的有效区域
    x, y, w, h = roi
    undistorted_frame = undistorted_frame[y:y + h, x:x + w]

    return undistorted_frame
