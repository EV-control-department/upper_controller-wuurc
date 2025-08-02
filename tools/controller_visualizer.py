"""
手柄可视化工具
提供图形化界面显示手柄按钮和轴的编号
"""

import os
import sys

import pygame
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGridLayout, QSplitter
)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.config_manager import ConfigManager


class ControllerButton(QWidget):
    """控制器按钮可视化组件"""

    def __init__(self, button_id, label="", parent=None):
        super().__init__(parent)
        self.button_id = button_id
        self.label = label
        self.pressed = False
        self.setMinimumSize(50, 50)
        self.setToolTip(f"按钮 {button_id}: {label}")

    def set_pressed(self, pressed):
        """设置按钮按下状态"""
        if self.pressed != pressed:
            self.pressed = pressed
            self.update()

    def paintEvent(self, event):
        """绘制按钮"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 绘制按钮
        rect = self.rect().adjusted(5, 5, -5, -5)

        # 按钮背景
        if self.pressed:
            painter.setBrush(QBrush(QColor(255, 100, 100)))
        else:
            painter.setBrush(QBrush(QColor(200, 200, 200)))

        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawEllipse(rect)

        # 绘制按钮ID
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(rect, Qt.AlignCenter, str(self.button_id))

        # 绘制按钮标签
        if self.label:
            label_rect = rect.adjusted(0, rect.height() + 5, 0, 20)
            painter.drawText(label_rect, Qt.AlignCenter, self.label)


class ControllerAxis(QWidget):
    """控制器轴可视化组件"""

    def __init__(self, axis_id, label="", parent=None):
        super().__init__(parent)
        self.axis_id = axis_id
        self.label = label
        self.value = 0.0
        self.setMinimumSize(100, 100)
        self.setToolTip(f"轴 {axis_id}: {label}")

    def set_value(self, value):
        """设置轴的值"""
        if abs(self.value - value) > 0.01:  # 只有当值变化足够大时才更新
            self.value = value
            self.update()

    def paintEvent(self, event):
        """绘制轴"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 绘制轴背景
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(rect)

        # 绘制轴值指示器
        indicator_width = 10
        indicator_height = rect.height() - 10
        indicator_x = rect.center().x() - indicator_width / 2

        # 计算指示器位置（将-1到1的值映射到控件高度）
        normalized_value = 1 - (self.value + 1) / 2  # 从[-1,1]映射到[0,1]
        indicator_y = rect.bottom() - 5 - normalized_value * indicator_height

        # 绘制指示器
        indicator_rect = QRect(int(indicator_x), int(indicator_y), indicator_width, 10)
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawRect(indicator_rect)

        # 绘制轴ID和值
        painter.setPen(QColor(0, 0, 0))
        id_rect = QRect(rect.left(), rect.top(), rect.width(), 20)
        painter.drawText(id_rect, Qt.AlignCenter, f"轴 {self.axis_id}")

        value_rect = QRect(rect.left(), rect.bottom() - 20, rect.width(), 20)
        painter.drawText(value_rect, Qt.AlignCenter, f"{self.value:.2f}")

        # 绘制轴标签
        if self.label:
            label_rect = QRect(rect.left(), rect.bottom() + 5, rect.width(), 20)
            painter.drawText(label_rect, Qt.AlignCenter, self.label)


