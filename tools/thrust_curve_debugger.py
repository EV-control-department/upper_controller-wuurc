"""
推力曲线调试工具
提供图形化界面显示和调整电机推力曲线参数
"""

import json
import os
import sys
import time

import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox, QSplitter,
    QCheckBox, QGridLayout, QSpinBox, QTextEdit, QSlider, QProgressBar,
    QRadioButton, QButtonGroup
)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.config_manager import ConfigManager
from modules.hardware_controller import controller_curve

# 尝试导入网络通信模块
try:
    import socket

    SOCKET_AVAILABLE = True
except ImportError:
    SOCKET_AVAILABLE = False


class CurveVisualizerWidget(QWidget):
    """曲线可视化组件"""

    # 定义信号
    point_dragged = pyqtSignal(str, str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)

        # 曲线数据
        self.curve_data = {}
        self.selected_motor = "m0"
        self.show_original_curve = True
        self.show_modified_curve = True

        # 创建原始曲线数据的副本用于比较
        self.original_curve_data = {}

        # 控制器曲线函数的输入输出数据
        self.controller_inputs = np.linspace(-1, 1, 100)
        self.controller_outputs = np.array([controller_curve(x) for x in self.controller_inputs])

        # 拖拽相关变量
        self.dragging = False
        self.drag_point = None
        self.drag_point_type = None

        # 设置背景色
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(240, 240, 240))
        self.setPalette(palette)

        # 启用鼠标跟踪
        self.setMouseTracking(True)

    def set_curve_data(self, curve_data, motor_id="m0"):
        """设置曲线数据"""
        self.curve_data = curve_data
        self.selected_motor = motor_id

        # 创建原始数据的深拷贝
        self.original_curve_data = json.loads(json.dumps(curve_data))

        self.update()

    def update_motor_selection(self, motor_id):
        """更新选中的电机"""
        self.selected_motor = motor_id
        self.update()

    def toggle_original_curve(self, show):
        """切换显示原始曲线"""
        self.show_original_curve = show
        self.update()

    def toggle_modified_curve(self, show):
        """切换显示修改后的曲线"""
        self.show_modified_curve = show
        self.update()

    def paintEvent(self, event):
        """绘制曲线"""
        if not self.curve_data or self.selected_motor not in self.curve_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 绘制坐标系
        self.draw_coordinate_system(painter)

        # 绘制控制器曲线
        self.draw_controller_curve(painter)

        # 绘制原始曲线
        if self.show_original_curve and self.original_curve_data and self.selected_motor in self.original_curve_data:
            self.draw_motor_curve(painter, self.original_curve_data[self.selected_motor], QColor(100, 100, 255, 180), 2)

        # 绘制修改后的曲线
        if self.show_modified_curve:
            self.draw_motor_curve(painter, self.curve_data[self.selected_motor], QColor(255, 100, 100), 2)

        # 绘制图例
        self.draw_legend(painter)

    def draw_coordinate_system(self, painter):
        """绘制坐标系"""
        width = self.width()
        height = self.height()
        margin = 50

        # 坐标轴
        painter.setPen(QPen(QColor(0, 0, 0), 2))

        # X轴
        painter.drawLine(margin, height - margin, width - margin, height - margin)

        # Y轴
        painter.drawLine(margin, height - margin, margin, margin)

        # X轴刻度
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        x_ticks = [-1.0, -0.5, 0.0, 0.5, 1.0]
        for tick in x_ticks:
            x = margin + (tick + 1) / 2 * (width - 2 * margin)
            painter.drawLine(int(x), height - margin, int(x), height - margin + 5)
            painter.drawText(int(x) - 15, height - margin + 20, f"{tick:.1f}")

        # Y轴刻度
        y_ticks = [-1.0, -0.5, 0.0, 0.5, 1.0]
        for tick in y_ticks:
            y = height - margin - (tick + 1) / 2 * (height - 2 * margin)
            painter.drawLine(margin - 5, int(y), margin, int(y))
            painter.drawText(margin - 40, int(y) + 5, f"{tick:.1f}")

        # 坐标轴标签
        painter.drawText(width // 2, height - 10, "输入值")
        painter.save()
        painter.translate(10, height // 2)
        painter.rotate(-90)
        painter.drawText(0, 0, "输出值")
        painter.restore()

        # 绘制网格
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        for tick in x_ticks:
            x = margin + (tick + 1) / 2 * (width - 2 * margin)
            painter.drawLine(int(x), margin, int(x), height - margin)

        for tick in y_ticks:
            y = height - margin - (tick + 1) / 2 * (height - 2 * margin)
            painter.drawLine(margin, int(y), width - margin, int(y))

    def draw_controller_curve(self, painter):
        """绘制控制器曲线"""
        width = self.width()
        height = self.height()
        margin = 50

        # 绘制控制器曲线
        painter.setPen(QPen(QColor(0, 150, 0, 180), 2))

        path = QPainterPath()
        first_point = True

        for i, (input_val, output_val) in enumerate(zip(self.controller_inputs, self.controller_outputs)):
            # 将[-1,1]范围映射到绘图区域
            x = margin + (input_val + 1) / 2 * (width - 2 * margin)
            y = height - margin - (output_val + 1) / 2 * (height - 2 * margin)

            if first_point:
                path.moveTo(x, y)
                first_point = False
            else:
                path.lineTo(x, y)

        painter.drawPath(path)

    def draw_motor_curve(self, painter, motor_data, color, width=2):
        """绘制电机曲线"""
        if not motor_data:
            return

        w = self.width()
        h = self.height()
        margin = 50

        # 提取曲线参数
        np_mid = motor_data.get("np_mid", 0)
        np_ini = motor_data.get("np_ini", 0)
        pp_ini = motor_data.get("pp_ini", 0)
        pp_mid = motor_data.get("pp_mid", 0)
        nt_end = motor_data.get("nt_end", 0)
        nt_mid = motor_data.get("nt_mid", 0)
        pt_mid = motor_data.get("pt_mid", 0)
        pt_end = motor_data.get("pt_end", 0)

        # 计算中点值
        mid_point = (np_mid + pp_mid) / 2

        # 归一化参数到[-1,1]范围
        # 位置参数归一化
        pos_range = max(abs(np_mid - mid_point), abs(pp_mid - mid_point)) * 2
        if pos_range == 0:
            pos_range = 1  # 防止除以零

        norm_np_mid = (np_mid - mid_point) / pos_range
        norm_np_ini = (np_ini - mid_point) / pos_range
        norm_pp_ini = (pp_ini - mid_point) / pos_range
        norm_pp_mid = (pp_mid - mid_point) / pos_range

        # 推力参数归一化
        thrust_range = max(abs(nt_end), abs(pt_end)) * 2
        if thrust_range == 0:
            thrust_range = 1  # 防止除以零

        norm_nt_end = nt_end / thrust_range
        norm_nt_mid = nt_mid / thrust_range
        norm_pt_mid = pt_mid / thrust_range
        norm_pt_end = pt_end / thrust_range

        # 绘制曲线
        painter.setPen(QPen(color, width))

        # 创建路径
        path = QPainterPath()

        # 负向部分
        x1 = margin + ((-1) + 1) / 2 * (w - 2 * margin)  # 输入 -1
        y1 = h - margin - ((norm_nt_end) + 1) / 2 * (h - 2 * margin)  # 输出 norm_nt_end

        x2 = margin + ((-0.5) + 1) / 2 * (w - 2 * margin)  # 输入 -0.5
        y2 = h - margin - ((norm_nt_mid) + 1) / 2 * (h - 2 * margin)  # 输出 norm_nt_mid

        # 中点
        x3 = margin + ((0) + 1) / 2 * (w - 2 * margin)  # 输入 0
        y3 = h - margin - ((0) + 1) / 2 * (h - 2 * margin)  # 输出 0

        # 正向部分
        x4 = margin + ((0.5) + 1) / 2 * (w - 2 * margin)  # 输入 0.5
        y4 = h - margin - ((norm_pt_mid) + 1) / 2 * (h - 2 * margin)  # 输出 norm_pt_mid

        x5 = margin + ((1) + 1) / 2 * (w - 2 * margin)  # 输入 1
        y5 = h - margin - ((norm_pt_end) + 1) / 2 * (h - 2 * margin)  # 输出 norm_pt_end

        # 绘制曲线
        path.moveTo(x1, y1)
        path.cubicTo(x2, y2, x2, y2, x3, y3)
        path.cubicTo(x4, y4, x4, y4, x5, y5)

        painter.drawPath(path)

        # 绘制控制点
        point_radius = 4
        if self.show_modified_curve and motor_data == self.curve_data.get(self.selected_motor, {}):
            # 如果是当前选中的电机的修改后曲线，绘制可拖拽的控制点
            # 负向终点 (nt_end)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x1) - point_radius, int(y1) - point_radius, point_radius * 2, point_radius * 2)

            # 负向中点 (nt_mid)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x2) - point_radius, int(y2) - point_radius, point_radius * 2, point_radius * 2)

            # 中点 (固定点)
            painter.setBrush(QBrush(QColor(100, 100, 100)))
            painter.drawEllipse(int(x3) - point_radius, int(y3) - point_radius, point_radius * 2, point_radius * 2)

            # 正向中点 (pt_mid)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x4) - point_radius, int(y4) - point_radius, point_radius * 2, point_radius * 2)

            # 正向终点 (pt_end)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x5) - point_radius, int(y5) - point_radius, point_radius * 2, point_radius * 2)

            # 如果正在拖拽，绘制高亮的控制点
            if self.dragging and self.drag_point is not None:
                painter.setBrush(QBrush(QColor(255, 255, 0)))
                if self.drag_point_type == "nt_end":
                    painter.drawEllipse(int(x1) - point_radius - 2, int(y1) - point_radius - 2, (point_radius + 2) * 2,
                                        (point_radius + 2) * 2)
                elif self.drag_point_type == "nt_mid":
                    painter.drawEllipse(int(x2) - point_radius - 2, int(y2) - point_radius - 2, (point_radius + 2) * 2,
                                        (point_radius + 2) * 2)
                elif self.drag_point_type == "pt_mid":
                    painter.drawEllipse(int(x4) - point_radius - 2, int(y4) - point_radius - 2, (point_radius + 2) * 2,
                                        (point_radius + 2) * 2)
                elif self.drag_point_type == "pt_end":
                    painter.drawEllipse(int(x5) - point_radius - 2, int(y5) - point_radius - 2, (point_radius + 2) * 2,
                                        (point_radius + 2) * 2)
        else:
            # 如果是原始曲线或其他电机的曲线，绘制普通控制点
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x1) - point_radius, int(y1) - point_radius, point_radius * 2, point_radius * 2)
            painter.drawEllipse(int(x2) - point_radius, int(y2) - point_radius, point_radius * 2, point_radius * 2)
            painter.drawEllipse(int(x3) - point_radius, int(y3) - point_radius, point_radius * 2, point_radius * 2)
            painter.drawEllipse(int(x4) - point_radius, int(y4) - point_radius, point_radius * 2, point_radius * 2)
            painter.drawEllipse(int(x5) - point_radius, int(y5) - point_radius, point_radius * 2, point_radius * 2)

        # 保存控制点位置，用于鼠标事件处理
        if motor_data == self.curve_data.get(self.selected_motor, {}):
            self.control_points = {
                "nt_end": (x1, y1),
                "nt_mid": (x2, y2),
                "center": (x3, y3),
                "pt_mid": (x4, y4),
                "pt_end": (x5, y5)
            }
            self.control_values = {
                "nt_end": nt_end,
                "nt_mid": nt_mid,
                "pt_mid": pt_mid,
                "pt_end": pt_end
            }
            self.normalization = {
                "thrust_range": thrust_range,
                "mid_point": mid_point
            }

    def draw_legend(self, painter):
        """绘制图例"""
        width = self.width()
        height = self.height()

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 图例位置
        legend_x = width - 200
        legend_y = 20
        legend_width = 180
        legend_height = 100  # 增加高度以容纳拖拽提示

        # 绘制图例背景
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRect(legend_x, legend_y, legend_width, legend_height)

        # 绘制图例项
        if self.show_original_curve:
            painter.setPen(QPen(QColor(100, 100, 255), 2))
            painter.drawLine(legend_x + 10, legend_y + 20, legend_x + 40, legend_y + 20)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(legend_x + 50, legend_y + 25, "原始曲线")

        if self.show_modified_curve:
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(legend_x + 10, legend_y + 40, legend_x + 40, legend_y + 40)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(legend_x + 50, legend_y + 45, "修改后曲线")

        painter.setPen(QPen(QColor(0, 150, 0), 2))
        painter.drawLine(legend_x + 10, legend_y + 60, legend_x + 40, legend_y + 60)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(legend_x + 50, legend_y + 65, "控制器曲线")

        # 添加拖拽提示
        painter.setPen(QColor(100, 100, 100))
        painter.drawText(legend_x + 10, legend_y + 85, "提示: 拖拽控制点调整曲线")

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self.curve_data or self.selected_motor not in self.curve_data:
            return

        if event.button() == Qt.LeftButton and hasattr(self, 'control_points'):
            # 检查是否点击了控制点
            pos = event.pos()
            for point_type, (x, y) in self.control_points.items():
                # 跳过中心点，它是固定的
                if point_type == "center":
                    continue

                # 检查点击位置是否在控制点附近
                if abs(pos.x() - x) <= 10 and abs(pos.y() - y) <= 10:
                    self.dragging = True
                    self.drag_point = (x, y)
                    self.drag_point_type = point_type
                    self.setCursor(Qt.ClosedHandCursor)
                    self.update()
                    break

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.curve_data or self.selected_motor not in self.curve_data:
            return

        # 如果鼠标悬停在控制点上，改变光标
        if not self.dragging and hasattr(self, 'control_points'):
            pos = event.pos()
            hover_on_point = False

            for point_type, (x, y) in self.control_points.items():
                if point_type != "center" and abs(pos.x() - x) <= 10 and abs(pos.y() - y) <= 10:
                    self.setCursor(Qt.OpenHandCursor)
                    hover_on_point = True
                    break

            if not hover_on_point:
                self.setCursor(Qt.ArrowCursor)

        # 处理拖拽
        if self.dragging and self.drag_point_type:
            pos = event.pos()
            h = self.height()
            margin = 50

            # 限制Y坐标在绘图区域内
            y = max(margin, min(pos.y(), h - margin))

            # 计算归一化值 (从屏幕坐标转换回参数值)
            norm_value = 2 * (h - margin - y) / (h - 2 * margin) - 1

            # 根据拖拽的点类型更新相应的参数
            if self.drag_point_type in ["nt_end", "nt_mid", "pt_mid", "pt_end"]:
                # 从归一化值转换回实际参数值
                thrust_range = self.normalization["thrust_range"]
                actual_value = norm_value * thrust_range / 2

                # 发送信号通知参数变更
                self.point_dragged.emit(self.selected_motor, self.drag_point_type, actual_value)

                # 更新拖拽点位置
                self.drag_point = (self.drag_point[0], y)
                self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.drag_point = None
            self.drag_point_type = None
            self.setCursor(Qt.ArrowCursor)
            self.update()


