"""
用户界面控制模块
用于管理用户界面和输入处理
"""

import os
import random
import subprocess
import time

import keyboard
import pygame


class UIController:
    """用户界面控制类，负责管理界面显示和输入处理"""

    def __init__(self, interface_settings, config_manager=None):
        """
        初始化用户界面控制器
        
        参数:
            interface_settings: 界面设置字典
            config_manager: 配置管理器实例
        """
        self.settings = interface_settings
        self.config_manager = config_manager
        self.screen = None
        self.font = None
        self.rotate_mode = False  # 初始为横屏
        self.in_fullscreen = False
        self.show_undistorted = False
        self.default_image = None  # 存储默认图像

        # 初始化键盘绑定和冷却时间
        self.keyboard_bindings = {}
        self.key_cooldowns = {}

        # 如果提供了配置管理器，从配置中加载键盘绑定和冷却时间
        if self.config_manager:
            self.keyboard_bindings = self.config_manager.get_keyboard_bindings()
            self.key_cooldowns = self.config_manager.get_key_cooldowns()

        # 用于非阻塞按键处理的状态变量
        self.key_states = {
            self.keyboard_bindings.get('xbox_debugger_key', 'd'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('xbox_debugger_cooldown', 0.5)},  # Xbox调试器
            self.keyboard_bindings.get('toggle_rotation_key', 't'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('toggle_rotation_cooldown', 0.5)},  # 切换屏幕方向
            self.keyboard_bindings.get('toggle_undistorted_key', 's'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('toggle_undistorted_cooldown', 0.5)},  # 切换无失真视图
            self.keyboard_bindings.get('toggle_fullscreen_key', 'f'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('toggle_fullscreen_cooldown', 0.5)},  # 切换全屏
            self.keyboard_bindings.get('capture_frame_key', 'p'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('capture_frame_cooldown', 0.2)},  # 捕获当前帧
            self.keyboard_bindings.get('controller_visualizer_key', 'v'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('controller_visualizer_cooldown', 0.5)},
            # 控制器可视化工具
            self.keyboard_bindings.get('controller_mapping_key', 'm'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('controller_mapping_cooldown', 0.5)},  # 控制器映射编辑器
            self.keyboard_bindings.get('deploy_thrust_curves_key', 'c'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('deploy_thrust_curves_cooldown', 1.0)},  # 部署推力曲线
            self.keyboard_bindings.get('toggle_joystick_correction_key', 'j'):
                {'last_press': 0, 'cooldown': self.key_cooldowns.get('toggle_joystick_correction_cooldown', 0.5)},
            # 切换手柄辅助修正
            'button7': {'last_press': 0, 'cooldown': self.key_cooldowns.get('button7_cooldown', 0.2)}  # 捕获当前帧（手柄按钮）
        }

        # 初始化Pygame
        pygame.init()
        self._init_display()
        self._init_font()
        self._load_icon()

        # 读取温度回退配置（用于异常时显示默认温度）
        self.default_temperature = 28.32
        self.fake_temp_jitter = 0.1
        # 温度显示的变化速度限制（单位：°C/秒），将速度调小10倍（默认0.1）
        self.temp_slew_rate = 0.1
        # 内部温度显示状态与时间戳
        self._temp_display_value = None
        self._last_temp_time = time.time()
        # 温度糊弄模式：'abnormal_only' = 仅异常糊弄；'always' = 全程糊弄
        self.temp_fooling_mode = 'abnormal_only'
        # 绑定切换按键（默认 i）与冷却
        self.toggle_temp_fooling_key = self.keyboard_bindings.get('toggle_temp_fooling_key',
                                                                  'i') if self.config_manager else 'i'
        self.key_states[self.toggle_temp_fooling_key] = {'last_press': 0, 'cooldown': self.key_cooldowns.get(
            'toggle_temp_fooling_cooldown', 0.5) if self.config_manager else 0.5}
        try:
            if self.config_manager and hasattr(self.config_manager, 'config'):
                if self.config_manager.config.has_section('sensor_fallback'):
                    self.default_temperature = self.config_manager.config['sensor_fallback'].getfloat(
                        'default_temperature', fallback=self.default_temperature)
                    # 可选：从配置读取温度变化速度限制
                    if 'temperature_slew_rate' in self.config_manager.config['sensor_fallback']:
                        self.temp_slew_rate = self.config_manager.config['sensor_fallback'].getfloat(
                            'temperature_slew_rate', fallback=self.temp_slew_rate)
        except Exception as e:
            print(
                f"读取默认温度/速度配置失败，使用默认值 {self.default_temperature}°C, slew={self.temp_slew_rate}°C/s: {e}")

    def _init_display(self):
        """初始化显示窗口"""
        self.screen = pygame.display.set_mode(
            (self.settings['width'], self.settings['height']),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("ROV控制上位机软件")

    def _init_font(self):
        """初始化字体"""
        try:
            # 尝试使用配置中指定的字体
            self.font = pygame.font.SysFont(
                self.settings['font'],
                self.settings['font_size']
            )

            # 测试字体是否支持中文
            test_text = "测试中文"
            test_render = self.font.render(test_text, True, (0, 0, 0))

            # 如果渲染的宽度太小，可能表示字体不支持中文
            if test_render.get_width() < len(test_text) * self.settings['font_size'] * 0.5:
                raise Exception("Font does not support Chinese characters")

        except:
            # 尝试使用系统中支持中文的字体
            system_fonts = pygame.font.get_fonts()
            chinese_fonts = [f for f in system_fonts if
                             f in ['simsun', 'simhei', 'microsoftyahei', 'dengxian', 'fangsong', 'kaiti']]

            if chinese_fonts:
                self.font = pygame.font.SysFont(chinese_fonts[0], self.settings['font_size'])
                print(f"使用中文字体: {chinese_fonts[0]}")
            else:
                # 如果没有找到中文字体，使用默认字体
                self.font = pygame.font.Font(None, self.settings['font_size'])
                print("警告: 未找到支持中文的字体，可能导致中文显示异常")

    def _load_icon(self):
        """加载窗口图标"""
        try:
            # 获取图标文件路径
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets\EV.jpg')
            icon_surface = pygame.image.load(icon_path)
            pygame.display.set_icon(icon_surface)
            print(f"成功设置窗口图标: {icon_path}")
        except Exception as e:
            print(f"设置窗口图标失败: {e}")

    def load_default_image(self):
        """加载默认图像"""
        try:
            image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'default_image.jpg')
            self.default_image = pygame.image.load(image_path)
            print(f"成功加载默认图片: {image_path}")
            return self.default_image
        except Exception as e:
            print(f"加载默认图片失败: {e}")
            self.default_image = None
            return None

    def handle_events(self, joystick, video_thread, main_controller=None):
        """
        处理pygame事件和键盘输入
        
        参数:
            joystick: 手柄对象
            video_thread: 视频处理线程
            main_controller: 主控制器实例，用于部署推力曲线
            
        返回:
            running: 是否继续运行
        """
        running = True
        screen_width, screen_height = self.screen.get_size()
        current_time = time.time()

        # 处理pygame事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 获取键盘绑定
        quit_key = self.keyboard_bindings.get('quit_key', 'q')
        xbox_debugger_key = self.keyboard_bindings.get('xbox_debugger_key', 'd')
        toggle_rotation_key = self.keyboard_bindings.get('toggle_rotation_key', 't')
        toggle_undistorted_key = self.keyboard_bindings.get('toggle_undistorted_key', 's')
        toggle_fullscreen_key = self.keyboard_bindings.get('toggle_fullscreen_key', 'f')
        capture_frame_key = self.keyboard_bindings.get('capture_frame_key', 'p')
        controller_visualizer_key = self.keyboard_bindings.get('controller_visualizer_key', 'v')
        controller_mapping_key = self.keyboard_bindings.get('controller_mapping_key', 'm')
        deploy_thrust_curves_key = self.keyboard_bindings.get('deploy_thrust_curves_key', 'c')
        toggle_joystick_correction_key = self.keyboard_bindings.get('toggle_joystick_correction_key', 'j')

        # 处理键盘输入 - 使用非阻塞方式
        if keyboard.is_pressed(quit_key):
            running = False

        # 使用非阻塞方式处理Xbox调试器键
        if keyboard.is_pressed(xbox_debugger_key):
            if current_time - self.key_states[xbox_debugger_key]['last_press'] > self.key_states[xbox_debugger_key][
                'cooldown']:
                self.open_xbox_debugger()
                self.key_states[xbox_debugger_key]['last_press'] = current_time

        # 使用非阻塞方式处理控制器可视化工具键
        if keyboard.is_pressed(controller_visualizer_key):
            if current_time - self.key_states[controller_visualizer_key]['last_press'] > \
                    self.key_states[controller_visualizer_key]['cooldown']:
                self.open_controller_visualizer()
                self.key_states[controller_visualizer_key]['last_press'] = current_time

        # 使用非阻塞方式处理控制器映射编辑器键
        if keyboard.is_pressed(controller_mapping_key):
            if current_time - self.key_states[controller_mapping_key]['last_press'] > \
                    self.key_states[controller_mapping_key]['cooldown']:
                self.open_controller_mapping_editor()
                self.key_states[controller_mapping_key]['last_press'] = current_time

        # 使用非阻塞方式处理部署推力曲线键
        if keyboard.is_pressed(deploy_thrust_curves_key):
            if current_time - self.key_states[deploy_thrust_curves_key]['last_press'] > \
                    self.key_states[deploy_thrust_curves_key]['cooldown']:
                if main_controller:
                    self.deploy_thrust_curves(main_controller)
                self.key_states[deploy_thrust_curves_key]['last_press'] = current_time

        # 使用非阻塞方式处理切换手柄辅助修正键
        if keyboard.is_pressed(toggle_joystick_correction_key):
            if current_time - self.key_states[toggle_joystick_correction_key]['last_press'] > \
                    self.key_states[toggle_joystick_correction_key]['cooldown']:
                if main_controller:
                    self.toggle_joystick_correction(main_controller)
                self.key_states[toggle_joystick_correction_key]['last_press'] = current_time

        # 使用非阻塞方式处理切换屏幕方向键
        if keyboard.is_pressed(toggle_rotation_key):
            if current_time - self.key_states[toggle_rotation_key]['last_press'] > self.key_states[toggle_rotation_key][
                'cooldown']:
                self.rotate_mode = not self.rotate_mode
                self.key_states[toggle_rotation_key]['last_press'] = current_time

        # 使用非阻塞方式处理切换无失真视图键
        if keyboard.is_pressed(toggle_undistorted_key):
            if current_time - self.key_states[toggle_undistorted_key]['last_press'] > \
                    self.key_states[toggle_undistorted_key]['cooldown']:
                self.show_undistorted = not self.show_undistorted
                self.key_states[toggle_undistorted_key]['last_press'] = current_time

        # 使用非阻塞方式处理切换全屏键
        if keyboard.is_pressed(toggle_fullscreen_key):
            if current_time - self.key_states[toggle_fullscreen_key]['last_press'] > \
                    self.key_states[toggle_fullscreen_key]['cooldown']:
                if self.in_fullscreen:
                    self.screen = pygame.display.set_mode((screen_width, screen_height))
                    pygame.display.set_mode((screen_width, screen_height))
                    self.in_fullscreen = False
                else:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    self.in_fullscreen = True
                self.key_states[toggle_fullscreen_key]['last_press'] = current_time

        # 使用非阻塞方式处理切换温度糊弄模式键（i）
        if keyboard.is_pressed(self.toggle_temp_fooling_key):
            state = self.key_states.get(self.toggle_temp_fooling_key, {'last_press': 0, 'cooldown': 0.5})
            if current_time - state['last_press'] > state['cooldown']:
                self.temp_fooling_mode = 'always' if self.temp_fooling_mode == 'abnormal_only' else 'abnormal_only'
                # 取消输出以减少暴露风险
                state['last_press'] = current_time
                self.key_states[self.toggle_temp_fooling_key] = state

        # 使用非阻塞方式处理捕获当前帧键或手柄按钮7
        if joystick:
            button7_pressed = joystick.get_button(7)
            p_key_pressed = keyboard.is_pressed(capture_frame_key)

            if button7_pressed:
                if current_time - self.key_states['button7']['last_press'] > self.key_states['button7']['cooldown']:
                    try:
                        frame = video_thread.get_latest_frame(self.show_undistorted)
                        if frame is not None:
                            video_thread.save_frame(frame)
                    except Exception as e:
                        print(f"捕获帧时发生异常: {str(e)}")
                    self.key_states['button7']['last_press'] = current_time
            elif p_key_pressed:
                if current_time - self.key_states[capture_frame_key]['last_press'] > self.key_states[capture_frame_key][
                    'cooldown']:
                    try:
                        frame = video_thread.get_latest_frame(self.show_undistorted)
                        if frame is not None:
                            video_thread.save_frame(frame)
                    except Exception as e:
                        print(f"捕获帧时发生异常: {str(e)}")
                    self.key_states[capture_frame_key]['last_press'] = current_time

        return running

    def draw_text(self, text, x, y, color=(255, 255, 255), bold=False, outline=True, outline_thickness=1):
        """
        绘制文本，可选带轮廓
        
        参数:
            text: 文本内容
            x, y: 文本位置
            color: 文本颜色
            bold: 是否加粗
            outline: 是否绘制轮廓
            outline_thickness: 轮廓厚度
        """
        # 使用已初始化的字体，确保中文显示正常
        word_font = self.font

        # 如果需要加粗
        if bold:
            word_font.set_bold(True)
        else:
            word_font.set_bold(False)  # 确保不加粗

        # 如果需要绘制轮廓
        if outline:
            # 渲染并旋转轮廓
            outline_surface = word_font.render(text, True, (0, 0, 0))  # 黑色轮廓
            if self.rotate_mode:
                outline_surface = pygame.transform.rotate(outline_surface, 90)

            # 获取旋转后轮廓的宽度和高度
            outline_width, outline_height = outline_surface.get_size()

            # 旋转后轮廓位置的计算
            if self.rotate_mode:
                outline_x = x - outline_width + 36  # 旋转后的轮廓左上角X
                outline_y = y - outline_height  # 旋转后的轮廓左上角Y
            else:
                outline_x, outline_y = x, y

            # 绘制轮廓
            self.screen.blit(outline_surface, (outline_x, outline_y))

        # 渲染文本
        video_text_surface = word_font.render(text, True, color)

        # 旋转文本，如果需要竖屏
        if self.rotate_mode:
            video_text_surface = pygame.transform.rotate(video_text_surface, 90)

        # 获取旋转后的文本宽度和高度
        video_text_width, text_height = video_text_surface.get_size()

        # 旋转后文本位置的调整
        if self.rotate_mode:
            # 旋转后，确保文本底部对齐
            y -= text_height  # 需要把Y坐标调整为底部对齐

        # 绘制文本
        self.screen.blit(video_text_surface, (x, y))

    def display_frame(self, frame_rgb):
        """
        显示视频帧
        
        参数:
            frame_rgb: RGB格式的视频帧或pygame Surface对象
        """
        # 首先清空屏幕，防止渲染数据重叠
        self.screen.fill((0, 0, 0))  # 用黑色填充屏幕

        # 获取当前窗口的大小
        screen_width, screen_height = self.screen.get_size()

        if frame_rgb is not None:
            # 检查输入类型
            if isinstance(frame_rgb, pygame.Surface):
                # 如果是pygame Surface对象，直接使用
                frame_surface = frame_rgb
            else:
                # 如果是numpy数组，转换为pygame Surface
                try:
                    frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                except Exception as e:
                    print(f"转换视频帧失败: {e}")
                    # 如果转换失败，使用默认图像
                    if self.default_image is not None:
                        frame_surface = self.default_image
                    else:
                        return

            # 确保图像大小适应当前窗口大小
            scaled_surface = pygame.transform.scale(frame_surface, (screen_width, screen_height))

            # 绘制到屏幕
            self.screen.blit(scaled_surface, (0, 0))
        elif self.default_image is not None:
            # 如果没有视频帧但有默认图像，则显示默认图像
            scaled_default = pygame.transform.scale(self.default_image, (screen_width, screen_height))
            self.screen.blit(scaled_default, (0, 0))

    def display_controller_data(self, controller_data, depth, temperature, modes, joystick_correction_enabled=None):
        """
        显示控制器数据和模式信息 - 简化版
        
        参数:
            controller_data: 控制器数据字典
            depth: 深度值
            temperature: 温度值
            modes: 模式信息字典
            joystick_correction_enabled: 手柄辅助修正是否启用
        """
        padding = self.settings['padding']
        screen_width, screen_height = self.screen.get_size()

        # 控制器数据
        data_lines = [
            f"X: {controller_data['x']:.1f}",
            f"Y: {controller_data['y']:.1f}",
            f"Z: {controller_data['z']:.1f}",
            f"Yaw: {controller_data['yaw']:.1f}",
            f"Servo: {controller_data['servo0']:.2f}"
        ]

        # 计算温度显示（异常情况下显示默认温度并标红）
        display_temp, temp_is_fake = self.get_display_temperature(depth, temperature)

        # 传感器数据
        right_data_lines = [
            f"深度: {depth:.3f} m",
            f"温度: {display_temp:.2f} °C"
        ]

        # 添加手柄辅助修正状态
        if joystick_correction_enabled is not None:
            status_text = "辅助修正: 已启用" if joystick_correction_enabled else "辅助修正: 已禁用"
            status_color = (0, 255, 0) if joystick_correction_enabled else (255, 165, 0)  # 绿色表示启用，橙色表示禁用
            right_data_lines.append(status_text)

        # 渲染控制器数据
        y_offset = padding
        for line in data_lines:
            if self.rotate_mode:
                self.draw_text(line, self.settings['y_h'] + y_offset, screen_height - padding,
                               color=(255, 255, 255))
            else:
                self.draw_text(line, padding, self.settings['y_h'] + y_offset, color=(255, 255, 255))
            y_offset += self.settings['y_offset']

        # 渲染模式信息
        if self.rotate_mode:
            self.draw_text(f"{modes['speed_mode']['name']}", self.settings['y_h'] + y_offset,
                           screen_height - padding, color=pygame.Color(modes['speed_mode']['color']))
            y_offset += self.settings['y_offset']
            self.draw_text(f"{modes['lock_mode']['name']}", self.settings['y_h'] + y_offset,
                           screen_height - padding, color=pygame.Color(modes['lock_mode']['color']))
            self.draw_text(f"{modes['catch_mode']['name']}", self.settings['y_h'] + screen_width - 100,
                           screen_height - padding, color=pygame.Color(modes['catch_mode']['color']))
        else:
            self.draw_text(f"{modes['speed_mode']['name']}", padding, self.settings['y_h'] + y_offset,
                           color=pygame.Color(modes['speed_mode']['color']))
            y_offset += self.settings['y_offset']
            self.draw_text(f"{modes['lock_mode']['name']}", padding, self.settings['y_h'] + y_offset,
                           color=pygame.Color(modes['lock_mode']['color']))
            y_offset += self.settings['y_offset']
            self.draw_text(f"{modes['catch_mode']['name']}", padding, self.settings['y_h'] + y_offset,
                           color=pygame.Color(modes['catch_mode']['color']))

        # 渲染传感器数据
        y_offset = padding
        for i, line in enumerate(right_data_lines):
            text_width = self.font.size(line)[0]

            if self.rotate_mode:
                x_pos = padding
            else:
                x_pos = screen_width - text_width - padding

            # 使用特定颜色显示状态信息
            text_color = (255, 255, 255)  # 默认白色

            # 辅助修正状态行
            if joystick_correction_enabled is not None and line.startswith("辅助修正"):
                text_color = status_color


            if self.rotate_mode:
                self.draw_text(line, y_offset, 250, color=text_color)
            else:
                self.draw_text(line, x_pos, self.settings['y_h'] + y_offset, color=text_color)

            y_offset += self.settings['y_offset']

    def update_display(self):
        """更新显示"""
        pygame.display.flip()

    # 公共方法：根据深度和温度返回用于显示的温度值
    def get_display_temperature(self, depth, temperature):
        import math
        try:
            # 如果处于“全程糊弄”模式，则始终显示默认温度（带轻微抖动），并标记为伪造
            if getattr(self, 'temp_fooling_mode', 'abnormal_only') == 'always':
                jitter = random.uniform(-self.fake_temp_jitter, self.fake_temp_jitter)
                target_temp = self.default_temperature + jitter
                temp_is_fake = True
            else:
                # 判定是否“查不到”传感器数据：None、NaN，或两个值均为0.0（初始化/未更新）
                depth_missing = depth is None or (
                        isinstance(depth, (int, float)) and isinstance(depth, float) and math.isnan(depth))
                temp_missing = temperature is None or (
                        isinstance(temperature, (int, float)) and isinstance(temperature, float) and math.isnan(
                    temperature))
                both_zero = False
                try:
                    both_zero = float(depth) == 0.0 and float(temperature) == 0.0
                except Exception:
                    # 如果无法转换为浮点数，保持both_zero为False
                    pass

                # 先计算“目标温度值”
                temp_is_fake = False
                if depth_missing or temp_missing or both_zero:
                    jitter = random.uniform(-self.fake_temp_jitter, self.fake_temp_jitter)
                    target_temp = self.default_temperature + jitter
                    temp_is_fake = True
                elif abs(float(depth)) > 3.0 or float(temperature) < 0.0:
                    # 异常判定：深度绝对值大于3米 或 温度小于0℃
                    jitter = random.uniform(-self.fake_temp_jitter, self.fake_temp_jitter)
                    target_temp = self.default_temperature + jitter
                    temp_is_fake = True
                else:
                    target_temp = float(temperature)
                    temp_is_fake = False

            # 应用“变化速度限制”（slew rate limit），将显示温度缓慢逼近目标温度
            now = time.time()
            dt = max(1e-3, now - self._last_temp_time) if hasattr(self,
                                                                  '_last_temp_time') and self._last_temp_time else 0.016
            if self._temp_display_value is None:
                # 首次赋值，直接采用目标值
                self._temp_display_value = target_temp
            else:
                allowed = max(0.0, float(self.temp_slew_rate)) * dt
                delta = target_temp - self._temp_display_value
                if abs(delta) <= allowed:
                    self._temp_display_value = target_temp
                else:
                    self._temp_display_value += allowed if delta > 0 else -allowed
            self._last_temp_time = now

            return float(self._temp_display_value), temp_is_fake
        except Exception:
            # 同样应用缓变
            now = time.time()
            dt = max(1e-3, now - getattr(self, '_last_temp_time', now))
            jitter = random.uniform(-self.fake_temp_jitter, self.fake_temp_jitter)
            fallback = self.default_temperature + jitter
            if getattr(self, '_temp_display_value', None) is None:
                self._temp_display_value = fallback
            else:
                allowed = max(0.0, float(getattr(self, 'temp_slew_rate', 0.1))) * dt
                delta = fallback - self._temp_display_value
                if abs(delta) <= allowed:
                    self._temp_display_value = fallback
                else:
                    self._temp_display_value += allowed if delta > 0 else -allowed
            self._last_temp_time = now
            return float(self._temp_display_value), True

    def cleanup(self):
        """清理资源"""
        pygame.quit()

    @staticmethod
    def open_xbox_debugger():
        """打开Xbox调试器"""
        try:
            # 使用 subprocess.Popen 启动 xbox_debugger.py
            subprocess.Popen(
                ["python", os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "xbox_debugger.py")])
            print("xbox_debugger 启动成功")
        except Exception as e:
            print(f"启动 xbox_debugger 失败: {e}")

    @staticmethod
    def open_controller_visualizer():
        """打开控制器可视化工具"""
        try:
            # 使用 subprocess.Popen 启动 controller_visualizer.py
            subprocess.Popen(["python", os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools",
                                                     "controller_visualizer.py")])
            print("控制器可视化工具启动成功")
        except Exception as e:
            print(f"启动控制器可视化工具失败: {e}")

    @staticmethod
    def open_controller_mapping_editor():
        """打开控制器映射编辑器"""
        try:
            # 使用 subprocess.Popen 启动 controller_mapping_editor.py
            subprocess.Popen(["python", os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools",
                                                     "controller_mapping_editor.py")])
            print("控制器映射编辑器启动成功")
        except Exception as e:
            print(f"启动控制器映射编辑器失败: {e}")

    def deploy_thrust_curves(self, main_controller):
        """部署推力曲线到ROV"""
        try:
            main_controller.deploy_thrust_curves()
            print("推力曲线部署命令已发送")
        except Exception as e:
            print(f"部署推力曲线失败: {e}")

    def toggle_joystick_correction(self, main_controller):
        """切换手柄辅助修正状态"""
        try:
            enabled = main_controller.joystick_controller.toggle_joystick_correction()
            print(f"手柄辅助修正: {'已启用' if enabled else '已禁用'}")
        except Exception as e:
            print(f"切换手柄辅助修正失败: {e}")


