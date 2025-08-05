"""
ROV控制上位机软件
主程序入口
"""

import time

import pygame

from modules.config_manager import ConfigManager
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
        self.ui_controller = UIController(self.config_manager.get_interface_settings(), self.config_manager)

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

        # 初始化电机参数
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

    def deploy_thrust_curves(self):
        """部署推力曲线到ROV"""
        print("正在部署推力曲线...")
        self.hw_controller.hwinit()
        print("推力曲线部署完成")

    def run(self):
        """运行主循环"""
        while self.running:
            # 处理事件
            frame_rgb = self.video_thread.get_latest_frame(self.ui_controller.show_undistorted)
            self.running = self.ui_controller.handle_events(self.joystick_handler.joystick, self.video_thread, self)

            # 更新手柄状态
            self.joystick_controller.update()

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


def main():
    """主函数"""
    # 初始化主控制器
    controller = None

    try:
        controller = MainController()

        # 运行主循环
        controller.run()
    except KeyboardInterrupt:
        print("用户中断程序")
    except Exception as e:
        print(f"程序异常: {str(e)}")
    finally:
        # 清理资源
        if controller is not None:
            controller.cleanup()


if __name__ == "__main__":
    main()