class MotorTestPanel(QWidget):
    """电机测试面板组件"""

    # 定义信号
    test_command_sent = pyqtSignal(str, float, int)  # 电机ID, 速度值, 持续时间
    test_command_stopped = pyqtSignal(str)  # 电机ID
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 电机数据
        self.motor_id = "m0"
        self.test_in_progress = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer_timeout)

        # 创建布局
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建电机测试组
        test_group = QGroupBox("电机测试")
        test_layout = QFormLayout(test_group)

        # 创建速度控制滑块
        slider_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(-100, 100)
        self.speed_slider.setValue(0)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)

        self.speed_label = QLabel("0%")
        self.speed_label.setMinimumWidth(50)
        self.speed_label.setAlignment(Qt.AlignCenter)

        slider_layout.addWidget(self.speed_slider)
        slider_layout.addWidget(self.speed_label)

        test_layout.addRow("速度:", slider_layout)

        # 创建持续时间控制
        duration_layout = QHBoxLayout()
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" 秒")

        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()

        test_layout.addRow("持续时间:", duration_layout)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v%")
        test_layout.addRow("进度:", self.progress_bar)

        # 创建按钮
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("开始测试")
        self.start_button.clicked.connect(self.start_test)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止测试")
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)

        test_layout.addRow("", buttons_layout)

        layout.addWidget(test_group)

        # 创建方向选择组
        direction_group = QGroupBox("测试方向")
        direction_layout = QHBoxLayout(direction_group)

        self.direction_group = QButtonGroup(self)

        self.forward_radio = QRadioButton("正向")
        self.forward_radio.setChecked(True)
        self.direction_group.addButton(self.forward_radio)
        direction_layout.addWidget(self.forward_radio)

        self.backward_radio = QRadioButton("反向")
        self.direction_group.addButton(self.backward_radio)
        direction_layout.addWidget(self.backward_radio)

        layout.addWidget(direction_group)

        # 添加弹性空间
        layout.addStretch()

    def set_motor_id(self, motor_id):
        """设置电机ID"""
        self.motor_id = motor_id

        # 如果正在测试，停止测试
        if self.test_in_progress:
            self.stop_test()

    def on_speed_changed(self, value):
        """处理速度滑块变化"""
        self.speed_label.setText(f"{value}%")

    def start_test(self):
        """开始测试"""
        if self.test_in_progress:
            return

        # 获取测试参数
        speed = self.speed_slider.value() / 100.0  # 转换为-1.0到1.0范围
        if self.backward_radio.isChecked():
            speed = -abs(speed)  # 确保为负值
        elif self.forward_radio.isChecked():
            speed = abs(speed)  # 确保为正值

        duration = self.duration_spin.value()

        # 更新UI状态
        self.test_in_progress = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.speed_slider.setEnabled(False)
        self.duration_spin.setEnabled(False)
        self.forward_radio.setEnabled(False)
        self.backward_radio.setEnabled(False)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 发送测试命令信号
        self.test_command_sent.emit(self.motor_id, speed, duration)

        # 记录日志
        self.log_message.emit(f"开始测试电机 {self.motor_id}，速度: {speed:.2f}，持续时间: {duration}秒")

        # 启动定时器
        self.timer_start_time = 0
        self.timer_duration = duration * 1000  # 转换为毫秒
        self.timer.start(100)  # 每100毫秒更新一次

    def stop_test(self):
        """停止测试"""
        if not self.test_in_progress:
            return

        # 停止定时器
        self.timer.stop()

        # 更新UI状态
        self.test_in_progress = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.speed_slider.setEnabled(True)
        self.duration_spin.setEnabled(True)
        self.forward_radio.setEnabled(True)
        self.backward_radio.setEnabled(True)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 发送停止命令信号
        self.test_command_stopped.emit(self.motor_id)

        # 记录日志
        self.log_message.emit(f"停止测试电机 {self.motor_id}")

    def on_timer_timeout(self):
        """定时器超时处理"""
        # 更新计时器
        self.timer_start_time += 100

        # 计算进度百分比
        progress = min(100, int(self.timer_start_time / self.timer_duration * 100))
        self.progress_bar.setValue(progress)

        # 检查是否完成
        if self.timer_start_time >= self.timer_duration:
            self.stop_test()


