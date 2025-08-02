"""
手柄控制器模块
用于封装手柄输入处理功能
"""

import time

from modules.hardware_controller import controller_curve


class JoystickController:
    """手柄控制器类，封装手柄输入处理功能"""

    def __init__(self, joystick_handler, config_manager, controller_monitor):
        """
        初始化手柄控制器
        
        参数:
            joystick_handler: 手柄处理器实例
            config_manager: 配置管理器实例
            controller_monitor: 控制器监控器实例
        """
        self.joystick_handler = joystick_handler
        self.config_manager = config_manager
        self.controller_monitor = controller_monitor

        # 模式设置
        self.speed_modes = self.config_manager.get_speed_modes()
        self.lock_modes = self.config_manager.get_lock_modes()
        self.loop_modes = self.config_manager.get_loop_modes()
        self.catch_modes = self.config_manager.get_catch_modes()

        # 获取模式默认值
        mode_defaults = self.config_manager.get_mode_defaults()

        # 模式指针
        self.speed_mode_ptr = mode_defaults["speed_mode_ptr"]  # 当前速度模式指针
        self.lock_mode_ptr = mode_defaults["lock_mode_ptr"]  # 当前锁定模式指针
        self.loop_mode_ptr = mode_defaults["loop_mode_ptr"]  # 当前闭环模式指针
        self.catch_mode_ptr = mode_defaults["catch_mode_ptr"]  # 当前抓取模式指针
        self.pre_speed_mode_ptr = 0

        # 舵机位置
        self.servo_positions = self.config_manager.get_servo_positions()

        # 获取控制器时间设置
        controller_timing = self.config_manager.get_controller_timing()

        # 阻塞状态变量
        self.button10_block_start = 0
        self.button10_block_duration = controller_timing["button10_block_duration"]  # 秒
        self.depth_temp_block_start = 0
        self.depth_temp_block_duration = controller_timing["depth_temp_block_duration"]  # 秒

        # 释放状态
        self.release_state = False

        # PID状态
        self.pid_state = False

        # 获取控制器阈值设置
        self.thresholds = self.config_manager.get_controller_thresholds()

    def update(self):
        """更新手柄状态"""
        self.joystick_handler.update_button_states()
        self.joystick_handler.update_rumble_states()

    def check_depth_temp_block(self):
        """检查深度温度阻塞状态"""
        if self.depth_temp_block_start > 0:
            if time.time() - self.depth_temp_block_start < self.depth_temp_block_duration:
                # 在阻塞期间跳过处理其他输入，但不阻塞主循环
                return True  # 跳过其他输入处理
            else:
                # 阻塞时间结束
                self.depth_temp_block_start = 0
        return False

    def check_button10_block(self):
        """检查按钮10阻塞状态"""
        if self.joystick_handler.buttons[10]["down"]:  # select键阻塞进程 - 改为非阻塞
            self.button10_block_start = time.time()

        if self.button10_block_start > 0:
            if time.time() - self.button10_block_start < self.button10_block_duration:
                # 在阻塞期间跳过处理其他输入，但不阻塞主循环
                return True  # 跳过其他输入处理
            else:
                # 阻塞时间结束
                self.button10_block_start = 0
        return False

    def process_speed_mode(self):
        """处理速度模式切换（左扳机）"""
        left_trigger_threshold = self.thresholds["left_trigger_threshold"]
        if self.joystick_handler.get_axis(4) > left_trigger_threshold and self.pre_speed_mode_ptr == 0:
            self.pre_speed_mode_ptr = self.speed_mode_ptr
            self.speed_mode_ptr = 0
        elif self.pre_speed_mode_ptr != 0 and self.joystick_handler.get_axis(4) < left_trigger_threshold:
            self.speed_mode_ptr = self.pre_speed_mode_ptr
            self.pre_speed_mode_ptr = 0

    def process_axes(self):
        """处理控制器轴输入"""
        # 处理控制器输入 - Yaw轴
        yaw_axis = self.config_manager.get_axis_config("yaw")
        if abs(self.joystick_handler.get_axis(yaw_axis["axis"])) >= yaw_axis["deadzone"]:
            self.controller_monitor.controller["yaw"] = (
                                                                yaw_axis["max"] *
                                                                self.speed_modes[self.speed_mode_ptr]["rate"]
                                                        ) * controller_curve(
                self.joystick_handler.get_axis(yaw_axis["axis"])
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 8)
        else:
            self.controller_monitor.controller["yaw"] = 0.0

        # 处理控制器输入 - Y轴（前后）
        y_axis = self.config_manager.get_axis_config("y")
        if abs(self.joystick_handler.get_axis(y_axis["axis"])) >= y_axis["deadzone"]:
            self.controller_monitor.controller["y"] = (
                                                              y_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                self.joystick_handler.get_axis(y_axis["axis"])
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 4)
        else:
            self.controller_monitor.controller["y"] = 0.0

        # 处理控制器输入 - X轴（左右）
        x_axis = self.config_manager.get_axis_config("x")
        if abs(self.joystick_handler.get_axis(x_axis["axis"])) >= x_axis["deadzone"]:
            self.controller_monitor.controller["x"] = (
                                                              x_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                self.joystick_handler.get_axis(x_axis["axis"])
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 4)
        else:
            self.controller_monitor.controller["x"] = 0.0

        # 处理控制器输入 - Z轴（上下）
        z_axis = self.config_manager.get_axis_config("z")
        if abs(self.joystick_handler.get_axis(z_axis["axis"])) >= z_axis["deadzone"] and not self.pid_state:
            self.controller_monitor.controller["z"] = (
                                                              z_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                self.joystick_handler.get_axis(z_axis["axis"])
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 8)
        else:
            self.controller_monitor.controller["z"] = 0.0

    def process_servo_controls(self):
        """处理舵机控制"""
        # 处理方向键输入
        if self.joystick_handler.get_hat(0) == self.thresholds["hat_up_value"]:
            self.controller_monitor.controller["servo0"] = self.servo_positions[4]

        # 处理舵机控制
        if self.lock_mode_ptr == 2:  # 未锁定
            if self.joystick_handler.get_axis(5) > self.config_manager.config["servo"].getfloat("deadzone"):  # 右扳机
                self.controller_monitor.controller["servo0"] = (
                                                                       self.servo_positions[0] - self.servo_positions[1]
                                                               ) * (1 - (self.joystick_handler.get_axis(5) + 1) / 2) + \
                                                               self.servo_positions[1]

        # 处理左肩键（打开舵机）
        open_button = self.config_manager.config["servo"].getint("open_button")
        open_trig = self.config_manager.config["servo"].get("open_trig")
        if self.joystick_handler.buttons[open_button][open_trig]:
            self.controller_monitor.controller["servo0"] = self.servo_positions[0]  # 打开
            self.joystick_handler.start_rumble(open_button)

        # 处理右肩键（关闭舵机）
        close_button = self.config_manager.config["servo"].getint("close_button")
        close_trig = self.config_manager.config["servo"].get("close_trig")
        if self.joystick_handler.buttons[close_button][close_trig]:
            self.controller_monitor.controller["servo0"] = self.servo_positions[1]  # 关闭
            self.lock_mode_ptr = 0
            self.joystick_handler.start_rumble(close_button)

        # 处理按钮3（Y按钮）
        if self.joystick_handler.buttons[3]["down"]:
            self.controller_monitor.controller["servo0"] = self.catch_modes[self.catch_mode_ptr]["servoY"]
            self.lock_mode_ptr = 0
            self.joystick_handler.start_rumble(3)

        # 处理按钮2（X按钮）
        if self.joystick_handler.buttons[2]["down"]:
            self.controller_monitor.controller["servo0"] = self.catch_modes[self.catch_mode_ptr]["servoX"]
            self.lock_mode_ptr = 0
            self.joystick_handler.start_rumble(2)

        # 处理右扳机释放状态
        right_trigger_threshold = self.thresholds["right_trigger_threshold"]
        servo_deadzone = self.config_manager.config["servo"].getfloat("deadzone")

        if self.joystick_handler.get_axis(5) > right_trigger_threshold and not self.release_state:
            self.release_state = self.controller_monitor.controller["servo0"]
        elif self.joystick_handler.get_axis(5) < servo_deadzone and self.release_state:
            self.release_state = False
            self.lock_mode_ptr = 2
        elif self.release_state:
            self.controller_monitor.controller["servo0"] = (
                                                                   self.servo_positions[0] - self.release_state
                                                           ) * (1 - (
                    self.joystick_handler.get_axis(5) + 1) / 2) + self.release_state
            self.lock_mode_ptr = 1

        # 处理按钮9（B按钮）- 切换抓取模式
        if self.joystick_handler.buttons[9]["down"]:
            self.catch_mode_ptr = (self.catch_mode_ptr + 1) % len(self.catch_modes)
            self.joystick_handler.start_rumble(9)

    def process_input(self):
        """处理所有手柄输入"""
        # 检查阻塞状态
        if self.check_depth_temp_block() or self.check_button10_block():
            return True  # 跳过其他输入处理

        # 处理速度模式
        self.process_speed_mode()

        # 处理轴输入
        self.process_axes()

        # 处理舵机控制
        self.process_servo_controls()

        return False  # 继续处理其他输入

    def set_depth_temp_block(self):
        """设置深度温度阻塞状态"""
        self.depth_temp_block_start = time.time()

    def get_current_modes(self):
        """获取当前模式信息"""
        return {
            'speed_mode': self.speed_modes[self.speed_mode_ptr],
            'lock_mode': self.lock_modes[self.lock_mode_ptr],
            'loop_mode': self.loop_modes[self.loop_mode_ptr],
            'catch_mode': self.catch_modes[self.catch_mode_ptr]
        }