class ControllerHat(QWidget):
    """控制器帽子开关可视化组件"""

    def __init__(self, hat_id, parent=None):
        super().__init__(parent)
        self.hat_id = hat_id
        self.x_value = 0
        self.y_value = 0
        self.setMinimumSize(100, 100)
        self.setToolTip(f"帽子开关 {hat_id}")

    def set_values(self, x, y):
        """设置帽子开关的值"""
        if self.x_value != x or self.y_value != y:
            self.x_value = x
            self.y_value = y
            self.update()

    def paintEvent(self, event):
        """绘制帽子开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 绘制背景
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawEllipse(rect)

        # 绘制十字
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(rect.center().x(), rect.top() + 10, rect.center().x(), rect.bottom() - 10)
        painter.drawLine(rect.left() + 10, rect.center().y(), rect.right() - 10, rect.center().y())

        # 绘制当前位置
        center_x = rect.center().x()
        center_y = rect.center().y()
        pos_x = center_x + self.x_value * (rect.width() / 2 - 15)
        pos_y = center_y - self.y_value * (rect.height() / 2 - 15)

        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawEllipse(int(pos_x - 10), int(pos_y - 10), 20, 20)

        # 绘制帽子开关ID和值
        painter.setPen(QColor(0, 0, 0))
        id_rect = QRect(rect.left(), rect.bottom() + 5, rect.width(), 20)
        painter.drawText(id_rect, Qt.AlignCenter, f"帽子 {self.hat_id}: ({self.x_value}, {self.y_value})")


class ControllerVisualizer(QMainWindow):
    """控制器可视化主窗口"""

    def __init__(self):
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("ROV控制器可视化工具")
        self.setMinimumSize(800, 600)

        # 初始化pygame
        pygame.init()
        pygame.joystick.init()

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建状态标签
        self.status_label = QLabel("正在检测控制器...")
        font = self.status_label.font()
        font.setPointSize(12)
        self.status_label.setFont(font)
        main_layout.addWidget(self.status_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 创建左侧控制器可视化面板
        self.controller_panel = QWidget()
        controller_layout = QVBoxLayout(self.controller_panel)

        # 创建按钮网格
        buttons_frame = QFrame()
        buttons_frame.setFrameShape(QFrame.StyledPanel)
        buttons_layout = QGridLayout(buttons_frame)

        # 创建按钮可视化组件
        self.buttons = {}
        button_labels = {
            0: "A", 1: "B", 2: "X", 3: "Y",
            4: "LB", 5: "RB", 6: "Back", 7: "Start",
            8: "LS", 9: "RS", 10: "Guide"
        }

        # 按钮布局
        row, col = 0, 0
        for i in range(11):  # 假设最多11个按钮
            button = ControllerButton(i, button_labels.get(i, ""))
            self.buttons[i] = button
            buttons_layout.addWidget(button, row, col)
            col += 1
            if col > 3:  # 每行4个按钮
                col = 0
                row += 1

        controller_layout.addWidget(QLabel("按钮:"))
        controller_layout.addWidget(buttons_frame)

        # 创建轴网格
        axes_frame = QFrame()
        axes_frame.setFrameShape(QFrame.StyledPanel)
        axes_layout = QGridLayout(axes_frame)

        # 创建轴可视化组件
        self.axes = {}
        axis_labels = {
            0: "左摇杆X", 1: "左摇杆Y", 2: "右摇杆X", 3: "右摇杆Y",
            4: "LT", 5: "RT"
        }

        # 轴布局
        row, col = 0, 0
        for i in range(6):  # 假设最多6个轴
            axis = ControllerAxis(i, axis_labels.get(i, ""))
            self.axes[i] = axis
            axes_layout.addWidget(axis, row, col)
            col += 1
            if col > 2:  # 每行3个轴
                col = 0
                row += 1

        controller_layout.addWidget(QLabel("轴:"))
        controller_layout.addWidget(axes_frame)

        # 创建帽子开关
        hats_frame = QFrame()
        hats_frame.setFrameShape(QFrame.StyledPanel)
        hats_layout = QHBoxLayout(hats_frame)

        # 创建帽子开关可视化组件
        self.hats = {}
        for i in range(1):  # 假设只有1个帽子开关
            hat = ControllerHat(i)
            self.hats[i] = hat
            hats_layout.addWidget(hat)

        controller_layout.addWidget(QLabel("帽子开关:"))
        controller_layout.addWidget(hats_frame)

        # 添加到分割器
        splitter.addWidget(self.controller_panel)

        # 创建右侧配置映射面板
        self.mapping_panel = QWidget()
        mapping_layout = QVBoxLayout(self.mapping_panel)

        # 添加配置信息标签
        self.mapping_label = QLabel("控制器映射配置:")
        font = self.mapping_label.font()
        font.setPointSize(12)
        self.mapping_label.setFont(font)
        mapping_layout.addWidget(self.mapping_label)

        # 添加配置详情
        self.mapping_details = QLabel()
        self.mapping_details.setWordWrap(True)
        mapping_layout.addWidget(self.mapping_details)

        # 添加到分割器
        splitter.addWidget(self.mapping_panel)

        # 设置分割器初始大小
        splitter.setSizes([500, 300])

        # 初始化控制器
        self.joystick = None
        self.init_joystick()

        # 创建定时器更新控制器状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller_state)
        self.timer.start(50)  # 每50毫秒更新一次

        # 显示配置映射
        self.update_mapping_display()

    def init_joystick(self):
        """初始化控制器"""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

            # 更新状态标签
            joystick_name = self.joystick.get_name()
            num_axes = self.joystick.get_numaxes()
            num_buttons = self.joystick.get_numbuttons()
            num_hats = self.joystick.get_numhats()

            self.status_label.setText(
                f"已检测到控制器: {joystick_name}\n"
                f"轴数量: {num_axes}, 按钮数量: {num_buttons}, 帽子开关数量: {num_hats}"
            )
        else:
            self.status_label.setText("未检测到控制器！请连接控制器后重启应用程序。")

    def update_controller_state(self):
        """更新控制器状态"""
        if not self.joystick:
            return

        # 更新pygame事件
        pygame.event.pump()

        # 更新按钮状态
        for button_id in self.buttons:
            if button_id < self.joystick.get_numbuttons():
                pressed = self.joystick.get_button(button_id) == 1
                self.buttons[button_id].set_pressed(pressed)

        # 更新轴状态
        for axis_id in self.axes:
            if axis_id < self.joystick.get_numaxes():
                value = self.joystick.get_axis(axis_id)
                self.axes[axis_id].set_value(value)

        # 更新帽子开关状态
        for hat_id in self.hats:
            if hat_id < self.joystick.get_numhats():
                x, y = self.joystick.get_hat(hat_id)
                self.hats[hat_id].set_values(x, y)

    def update_mapping_display(self):
        """更新映射显示"""
        if not self.config_manager:
            return

        # 获取配置中的轴映射
        x_config = self.config_manager.get_axis_config("x")
        y_config = self.config_manager.get_axis_config("y")
        z_config = self.config_manager.get_axis_config("z")
        yaw_config = self.config_manager.get_axis_config("yaw")

        # 获取舵机按钮映射
        servo_config = {
            "close_button": self.config_manager.config["servo"].getint("close_button"),
            "close_trig": self.config_manager.config["servo"].get("close_trig"),
            "open_button": self.config_manager.config["servo"].getint("open_button"),
            "open_trig": self.config_manager.config["servo"].get("open_trig"),
            "mid1_button": self.config_manager.config["servo"].getint("mid1_button"),
            "mid1_trig": self.config_manager.config["servo"].get("mid1_trig"),
            "mid2_button": self.config_manager.config["servo"].getint("mid2_button"),
            "mid2_trig": self.config_manager.config["servo"].get("mid2_trig")
        }

        # 获取模式按钮映射
        speed_mode_button = self.config_manager.config["speed_mode"].getint("button")
        lock_mode_button = self.config_manager.config["lock_mode"].getint("button")
        loop_mode_button = self.config_manager.config["loop_mode"].getint("button")

        # 构建映射文本
        mapping_text = "<b>控制器映射配置:</b><br><br>"

        # 轴映射
        mapping_text += "<b>轴映射:</b><br>"
        mapping_text += f"X轴 (左右): 轴 {x_config['axis']}, 死区: {x_config['deadzone']}, 最大值: {x_config['max']}<br>"
        mapping_text += f"Y轴 (前后): 轴 {y_config['axis']}, 死区: {y_config['deadzone']}, 最大值: {y_config['max']}<br>"
        mapping_text += f"Z轴 (上下): 轴 {z_config['axis']}, 死区: {z_config['deadzone']}, 最大值: {z_config['max']}<br>"
        mapping_text += f"偏航轴 (旋转): 轴 {yaw_config['axis']}, 死区: {yaw_config['deadzone']}, 最大值: {yaw_config['max']}<br><br>"

        # 舵机按钮映射
        mapping_text += "<b>舵机按钮映射:</b><br>"
        mapping_text += f"打开舵机: 按钮 {servo_config['open_button']} ({servo_config['open_trig']})<br>"
        mapping_text += f"关闭舵机: 按钮 {servo_config['close_button']} ({servo_config['close_trig']})<br>"
        mapping_text += f"中间位置1: 按钮 {servo_config['mid1_button']} ({servo_config['mid1_trig']})<br>"
        mapping_text += f"中间位置2: 按钮 {servo_config['mid2_button']} ({servo_config['mid2_trig']})<br><br>"

        # 模式按钮映射
        mapping_text += "<b>模式按钮映射:</b><br>"
        mapping_text += f"速度模式切换: 按钮 {speed_mode_button}<br>"
        mapping_text += f"锁定模式切换: 按钮 {lock_mode_button}<br>"
        mapping_text += f"循环模式切换: 按钮 {loop_mode_button}<br>"

        # 设置映射文本
        self.mapping_details.setText(mapping_text)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ControllerVisualizer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