class CombinedMotorTestPanel(QWidget):
    """组合电机测试面板组件，用于同时测试多个电机"""

    # 定义信号
    test_command_sent = pyqtSignal(dict, int)  # 电机速度字典, 持续时间
    test_command_stopped = pyqtSignal()  # 停止所有电机
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 测试状态
        self.test_in_progress = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer_timeout)

        # 创建布局
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建组合测试组
        test_group = QGroupBox("组合电机测试")
        test_layout = QFormLayout(test_group)

        # 创建X轴控制
        x_layout = QHBoxLayout()
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.setRange(-100, 100)
        self.x_slider.setValue(0)
        self.x_slider.setTickPosition(QSlider.TicksBelow)
        self.x_slider.setTickInterval(10)
        self.x_slider.valueChanged.connect(lambda v: self.on_value_changed("x", v))

        self.x_label = QLabel("0.00")
        self.x_label.setMinimumWidth(50)
        self.x_label.setAlignment(Qt.AlignCenter)

        x_layout.addWidget(self.x_slider)
        x_layout.addWidget(self.x_label)

        test_layout.addRow("X轴 (左右):", x_layout)

        # 创建Y轴控制
        y_layout = QHBoxLayout()
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setRange(-100, 100)
        self.y_slider.setValue(0)
        self.y_slider.setTickPosition(QSlider.TicksBelow)
        self.y_slider.setTickInterval(10)
        self.y_slider.valueChanged.connect(lambda v: self.on_value_changed("y", v))

        self.y_label = QLabel("0.00")
        self.y_label.setMinimumWidth(50)
        self.y_label.setAlignment(Qt.AlignCenter)

        y_layout.addWidget(self.y_slider)
        y_layout.addWidget(self.y_label)

        test_layout.addRow("Y轴 (前后):", y_layout)

        # 创建Z轴控制
        z_layout = QHBoxLayout()
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(-100, 100)
        self.z_slider.setValue(0)
        self.z_slider.setTickPosition(QSlider.TicksBelow)
        self.z_slider.setTickInterval(10)
        self.z_slider.valueChanged.connect(lambda v: self.on_value_changed("z", v))

        self.z_label = QLabel("0.00")
        self.z_label.setMinimumWidth(50)
        self.z_label.setAlignment(Qt.AlignCenter)

        z_layout.addWidget(self.z_slider)
        z_layout.addWidget(self.z_label)

        test_layout.addRow("Z轴 (上下):", z_layout)

        # 创建持续时间控制
        duration_layout = QHBoxLayout()
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" 秒")

        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()

        test_layout.addRow("持续时间:", duration_layout)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v%")
        test_layout.addRow("进度:", self.progress_bar)

        # 创建按钮
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("开始组合测试")
        self.start_button.clicked.connect(self.start_test)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止测试")
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)

        test_layout.addRow("", buttons_layout)

        layout.addWidget(test_group)

        # 添加当前值显示
        values_group = QGroupBox("当前值")
        values_layout = QGridLayout(values_group)

        # X, Y, Z 当前值
        self.x_value = 0.0
        self.y_value = 0.0
        self.z_value = 0.0

        values_layout.addWidget(QLabel("X:"), 0, 0)
        values_layout.addWidget(QLabel("Y:"), 1, 0)
        values_layout.addWidget(QLabel("Z:"), 2, 0)

        self.x_value_label = QLabel("0.00")
        self.y_value_label = QLabel("0.00")
        self.z_value_label = QLabel("0.00")

        values_layout.addWidget(self.x_value_label, 0, 1)
        values_layout.addWidget(self.y_value_label, 1, 1)
        values_layout.addWidget(self.z_value_label, 2, 1)

        layout.addWidget(values_group)

        # 添加弹性空间
        layout.addStretch()

    def on_value_changed(self, axis, value):
        """处理轴值变化"""
        # 转换为-1.0到1.0范围
        normalized_value = value / 100.0

        # 更新标签
        if axis == "x":
            self.x_value = normalized_value
            self.x_label.setText(f"{normalized_value:.2f}")
            self.x_value_label.setText(f"{normalized_value:.2f}")
        elif axis == "y":
            self.y_value = normalized_value
            self.y_label.setText(f"{normalized_value:.2f}")
            self.y_value_label.setText(f"{normalized_value:.2f}")
        elif axis == "z":
            self.z_value = normalized_value
            self.z_label.setText(f"{normalized_value:.2f}")
            self.z_value_label.setText(f"{normalized_value:.2f}")

    def start_test(self):
        """开始组合测试"""
        if self.test_in_progress:
            return

        # 获取测试参数
        duration = self.duration_spin.value()

        # 创建电机速度字典
        motor_speeds = {
            "x": self.x_value,
            "y": self.y_value,
            "z": self.z_value
        }

        # 更新UI状态
        self.test_in_progress = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.x_slider.setEnabled(False)
        self.y_slider.setEnabled(False)
        self.z_slider.setEnabled(False)
        self.duration_spin.setEnabled(False)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 发送测试命令信号
        self.test_command_sent.emit(motor_speeds, duration)

        # 记录日志
        self.log_message.emit(
            f"开始组合测试，X: {self.x_value:.2f}, Y: {self.y_value:.2f}, Z: {self.z_value:.2f}，持续时间: {duration}秒")

        # 启动定时器
        self.timer_start_time = 0
        self.timer_duration = duration * 1000  # 转换为毫秒
        self.timer.start(100)  # 每100毫秒更新一次

    def stop_test(self):
        """停止测试"""
        if not self.test_in_progress:
            return

        # 停止定时器
        self.timer.stop()

        # 更新UI状态
        self.test_in_progress = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.x_slider.setEnabled(True)
        self.y_slider.setEnabled(True)
        self.z_slider.setEnabled(True)
        self.duration_spin.setEnabled(True)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 发送停止命令信号
        self.test_command_stopped.emit()

        # 记录日志
        self.log_message.emit("停止组合测试")

    def on_timer_timeout(self):
        """定时器超时处理"""
        # 更新计时器
        self.timer_start_time += 100

        # 计算进度百分比
        progress = min(100, int(self.timer_start_time / self.timer_duration * 100))
        self.progress_bar.setValue(progress)

        # 检查是否完成
        if self.timer_start_time >= self.timer_duration:
            self.stop_test()


