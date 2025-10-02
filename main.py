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
        self.all_motors_initialized = self._init_motors()

        # 记录初始化状态
        self.motors_initialization_status = {
            "all_initialized": self.all_motors_initialized,
            "failed_motors": self.hw_controller.get_failed_motors() if not self.all_motors_initialized else []
        }

        # 如果不是所有电机都初始化成功，记录日志
        if not self.all_motors_initialized:
            print(f"警告: 部分电机初始化失败: {', '.join(self.motors_initialization_status['failed_motors'])}")
            print("系统将继续运行，但可能会影响某些功能")

        # 初始化网络工作线程
        self.network_worker = NetworkWorker(self.hw_controller, self.controller_monitor)
        self.network_worker.start()

        # 初始化视频处理线程
        rtsp_url = self.config_manager.get_rtsp_url()
        base_width, base_height = self.config_manager.get_camera_dimensions()
        buffer_size = self.config_manager.config["camera"].getint("buffer")
        self.video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
        self.video_thread.start()

        # 视频线程监控变量
        self.last_video_check_time = time.time()
        self.video_check_interval = 10  # 每10秒检查一次视频线程状态

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

        # 等待所有组件就绪
        self._wait_for_components()

    def _wait_for_components(self):
        """等待所有组件就绪，持续轮询直到所有组件初始化成功或用户取消"""
        print("\n开始初始化组件...")

        # 初始化参数
        max_retry_count = 100  # 最大重试次数
        retry_count = 0
        retry_delay = 0.5  # 重试间隔（秒）
        force_entry = False  # 是否强制进入
        all_ready = False  # 是否所有组件都已初始化

        # 组件初始化状态
        video_ready = False
        joystick_ready = False
        sensor_ready = False
        current_ready = False
        motors_ready = False

        # 持续轮询直到所有非电机组件初始化成功或用户取消
        while (not (video_ready and joystick_ready and sensor_ready and current_ready) and
               not force_entry and retry_count < max_retry_count):

            # 检查是否有按钮被按下
            if self.joystick_handler.is_any_button_pressed():
                force_entry = True
                print("检测到手柄按键，强制进入系统")
                break

            # 显示初始化界面
            self.ui_controller.display_frame(self.default_image)
            self.ui_controller.draw_text("系统初始化中...",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 - 200,
                                         color=(255, 255, 255),
                                         bold=True,
                                         outline=True)

            self.ui_controller.draw_text("按下任意手柄按键可强制进入",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 - 120,
                                         color=(255, 200, 0),
                                         bold=True,
                                         outline=True)

            # 检查视频流
            if not video_ready:
                print("正在连接视频流...")
                status_text = "视频流: 正在连接..."
                status_color = (255, 255, 0)  # 黄色

                # 尝试连接视频流
                if hasattr(self.video_thread, 'video_connected') and self.video_thread.video_connected:
                    with self.video_thread.lock:
                        if len(self.video_thread.frame_queue) > 0:
                            video_ready = True
                            status_text = "视频流: √ 已连接"
                            status_color = (0, 255, 0)  # 绿色

                # 如果超过检查间隔仍未就绪，则尝试重启视频线程（约每10秒一次）
                current_time = time.time()
                if not video_ready and (current_time - self.last_video_check_time >= self.video_check_interval):
                    self.last_video_check_time = current_time
                    print("[DEBUG] 初始化阶段视频未就绪，尝试重启视频线程...")
                    try:
                        # 优先尝试优雅停止
                        if hasattr(self.video_thread, 'stop'):
                            self.video_thread.stop()
                        # 等待片刻让线程退出
                        time.sleep(0.2)
                        # 若仍存活则强制停止
                        if hasattr(self.video_thread, 'is_alive') and self.video_thread.is_alive():
                            if hasattr(self.video_thread, 'stop_force'):
                                self.video_thread.stop_force()
                    except Exception as e:
                        print(f"停止旧视频线程时出错: {str(e)}")

                    # 重新创建并启动视频线程
                    try:
                        rtsp_url = self.config_manager.get_rtsp_url()
                        base_width, base_height = self.config_manager.get_camera_dimensions()
                        buffer_size = self.config_manager.config["camera"].getint("buffer")
                        self.video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
                        self.video_thread.start()
                        print("[DEBUG] 已重启视频线程（初始化阶段）")
                    except Exception as e:
                        print(f"重启视频线程时出错: {str(e)}")
            else:
                status_text = "视频流: √ 已连接"
                status_color = (0, 255, 0)  # 绿色

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 - 60,
                                         color=status_color,
                                         outline=False)

            # 检查手柄
            if not joystick_ready:
                print("正在检测手柄...")
                status_text = "手柄: 正在检测..."
                status_color = (255, 255, 0)  # 黄色

                # 尝试初始化手柄
                if self.joystick_handler.joystick is not None:
                    joystick_ready = True
                    status_text = "手柄: √ 已连接"
                    status_color = (0, 255, 0)  # 绿色
                else:
                    # 尝试重新初始化手柄
                    pygame.joystick.quit()
                    pygame.joystick.init()
                    if pygame.joystick.get_count() > 0:
                        self.joystick_handler._init_joystick()
                        if self.joystick_handler.joystick is not None:
                            joystick_ready = True
                            status_text = "手柄: √ 已连接"
                            status_color = (0, 255, 0)  # 绿色
                        else:
                            status_text = "手柄: × 未检测到"
                            status_color = (255, 0, 0)  # 红色
                    else:
                        status_text = "手柄: × 未检测到"
                        status_color = (255, 0, 0)  # 红色
            else:
                status_text = "手柄: √ 已连接"
                status_color = (0, 255, 0)  # 绿色

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2,
                                         color=status_color,
                                         outline=False)

            # 检查温湿度传感器
            if not sensor_ready:
                print("正在检测温湿度传感器...")
                status_text = "温湿度传感器: 正在检测..."
                status_color = (255, 255, 0)  # 黄色

                # 记录初始值
                initial_depth = self.controller_monitor.depth
                initial_temperature = self.controller_monitor.temperature

                # 触发网络通信以获取传感器数据
                self.network_worker.trigger_communication()

                # 检查深度或温度是否有变化，或者是否已经有有效值
                if (self.controller_monitor.depth != initial_depth or
                        self.controller_monitor.temperature != initial_temperature or
                        self.controller_monitor.depth != 0.0 or
                        self.controller_monitor.temperature != 0.0):
                    sensor_ready = True
                    status_text = "温湿度传感器: √ 已连接"
                    status_color = (0, 255, 0)  # 绿色
                else:
                    status_text = "温湿度传感器: × 未连接"
                    status_color = (255, 0, 0)  # 红色
            else:
                status_text = "温湿度传感器: √ 已连接"
                status_color = (0, 255, 0)  # 绿色

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 + 60,
                                         color=status_color,
                                         outline=False)

            # 显示当前温度和深度值
            # 只要温度或深度值不为0，就显示它们，不需要等待sensor_ready
            if self.controller_monitor.depth != 0.0 or self.controller_monitor.temperature != 0.0:
                depth_text = f"深度: {self.controller_monitor.depth:.3f} m"

                # 使用UI控制器的辅助函数，根据异常情况决定温度显示与颜色
                display_temp, temp_is_fake = self.ui_controller.get_display_temperature(
                    self.controller_monitor.depth, self.controller_monitor.temperature
                )
                temp_text = f"温度: {display_temp:.2f} °C"
                temp_color = (255, 0, 0) if temp_is_fake else (255, 255, 255)

                self.ui_controller.draw_text(depth_text,
                                             self.ui_controller.settings['width'] // 2 + 200,
                                             self.ui_controller.settings['height'] // 2 + 60,
                                             color=(255, 255, 255),
                                             outline=False)

                self.ui_controller.draw_text(temp_text,
                                             self.ui_controller.settings['width'] // 2 + 200,
                                             self.ui_controller.settings['height'] // 2 + 90,
                                             color=temp_color,
                                             outline=False)

            # 检查电流下发
            if not current_ready:
                print("正在初始化电流下发...")
                status_text = "电流下发: 正在初始化..."
                status_color = (255, 255, 0)  # 黄色

                # 检查网络工作器是否运行
                if self.network_worker.running:
                    # 尝试发送控制器数据
                    try:
                        self.hw_controller.send_controller_data(self.controller_monitor.controller)
                        current_ready = True
                        status_text = "电流下发: √ 已就绪"
                        status_color = (0, 255, 0)  # 绿色
                    except Exception as e:
                        print(f"电流下发测试失败: {e}")
                        status_text = "电流下发: × 初始化失败"
                        status_color = (255, 0, 0)  # 红色
                else:
                    status_text = "电流下发: × 网络未就绪"
                    status_color = (255, 0, 0)  # 红色
            else:
                status_text = "电流下发: √ 已就绪"
                status_color = (0, 255, 0)  # 绿色

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,

                                         self.ui_controller.settings['height'] // 2 + 120,
                                         color=status_color,
                                         outline=False)

            # 电机状态提示（将在其他组件初始化后进行）
            status_text = "电机: 等待其他组件初始化完成..."
            status_color = (200, 200, 200)  # 灰色

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 + 180,
                                         color=status_color,
                                         outline=False)

            # 显示总体状态（不包括电机）
            other_components_ready = video_ready and joystick_ready and sensor_ready and current_ready
            status_color = (0, 255, 0) if other_components_ready else (255, 165, 0)  # 绿色或橙色
            status_text = "基础组件已就绪，即将初始化电机..." if other_components_ready else "部分基础组件未就绪..."

            self.ui_controller.draw_text(status_text,
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 + 240,
                                         color=status_color,
                                         bold=True,
                                         outline=True)

            self.ui_controller.update_display()

            # 增加重试计数
            retry_count += 1

            # 延迟一段时间
            time.sleep(retry_delay)
            pygame.event.pump()  # 保持UI响应

        # 检查基础组件初始化状态
        other_components_ready = video_ready and joystick_ready and sensor_ready and current_ready

        # 初始化电机状态为未就绪
        motors_ready = False

        # 如果用户没有强制进入且基础组件已就绪，则进行电机初始化
        if not force_entry and other_components_ready:
            print("基础组件已就绪，开始初始化电机...")

            # 显示电机初始化开始的提示
            self.ui_controller.display_frame(self.default_image)
            self.ui_controller.draw_text("基础组件已就绪",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 - 100,
                                         color=(0, 255, 0),
                                         bold=True,
                                         outline=True)
            self.ui_controller.draw_text("开始初始化电机...",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2,
                                         color=(255, 255, 255),
                                         bold=True,
                                         outline=True)
            self.ui_controller.update_display()
            time.sleep(1)  # 短暂停顿，让用户看到状态变化

            # 调用电机初始化方法
            motors_ready = self._init_motors()

        # 显示最终状态
        self.ui_controller.display_frame(self.default_image)

        # 更新all_ready状态
        # all_ready = other_components_ready and motors_ready

        # if all_ready:
        #     status_text = "所有组件已就绪，即将启动主程序..."
        #     status_color = (0, 255, 0)  # 绿色
        # elif force_entry:
        #     status_text = "用户强制进入系统"
        #     status_color = (255, 200, 0)  # 黄色
        # else:
        #     # 列出未就绪的组件
        #     failed_components = []
        #     if not video_ready:
        #         failed_components.append("视频流")
        #     if not joystick_ready:
        #         failed_components.append("手柄")
        #     if not sensor_ready:
        #         failed_components.append("温湿度传感器")
        #     if not current_ready:
        #         failed_components.append("电流下发")
        #     if not motors_ready:
        #         failed_components.append("电机")
        #
        #     status_text = f"部分组件未就绪 ({', '.join(failed_components)})，将尝试启动主程序..."
        #     status_color = (255, 165, 0)  # 橙色

        # 绘制标题
        # self.ui_controller.draw_text("初始化结果",
        #                              self.ui_controller.settings['width'] // 2,
        #                              self.ui_controller.settings['height'] // 2 - 100,
        #                              color=(255, 255, 255),
        #                              bold=True,
        #                              outline=True)
        #
        # # 绘制状态信息
        # self.ui_controller.draw_text(status_text,
        #                              self.ui_controller.settings['width'] // 2,
        #                              self.ui_controller.settings['height'] // 2,
        #                              color=status_color,
        #                              bold=True,
        #                              outline=True)
        #
        # # 绘制提示信息
        # self.ui_controller.draw_text("即将进入主程序...",
        #                              self.ui_controller.settings['width'] // 2,
        #                              self.ui_controller.settings['height'] // 2 + 100,
        #                              color=(200, 200, 200),
        #                              bold=False,
        #                              outline=True)
        #
        # self.ui_controller.update_display()
        #
        # # 等待3秒让用户查看状态
        # time.sleep(3)

        # 如果用户强制进入，确保仍然部署推力曲线
        if force_entry:
            print("用户强制进入，部署推力曲线...")
            self.deploy_thrust_curves()

        print("初始化完成，启动主程序\n")

    def _init_motors(self):
        """
        初始化电机参数
        
        如果有电机初始化失败，会持续重试，直到所有电机都初始化成功或用户按下手柄按键强制进入
        
        返回:
            bool: 如果所有电机都成功初始化则返回True，如果用户强制进入则返回False
        """
        # 初始化参数
        max_retry_count = 100  # 最大重试次数
        retry_count = 0
        retry_delay = 0.1  # 重试间隔（秒）
        force_entry = False  # 是否强制进入
        all_initialized = False  # 是否所有电机都已初始化

        # 显示初始化状态
        self.ui_controller.screen.fill((0, 0, 0))  # 清空屏幕
        self.ui_controller.draw_text("正在初始化电机...",
                                     self.ui_controller.settings['width'] // 2,
                                     self.ui_controller.settings['height'] // 2 - 50,
                                     color=(255, 255, 255),
                                     bold=True,
                                     outline=True)
        self.ui_controller.draw_text("按下任意手柄按键可强制进入",
                                     self.ui_controller.settings['width'] // 2,
                                     self.ui_controller.settings['height'] // 2 + 50,
                                     color=(255, 200, 0),
                                     bold=True,
                                     outline=True)
        self.ui_controller.update_display()

        # 首次尝试初始化所有电机
        all_initialized = self.hw_controller.hwinit()

        # 如果首次初始化不成功，进入重试循环
        while not all_initialized and not force_entry and retry_count < max_retry_count:
            # 检查是否有按钮被按下
            if self.joystick_handler.is_any_button_pressed():
                force_entry = True
                print("检测到手柄按键，强制进入系统")
                break

            # 获取失败的电机列表
            failed_motors = self.hw_controller.get_failed_motors()

            # 显示重试状态
            self.ui_controller.screen.fill((0, 0, 0))  # 清空屏幕
            self.ui_controller.draw_text("正在初始化电机...",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 - 100,
                                         color=(255, 255, 255),
                                         bold=True,
                                         outline=True)
            self.ui_controller.draw_text(f"失败的电机: {', '.join(failed_motors)}",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2,
                                         color=(255, 100, 100),
                                         bold=True,
                                         outline=True)
            self.ui_controller.draw_text("按下任意手柄按键可强制进入",
                                         self.ui_controller.settings['width'] // 2,
                                         self.ui_controller.settings['height'] // 2 + 100,
                                         color=(255, 200, 0),
                                         bold=True,
                                         outline=True)
            self.ui_controller.update_display()

            # 重试失败的电机
            still_failed = self.hw_controller.retry_failed_motors()

            # 检查是否所有电机都已初始化成功
            all_initialized = self.hw_controller.all_motors_initialized()

            # 增加重试计数
            retry_count += 1

            # 延迟一段时间
            time.sleep(retry_delay)

        # 显示最终状态
        self.ui_controller.screen.fill((0, 0, 0))  # 清空屏幕

        if all_initialized:
            status_text = "所有电机初始化成功"
            status_color = (100, 255, 100)  # 绿色
            time.sleep(0.5)
        elif force_entry:
            status_text = "用户强制进入系统"
            status_color = (255, 200, 0)  # 黄色
            time.sleep(2)
        else:
            status_text = f"部分电机初始化失败: {', '.join(self.hw_controller.get_failed_motors())}"
            status_color = (255, 100, 100)  # 红色
            time.sleep(2)

        self.ui_controller.draw_text(status_text,
                                     self.ui_controller.settings['width'] // 2,
                                     self.ui_controller.settings['height'] // 2,
                                     color=status_color,
                                     bold=True,
                                     outline=True)
        self.ui_controller.update_display()

        # 等待2秒让用户查看状态

        return all_initialized

    def deploy_thrust_curves(self):
        """部署推力曲线到ROV"""
        print("正在部署推力曲线...")
        self.hw_controller.hwinit()
        print("推力曲线部署完成")

    def run(self):
        """运行主循环"""
        while self.running:
            # 处理事件
            try:
                frame_rgb = self.video_thread.get_latest_frame(self.ui_controller.show_undistorted)
            except Exception as e:
                print(f"获取视频帧时发生异常: {str(e)}")
                frame_rgb = None
                
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
            # 获取手柄辅助修正状态
            joystick_correction_enabled = self.joystick_controller.joystick_correction.enabled

            # 简化版 - 不再显示电机控制健康状态
            self.ui_controller.display_controller_data(
                self.controller_monitor.controller,
                self.controller_monitor.depth,
                self.controller_monitor.temperature,
                modes,
                joystick_correction_enabled
            )

            # 更新显示
            self.ui_controller.update_display()

            # 检查视频线程状态（每10秒检查一次）
            current_time = time.time()
            if current_time - self.last_video_check_time >= self.video_check_interval:
                self.last_video_check_time = current_time

                # 添加调试日志
                print(f"[DEBUG] 检查视频线程状态: {'运行中' if self.video_thread.is_alive() else '已停止'}")

                # 检查视频线程是否还在运行
                if not self.video_thread.is_alive():
                    print("视频线程已停止，正在重新启动...")
                    # 重新初始化视频线程
                    rtsp_url = self.config_manager.get_rtsp_url()
                    base_width, base_height = self.config_manager.get_camera_dimensions()
                    buffer_size = self.config_manager.config["camera"].getint("buffer")

                    # 尝试停止旧线程（如果还存在）
                    try:
                        if hasattr(self.video_thread, 'stop'):
                            self.video_thread.stop()
                    except Exception as e:
                        print(f"停止旧视频线程时出错: {str(e)}")

                    # 创建并启动新线程
                    self.video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
                    self.video_thread.start()
                    print("视频线程已重新启动")

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
