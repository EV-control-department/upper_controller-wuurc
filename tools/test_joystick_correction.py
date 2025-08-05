"""
手柄辅助修正测试工具

该工具用于测试手柄辅助修正功能，模拟不同的摇杆输入场景，
并显示修正前后的值，以便评估修正效果。
"""

import os
import sys
import time

import matplotlib.pyplot as plt
import pygame
from matplotlib.animation import FuncAnimation

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入手柄辅助修正模块
from modules.joystick_correction import JoystickCorrection


class JoystickCorrectionTester:
    """手柄辅助修正测试类"""

    def __init__(self):
        """初始化测试器"""
        # 初始化Pygame
        pygame.init()
        pygame.joystick.init()

        # 检查是否有手柄连接
        if pygame.joystick.get_count() == 0:
            print("未检测到手柄，将使用模拟数据进行测试")
            self.joystick = None
            self.use_simulated_data = True
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"已连接手柄: {self.joystick.get_name()}")
            self.use_simulated_data = False

        # 初始化手柄辅助修正
        self.correction = JoystickCorrection({
            "detection_threshold": 0.1,
            "stationary_threshold": 0.05,
            "correction_duration": 0.5,
            "filter_strength": 2.0
        })

        # 启用修正
        self.correction.toggle()

        # 数据存储
        self.raw_data = {
            'x': [], 'y': [], 'z': [], 'yaw': [],
            'time': []
        }
        self.corrected_data = {
            'x': [], 'y': [], 'z': [], 'yaw': [],
            'time': []
        }

        # 设置图表
        self.setup_plot()

    def setup_plot(self):
        """设置实时图表"""
        self.fig, self.axs = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('手柄辅助修正测试', fontsize=16)

        # 左摇杆 (X/Y)
        self.left_stick_raw, = self.axs[0, 0].plot([], [], 'bo-', label='原始')
        self.left_stick_corrected, = self.axs[0, 0].plot([], [], 'ro-', label='修正后')
        self.axs[0, 0].set_xlim(-1.1, 1.1)
        self.axs[0, 0].set_ylim(-1.1, 1.1)
        self.axs[0, 0].set_title('左摇杆 (X/Y)')
        self.axs[0, 0].set_xlabel('X轴')
        self.axs[0, 0].set_ylabel('Y轴')
        self.axs[0, 0].grid(True)
        self.axs[0, 0].legend()

        # 右摇杆 (Z/Yaw)
        self.right_stick_raw, = self.axs[0, 1].plot([], [], 'bo-', label='原始')
        self.right_stick_corrected, = self.axs[0, 1].plot([], [], 'ro-', label='修正后')
        self.axs[0, 1].set_xlim(-1.1, 1.1)
        self.axs[0, 1].set_ylim(-1.1, 1.1)
        self.axs[0, 1].set_title('右摇杆 (Z/Yaw)')
        self.axs[0, 1].set_xlabel('Z轴')
        self.axs[0, 1].set_ylabel('Yaw轴')
        self.axs[0, 1].grid(True)
        self.axs[0, 1].legend()

        # X/Y轴随时间变化
        self.x_time_raw, = self.axs[1, 0].plot([], [], 'b-', label='X原始')
        self.x_time_corrected, = self.axs[1, 0].plot([], [], 'r-', label='X修正后')
        self.y_time_raw, = self.axs[1, 0].plot([], [], 'g-', label='Y原始')
        self.y_time_corrected, = self.axs[1, 0].plot([], [], 'm-', label='Y修正后')
        self.axs[1, 0].set_xlim(0, 10)
        self.axs[1, 0].set_ylim(-1.1, 1.1)
        self.axs[1, 0].set_title('X/Y轴随时间变化')
        self.axs[1, 0].set_xlabel('时间 (秒)')
        self.axs[1, 0].set_ylabel('值')
        self.axs[1, 0].grid(True)
        self.axs[1, 0].legend()

        # Z/Yaw轴随时间变化
        self.z_time_raw, = self.axs[1, 1].plot([], [], 'b-', label='Z原始')
        self.z_time_corrected, = self.axs[1, 1].plot([], [], 'r-', label='Z修正后')
        self.yaw_time_raw, = self.axs[1, 1].plot([], [], 'g-', label='Yaw原始')
        self.yaw_time_corrected, = self.axs[1, 1].plot([], [], 'm-', label='Yaw修正后')
        self.axs[1, 1].set_xlim(0, 10)
        self.axs[1, 1].set_ylim(-1.1, 1.1)
        self.axs[1, 1].set_title('Z/Yaw轴随时间变化')
        self.axs[1, 1].set_xlabel('时间 (秒)')
        self.axs[1, 1].set_ylabel('值')
        self.axs[1, 1].grid(True)
        self.axs[1, 1].legend()

        plt.tight_layout()

    def get_joystick_values(self):
        """获取手柄值"""
        if self.use_simulated_data:
            # 模拟数据 - 快速从静止到某个方向的移动
            t = time.time() % 10  # 10秒循环

            if t < 2:  # 静止
                return 0, 0, 0, 0
            elif t < 4:  # X轴快速移动，带有少量Y轴
                return 0.8, 0.2, 0, 0
            elif t < 6:  # Y轴快速移动，带有少量X轴
                return 0.2, 0.8, 0, 0
            elif t < 8:  # Z轴快速移动，带有少量Yaw轴
                return 0, 0, 0.8, 0.2
            else:  # Yaw轴快速移动，带有少量Z轴
                return 0, 0, 0.2, 0.8
        else:
            # 从实际手柄获取数据
            pygame.event.pump()  # 处理事件队列
            x = self.joystick.get_axis(0)
            y = self.joystick.get_axis(1)
            z = self.joystick.get_axis(3)
            yaw = self.joystick.get_axis(2)
            return x, y, z, yaw

    def update_plot(self, frame):
        """更新图表"""
        # 获取原始值
        x, y, z, yaw = self.get_joystick_values()

        # 应用修正
        corrected_x, corrected_y, corrected_z, corrected_yaw = self.correction.process_axes(x, y, z, yaw)

        # 记录当前时间
        current_time = time.time() - self.start_time

        # 存储数据
        self.raw_data['x'].append(x)
        self.raw_data['y'].append(y)
        self.raw_data['z'].append(z)
        self.raw_data['yaw'].append(yaw)
        self.raw_data['time'].append(current_time)

        self.corrected_data['x'].append(corrected_x)
        self.corrected_data['y'].append(corrected_y)
        self.corrected_data['z'].append(corrected_z)
        self.corrected_data['yaw'].append(corrected_yaw)
        self.corrected_data['time'].append(current_time)

        # 限制数据点数量
        max_points = 100
        if len(self.raw_data['time']) > max_points:
            for key in self.raw_data:
                self.raw_data[key] = self.raw_data[key][-max_points:]
            for key in self.corrected_data:
                self.corrected_data[key] = self.corrected_data[key][-max_points:]

        # 更新左摇杆图表
        self.left_stick_raw.set_data(self.raw_data['x'], self.raw_data['y'])
        self.left_stick_corrected.set_data(self.corrected_data['x'], self.corrected_data['y'])

        # 更新右摇杆图表
        self.right_stick_raw.set_data(self.raw_data['z'], self.raw_data['yaw'])
        self.right_stick_corrected.set_data(self.corrected_data['z'], self.corrected_data['yaw'])

        # 更新X/Y轴时间图表
        self.x_time_raw.set_data(self.raw_data['time'], self.raw_data['x'])
        self.x_time_corrected.set_data(self.corrected_data['time'], self.corrected_data['x'])
        self.y_time_raw.set_data(self.raw_data['time'], self.raw_data['y'])
        self.y_time_corrected.set_data(self.corrected_data['time'], self.corrected_data['y'])

        # 更新Z/Yaw轴时间图表
        self.z_time_raw.set_data(self.raw_data['time'], self.raw_data['z'])
        self.z_time_corrected.set_data(self.corrected_data['time'], self.corrected_data['z'])
        self.yaw_time_raw.set_data(self.raw_data['time'], self.raw_data['yaw'])
        self.yaw_time_corrected.set_data(self.corrected_data['time'], self.corrected_data['yaw'])

        # 调整时间轴范围
        if self.raw_data['time']:
            min_time = max(0, self.raw_data['time'][-1] - 10)
            max_time = self.raw_data['time'][-1] + 0.5
            self.axs[1, 0].set_xlim(min_time, max_time)
            self.axs[1, 1].set_xlim(min_time, max_time)

        # 打印当前值
        print(f"原始值: X={x:.2f}, Y={y:.2f}, Z={z:.2f}, Yaw={yaw:.2f}")
        print(f"修正后: X={corrected_x:.2f}, Y={corrected_y:.2f}, Z={corrected_z:.2f}, Yaw={corrected_yaw:.2f}")
        print("-" * 50)

        return (self.left_stick_raw, self.left_stick_corrected,
                self.right_stick_raw, self.right_stick_corrected,
                self.x_time_raw, self.x_time_corrected,
                self.y_time_raw, self.y_time_corrected,
                self.z_time_raw, self.z_time_corrected,
                self.yaw_time_raw, self.yaw_time_corrected)

    def run(self):
        """运行测试"""
        self.start_time = time.time()

        # 创建动画
        ani = FuncAnimation(self.fig, self.update_plot, blit=True, interval=50)

        # 显示图表
        plt.show()

        # 清理资源
        pygame.quit()


if __name__ == "__main__":
    tester = JoystickCorrectionTester()
    tester.run()