class DebugInfoPanel(QWidget):
    """调试信息面板组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建布局
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建日志显示区域
        log_group = QGroupBox("调试信息")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_text.setStyleSheet("font-family: Consolas, Courier New, monospace; font-size: 10pt;")
        log_layout.addWidget(self.log_text)

        # 创建按钮
        buttons_layout = QHBoxLayout()

        self.clear_button = QPushButton("清除日志")
        self.clear_button.clicked.connect(self.clear_log)
        buttons_layout.addWidget(self.clear_button)

        self.save_button = QPushButton("保存日志")
        self.save_button.clicked.connect(self.save_log)
        buttons_layout.addWidget(self.save_button)

        log_layout.addLayout(buttons_layout)

        layout.addWidget(log_group)

    def add_log(self, message):
        """添加日志消息"""
        # 获取当前时间
        timestamp = time.strftime("%H:%M:%S", time.localtime())

        # 添加带时间戳的消息
        self.log_text.append(f"[{timestamp}] {message}")

        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()

    def save_log(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志文件", "", "文本文件 (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "保存成功", f"日志已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存日志失败: {str(e)}")


class MotorCurveEditor(QWidget):
    """电机曲线编辑组件"""

    # 定义信号
    curve_updated = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 电机数据
        self.motor_id = "m0"
        self.motor_data = {}

        # 创建布局
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建位置参数组
        position_group = QGroupBox("位置参数")
        position_layout = QFormLayout(position_group)

        # 创建位置参数控件
        self.np_mid_spin = QDoubleSpinBox()
        self.np_mid_spin.setRange(0, 10000)
        self.np_mid_spin.setDecimals(2)
        self.np_mid_spin.setSingleStep(10)
        self.np_mid_spin.valueChanged.connect(self.update_curve)
        position_layout.addRow("负向中点 (np_mid):", self.np_mid_spin)

        self.np_ini_spin = QDoubleSpinBox()
        self.np_ini_spin.setRange(0, 10000)
        self.np_ini_spin.setDecimals(2)
        self.np_ini_spin.setSingleStep(10)
        self.np_ini_spin.valueChanged.connect(self.update_curve)
        position_layout.addRow("负向初始点 (np_ini):", self.np_ini_spin)

        self.pp_ini_spin = QDoubleSpinBox()
        self.pp_ini_spin.setRange(0, 10000)
        self.pp_ini_spin.setDecimals(2)
        self.pp_ini_spin.setSingleStep(10)
        self.pp_ini_spin.valueChanged.connect(self.update_curve)
        position_layout.addRow("正向初始点 (pp_ini):", self.pp_ini_spin)

        self.pp_mid_spin = QDoubleSpinBox()
        self.pp_mid_spin.setRange(0, 10000)
        self.pp_mid_spin.setDecimals(2)
        self.pp_mid_spin.setSingleStep(10)
        self.pp_mid_spin.valueChanged.connect(self.update_curve)
        position_layout.addRow("正向中点 (pp_mid):", self.pp_mid_spin)

        layout.addWidget(position_group)

        # 创建推力参数组
        thrust_group = QGroupBox("推力参数")
        thrust_layout = QFormLayout(thrust_group)

        # 创建推力参数控件
        self.nt_end_spin = QDoubleSpinBox()
        self.nt_end_spin.setRange(-10000, 10000)
        self.nt_end_spin.setDecimals(2)
        self.nt_end_spin.setSingleStep(10)
        self.nt_end_spin.valueChanged.connect(self.update_curve)
        thrust_layout.addRow("负向终点 (nt_end):", self.nt_end_spin)

        self.nt_mid_spin = QDoubleSpinBox()
        self.nt_mid_spin.setRange(-10000, 10000)
        self.nt_mid_spin.setDecimals(2)
        self.nt_mid_spin.setSingleStep(10)
        self.nt_mid_spin.valueChanged.connect(self.update_curve)
        thrust_layout.addRow("负向中点 (nt_mid):", self.nt_mid_spin)

        self.pt_mid_spin = QDoubleSpinBox()
        self.pt_mid_spin.setRange(-10000, 10000)
        self.pt_mid_spin.setDecimals(2)
        self.pt_mid_spin.setSingleStep(10)
        self.pt_mid_spin.valueChanged.connect(self.update_curve)
        thrust_layout.addRow("正向中点 (pt_mid):", self.pt_mid_spin)

        self.pt_end_spin = QDoubleSpinBox()
        self.pt_end_spin.setRange(-10000, 10000)
        self.pt_end_spin.setDecimals(2)
        self.pt_end_spin.setSingleStep(10)
        self.pt_end_spin.valueChanged.connect(self.update_curve)
        thrust_layout.addRow("正向终点 (pt_end):", self.pt_end_spin)

        layout.addWidget(thrust_group)

        # 创建按钮
        buttons_layout = QHBoxLayout()

        self.reset_button = QPushButton("重置参数")
        self.reset_button.clicked.connect(self.reset_parameters)
        buttons_layout.addWidget(self.reset_button)

        self.apply_all_button = QPushButton("应用到所有电机")
        self.apply_all_button.clicked.connect(self.apply_to_all_motors)
        buttons_layout.addWidget(self.apply_all_button)

        layout.addLayout(buttons_layout)

        # 添加弹性空间
        layout.addStretch()

    def set_motor_data(self, motor_id, motor_data, all_motors_data):
        """设置电机数据"""
        self.motor_id = motor_id
        self.motor_data = motor_data
        self.all_motors_data = all_motors_data

        # 更新UI控件
        self.update_ui_from_data()

    def update_ui_from_data(self):
        """从数据更新UI"""
        if not self.motor_data:
            return

        # 阻止信号触发
        self.np_mid_spin.blockSignals(True)
        self.np_ini_spin.blockSignals(True)
        self.pp_ini_spin.blockSignals(True)
        self.pp_mid_spin.blockSignals(True)
        self.nt_end_spin.blockSignals(True)
        self.nt_mid_spin.blockSignals(True)
        self.pt_mid_spin.blockSignals(True)
        self.pt_end_spin.blockSignals(True)

        # 设置位置参数
        self.np_mid_spin.setValue(self.motor_data.get("np_mid", 0))
        self.np_ini_spin.setValue(self.motor_data.get("np_ini", 0))
        self.pp_ini_spin.setValue(self.motor_data.get("pp_ini", 0))
        self.pp_mid_spin.setValue(self.motor_data.get("pp_mid", 0))

        # 设置推力参数
        self.nt_end_spin.setValue(self.motor_data.get("nt_end", 0))
        self.nt_mid_spin.setValue(self.motor_data.get("nt_mid", 0))
        self.pt_mid_spin.setValue(self.motor_data.get("pt_mid", 0))
        self.pt_end_spin.setValue(self.motor_data.get("pt_end", 0))

        # 恢复信号
        self.np_mid_spin.blockSignals(False)
        self.np_ini_spin.blockSignals(False)
        self.pp_ini_spin.blockSignals(False)
        self.pp_mid_spin.blockSignals(False)
        self.nt_end_spin.blockSignals(False)
        self.nt_mid_spin.blockSignals(False)
        self.pt_mid_spin.blockSignals(False)
        self.pt_end_spin.blockSignals(False)

    def update_curve(self):
        """更新曲线数据"""
        if not self.motor_data:
            return

        # 更新电机数据
        self.motor_data["np_mid"] = self.np_mid_spin.value()
        self.motor_data["np_ini"] = self.np_ini_spin.value()
        self.motor_data["pp_ini"] = self.pp_ini_spin.value()
        self.motor_data["pp_mid"] = self.pp_mid_spin.value()
        self.motor_data["nt_end"] = self.nt_end_spin.value()
        self.motor_data["nt_mid"] = self.nt_mid_spin.value()
        self.motor_data["pt_mid"] = self.pt_mid_spin.value()
        self.motor_data["pt_end"] = self.pt_end_spin.value()

        # 发送信号
        self.curve_updated.emit(self.motor_id, self.motor_data)

    def reset_parameters(self):
        """重置参数"""
        if not self.motor_data:
            return

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认重置",
            f"确定要重置电机 {self.motor_id} 的参数吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 重置为默认值
            default_values = {
                "num": int(self.motor_id[1:]),
                "np_mid": 2717.21,
                "np_ini": 2921.03,
                "pp_ini": 3066.62,
                "pp_mid": 3212.21,
                "nt_end": -931.92,
                "nt_mid": -137.17,
                "pt_mid": 165.37,
                "pt_end": 1329.89
            }

            # 更新数据
            for key, value in default_values.items():
                self.motor_data[key] = value

            # 更新UI
            self.update_ui_from_data()

            # 发送信号
            self.curve_updated.emit(self.motor_id, self.motor_data)

    def apply_to_all_motors(self):
        """应用参数到所有电机"""
        if not self.motor_data or not self.all_motors_data:
            return

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认应用",
            f"确定要将电机 {self.motor_id} 的参数应用到所有电机吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 获取当前电机的参数
            params = {
                "np_mid": self.motor_data["np_mid"],
                "np_ini": self.motor_data["np_ini"],
                "pp_ini": self.motor_data["pp_ini"],
                "pp_mid": self.motor_data["pp_mid"],
                "nt_end": self.motor_data["nt_end"],
                "nt_mid": self.motor_data["nt_mid"],
                "pt_mid": self.motor_data["pt_mid"],
                "pt_end": self.motor_data["pt_end"]
            }

            # 应用到所有电机
            for motor_id, motor_data in self.all_motors_data.items():
                if motor_id != self.motor_id:
                    # 保留电机编号
                    motor_num = motor_data["num"]

                    # 更新参数
                    for key, value in params.items():
                        motor_data[key] = value

                    # 确保电机编号不变
                    motor_data["num"] = motor_num

                    # 发送信号
                    self.curve_updated.emit(motor_id, motor_data)


class ThrustCurveDebugger(QMainWindow):
    """推力曲线调试工具主窗口"""

    def __init__(self):
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("ROV推力曲线调试工具")
        self.setMinimumSize(1000, 700)

        # 加载曲线数据
        self.curve_data = {}
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config",
                                        "curve.json")
        self.load_curve_data()

        # 初始化网络通信变量
        self.udp_socket = None
        self.remote_addr = None
        self.remote_port = 8888  # 默认端口

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()

        # 创建电机选择下拉框
        self.motor_combo = QComboBox()
        self.motor_combo.addItems(["m0", "m1", "m2", "m3", "m4", "m5"])
        self.motor_combo.currentTextChanged.connect(self.on_motor_selected)
        toolbar_layout.addWidget(QLabel("选择电机:"))
        toolbar_layout.addWidget(self.motor_combo)

        # 创建显示选项
        self.show_original_check = QCheckBox("显示原始曲线")
        self.show_original_check.setChecked(True)
        self.show_original_check.stateChanged.connect(self.on_show_original_changed)
        toolbar_layout.addWidget(self.show_original_check)

        self.show_modified_check = QCheckBox("显示修改后曲线")
        self.show_modified_check.setChecked(True)
        self.show_modified_check.stateChanged.connect(self.on_show_modified_changed)
        toolbar_layout.addWidget(self.show_modified_check)

        # 添加弹性空间
        toolbar_layout.addStretch()

        # 创建文件操作按钮
        self.load_button = QPushButton("加载配置")
        self.load_button.clicked.connect(self.load_config)
        toolbar_layout.addWidget(self.load_button)

        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)
        toolbar_layout.addWidget(self.save_button)

        # 添加测试连接按钮
        self.test_connection_button = QPushButton("测试连接")
        self.test_connection_button.clicked.connect(self.test_connection)
        toolbar_layout.addWidget(self.test_connection_button)

        main_layout.addLayout(toolbar_layout)

        # 创建主分割器 (水平)
        main_splitter = QSplitter(Qt.Horizontal)

        # 创建左侧面板 (曲线可视化)
        self.curve_visualizer = CurveVisualizerWidget()
        if self.curve_data:
            self.curve_visualizer.set_curve_data(self.curve_data, "m0")
        # 连接拖拽信号
        self.curve_visualizer.point_dragged.connect(self.on_point_dragged)
        main_splitter.addWidget(self.curve_visualizer)

        # 创建右侧面板 (垂直分割)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 创建右侧垂直分割器
        right_splitter = QSplitter(Qt.Vertical)

        # 创建电机曲线编辑组件
        self.curve_editor = MotorCurveEditor()
        if self.curve_data and "m0" in self.curve_data:
            self.curve_editor.set_motor_data("m0", self.curve_data["m0"], self.curve_data)
        self.curve_editor.curve_updated.connect(self.on_curve_updated)
        right_splitter.addWidget(self.curve_editor)

        # 创建电机测试面板
        self.motor_test_panel = MotorTestPanel()
        self.motor_test_panel.test_command_sent.connect(self.on_test_command_sent)
        self.motor_test_panel.test_command_stopped.connect(self.on_test_command_stopped)
        self.motor_test_panel.log_message.connect(self.on_log_message)
        right_splitter.addWidget(self.motor_test_panel)

        # 创建组合电机测试面板
        self.combined_test_panel = CombinedMotorTestPanel()
        self.combined_test_panel.test_command_sent.connect(self.on_combined_test_command_sent)
        self.combined_test_panel.test_command_stopped.connect(self.on_combined_test_command_stopped)
        self.combined_test_panel.log_message.connect(self.on_log_message)
        right_splitter.addWidget(self.combined_test_panel)

        # 创建调试信息面板
        self.debug_info_panel = DebugInfoPanel()
        right_splitter.addWidget(self.debug_info_panel)

        # 设置右侧分割器初始大小
        right_splitter.setSizes([250, 150, 150, 150])

        right_layout.addWidget(right_splitter)
        main_splitter.addWidget(right_panel)

        # 设置主分割器初始大小
        main_splitter.setSizes([600, 400])

        main_layout.addWidget(main_splitter)

        # 添加初始日志
        self.debug_info_panel.add_log("推力曲线调试工具已启动")

        # 初始化网络通信
        self.init_network()

        # 创建状态栏
        self.statusBar().showMessage("就绪")

    def load_curve_data(self):
        """加载曲线数据"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.curve_data = json.load(f)
            self.statusBar().showMessage(f"已加载配置: {self.config_path}")
        except Exception as e:
            self.statusBar().showMessage(f"加载配置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")

    def on_motor_selected(self, motor_id):
        """处理电机选择变更"""
        if motor_id in self.curve_data:
            # 更新曲线可视化
            self.curve_visualizer.update_motor_selection(motor_id)

            # 更新曲线编辑器
            self.curve_editor.set_motor_data(motor_id, self.curve_data[motor_id], self.curve_data)

            # 更新电机测试面板
            self.motor_test_panel.set_motor_id(motor_id)

            # 添加日志
            self.debug_info_panel.add_log(f"已选择电机: {motor_id}")

            # 更新状态栏
            self.statusBar().showMessage(f"已选择电机: {motor_id}")

    def on_show_original_changed(self, state):
        """处理显示原始曲线选项变更"""
        self.curve_visualizer.toggle_original_curve(state == Qt.Checked)

    def on_show_modified_changed(self, state):
        """处理显示修改后曲线选项变更"""
        self.curve_visualizer.toggle_modified_curve(state == Qt.Checked)

    def on_curve_updated(self, motor_id, motor_data):
        """处理曲线更新"""
        # 更新曲线数据
        self.curve_data[motor_id] = motor_data

        # 更新曲线可视化
        self.curve_visualizer.update()

        # 更新状态栏
        self.statusBar().showMessage(f"已更新电机 {motor_id} 的曲线参数")

    def on_point_dragged(self, motor_id, point_type, value):
        """处理控制点拖拽"""
        if motor_id not in self.curve_data:
            return

        # 更新曲线数据
        self.curve_data[motor_id][point_type] = value

        # 如果是当前选中的电机，更新编辑器UI
        if motor_id == self.motor_combo.currentText():
            # 阻止信号循环
            self.curve_editor.blockSignals(True)

            # 更新编辑器中的值
            if point_type == "nt_end":
                self.curve_editor.nt_end_spin.setValue(value)
            elif point_type == "nt_mid":
                self.curve_editor.nt_mid_spin.setValue(value)
            elif point_type == "pt_mid":
                self.curve_editor.pt_mid_spin.setValue(value)
            elif point_type == "pt_end":
                self.curve_editor.pt_end_spin.setValue(value)

            self.curve_editor.blockSignals(False)

        # 更新曲线可视化
        self.curve_visualizer.update()

        # 更新状态栏
        self.statusBar().showMessage(f"已拖拽更新电机 {motor_id} 的 {point_type} 参数为 {value:.2f}")

        # 添加日志
        self.debug_info_panel.add_log(f"拖拽更新: 电机 {motor_id}, {point_type} = {value:.2f}")

    def init_network(self):
        """初始化网络通信"""
        if not SOCKET_AVAILABLE:
            self.debug_info_panel.add_log("警告: socket模块不可用，网络通信功能将被禁用")
            return

        try:
            # 创建UDP套接字
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # 尝试从配置文件加载远程地址和端口
            config_manager = ConfigManager()

            # 获取本地端口并绑定
            local_port = config_manager.get_local_port()
            self.udp_socket.setblocking(False)  # 设置为非阻塞模式
            self.udp_socket.bind(('', local_port))  # 绑定本地端口

            # 获取远程地址和端口
            if "network" in config_manager.config:
                self.remote_addr = config_manager.config["network"].get("remote_ip", "127.0.0.1")
                self.remote_port = config_manager.config["network"].getint("remote_port", 8888)
            else:
                server_address = config_manager.get_server_address()
                self.remote_addr = server_address[0]
                self.remote_port = server_address[1]

            self.debug_info_panel.add_log(
                f"网络通信初始化成功: 本地端口 {local_port}, 远程地址 {self.remote_addr}:{self.remote_port}")
        except Exception as e:
            self.debug_info_panel.add_log(f"网络通信初始化失败: {str(e)}")
            self.udp_socket = None

    def send_motor_command(self, motor_id, speed):
        """发送单个电机命令"""
        if not SOCKET_AVAILABLE or not self.udp_socket:
            self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
            return False

        try:
            # 提取电机编号
            motor_num = int(motor_id[1:])

            # 创建命令数据
            command = {
                "type": "motor_test",
                "motor": motor_num,
                "speed": speed
            }

            # 转换为JSON字符串
            command_json = json.dumps(command)

            # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
            self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

            return True
        except Exception as e:
            self.debug_info_panel.add_log(f"发送命令失败: {str(e)}")
            return False

    def send_combined_motor_command(self, motor_speeds):
        """发送组合电机命令
        
        参数:
            motor_speeds: 包含x, y, z轴速度的字典
        """
        if not SOCKET_AVAILABLE or not self.udp_socket:
            self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
            return False

        try:
            # 从x, y, z值计算各个电机的速度
            x_raw = motor_speeds.get("x", 0.0)
            y_raw = motor_speeds.get("y", 0.0)
            z_raw = motor_speeds.get("z", 0.0)

            # 应用控制器曲线函数和正确的幅度
            # 根据config_beyond.ini中的设置: x=3000, y=5000, z=6000
            x = 3000 * controller_curve(x_raw)
            y = 5000 * controller_curve(y_raw)
            z = 6000 * controller_curve(z_raw)

            # 根据ROV的电机布局计算各个电机的速度
            # 这里使用一个简化的映射，实际应用中可能需要更复杂的计算
            # 假设:
            # m0, m1: 左右水平推进器
            # m2, m3: 前后水平推进器
            # m4, m5: 上下垂直推进器

            # 水平推进器 (左右)
            m0_speed = x  # 左侧推进器
            m1_speed = -x  # 右侧推进器 (反向)

            # 水平推进器 (前后)
            m2_speed = y  # 前侧推进器
            m3_speed = -y  # 后侧推进器 (反向)

            # 垂直推进器 (上下)
            m4_speed = z  # 垂直推进器1
            m5_speed = z  # 垂直推进器2

            # 创建命令数据
            command = {
                "type": "combined_test",
                "motors": {
                    "0": m0_speed,
                    "1": m1_speed,
                    "2": m2_speed,
                    "3": m3_speed,
                    "4": m4_speed,
                    "5": m5_speed
                }
            }

            # 转换为JSON字符串
            command_json = json.dumps(command)

            # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
            self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

            # 记录日志
            self.debug_info_panel.add_log(f"发送组合命令: 原始值 X={x_raw:.2f}, Y={y_raw:.2f}, Z={z_raw:.2f}")
            self.debug_info_panel.add_log(f"处理后值: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
            self.debug_info_panel.add_log(
                f"电机速度: M0={m0_speed:.2f}, M1={m1_speed:.2f}, M2={m2_speed:.2f}, M3={m3_speed:.2f}, M4={m4_speed:.2f}, M5={m5_speed:.2f}")

            return True
        except Exception as e:
            self.debug_info_panel.add_log(f"发送组合命令失败: {str(e)}")
            return False

    def on_test_command_sent(self, motor_id, speed, duration):
        """处理测试命令发送"""
        # 更新状态栏
        self.statusBar().showMessage(f"正在测试电机 {motor_id}，速度: {speed:.2f}，持续时间: {duration}秒")

        # 添加日志
        self.debug_info_panel.add_log(f"发送测试命令: 电机 {motor_id}, 速度 = {speed:.2f}, 持续时间 = {duration}秒")

        # 发送命令到硬件
        if self.send_motor_command(motor_id, speed):
            self.debug_info_panel.add_log(f"命令已发送: 电机 {motor_id} 开始运行")
        else:
            self.debug_info_panel.add_log(f"命令发送失败: 电机 {motor_id}")

    def on_test_command_stopped(self, motor_id):
        """处理测试命令停止"""
        # 更新状态栏
        self.statusBar().showMessage(f"已停止测试电机 {motor_id}")

        # 添加日志
        self.debug_info_panel.add_log(f"停止测试命令: 电机 {motor_id}")

        # 发送停止命令到硬件 (速度设为0)
        if self.send_motor_command(motor_id, 0.0):
            self.debug_info_panel.add_log(f"命令已发送: 电机 {motor_id} 已停止")
        else:
            self.debug_info_panel.add_log(f"停止命令发送失败: 电机 {motor_id}")

    def on_combined_test_command_sent(self, motor_speeds, duration):
        """处理组合测试命令发送"""
        # 更新状态栏
        self.statusBar().showMessage(
            f"正在进行组合测试，X: {motor_speeds['x']:.2f}, Y: {motor_speeds['y']:.2f}, Z: {motor_speeds['z']:.2f}，持续时间: {duration}秒")

        # 添加日志
        self.debug_info_panel.add_log(
            f"发送组合测试命令: X={motor_speeds['x']:.2f}, Y={motor_speeds['y']:.2f}, Z={motor_speeds['z']:.2f}, 持续时间={duration}秒")

        # 发送命令到硬件
        if self.send_combined_motor_command(motor_speeds):
            self.debug_info_panel.add_log("组合命令已发送: 所有电机开始运行")
        else:
            self.debug_info_panel.add_log("组合命令发送失败")

    def on_combined_test_command_stopped(self):
        """处理组合测试命令停止"""
        # 更新状态栏
        self.statusBar().showMessage("已停止组合测试")

        # 添加日志
        self.debug_info_panel.add_log("停止组合测试命令")

        # 发送停止命令到硬件 (所有速度设为0)
        stop_speeds = {"x": 0.0, "y": 0.0, "z": 0.0}
        if self.send_combined_motor_command(stop_speeds):
            self.debug_info_panel.add_log("停止命令已发送: 所有电机已停止")
        else:
            self.debug_info_panel.add_log("停止命令发送失败")

    def on_log_message(self, message):
        """处理日志消息"""
        self.debug_info_panel.add_log(message)

    def test_connection(self):
        """测试与ROV的网络连接"""
        if not SOCKET_AVAILABLE or not self.udp_socket:
            self.debug_info_panel.add_log("警告: 网络通信不可用，无法测试连接")
            return

        try:
            # 创建测试命令
            test_command = {
                "type": "connection_test",
                "timestamp": time.time()
            }

            # 转换为JSON字符串
            command_json = json.dumps(test_command)

            # 发送数据
            self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

            # 更新状态栏
            self.statusBar().showMessage(f"已发送测试连接命令到 {self.remote_addr}:{self.remote_port}")

            # 添加日志
            self.debug_info_panel.add_log(f"测试连接: 已发送测试命令到 {self.remote_addr}:{self.remote_port}")

            # 尝试接收响应（非阻塞方式）
            try:
                self.udp_socket.settimeout(0.5)  # 设置0.5秒超时
                data, addr = self.udp_socket.recvfrom(1024)
                if data:
                    self.debug_info_panel.add_log(f"测试连接成功: 收到来自 {addr[0]}:{addr[1]} 的响应")
                    self.statusBar().showMessage(f"连接测试成功: 已连接到 {addr[0]}:{addr[1]}")
                self.udp_socket.settimeout(0)  # 恢复非阻塞模式
            except socket.timeout:
                self.debug_info_panel.add_log("测试连接: 未收到响应，但命令已发送")
                self.statusBar().showMessage("测试连接: 已发送命令，但未收到响应")
            except Exception as e:
                self.debug_info_panel.add_log(f"测试连接: 接收响应时出错: {str(e)}")

        except Exception as e:
            self.debug_info_panel.add_log(f"测试连接失败: {str(e)}")
            self.statusBar().showMessage("测试连接失败，请检查网络设置")

    def load_config(self):
        """加载配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载配置文件", "", "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    new_data = json.load(f)

                # 验证数据格式
                if not all(f"m{i}" in new_data for i in range(6)):
                    raise ValueError("配置文件格式不正确，缺少必要的电机配置")

                # 更新数据
                self.curve_data = new_data
                self.config_path = file_path

                # 更新UI
                current_motor = self.motor_combo.currentText()
                self.curve_visualizer.set_curve_data(self.curve_data, current_motor)
                self.curve_editor.set_motor_data(current_motor, self.curve_data[current_motor], self.curve_data)

                # 更新状态栏
                self.statusBar().showMessage(f"已加载配置: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"加载配置失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")

    def save_config(self):
        """保存配置文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置文件", self.config_path, "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.curve_data, f, ensure_ascii=False)

                self.config_path = file_path
                self.statusBar().showMessage(f"已保存配置: {file_path}")
                self.debug_info_panel.add_log(f"配置已保存到: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"保存配置失败: {str(e)}")
                self.debug_info_panel.add_log(f"保存配置失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止所有正在进行的测试
        if hasattr(self, 'motor_test_panel') and self.motor_test_panel.test_in_progress:
            self.motor_test_panel.stop_test()

        # 停止组合测试
        if hasattr(self, 'combined_test_panel') and self.combined_test_panel.test_in_progress:
            self.combined_test_panel.stop_test()

        # 关闭网络连接
        if self.udp_socket:
            try:
                self.udp_socket.close()
                self.debug_info_panel.add_log("网络连接已关闭")
            except Exception as e:
                self.debug_info_panel.add_log(f"关闭网络连接时出错: {str(e)}")

        # 记录应用程序关闭
        self.debug_info_panel.add_log("推力曲线调试工具已关闭")

        # 继续事件处理
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ThrustCurveDebugger()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
