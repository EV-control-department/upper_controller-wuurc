"""
配置管理模块
用于加载和管理系统配置
"""

import json
import os
from configparser import ConfigParser


class ConfigManager:
    """配置管理类，负责加载和访问系统配置"""

    def __init__(self, config_path=None):
        """
        初始化配置管理器
        
        参数:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.config = ConfigParser()

        # 如果未指定配置文件路径，使用默认路径
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config_beyond.ini")

        # 使用UTF-8编码读取配置文件
        self.config.read(config_path, encoding='utf-8')
        self.motor_params = {}
        self.load_motor_params()

    def load_motor_params(self):
        """从curve.json加载电机参数"""
        try:
            # 使用绝对路径确保文件位置正确
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config",
                                     self.config["curve"].get("location"))
            with open(json_path, 'r') as f:
                self.motor_params = json.load(f)
                print(f"成功从 curve.json 加载电机参数")

            # 验证参数完整性
            required_keys = ["np_mid", "np_ini", "pp_ini", "pp_mid", "nt_end", "nt_mid", "pt_mid", "pt_end"]
            for motor, params in self.motor_params.items():
                if not all(key in params for key in required_keys):
                    raise ValueError(f"{motor} 缺少必要参数")

        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"加载 curve.json 失败: {e}, 使用默认参数")
            # 保留原始默认参数作为回退
            self.motor_params = {
                "m0": {"num": 0, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89},
                "m1": {"num": 1, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89},
                "m2": {"num": 2, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89},
                "m3": {"num": 3, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89},
                "m4": {"num": 4, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89},
                "m5": {"num": 5, "np_mid": 2717.21, "np_ini": 2921.03, "pp_ini": 3066.62, "pp_mid": 3212.21,
                       "nt_end": -931.92, "nt_mid": -137.17, "pt_mid": 165.37, "pt_end": 1329.89}
            }

    def get_rtsp_url(self):
        """获取RTSP URL"""
        return "rtsp://" + self.config["camera"].get("username") + ":" + self.config["camera"].get("password") + "@" + \
            self.config["camera"].get("host") + ":554/stream0"

    def get_camera_dimensions(self):
        """获取摄像头分辨率"""
        return self.config["camera"].getint("width"), self.config["camera"].getint("height")

    def get_server_address(self):
        """获取服务器地址"""
        host = self.config["serial"].get("host")
        port = self.config["serial"].getint("remote_port")
        return (host, port)

    def get_local_port(self):
        """获取本地端口"""
        return self.config["serial"].getint("local_port")

    def get_controller_init(self):
        """获取控制器初始状态"""
        return {
            "x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0,
            "servo0": self.config["servo"].getfloat("open"),  # 舵机初始值
        }

    def get_servo_positions(self):
        """获取舵机位置配置"""
        return [
            self.config["servo"].getfloat("open"),
            self.config["servo"].getfloat("close"),
            self.config["servo"].getfloat("mid1"),
            self.config["servo"].getfloat("mid2")
        ]

    def get_interface_settings(self):
        """获取界面设置"""
        return {
            "width": self.config["interface"].getint("width"),
            "height": self.config["interface"].getint("height"),
            "font": self.config["interface"].get("font"),
            "font_size": self.config["interface"].getint("font_size"),
            "padding": self.config["interface"].getint("padding"),
            "y_h": self.config["interface"].getint("y_h"),
            "y_offset": self.config["interface"].getint("y_offset")
        }

    def get_joystick_settings(self):
        """获取手柄设置"""
        return {
            "buttons": self.config["joystick"].getint("buttons"),
            "axes": self.config["joystick"].getint("axes"),
            "long": self.config["joystick"].getint("long"),
            "double": self.config["joystick"].getint("double"),
            "tick": self.config["joystick"].getint("tick")
        }

    def get_axis_config(self, axis_name):
        """获取指定轴的配置"""
        if axis_name not in ["x", "y", "z", "yaw"]:
            raise ValueError(f"未知的轴名称: {axis_name}")

        return {
            "max": self.config[axis_name].getfloat("max"),
            "axis": self.config[axis_name].getint("axis"),
            "deadzone": self.config[axis_name].getfloat("deadzone")
        }

    def get_speed_modes(self):
        """获取速度模式配置"""
        return [
            {"name": "Mild Mode", "rate": self.config["speed_mode"].getfloat("rate0"), "color": "#00FF00"},
            {"name": "Normal Mode", "rate": self.config["speed_mode"].getfloat("rate1"), "color": "#FFFF00"},
            {"name": "Wild Mode", "rate": self.config["speed_mode"].getfloat("rate2"), "color": "#FF0000"}
        ]

    def get_lock_modes(self):
        """获取锁定模式配置"""
        return [
            {"name": "Lock", "value": 1, "color": "#FF0000"},
            {"name": "Releasing", "value": 1, "color": "#fbc11a"},
            {"name": "Unlock", "value": 2, "color": "#00FF00"}
        ]

    def get_loop_modes(self):
        """获取循环模式配置"""
        return [
            {"name": "开环", "value": 0, "color": "#00FF00"},
            {"name": "闭环", "value": 1, "color": "#FF0000"},
            {"name": "半闭环", "value": 2, "color": "#0000FF"}
        ]

    def get_catch_modes(self):
        """获取抓取模式配置"""
        return [
            {"name": "1.海螺捕捞", "servoX": 0.85, "servoY": 0.79, "color": "#e800b6"},
            {"name": "2.精确作业", "servoX": 0.99, "servoY": 0.79, "color": "#00d5e8"},
            {"name": "3.回收网箱", "servoX": 0.80, "servoY": 0.76, "color": "#8fe800"},
            {"name": "4.饲料投放", "servoX": 0.74, "servoY": 0.79, "color": "#e86800"}
        ]

    def get_mode_defaults(self):
        """获取模式默认值配置"""
        return {
            "speed_mode_ptr": self.config["mode_defaults"].getint("speed_mode_ptr"),
            "lock_mode_ptr": self.config["mode_defaults"].getint("lock_mode_ptr"),
            "loop_mode_ptr": self.config["mode_defaults"].getint("loop_mode_ptr"),
            "catch_mode_ptr": self.config["mode_defaults"].getint("catch_mode_ptr")
        }

    def get_controller_timing(self):
        """获取控制器时间设置"""
        return {
            "button10_block_duration": self.config["controller_timing"].getfloat("button10_block_duration"),
            "depth_temp_block_duration": self.config["controller_timing"].getfloat("depth_temp_block_duration")
        }

    def get_controller_thresholds(self):
        """获取控制器阈值设置"""
        return {
            "left_trigger_threshold": self.config["controller_thresholds"].getfloat("left_trigger_threshold"),
            "right_trigger_threshold": self.config["controller_thresholds"].getfloat("right_trigger_threshold"),
            "hat_up_value": self.config["controller_thresholds"].getint("hat_up_value")
        }

    def get_keyboard_bindings(self):
        """获取键盘绑定设置"""
        return {
            "quit_key": self.config["keyboard_bindings"].get("quit_key"),
            "xbox_debugger_key": self.config["keyboard_bindings"].get("xbox_debugger_key"),
            "toggle_rotation_key": self.config["keyboard_bindings"].get("toggle_rotation_key"),
            "toggle_undistorted_key": self.config["keyboard_bindings"].get("toggle_undistorted_key"),
            "toggle_fullscreen_key": self.config["keyboard_bindings"].get("toggle_fullscreen_key"),
            "capture_frame_key": self.config["keyboard_bindings"].get("capture_frame_key"),
            "controller_visualizer_key": self.config["keyboard_bindings"].get("controller_visualizer_key", "v"),
            "controller_mapping_key": self.config["keyboard_bindings"].get("controller_mapping_key", "m")
        }

    def get_key_cooldowns(self):
        """获取按键冷却时间设置"""
        return {
            "xbox_debugger_cooldown": self.config["key_cooldowns"].getfloat("xbox_debugger_cooldown"),
            "toggle_rotation_cooldown": self.config["key_cooldowns"].getfloat("toggle_rotation_cooldown"),
            "toggle_undistorted_cooldown": self.config["key_cooldowns"].getfloat("toggle_undistorted_cooldown"),
            "toggle_fullscreen_cooldown": self.config["key_cooldowns"].getfloat("toggle_fullscreen_cooldown"),
            "capture_frame_cooldown": self.config["key_cooldowns"].getfloat("capture_frame_cooldown"),
            "button7_cooldown": self.config["key_cooldowns"].getfloat("button7_cooldown"),
            "controller_visualizer_cooldown": self.config["key_cooldowns"].getfloat("controller_visualizer_cooldown",
                                                                                    0.5),
            "controller_mapping_cooldown": self.config["key_cooldowns"].getfloat("controller_mapping_cooldown", 0.5)
        }