class JoystickHandler:
    """手柄处理类，负责处理手柄输入"""

    def __init__(self, joystick_settings):
        """
        初始化手柄处理器
        
        参数:
            joystick_settings: 手柄设置字典
        """
        self.settings = joystick_settings
        self.joystick = None
        self.buttons = []
        self.rumble_states = {}  # 存储不同按钮的震动状态 {button_id: {'start': timestamp, 'duration': seconds}}
        self.any_button_pressed = False  # 标记是否有任何按钮被按下

        # 初始化手柄
        pygame.joystick.init()
        self._init_joystick()
        self._init_buttons()

    def _init_joystick(self):
        """初始化手柄"""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"已连接手柄: {self.joystick.get_name()}")
        else:
            print("未检测到手柄")

    def _init_buttons(self):
        """初始化按钮状态"""
        num_buttons = self.settings['buttons'] + 1
        self.buttons = [
            {
                "new": False, "old": False, "edge": False, "down": False,
                "up": False, "long": False, "short": False, "double": False,
                "down_time": 0.0, "up_time": 0.0
            }
            for _ in range(num_buttons)
        ]

    def update_button_states(self):
        """更新按钮状态"""
        if not self.joystick:
            return

        # 重置按钮按下标志
        self.any_button_pressed = False
        
        num_buttons = self.settings['buttons'] + 1
        for i in range(num_buttons):
            self.buttons[i]["old"] = self.buttons[i]["new"]
            self.buttons[i]["new"] = self.joystick.get_button(i)
            self.buttons[i]["edge"] = self.buttons[i]["new"] ^ self.buttons[i]["old"]
            self.buttons[i]["down"] = self.buttons[i]["edge"] & self.buttons[i]["new"]
            self.buttons[i]["up"] = self.buttons[i]["edge"] & self.buttons[i]["old"]
            self.buttons[i]["long"] = False
            self.buttons[i]["short"] = False
            self.buttons[i]["double"] = False

            # 检查是否有按钮被按下
            if self.buttons[i]["new"]:
                self.any_button_pressed = True

            if self.buttons[i]["down"]:
                self.buttons[i]["down_time"] = 0
            else:
                self.buttons[i]["down_time"] += 1
            if self.buttons[i]["up"]:
                self.buttons[i]["up_time"] = 0
            else:
                self.buttons[i]["up_time"] += 1

            if self.buttons[i]["down_time"] >= self.settings['long'] and self.buttons[i]["new"]:  # 长按
                self.buttons[i]["long"] = True
                self.buttons[i]["down_time"] = 0
            if self.buttons[i]["down_time"] < self.settings['long'] and self.buttons[i]["up"]:
                self.buttons[i]["short"] = True
                if self.buttons[i]["long"]:
                    self.buttons[i]["short"] = False  # 如果是长按则不算短按
            if self.buttons[i]["up_time"] <= self.settings['double'] and self.buttons[i]["down"]:
                self.buttons[i]["double"] = True

    def is_any_button_pressed(self):
        """
        检查是否有任何按钮被按下
        
        返回:
            bool: 如果有任何按钮被按下则返回True，否则返回False
        """
        # 确保按钮状态是最新的
        self.update_button_states()
        return self.any_button_pressed

    def update_rumble_states(self):
        """更新震动状态"""
        if not self.joystick:
            return

        rumble_keys_to_remove = []
        for button_id, state in self.rumble_states.items():
            if time.time() - state['start'] >= state['duration'] / 1000:  # 转换为秒
                # 震动时间结束，停止震动
                self.joystick.rumble(0, 0, 0)
                rumble_keys_to_remove.append(button_id)

        # 清理已完成的震动状态
        for key in rumble_keys_to_remove:
            del self.rumble_states[key]

    def start_rumble(self, button_id, duration=5):
        """
        开始手柄震动
        
        参数:
            button_id: 按钮ID
            duration: 震动持续时间（毫秒）
        """
        if not self.joystick:
            return

        self.rumble_states[button_id] = {'start': time.time(), 'duration': duration}
        self.joystick.rumble(1, 1, 0)  # 立即开始震动，但不阻塞

    def get_axis(self, axis_id):
        """
        获取轴的值
        
        参数:
            axis_id: 轴ID
            
        返回:
            轴的值，如果没有手柄则返回0
        """
        if not self.joystick:
            return 0
        return self.joystick.get_axis(axis_id)

    def get_button(self, button_id):
        """
        获取按钮状态
        
        参数:
            button_id: 按钮ID
            
        返回:
            按钮状态，如果没有手柄则返回False
        """
        if not self.joystick:
            return False
        return self.joystick.get_button(button_id)

    def get_hat(self, hat_id):
        """
        获取方向键状态
        
        参数:
            hat_id: 方向键ID
            
        返回:
            方向键状态，如果没有手柄则返回(0, 0)
        """
        if not self.joystick:
            return (0, 0)
        return self.joystick.get_hat(hat_id)
