"""
手柄控制器模块
用于封装手柄输入处理功能
"""

import time

from modules.hardware_controller import controller_curve
from modules.joystick_correction import JoystickCorrection


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

        # 初始化手柄辅助修正
        try:
            # 检查joystick_correction是否是ConfigParser的section
            if "joystick_correction" in self.config_manager.config:
                # 使用ConfigParser的方式获取值
                self.joystick_correction = JoystickCorrection({
                    "detection_threshold": self.config_manager.config["joystick_correction"].getfloat(
                        "detection_threshold", 0.1),
                    "stationary_threshold": self.config_manager.config["joystick_correction"].getfloat(
                        "stationary_threshold", 0.05),
                    "correction_duration": self.config_manager.config["joystick_correction"].getfloat(
                        "correction_duration", 0.5),
                    "filter_strength": self.config_manager.config["joystick_correction"].getfloat("filter_strength",
                                                                                                  2.0)
                })
            else:
                # 使用默认值
                self.joystick_correction = JoystickCorrection({
                    "detection_threshold": 0.1,
                    "stationary_threshold": 0.05,
                    "correction_duration": 0.5,
                    "filter_strength": 2.0
                })
        except Exception as e:
            print(f"初始化手柄辅助修正失败: {str(e)}，使用默认值")
            # 使用默认值
            self.joystick_correction = JoystickCorrection({
                "detection_threshold": 0.1,
                "stationary_threshold": 0.05,
                "correction_duration": 0.5,
                "filter_strength": 2.0
            })

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
        # 获取轴配置
        yaw_axis = self.config_manager.get_axis_config("yaw")
        y_axis = self.config_manager.get_axis_config("y")
        x_axis = self.config_manager.get_axis_config("x")
        z_axis = self.config_manager.get_axis_config("z")

        # 获取原始轴值
        raw_yaw = self.joystick_handler.get_axis(yaw_axis["axis"])
        raw_y = self.joystick_handler.get_axis(y_axis["axis"])
        raw_x = self.joystick_handler.get_axis(x_axis["axis"])
        raw_z = self.joystick_handler.get_axis(z_axis["axis"])

        # 应用辅助修正
        corrected_x, corrected_y, corrected_z, corrected_yaw = self.joystick_correction.process_axes(
            raw_x, raw_y, raw_z, raw_yaw
        )

        # 处理控制器输入 - Yaw轴
        if abs(corrected_yaw) >= yaw_axis["deadzone"]:
            self.controller_monitor.controller["yaw"] = (
                                                                yaw_axis["max"] *
                                                                self.speed_modes[self.speed_mode_ptr]["rate"]
                                                        ) * controller_curve(
                corrected_yaw
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 8)
        else:
            self.controller_monitor.controller["yaw"] = 0.0

        # 处理控制器输入 - Y轴（前后）
        if abs(corrected_y) >= y_axis["deadzone"]:
            self.controller_monitor.controller["y"] = (
                                                              y_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                corrected_y
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 4)
        else:
            self.controller_monitor.controller["y"] = 0.0

        # 处理控制器输入 - X轴（左右）
        if abs(corrected_x) >= x_axis["deadzone"]:
            self.controller_monitor.controller["x"] = (
                                                              x_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                corrected_x
            ) * (1 - (self.joystick_handler.get_axis(4) + 1) / 4)
        else:
            self.controller_monitor.controller["x"] = 0.0

        # 处理控制器输入 - Z轴（上下）
        if abs(corrected_z) >= z_axis["deadzone"] and not self.pid_state:
            self.controller_monitor.controller["z"] = (
                                                              z_axis["max"] *
                                                              self.speed_modes[self.speed_mode_ptr]["rate"]
                                                      ) * controller_curve(
                corrected_z
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

    def toggle_joystick_correction(self):
        """切换手柄辅助修正状态"""
        enabled = self.joystick_correction.toggle()
        print(f"手柄辅助修正: {'已启用' if enabled else '已禁用'}")
        return enabled
        
    def process_input(self):
        """处理所有手柄输入"""
        # 检查阻塞状态
        if self.check_depth_temp_block() or self.check_button10_block():
            return True  # 跳过其他输入处理

        # 处理速度模式
        self.process_speed_mode()

        # 处理辅助修正切换（按钮8 - 左摇杆按下）
        if self.joystick_handler.buttons[8]["down"]:
            self.toggle_joystick_correction()
            self.joystick_handler.start_rumble(8)  # 提供震动反馈

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
