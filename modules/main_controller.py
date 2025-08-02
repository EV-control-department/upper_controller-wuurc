"""
主控制器模块
用于封装主循环功能和协调各个组件
"""

import time

import pygame

from modules.config_manager import ConfigManager
from modules.depth_temperature_controller import DepthTemperatureController
from modules.hardware_controller import (
    HardwareController,
    ControllerMonitor,
    NetworkWorker
)
from modules.joystick_controller import JoystickController
from modules.ui_controller import UIController, JoystickHandler
from modules.video_processor import VideoThread


class MainController:
    """主控制器类，封装主循环功能和协调各个组件"""

    def __init__(self):
        """初始化主控制器"""
        # 加载配置
        self.config_manager = ConfigManager()

        # 初始化UI控制器
        self.ui_controller = UIController(self.config_manager.get_interface_settings())

        # 初始化手柄处理器
        self.joystick_handler = JoystickHandler(self.config_manager.get_joystick_settings())

        # 加载默认图像
        self.default_image = self.ui_controller.load_default_image()

        # 初始化控制器监控
        self.controller_monitor = ControllerMonitor(self.config_manager.get_controller_init())

        # 初始化硬件控制器
        server_address = self.config_manager.get_server_address()
        self.hw_controller = HardwareController(server_address, self.config_manager.motor_params)

        # 设置网络套接字
        self.client_socket = self.hw_controller.setup_socket(self.config_manager.get_local_port())

        # 初始化电机参数（非阻塞方式）
        self._init_motors()

        # 初始化网络工作线程
        self.network_worker = NetworkWorker(self.hw_controller, self.controller_monitor)
        self.network_worker.start()

        # 初始化视频处理线程
        rtsp_url = self.config_manager.get_rtsp_url()
        base_width, base_height = self.config_manager.get_camera_dimensions()
        buffer_size = self.config_manager.config["camera"].getint("buffer")
        self.video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
        self.video_thread.start()

        # 初始化手柄控制器
        self.joystick_controller = JoystickController(
            self.joystick_handler,
            self.config_manager,
            self.controller_monitor
        )

        # 初始化深度温度线程（不立即启动）
        self.depth_temperature_thread = None

        # 主循环变量
        self.running = True
        self.clock = pygame.time.Clock()

        # 记录状态
        self.tem_record = False

    def _init_motors(self):
        """初始化电机参数"""
        for _ in range(10):
            self.hw_controller.hwinit()
            time.sleep(0.05)

    def handle_depth_temperature_thread(self, start_recording):
        """处理深度温度线程的启动和停止"""
        if start_recording:
            # 检查线程是否已经在运行
            if self.depth_temperature_thread is not None and self.depth_temperature_thread.is_alive():
                if hasattr(self.depth_temperature_thread, 'running') and self.depth_temperature_thread.running:
                    print("线程已在运行中，无需重复启动")
                    return
                else:
                    # 线程存在但已停止运行，只需设置运行状态
                    self.depth_temperature_thread.start_log()
                    print("深度温度线程已重新启动")
                    return

            # 创建新线程实例并启动
            self.depth_temperature_thread = DepthTemperatureController(self.controller_monitor)
            self.depth_temperature_thread.start_log()  # 设置运行状态
            self.depth_temperature_thread.start()  # 启动线程
            print("深度温度线程已启动")
        else:
            # 检查线程是否存在且正在运行
            if self.depth_temperature_thread is not None and self.depth_temperature_thread.is_alive():
                if hasattr(self.depth_temperature_thread, 'running') and self.depth_temperature_thread.running:
                    self.depth_temperature_thread.stop_log()  # 停止线程并保存数据
                    print("深度温度线程已停止")
                else:
                    print("线程已经停止，无需再次停止")
            else:
                print("线程未在运行中，无需停止")

    def run(self):
        """运行主循环"""
        while self.running:
            # 处理事件
            frame_rgb = self.video_thread.get_latest_frame(self.ui_controller.show_undistorted)
            self.running = self.ui_controller.handle_events(self.joystick_handler.joystick, self.video_thread)

            # 更新手柄状态
            self.joystick_controller.update()

            # 处理手柄按钮6（启动/停止深度温度记录）
            if self.joystick_handler.get_button(6):
                self.tem_record = not self.tem_record
                self.handle_depth_temperature_thread(self.tem_record)
                self.joystick_controller.set_depth_temp_block()

            # 处理手柄输入
            skip_input = self.joystick_controller.process_input()
            if skip_input:
                continue

            # 触发网络通信
            self.network_worker.trigger_communication()

            # 显示视频帧
            self.ui_controller.display_frame(frame_rgb)

            # 显示控制器数据和模式信息
            modes = self.joystick_controller.get_current_modes()
            self.ui_controller.display_controller_data(
                self.controller_monitor.controller,
                self.controller_monitor.depth,
                self.controller_monitor.temperature,
                modes
            )

            # 更新显示
            self.ui_controller.update_display()

            # 控制主循环频率
            self.clock.tick(self.config_manager.config["joystick"].getint("tick"))

    def cleanup(self):
        """清理资源"""
        # 停止视频线程
        try:
            if hasattr(self.video_thread, 'stop'):
                self.video_thread.stop()
                print("视频线程停止中...")

                # 等待一小段时间让线程有机会退出
                time.sleep(0.5)

                # 如果线程仍在运行，强制停止
                if hasattr(self.video_thread, 'is_alive') and self.video_thread.is_alive():
                    if hasattr(self.video_thread, 'stop_force'):
                        self.video_thread.stop_force()
                        print("强制停止视频线程")
        except Exception as e:
            print(f"停止视频线程时出错: {str(e)}")

        # 清理其他资源
        self._cleanup_other_resources()

    def _cleanup_other_resources(self):
        """清理其他资源"""
        # 停止网络工作线程
        try:
            if hasattr(self.network_worker, 'stop'):
                self.network_worker.stop()
        except Exception as e:
            print(f"停止网络线程时出错: {str(e)}")

        # 停止深度温度线程（如果存在）
        try:
            if self.depth_temperature_thread is not None:
                if hasattr(self.depth_temperature_thread, 'is_alive') and self.depth_temperature_thread.is_alive():
                    if hasattr(self.depth_temperature_thread, 'stop_log'):
                        self.depth_temperature_thread.stop_log()
                        print("深度温度线程已停止")
        except Exception as e:
            print(f"停止深度温度线程时出错: {str(e)}")

        # 清理UI资源
        try:
            if hasattr(self.ui_controller, 'cleanup'):
                self.ui_controller.cleanup()
        except Exception as e:
            print(f"清理UI资源时出错: {str(e)}")

        print("程序已退出")
