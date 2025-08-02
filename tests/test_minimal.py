"""
最小化测试应用程序
用于隔离线程问题
"""

import os
import sys
import time

import pygame

# 添加父目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.config_manager import ConfigManager
from modules.hardware_controller import ControllerMonitor, HardwareController, NetworkWorker
from modules.video_processor import VideoThread
from modules.ui_controller import UIController, JoystickHandler


def main():
    """主函数"""
    print("初始化最小化测试应用程序...")

    # 初始化pygame
    pygame.init()

    try:
        # 加载配置
        config_manager = ConfigManager()
        print("配置加载完成")

        # 初始化UI控制器
        ui_controller = UIController(config_manager.get_interface_settings())
        print("UI控制器初始化完成")

        # 初始化手柄处理器
        joystick_handler = JoystickHandler(config_manager.get_joystick_settings())
        print("手柄处理器初始化完成")

        # 初始化控制器监控
        controller_monitor = ControllerMonitor(config_manager.get_controller_init())
        print("控制器监控初始化完成")

        # 初始化硬件控制器
        server_address = config_manager.get_server_address()
        hw_controller = HardwareController(server_address, config_manager.motor_params)
        print("硬件控制器初始化完成")

        # 设置网络套接字
        client_socket = hw_controller.setup_socket(config_manager.get_local_port())
        print("网络套接字设置完成")

        # 初始化电机参数
        print("初始化电机参数...")
        for _ in range(3):  # 减少循环次数，只是为了测试
            hw_controller.hwinit()
            time.sleep(0.05)
        print("电机参数初始化完成")

        # 初始化网络工作线程
        print("初始化网络工作线程...")
        network_worker = NetworkWorker(hw_controller, controller_monitor)
        network_worker.start()
        print("网络工作线程启动完成")

        # 等待一小段时间
        time.sleep(1)

        # 初始化视频处理线程
        print("初始化视频处理线程...")
        rtsp_url = config_manager.get_rtsp_url()
        base_width, base_height = config_manager.get_camera_dimensions()
        buffer_size = config_manager.config["camera"].getint("buffer")
        video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
        video_thread.start()
        print("视频处理线程启动完成")

        # 等待一小段时间
        time.sleep(1)

        # 简单的主循环
        print("开始简单的主循环...")
        for _ in range(5):  # 只运行5次循环
            # 获取视频帧
            frame_rgb = video_thread.get_latest_frame(ui_controller.show_undistorted)

            # 触发网络通信
            network_worker.trigger_communication()

            # 显示视频帧
            if frame_rgb is not None:
                ui_controller.display_frame(frame_rgb)
                ui_controller.update_display()

            # 等待一小段时间
            time.sleep(0.1)

        print("主循环完成")

        # 清理资源
        print("开始清理资源...")

        # 停止视频线程
        print("停止视频线程...")
        video_thread.stop()
        time.sleep(0.5)
        if video_thread.is_alive():
            video_thread.stop_force()
            print("强制停止视频线程")

        # 停止网络工作线程
        print("停止网络工作线程...")
        network_worker.stop()

        # 清理UI资源
        print("清理UI资源...")
        ui_controller.cleanup()

        print("所有资源清理完成")

    except Exception as e:
        print(f"程序异常: {str(e)}")
    finally:
        pygame.quit()
        print("程序已退出")


if __name__ == "__main__":
    main()
