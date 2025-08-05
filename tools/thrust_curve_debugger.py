import json
import sys
import time
import socket
import re
import os
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QLabel, QLineEdit, QGridLayout, QGroupBox,
                             QMessageBox, QFileDialog, QSlider, QListWidget, QListWidgetItem,
                             QSplitter, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import text
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import platform

matplotlib.use('Qt5Agg')

# 配置matplotlib字体以支持中文
if platform.system() == 'Windows':
    # Windows系统使用微软雅黑或宋体
    matplotlib.rcParams['font.family'] = ['Microsoft YaHei', 'SimSun', 'sans-serif']
else:
    # Linux/Mac系统使用其他字体
    matplotlib.rcParams['font.family'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK JP', 'sans-serif']

# 设置字体属性
matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号

# --- 全局常量 ---
PWM_MID = 3000
PWM_HALF_P_DEFAULT = 600
PWM_HALF_N_DEFAULT = 400
MOTOR_COUNT = 6  # 电机数量参数，方便扩展


# --- Matplotlib 可拖拽点交互式画布 ---
class DraggablePointPlot(FigureCanvas):
    point_dragged = pyqtSignal()
    point_selected = pyqtSignal(str)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.points_artists = []
        self.lines = []
        self._drag_point_info = None
        self.comparison_lines = []  # 用于存储比较曲线的线条
        self.is_dual_view = False  # 是否处于双曲线视图模式
        self.comparison_artists = []  # 用于存储比较曲线的点
        self.update_interval = 5  # 刷新间隔（毫秒），较小的值使UI更响应

    def plot_curve(self, curve_params, pwm_end_p, pwm_end_n):
        """绘制单条曲线"""
        self.axes.clear()
        self.is_dual_view = False
        self.point_params = curve_params

        self.points_data = {
            'nt_end': (curve_params['nt_end'], pwm_end_n),
            'nt_mid': (curve_params['nt_mid'], curve_params['np_mid']),
            'np_ini': (0, curve_params['np_ini']),
            'pp_ini': (0, curve_params['pp_ini']),
            'pt_mid': (curve_params['pt_mid'], curve_params['pp_mid']),
            'pt_end': (curve_params['pt_end'], pwm_end_p),
        }

        neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]

        self.lines = [];
        self.lines.extend(self.axes.plot(neg_x, neg_y, 'b-', linewidth=2));
        self.lines.extend(self.axes.plot(pos_x, pos_y, 'g-', linewidth=2))
        self.points_artists = []
        for name, (x, y) in self.points_data.items():
            artist = self.axes.plot(x, y, 'ro', markersize=8)[0]
            artist.set_gid(name);
            self.points_artists.append(artist)

        self._setup_plot_style();
        self.draw()

    def plot_dual_curves(self, primary_params, comparison_params, pwm_end_p, pwm_end_n, primary_name, comparison_name,
                         editing_primary_motor=True):
        """绘制双曲线对比视图"""
        self.axes.clear()
        self.is_dual_view = True
        self.point_params = primary_params
        self.comparison_params = comparison_params  # 保存比较参数
        self.editing_primary_motor = editing_primary_motor  # 保存当前正在编辑的是哪个电机

        # 主曲线数据点
        self.points_data = {
            'nt_end': (primary_params['nt_end'], pwm_end_n),
            'nt_mid': (primary_params['nt_mid'], primary_params['np_mid']),
            'np_ini': (0, primary_params['np_ini']),
            'pp_ini': (0, primary_params['pp_ini']),
            'pt_mid': (primary_params['pt_mid'], primary_params['pp_mid']),
            'pt_end': (primary_params['pt_end'], pwm_end_p),
        }

        # 比较曲线数据点
        self.comparison_points = {
            'nt_end_comp': (comparison_params['nt_end'], pwm_end_n),
            'nt_mid_comp': (comparison_params['nt_mid'], comparison_params['np_mid']),
            'np_ini_comp': (0, comparison_params['np_ini']),
            'pp_ini_comp': (0, comparison_params['pp_ini']),
            'pt_mid_comp': (comparison_params['pt_mid'], comparison_params['pp_mid']),
            'pt_end_comp': (comparison_params['pt_end'], pwm_end_p),
        }

        # 主曲线坐标
        primary_neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        primary_neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        primary_pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        primary_pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]

        # 比较曲线坐标
        comp_neg_x = [self.comparison_points['nt_end_comp'][0], self.comparison_points['nt_mid_comp'][0],
                      self.comparison_points['np_ini_comp'][0]]
        comp_neg_y = [self.comparison_points['nt_end_comp'][1], self.comparison_points['nt_mid_comp'][1],
                      self.comparison_points['np_ini_comp'][1]]
        comp_pos_x = [self.comparison_points['pp_ini_comp'][0], self.comparison_points['pt_mid_comp'][0],
                      self.comparison_points['pt_end_comp'][0]]
        comp_pos_y = [self.comparison_points['pp_ini_comp'][1], self.comparison_points['pt_mid_comp'][1],
                      self.comparison_points['pt_end_comp'][1]]

        # 根据当前编辑的电机决定线型
        self.lines = []
        self.comparison_lines = []

        if self.editing_primary_motor:
            # 编辑主电机时，主曲线为实线，比较曲线为虚线
            self.lines.extend(
                self.axes.plot(primary_neg_x, primary_neg_y, 'b-', linewidth=2.5, label=f"{primary_name} 负向"))
            self.lines.extend(
                self.axes.plot(primary_pos_x, primary_pos_y, 'g-', linewidth=2.5, label=f"{primary_name} 正向"))

            self.comparison_lines.extend(self.axes.plot(comp_neg_x, comp_neg_y, 'b--', linewidth=1.5, alpha=0.8,
                                                        label=f"{comparison_name} 负向"))
            self.comparison_lines.extend(self.axes.plot(comp_pos_x, comp_pos_y, 'g--', linewidth=1.5, alpha=0.8,
                                                        label=f"{comparison_name} 正向"))
        else:
            # 编辑比较电机时，比较曲线为实线，主曲线为虚线
            self.lines.extend(self.axes.plot(primary_neg_x, primary_neg_y, 'b--', linewidth=1.5, alpha=0.8,
                                             label=f"{primary_name} 负向"))
            self.lines.extend(self.axes.plot(primary_pos_x, primary_pos_y, 'g--', linewidth=1.5, alpha=0.8,
                                             label=f"{primary_name} 正向"))

            self.comparison_lines.extend(
                self.axes.plot(comp_neg_x, comp_neg_y, 'b-', linewidth=2.5, label=f"{comparison_name} 负向"))
            self.comparison_lines.extend(
                self.axes.plot(comp_pos_x, comp_pos_y, 'g-', linewidth=2.5, label=f"{comparison_name} 正向"))

        # 绘制主曲线的可拖动点
        self.points_artists = []
        for name, (x, y) in self.points_data.items():
            artist = self.axes.plot(x, y, 'ro', markersize=8)[0]
            artist.set_gid(name)
            self.points_artists.append(artist)

        # 绘制比较曲线的可拖动点
        self.comparison_artists = []
        for name, (x, y) in self.comparison_points.items():
            artist = self.axes.plot(x, y, 'bo', markersize=8)[0]
            artist.set_gid(name)
            self.comparison_artists.append(artist)
            self.points_artists.append(artist)  # 添加到总的可拖动点列表中

        # 设置图表样式
        self._setup_plot_style(is_dual=True)
        self.draw()

    def _setup_plot_style(self, is_dual=False):
        """设置推力曲线图表样式"""
        if is_dual:
            self.axes.set_title("双曲线对比视图");
        else:
            self.axes.set_title("推力曲线 (Thrust-PWM)");

        self.axes.set_xlabel("推力 (g)");
        self.axes.set_ylabel("PWM")
        self.axes.grid(True, linestyle='--', alpha=0.7);
        self.axes.axhline(PWM_MID, color='grey', linestyle='--', linewidth=0.8)
        self.axes.axvline(0, color='black', linewidth=0.8);

        # 设置图例
        if is_dual:
            # 双曲线模式下使用自动生成的图例
            self.axes.legend(loc='upper right', fontsize=9)
        else:
            # 单曲线模式下使用简单图例
            self.axes.legend(self.lines, ['负向推力', '正向推力'])

        # 设置坐标轴范围
        self.axes.set_xlim([-2000, 2000])  # 适当设置推力范围
        self.axes.set_ylim([PWM_MID - 800, PWM_MID + 800])  # 适当设置PWM范围

    def connect_events(self):
        """连接鼠标事件"""
        self.mpl_connect('button_press_event', self.on_press);
        self.mpl_connect('motion_notify_event', self.on_motion)
        self.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        if event.inaxes != self.axes: return
        for artist in self.points_artists:
            contains, _ = artist.contains(event)
            if contains:
                name = artist.get_gid()

                # 检查是否是比较曲线的点
                is_comparison_point = name.endswith('_comp')

                # 在双曲线视图模式下，只允许拖动当前正在编辑的电机的点
                if self.is_dual_view:
                    if (is_comparison_point and self.editing_primary_motor) or \
                            (not is_comparison_point and not self.editing_primary_motor):
                        # 不允许拖动非编辑电机的点
                        return

                self._drag_point_info = (artist, name)
                self.point_selected.emit(name);
                return

    def on_motion(self, event):
        if self._drag_point_info is None or event.xdata is None or event.ydata is None: return
        artist, name = self._drag_point_info
        x, y = event.xdata, event.ydata

        # 检查是否是比较曲线的点
        is_comparison_point = name.endswith('_comp')

        # 处理固定点和端点的特殊情况
        if name in ['np_ini', 'pp_ini'] or name in ['np_ini_comp', 'pp_ini_comp']:
            # 这些点的x坐标固定为0
            x = 0
            if is_comparison_point:
                y = self.comparison_points[name][1]
            else:
                y = self.points_data[name][1]
        elif name in ['nt_end', 'pt_end'] or name in ['nt_end_comp', 'pt_end_comp']:
            # 这些点的y坐标固定
            if is_comparison_point:
                y = self.comparison_points[name][1]
            else:
                y = self.points_data[name][1]

        # 更新点的位置
        artist.set_data([x], [y])

        # 根据是否是比较点更新相应的数据
        if is_comparison_point:
            self.comparison_points[name] = (x, y)

            # 更新比较参数
            base_name = name[:-5]  # 移除 '_comp' 后缀
            if base_name == 'nt_end':
                self.comparison_params['nt_end'] = x
            elif base_name == 'nt_mid':
                self.comparison_params['nt_mid'] = x
                self.comparison_params['np_mid'] = y
            elif base_name == 'pt_mid':
                self.comparison_params['pt_mid'] = x
                self.comparison_params['pp_mid'] = y
            elif base_name == 'pt_end':
                self.comparison_params['pt_end'] = x
            elif base_name == 'np_ini':
                self.comparison_params['np_ini'] = y
            elif base_name == 'pp_ini':
                self.comparison_params['pp_ini'] = y

            # 更新比较曲线
            self._update_comparison_lines()
        else:
            self.points_data[name] = (x, y)

            # 更新主参数
            if name == 'nt_end':
                self.point_params['nt_end'] = x
            elif name == 'nt_mid':
                self.point_params['nt_mid'] = x
                self.point_params['np_mid'] = y
            elif name == 'pt_mid':
                self.point_params['pt_mid'] = x
                self.point_params['pp_mid'] = y
            elif name == 'pt_end':
                self.point_params['pt_end'] = x
            elif name == 'np_ini':
                self.point_params['np_ini'] = y
            elif name == 'pp_ini':
                self.point_params['pp_ini'] = y

            # 更新主曲线
            self._update_lines()

        self.draw()
        # 发送信号通知UI实时更新
        self.point_dragged.emit()

    def on_release(self, event):
        if self._drag_point_info is None: return
        artist, name = self._drag_point_info

        if name in ['np_ini', 'pp_ini']:
            self._drag_point_info = None
            return

        # Parameters are already updated in on_motion
        # Just release the drag point info
        self._drag_point_info = None

    def _update_lines(self):
        neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]
        self.lines[0].set_data(neg_x, neg_y);
        self.lines[1].set_data(pos_x, pos_y)

    def _update_comparison_lines(self):
        """更新比较曲线"""
        if not self.is_dual_view or not hasattr(self, 'comparison_lines') or len(self.comparison_lines) < 2:
            return

        neg_x = [self.comparison_points['nt_end_comp'][0], self.comparison_points['nt_mid_comp'][0],
                 self.comparison_points['np_ini_comp'][0]]
        neg_y = [self.comparison_points['nt_end_comp'][1], self.comparison_points['nt_mid_comp'][1],
                 self.comparison_points['np_ini_comp'][1]]
        pos_x = [self.comparison_points['pp_ini_comp'][0], self.comparison_points['pt_mid_comp'][0],
                 self.comparison_points['pt_end_comp'][0]]
        pos_y = [self.comparison_points['pp_ini_comp'][1], self.comparison_points['pt_mid_comp'][1],
                 self.comparison_points['pt_end_comp'][1]]

        self.comparison_lines[0].set_data(neg_x, neg_y)
        self.comparison_lines[1].set_data(pos_x, pos_y)


# --- 电机推力状态可视化 ---
class ThrustVisualization(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection='3d')
        super().__init__(self.fig)
        self.setParent(parent)

        # 初始化ROV模型
        self.setup_rov_model()

        # 初始化推力箭头
        self.thrust_arrows = []

        # 初始化推力值
        self.x_thrust = 0
        self.y_thrust = 0
        self.z_thrust = 0
        self.yaw_thrust = 0

        # 设置图表样式
        self._setup_plot_style()

    def setup_rov_model(self):
        """设置ROV模型的基本形状和电机位置"""
        # 创建更详细的ROV主体
        self._create_rov_body()

        # 设置电机位置
        self._setup_motor_positions()

        # 绘制电机模型
        self._create_motor_models()

    def _create_rov_body(self):
        """创建更详细的ROV主体模型"""
        # 主体尺寸
        length, width, height = 2.0, 1.6, 0.6

        # 主体 - 中心长方体
        x_main = [-length / 2, length / 2, length / 2, -length / 2, -length / 2, length / 2, length / 2, -length / 2]
        y_main = [-width / 2, -width / 2, width / 2, width / 2, -width / 2, -width / 2, width / 2, width / 2]
        z_main = [-height / 2, -height / 2, -height / 2, -height / 2, height / 2, height / 2, height / 2, height / 2]

        # 绘制主体
        # 底部面
        self.axes.plot(x_main[:4], y_main[:4], z_main[:4], 'b-', linewidth=2)
        # 顶部面
        self.axes.plot(x_main[4:], y_main[4:], z_main[4:], 'b-', linewidth=2)
        # 连接线
        for i in range(4):
            self.axes.plot([x_main[i], x_main[i + 4]], [y_main[i], y_main[i + 4]], [z_main[i], z_main[i + 4]], 'b-',
                           linewidth=2)

        # 添加透明面板以增强3D效果
        from matplotlib.patches import Polygon
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        # 定义面
        faces = [
            # 底面
            [
                [x_main[0], y_main[0], z_main[0]],
                [x_main[1], y_main[1], z_main[1]],
                [x_main[2], y_main[2], z_main[2]],
                [x_main[3], y_main[3], z_main[3]]
            ],
            # 顶面
            [
                [x_main[4], y_main[4], z_main[4]],
                [x_main[5], y_main[5], z_main[5]],
                [x_main[6], y_main[6], z_main[6]],
                [x_main[7], y_main[7], z_main[7]]
            ],
            # 前面
            [
                [x_main[2], y_main[2], z_main[2]],
                [x_main[3], y_main[3], z_main[3]],
                [x_main[7], y_main[7], z_main[7]],
                [x_main[6], y_main[6], z_main[6]]
            ],
            # 后面
            [
                [x_main[0], y_main[0], z_main[0]],
                [x_main[1], y_main[1], z_main[1]],
                [x_main[5], y_main[5], z_main[5]],
                [x_main[4], y_main[4], z_main[4]]
            ],
            # 左面
            [
                [x_main[0], y_main[0], z_main[0]],
                [x_main[3], y_main[3], z_main[3]],
                [x_main[7], y_main[7], z_main[7]],
                [x_main[4], y_main[4], z_main[4]]
            ],
            # 右面
            [
                [x_main[1], y_main[1], z_main[1]],
                [x_main[2], y_main[2], z_main[2]],
                [x_main[6], y_main[6], z_main[6]],
                [x_main[5], y_main[5], z_main[5]]
            ]
        ]

        # 创建3D多边形集合
        poly3d = Poly3DCollection(faces, alpha=0.15, linewidth=1, edgecolor='b', facecolor='cyan')
        self.axes.add_collection3d(poly3d)

        # 添加一些细节特征
        # 前部摄像头位置 - 移到顶部
        camera_x, camera_y, camera_z = 0, 0, height / 2 + 0.1
        self.axes.plot([camera_x], [camera_y], [camera_z], 'ko', markersize=6)
        self.axes.text(camera_x, camera_y, camera_z + 0.1, "摄像头", fontsize=8)

        # 添加机械抓
        self._create_mechanical_claw(width / 2 + 0.1)

    def _create_mechanical_claw(self, front_y):
        """创建机械抓模型"""
        # 机械抓的基座位置 (在ROV前部)
        base_x, base_y, base_z = 0, front_y, 0

        # 机械抓尺寸 - 调整尺寸使其在俯视图中更明显
        claw_length = 0.6
        claw_width = 0.4
        claw_height = 0.15

        # 绘制机械抓基座
        self.axes.plot([base_x], [base_y], [base_z], 'ko', markersize=5)

        # 绘制机械抓主体 (简化为长方体)
        claw_x = [base_x - claw_width / 2, base_x + claw_width / 2, base_x + claw_width / 2, base_x - claw_width / 2,
                  base_x - claw_width / 2, base_x + claw_width / 2, base_x + claw_width / 2, base_x - claw_width / 2]
        claw_y = [base_y, base_y, base_y + claw_length, base_y + claw_length,
                  base_y, base_y, base_y + claw_length, base_y + claw_length]
        claw_z = [base_z - claw_height / 2, base_z - claw_height / 2, base_z - claw_height / 2,
                  base_z - claw_height / 2,
                  base_z + claw_height / 2, base_z + claw_height / 2, base_z + claw_height / 2,
                  base_z + claw_height / 2]

        # 绘制机械抓主体
        self.axes.plot(claw_x[:4], claw_y[:4], claw_z[:4], 'r-', linewidth=2)  # 底部
        self.axes.plot(claw_x[4:], claw_y[4:], claw_z[4:], 'r-', linewidth=2)  # 顶部
        for i in range(4):
            self.axes.plot([claw_x[i], claw_x[i + 4]], [claw_y[i], claw_y[i + 4]], [claw_z[i], claw_z[i + 4]], 'r-',
                           linewidth=2)

        # 添加透明面板以增强3D效果
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        # 定义机械抓的面
        claw_faces = [
            # 底面
            [
                [claw_x[0], claw_y[0], claw_z[0]],
                [claw_x[1], claw_y[1], claw_z[1]],
                [claw_x[2], claw_y[2], claw_z[2]],
                [claw_x[3], claw_y[3], claw_z[3]]
            ],
            # 顶面
            [
                [claw_x[4], claw_y[4], claw_z[4]],
                [claw_x[5], claw_y[5], claw_z[5]],
                [claw_x[6], claw_y[6], claw_z[6]],
                [claw_x[7], claw_y[7], claw_z[7]]
            ],
            # 前面
            [
                [claw_x[2], claw_y[2], claw_z[2]],
                [claw_x[3], claw_y[3], claw_z[3]],
                [claw_x[7], claw_y[7], claw_z[7]],
                [claw_x[6], claw_y[6], claw_z[6]]
            ],
            # 后面
            [
                [claw_x[0], claw_y[0], claw_z[0]],
                [claw_x[1], claw_y[1], claw_z[1]],
                [claw_x[5], claw_y[5], claw_z[5]],
                [claw_x[4], claw_y[4], claw_z[4]]
            ],
            # 左面
            [
                [claw_x[0], claw_y[0], claw_z[0]],
                [claw_x[3], claw_y[3], claw_z[3]],
                [claw_x[7], claw_y[7], claw_z[7]],
                [claw_x[4], claw_y[4], claw_z[4]]
            ],
            # 右面
            [
                [claw_x[1], claw_y[1], claw_z[1]],
                [claw_x[2], claw_y[2], claw_z[2]],
                [claw_x[6], claw_y[6], claw_z[6]],
                [claw_x[5], claw_y[5], claw_z[5]]
            ]
        ]

        # 创建3D多边形集合
        claw_poly3d = Poly3DCollection(claw_faces, alpha=0.2, linewidth=1, edgecolor='r', facecolor='red')
        self.axes.add_collection3d(claw_poly3d)

        # 添加机械抓爪子 (从俯视图看更明显的设计)
        # 左爪 - 横向展开
        left_claw_x = [base_x - claw_width / 3, base_x - claw_width * 0.8, base_x - claw_width * 0.7]
        left_claw_y = [base_y + claw_length, base_y + claw_length + claw_width / 2,
                       base_y + claw_length + claw_width / 3]
        left_claw_z = [base_z, base_z, base_z]
        self.axes.plot(left_claw_x, left_claw_y, left_claw_z, 'r-', linewidth=3)

        # 右爪 - 横向展开
        right_claw_x = [base_x + claw_width / 3, base_x + claw_width * 0.8, base_x + claw_width * 0.7]
        right_claw_y = [base_y + claw_length, base_y + claw_length + claw_width / 2,
                        base_y + claw_length + claw_width / 3]
        right_claw_z = [base_z, base_z, base_z]
        self.axes.plot(right_claw_x, right_claw_y, right_claw_z, 'r-', linewidth=3)

        # 添加爪子的闭合线，使其看起来像一个夹子
        self.axes.plot(
            [left_claw_x[2], right_claw_x[2]],
            [left_claw_y[2], right_claw_y[2]],
            [left_claw_z[2], right_claw_z[2]],
            'r-', linewidth=2
        )

        # 添加标签
        self.axes.text(base_x, base_y + claw_length / 2, base_z + claw_height / 2 + 0.1, "机械抓", fontsize=8,
                       horizontalalignment='center')

    def _setup_motor_positions(self):
        """设置电机位置"""
        # 6个电机的布局: 4个水平电机形成菱形布局用于X/Y/Yaw, 2个垂直电机用于Z
        self.motor_positions = {
            'm0': [0.8, 1, 0],  # 右前 (45度角)
            'm1': [0.8, -1, 0],  # 右后 (45度角)
            'm2': [-0.8, -1, 0],  # 左后 (45度角)
            'm3': [-0.8, 1, 0],  # 左前 (45度角)
            'm4': [0, 0.5, 0.3],  # 上前
            'm5': [0, -0.5, 0.3]  # 上后
        }

    def _create_motor_models(self):
        """创建更详细的电机模型"""
        # 电机尺寸
        motor_radius = 0.15
        motor_length = 0.3

        # 为每个电机创建一个简化的圆柱体模型
        for motor, pos in self.motor_positions.items():
            # 绘制电机位置点
            self.axes.plot([pos[0]], [pos[1]], [pos[2]], 'ro', markersize=8)

            # 添加电机标签
            self.axes.text(pos[0], pos[1], pos[2] + 0.2, motor, fontsize=8, horizontalalignment='center')

            # 创建电机圆柱体
            if motor in ['m0', 'm1', 'm2', 'm3']:  # 水平电机
                # 水平电机的方向取决于其位置
                if motor == 'm0':  # 右前
                    direction = np.array([1, 1, 0]) / np.sqrt(2)
                elif motor == 'm1':  # 右后
                    direction = np.array([1, -1, 0]) / np.sqrt(2)
                elif motor == 'm2':  # 左后
                    direction = np.array([-1, -1, 0]) / np.sqrt(2)
                elif motor == 'm3':  # 左前
                    direction = np.array([-1, 1, 0]) / np.sqrt(2)

                # 创建电机圆柱体的端点
                end_point = np.array(pos) + direction * motor_length

                # 绘制电机主体 (简化为线段)
                self.axes.plot([pos[0], end_point[0]], [pos[1], end_point[1]], [pos[2], end_point[2]],
                               'r-', linewidth=4)

                # 绘制电机螺旋桨 (简化为圆盘)
                theta = np.linspace(0, 2 * np.pi, 20)
                # 创建垂直于方向的平面
                if abs(direction[0]) > 0.01:
                    # 如果x方向有分量，使用y-z平面
                    v1 = np.array([0, 1, 0])
                    v2 = np.array([0, 0, 1])
                else:
                    # 否则使用x-z平面
                    v1 = np.array([1, 0, 0])
                    v2 = np.array([0, 0, 1])

                # 确保v1和v2与direction正交
                v1 = v1 - np.dot(v1, direction) * direction
                v1 = v1 / np.linalg.norm(v1)
                v2 = v2 - np.dot(v2, direction) * direction
                v2 = v2 / np.linalg.norm(v2)

                # 创建圆盘点
                circle_points_x = []
                circle_points_y = []
                circle_points_z = []
                for t in theta:
                    point = end_point + motor_radius * (v1 * np.cos(t) + v2 * np.sin(t))
                    circle_points_x.append(point[0])
                    circle_points_y.append(point[1])
                    circle_points_z.append(point[2])

                # 绘制圆盘
                self.axes.plot(circle_points_x, circle_points_y, circle_points_z, 'r-')

            else:  # 垂直电机
                # 垂直电机指向z轴
                direction = np.array([0, 0, 1])

                # 创建电机圆柱体的端点
                end_point = np.array(pos) + direction * motor_length

                # 绘制电机主体 (简化为线段)
                self.axes.plot([pos[0], end_point[0]], [pos[1], end_point[1]], [pos[2], end_point[2]],
                               'b-', linewidth=4)

                # 绘制电机螺旋桨 (简化为圆盘)
                theta = np.linspace(0, 2 * np.pi, 20)
                circle_points_x = []
                circle_points_y = []
                circle_points_z = []
                for t in theta:
                    circle_points_x.append(end_point[0] + motor_radius * np.cos(t))
                    circle_points_y.append(end_point[1] + motor_radius * np.sin(t))
                    circle_points_z.append(end_point[2])

                # 绘制圆盘
                self.axes.plot(circle_points_x, circle_points_y, circle_points_z, 'b-')

    def update_thrust(self, x, y, z, yaw):
        """更新推力值并重绘"""
        self.x_thrust = x
        self.y_thrust = y
        self.z_thrust = z
        self.yaw_thrust = yaw

        # 清除现有箭头
        for arrow in self.thrust_arrows:
            arrow.remove()
        self.thrust_arrows = []

        # 计算每个电机的推力
        motor_thrusts = self.calculate_motor_thrusts(x, y, z, yaw)

        # 显示当前推力值
        self._display_thrust_values(x, y, z, yaw)

        # 绘制推力箭头
        for motor, thrust in motor_thrusts.items():
            pos = self.motor_positions[motor]

            # 获取电机方向
            direction = self._get_motor_direction(motor)

            # 根据推力值缩放方向向量
            # 使用非线性缩放使小推力也可见
            scale = np.sign(thrust) * (np.log(abs(thrust) + 1) / np.log(6001)) * 0.8

            # 计算箭头向量
            if motor in ['m0', 'm1', 'm2', 'm3']:  # 水平电机
                arrow_vec = direction * scale
                dx, dy, dz = arrow_vec
            else:  # 垂直电机
                dx, dy = 0, 0
                dz = scale  # 向上的推力

            # 只有当推力足够大时才绘制箭头
            if abs(scale) > 0.01:
                # 计算箭头起点 - 从电机螺旋桨开始
                if motor in ['m0', 'm1', 'm2', 'm3']:
                    start_pos = np.array(pos) + direction * 0.3  # 电机长度
                else:
                    start_pos = np.array([pos[0], pos[1], pos[2] + 0.3])  # 垂直电机

                # 绘制更美观的箭头
                arrow = self.axes.quiver(
                    start_pos[0], start_pos[1], start_pos[2],
                    dx, dy, dz,
                    color='r' if thrust > 0 else 'b',
                    linewidth=2,
                    arrow_length_ratio=0.3,  # 箭头头部比例
                    alpha=0.8,  # 半透明
                    length=abs(max(dx, dy, dz, key=abs)) * 1.5,  # 长度
                    normalize=False  # 不标准化，保持比例
                )
                self.thrust_arrows.append(arrow)

                # 添加推力值标签
                if abs(thrust) > 500:  # 只显示较大的推力值
                    # 计算标签位置
                    label_pos = start_pos + np.array([dx, dy, dz]) * 0.7
                    # 添加文本标签
                    thrust_text = self.axes.text(
                        label_pos[0], label_pos[1], label_pos[2],
                        f"{int(thrust)}",
                        color='r' if thrust > 0 else 'b',
                        fontsize=8,
                        horizontalalignment='center',
                        verticalalignment='center',
                        bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.2')
                    )
                    self.thrust_arrows.append(thrust_text)

        # 绘制总体推力向量
        self._draw_resultant_thrust_vector(x, y, z)

        self.draw()

    def _get_motor_direction(self, motor):
        """获取电机的方向向量"""
        if motor == 'm0':  # 右前
            return np.array([1, 1, 0]) / np.sqrt(2)
        elif motor == 'm1':  # 右后
            return np.array([1, -1, 0]) / np.sqrt(2)
        elif motor == 'm2':  # 左后
            return np.array([-1, -1, 0]) / np.sqrt(2)
        elif motor == 'm3':  # 左前
            return np.array([-1, 1, 0]) / np.sqrt(2)
        else:  # 垂直电机
            return np.array([0, 0, 1])

    def _display_thrust_values(self, x, y, z, yaw):
        """在图表上显示当前推力值"""
        # 移除之前的文本
        for arrow in self.thrust_arrows:
            if isinstance(arrow, text.Text):
                if arrow.get_position()[0] < -1.5 or arrow.get_position()[0] > 1.5:
                    arrow.remove()

        # 在图表角落显示推力值
        thrust_info = f"X: {int(x)}\nY: {int(y)}\nZ: {int(z)}\nYaw: {int(yaw)}"
        text = self.axes.text(
            -1.8, 0, 0,
            thrust_info,
            fontsize=10,
            bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.5')
        )
        self.thrust_arrows.append(text)

    def _draw_resultant_thrust_vector(self, x, y, z):
        """绘制合成推力向量"""
        # 只有当有明显的推力时才绘制
        if abs(x) > 100 or abs(y) > 100 or abs(z) > 100:
            # 计算合成向量的起点 (ROV中心)
            start = np.array([0, 0, 0])

            # 计算合成向量
            # 使用对数缩放使向量长度合理
            scale = 0.5
            dx = np.sign(x) * np.log(abs(x) + 1) / np.log(6001) * scale
            dy = np.sign(y) * np.log(abs(y) + 1) / np.log(6001) * scale
            dz = np.sign(z) * np.log(abs(z) + 1) / np.log(6001) * scale

            # 绘制合成推力向量
            arrow = self.axes.quiver(
                start[0], start[1], start[2],
                dx, dy, dz,
                color='g',  # 绿色表示合成推力
                linewidth=3,
                arrow_length_ratio=0.2,
                alpha=0.7,
                length=np.sqrt(dx ** 2 + dy ** 2 + dz ** 2) * 2,
                normalize=False
            )
            self.thrust_arrows.append(arrow)

            # 添加合成推力标签
            magnitude = np.sqrt(x ** 2 + y ** 2 + z ** 2)
            if magnitude > 500:
                label_pos = start + np.array([dx, dy, dz]) * 1.2
                text = self.axes.text(
                    label_pos[0], label_pos[1], label_pos[2],
                    f"合成: {int(magnitude)}",
                    color='g',
                    fontsize=9,
                    horizontalalignment='center',
                    verticalalignment='center',
                    bbox=dict(facecolor='white', alpha=0.6, boxstyle='round,pad=0.3')
                )
                self.thrust_arrows.append(text)

    def calculate_motor_thrusts(self, x, y, z, yaw):
        """计算每个电机的推力值
        
        这是一个简化的模型，实际ROV的推力分配可能更复杂
        """
        # 简化的推力分配模型
        motor_thrusts = {
            'm0': x + yaw,  # 右前
            'm1': x - yaw,  # 右后
            'm2': -x - yaw,  # 左后
            'm3': -x + yaw,  # 左前
            'm4': z,  # 上前
            'm5': z  # 上后
        }

        # 添加Y方向的影响 (前后)
        motor_thrusts['m0'] += y
        motor_thrusts['m3'] += y
        motor_thrusts['m1'] -= y
        motor_thrusts['m2'] -= y

        return motor_thrusts

    def _setup_plot_style(self):
        """设置图表样式"""
        self.axes.set_title("ROV推力状态示意图")
        self.axes.set_xlabel("X轴")
        self.axes.set_ylabel("Y轴")
        self.axes.set_zlabel("Z轴")

        # 设置坐标轴范围
        self.axes.set_xlim([-2.0, 2.0])
        self.axes.set_ylim([-2.0, 2.0])
        self.axes.set_zlim([-0.8, 0.8])

        # 设置视角 - 正向俯视图 (Y轴向上)
        self.axes.view_init(elev=90, azim=0)

        # 设置背景色
        self.axes.set_facecolor('#f0f0f8')  # 浅蓝灰色背景

        # 设置网格
        self.axes.grid(True, linestyle='--', alpha=0.3)

        # 添加图例说明
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='r', lw=2, label='正向推力'),
            Line2D([0], [0], color='b', lw=2, label='负向推力'),
            Line2D([0], [0], color='g', lw=2, label='合成推力')
        ]
        self.axes.legend(handles=legend_elements, loc='upper right', framealpha=0.7)

        # 添加水平面参考
        x_grid = np.linspace(-2.0, 2.0, 5)
        y_grid = np.linspace(-2.0, 2.0, 5)
        X, Y = np.meshgrid(x_grid, y_grid)
        Z = np.zeros_like(X)
        self.axes.plot_surface(X, Y, Z, alpha=0.1, color='cyan')

    def on_press(self, event):
        if event.inaxes != self.axes: return
        for artist in self.points_artists:
            contains, _ = artist.contains(event)
            if contains:
                name = artist.get_gid()
                self._drag_point_info = (artist, name)
                self.point_selected.emit(name);
                return

    def on_motion(self, event):
        if self._drag_point_info is None or event.xdata is None or event.ydata is None: return
        artist, name = self._drag_point_info
        x, y = event.xdata, event.ydata

        if name in ['np_ini', 'pp_ini']:
            x, y = self.points_data[name]
        elif name in ['nt_end', 'pt_end']:
            y = self.points_data[name][1]

        artist.set_data([x], [y]);
        self.points_data[name] = (x, y)

        # Update parameters in real-time during dragging
        if name == 'nt_end':
            self.point_params['nt_end'] = x
        elif name == 'nt_mid':
            self.point_params['nt_mid'], self.point_params['np_mid'] = x, y
        elif name == 'pt_mid':
            self.point_params['pt_mid'], self.point_params['pp_mid'] = x, y
        elif name == 'pt_end':
            self.point_params['pt_end'] = x

        self._update_lines();
        self.draw()
        # Emit signal to update UI in real-time
        self.point_dragged.emit()

    def on_release(self, event):
        if self._drag_point_info is None: return
        artist, name = self._drag_point_info

        if name in ['np_ini', 'pp_ini']:
            self._drag_point_info = None
            return

        # Parameters are already updated in on_motion
        # Just release the drag point info
        self._drag_point_info = None

    def _update_lines(self):
        neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]
        self.lines[0].set_data(neg_x, neg_y);
        self.lines[1].set_data(pos_x, pos_y)

    def connect_events(self):
        self.mpl_connect('button_press_event', self.on_press);
        self.mpl_connect('motion_notify_event', self.on_motion)
        self.mpl_connect('button_release_event', self.on_release)


# --- 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROV 推力曲线调参上位机 V14 - 双曲线实时调整")
        self.setGeometry(100, 100, 1600, 1000)

        # Data Models
        self.motor_data = {};
        self.initial_motor_data = {};
        self.current_motor = "m0"
        self.comparison_motor = None  # 用于双曲线视图中的比较电机
        self.motor_selection_queue = []  # 用于存储选中的电机队列，最多保留两个
        self.disabled_curves = {}
        self.history_log = {f'm{i}': [] for i in range(MOTOR_COUNT)}
        self.dual_view_active = False  # 双曲线视图状态

        self.pwm_end_p = PWM_MID + PWM_HALF_P_DEFAULT;
        self.pwm_end_n = PWM_MID - PWM_HALF_N_DEFAULT
        self.bisection_target_info = {'name': None};
        self.bisection_bounds = {'low': None, 'high': None}
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
        self.target_address = ("192.168.0.233", 2200)

        # Track the current loaded JSON file path
        self.current_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "curve_beyond.json")

        self._init_ui()
        self.load_curve_data(self.current_json_path, is_initial_load=True)

        # Select the first motor button by default
        if self.motor_buttons and self.current_motor:
            self.on_motor_button_clicked(self.current_motor)

        # 初始化推力状态可视化
        self.update_thrust_visualization()

    def _init_ui(self):
        main_widget = QWidget();
        self.setCentralWidget(main_widget);

        # 使用QSplitter使界面可以调整大小
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(self.main_splitter)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # 添加到分割器
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)

        # 设置初始分割比例
        self.main_splitter.setSizes([400, 1200])

        # --- Left Panel ---
        # 创建左侧控制面板
        left_control_panel = QGroupBox("控制面板")
        left_control_layout = QVBoxLayout(left_control_panel)

        # 文件和网络组
        file_net_group = QGroupBox("文件 & 网络");
        file_net_layout = QGridLayout(file_net_group)
        self.load_btn = QPushButton("导入JSON");
        self.save_btn = QPushButton("导出JSON")
        self.ip_input = QLineEdit(self.target_address[0]);
        self.port_input = QLineEdit(str(self.target_address[1]))

        # 当前JSON文件显示
        self.current_json_label = QLabel("当前JSON文件:");
        self.current_json_display = QLineEdit()
        self.current_json_display.setReadOnly(True)
        self.current_json_display.setText(self.current_json_path)

        file_net_layout.addWidget(self.load_btn, 0, 0);
        file_net_layout.addWidget(self.save_btn, 0, 1)
        file_net_layout.addWidget(self.current_json_label, 1, 0)
        file_net_layout.addWidget(self.current_json_display, 1, 1)
        file_net_layout.addWidget(QLabel("目标IP:"), 2, 0);
        file_net_layout.addWidget(self.ip_input, 2, 1)
        file_net_layout.addWidget(QLabel("端口:"), 3, 0);
        file_net_layout.addWidget(self.port_input, 3, 1)

        # 电机选择与操作组
        motor_select_group = QGroupBox("电机选择与操作");
        motor_select_layout = QGridLayout(motor_select_group)

        # 创建电机选择按钮布局
        motor_buttons_layout = QHBoxLayout()
        self.motor_buttons = {}
        for i in range(MOTOR_COUNT):
            motor_name = f"m{i}"
            btn = QPushButton(motor_name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, name=motor_name: self.on_motor_button_clicked(name))
            self.motor_buttons[motor_name] = btn
            motor_buttons_layout.addWidget(btn)

        self.send_curve_btn = QPushButton("下发当前电机曲线");
        self.undo_btn = QPushButton("撤回上次下发")
        self.disable_motor_btn = QPushButton("禁用当前电机");
        self.restore_motor_btn = QPushButton("恢复当前电机")

        motor_select_layout.addWidget(QLabel("选择电机:"), 0, 0)
        motor_select_layout.addLayout(motor_buttons_layout, 0, 1)
        motor_select_layout.addWidget(self.send_curve_btn, 1, 0, 1, 2);
        motor_select_layout.addWidget(self.undo_btn, 2, 0, 1, 2)
        motor_select_layout.addWidget(self.disable_motor_btn, 3, 0);
        motor_select_layout.addWidget(self.restore_motor_btn, 3, 1)

        # 电机状态组
        all_status_group = QGroupBox("所有电机状态");
        self.all_status_layout = QGridLayout(all_status_group)
        self.all_motor_status_labels = {}
        for i in range(MOTOR_COUNT):
            name = f"m{i}";
            self.all_status_layout.addWidget(QLabel(f"{name}:"), i, 0)
            status_label = QLabel("[未知]");
            self.all_motor_status_labels[name] = status_label
            self.all_status_layout.addWidget(status_label, i, 1)

        # 操作历史组
        history_group = QGroupBox("操作历史");
        history_layout = QVBoxLayout(history_group)
        self.history_list_widget = QListWidget();
        self.restore_history_btn = QPushButton("恢复到选中历史")
        history_layout.addWidget(self.history_list_widget);
        history_layout.addWidget(self.restore_history_btn)

        # 添加所有组到左侧面板
        left_control_layout.addWidget(file_net_group);
        left_control_layout.addWidget(motor_select_group);
        left_control_layout.addWidget(all_status_group)
        left_control_layout.addWidget(history_group);
        left_control_layout.addStretch()

        # 将左侧控制面板添加到左侧布局
        left_layout.addWidget(left_control_panel)

        # --- Right Panel ---
        # 创建右侧主面板
        right_main_panel = QWidget()
        right_main_layout = QVBoxLayout(right_main_panel)
        right_main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()
        self.dual_view_btn = QPushButton("双曲线视图")
        self.dual_view_btn.setCheckable(True)
        self.dual_view_btn.clicked.connect(self.toggle_dual_view)
        toolbar_layout.addWidget(self.dual_view_btn)

        # 添加切换调整电机按钮
        self.switch_motor_btn = QPushButton("切换调整电机")
        self.switch_motor_btn.setEnabled(False)  # 初始禁用，只有在双曲线模式下才启用
        self.switch_motor_btn.clicked.connect(self.switch_editing_motor)
        toolbar_layout.addWidget(self.switch_motor_btn)
        
        toolbar_layout.addStretch()

        # 创建参数面板容器
        self.params_container = QWidget()
        params_layout = QHBoxLayout(self.params_container)
        params_layout.setContentsMargins(0, 0, 0, 0)

        # 主曲线参数组
        self.curve_params_group = QGroupBox("曲线核心参数 (当前电机)");
        self.curve_params_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        self.curve_params_layout = QGridLayout(self.curve_params_group)
        self.curve_params_layout.setVerticalSpacing(10)
        self.curve_params_layout.setHorizontalSpacing(15)

        # 创建参数输入框
        self.param_inputs = {};

        # 负向参数组
        neg_group = QGroupBox("负向参数")
        neg_layout = QGridLayout(neg_group)
        neg_layout.setVerticalSpacing(8)

        # 正向参数组
        pos_group = QGroupBox("正向参数")
        pos_layout = QGridLayout(pos_group)
        pos_layout.setVerticalSpacing(8)

        # 负向参数
        neg_params = [("nt_end", "推力终点"), ("nt_mid", "推力中点"), ("np_mid", "PWM中点"), ("np_ini", "PWM起点")]
        for i, (key, label) in enumerate(neg_params):
            neg_layout.addWidget(QLabel(f"{label}:"), i, 0)
            line_edit = QLineEdit()
            line_edit.setMinimumWidth(80)
            self.param_inputs[key] = line_edit
            neg_layout.addWidget(line_edit, i, 1)

        # 正向参数
        pos_params = [("pt_end", "推力终点"), ("pt_mid", "推力中点"), ("pp_mid", "PWM中点"), ("pp_ini", "PWM起点")]
        for i, (key, label) in enumerate(pos_params):
            pos_layout.addWidget(QLabel(f"{label}:"), i, 0)
            line_edit = QLineEdit()
            line_edit.setMinimumWidth(80)
            self.param_inputs[key] = line_edit
            pos_layout.addWidget(line_edit, i, 1)

        # PWM端点参数
        pwm_group = QGroupBox("PWM端点")
        pwm_layout = QGridLayout(pwm_group)
        self.pwm_end_n_input = QLineEdit(str(self.pwm_end_n))
        self.pwm_end_p_input = QLineEdit(str(self.pwm_end_p))
        pwm_layout.addWidget(QLabel("负端点:"), 0, 0)
        pwm_layout.addWidget(self.pwm_end_n_input, 0, 1)
        pwm_layout.addWidget(QLabel("正端点:"), 1, 0)
        pwm_layout.addWidget(self.pwm_end_p_input, 1, 1)

        # 添加参数组到主参数布局
        self.curve_params_layout.addWidget(neg_group, 0, 0)
        self.curve_params_layout.addWidget(pos_group, 0, 1)
        self.curve_params_layout.addWidget(pwm_group, 1, 0, 1, 2)

        # 创建比较曲线参数组 (初始隐藏)
        self.comparison_params_group = QGroupBox("比较电机参数");
        self.comparison_params_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0066cc; }")
        self.comparison_params_layout = QGridLayout(self.comparison_params_group)
        self.comparison_params_layout.setVerticalSpacing(10)
        self.comparison_params_layout.setHorizontalSpacing(15)

        # 比较电机选择
        comparison_select_layout = QHBoxLayout()
        self.comparison_motor_label = QLabel("选择比较电机:")
        self.comparison_motor_combo = QComboBox()
        for i in range(MOTOR_COUNT):
            self.comparison_motor_combo.addItem(f"m{i}")
        self.comparison_motor_combo.currentIndexChanged.connect(self.on_comparison_motor_changed)
        comparison_select_layout.addWidget(self.comparison_motor_label)
        comparison_select_layout.addWidget(self.comparison_motor_combo)
        comparison_select_layout.addStretch()

        # 比较电机参数输入框
        self.comparison_param_inputs = {}

        # 负向参数组 (比较)
        comp_neg_group = QGroupBox("负向参数")
        comp_neg_layout = QGridLayout(comp_neg_group)

        # 正向参数组 (比较)
        comp_pos_group = QGroupBox("正向参数")
        comp_pos_layout = QGridLayout(comp_pos_group)

        # 负向参数 (比较)
        for i, (key, label) in enumerate(neg_params):
            comp_neg_layout.addWidget(QLabel(f"{label}:"), i, 0)
            input_field = QLineEdit()
            input_field.setMinimumWidth(80)
            self.comparison_param_inputs[key] = input_field
            comp_neg_layout.addWidget(input_field, i, 1)

        # 正向参数 (比较)
        for i, (key, label) in enumerate(pos_params):
            comp_pos_layout.addWidget(QLabel(f"{label}:"), i, 0)
            input_field = QLineEdit()
            input_field.setMinimumWidth(80)
            self.comparison_param_inputs[key] = input_field
            comp_pos_layout.addWidget(input_field, i, 1)

        # 添加比较参数组到布局
        self.comparison_params_layout.addLayout(comparison_select_layout, 0, 0, 1, 2)
        self.comparison_params_layout.addWidget(comp_neg_group, 1, 0)
        self.comparison_params_layout.addWidget(comp_pos_group, 1, 1)

        # 初始隐藏比较参数组
        self.comparison_params_group.setVisible(False)

        # 二分查找辅助组
        bisection_group = QGroupBox("二分查找辅助");
        bisection_layout = QGridLayout(bisection_group)
        self.bisect_target_label = QLabel("目标点: [请在图上点击选择]");
        self.bisect_target_label.setStyleSheet("font-weight: bold;")
        self.bisect_low_bound_display = QLineEdit();
        self.bisect_low_bound_display.setReadOnly(True)
        self.bisect_high_bound_display = QLineEdit();
        self.bisect_high_bound_display.setReadOnly(True)
        self.too_high_btn = QPushButton("推力过大");
        self.too_low_btn = QPushButton("推力过小");
        self.suggest_next_btn = QPushButton("计算下一个建议值")

        bisection_layout.addWidget(self.bisect_target_label, 0, 0, 1, 2)
        bisection_layout.addWidget(QLabel("下限 (Low):"), 1, 0);
        bisection_layout.addWidget(self.bisect_low_bound_display, 1, 1)
        bisection_layout.addWidget(QLabel("上限 (High):"), 2, 0);
        bisection_layout.addWidget(self.bisect_high_bound_display, 2, 1)
        bisection_layout.addWidget(self.too_low_btn, 3, 0);
        bisection_layout.addWidget(self.too_high_btn, 3, 1)
        bisection_layout.addWidget(self.suggest_next_btn, 4, 0, 1, 2)

        # 添加到参数容器
        params_layout.addWidget(self.curve_params_group, 2)
        params_layout.addWidget(self.comparison_params_group, 2)
        params_layout.addWidget(bisection_group, 1)

        # 创建右侧顶部布局
        right_top_layout = QVBoxLayout()
        right_top_layout.addLayout(toolbar_layout)
        right_top_layout.addWidget(self.params_container)

        # 创建中间部分的可分割视图
        middle_splitter = QSplitter(Qt.Horizontal)
        middle_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 推力曲线面板
        plot_group = QGroupBox("推力曲线 (Thrust-PWM)");
        plot_layout = QVBoxLayout(plot_group)
        self.plot_canvas = DraggablePointPlot(self);
        self.plot_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout.addWidget(self.plot_canvas)

        # 推力状态可视化面板
        thrust_viz_group = QGroupBox("电机推力状态示意图");
        thrust_viz_layout = QVBoxLayout(thrust_viz_group)
        self.thrust_viz_canvas = ThrustVisualization(self);
        self.thrust_viz_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        thrust_viz_layout.addWidget(self.thrust_viz_canvas)

        # 添加到分割器
        middle_splitter.addWidget(plot_group)
        middle_splitter.addWidget(thrust_viz_group)
        middle_splitter.setSizes([1, 1])  # 均等分配空间

        # 运动控制面板
        motion_group = QGroupBox("直接运动控制");
        motion_layout = QGridLayout(motion_group)
        self.motion_sliders = {};
        self.motion_lineedits = {};
        axes = ["X", "Y", "Z", "Yaw"]
        for i, axis in enumerate(axes):
            slider = QSlider(Qt.Horizontal);
            slider.setRange(-6000, 6000);
            line_edit = QLineEdit("0")
            motion_layout.addWidget(QLabel(f"{axis} 推力:"), i, 0);
            motion_layout.addWidget(slider, i, 1)
            motion_layout.addWidget(line_edit, i, 2);
            self.motion_sliders[axis.lower()] = slider;
            self.motion_lineedits[axis.lower()] = line_edit
        self.send_motion_btn = QPushButton("下发运动指令");
        self.zero_motion_btn = QPushButton("所有轴置零")
        motion_layout.addWidget(self.send_motion_btn, len(axes), 0, 1, 2);
        motion_layout.addWidget(self.zero_motion_btn, len(axes), 2)

        # 添加所有组件到右侧主布局
        right_main_layout.addLayout(right_top_layout)
        right_main_layout.addWidget(middle_splitter, 4)  # 给中间部分更多空间
        right_main_layout.addWidget(motion_group)

        # 将右侧主面板添加到右侧布局
        right_layout.addWidget(right_main_panel)
        self._connect_signals()

    def _connect_signals(self):
        self.load_btn.clicked.connect(self.on_load_clicked);
        self.save_btn.clicked.connect(self.on_save_clicked)
        # Motor selection is now handled by buttons

        self.plot_canvas.point_dragged.connect(self.on_plot_drag_finished)
        self.plot_canvas.point_selected.connect(self.on_point_selected_for_bisect);
        self.plot_canvas.connect_events()

        # Connect primary motor parameter inputs to real-time update handlers
        for line_edit in self.param_inputs.values():
            line_edit.textChanged.connect(self.on_param_text_changed)

        # Keep editingFinished for validation
        for line_edit in self.param_inputs.values():
            line_edit.editingFinished.connect(self.on_param_edited)

        # Connect comparison motor parameter inputs to real-time update handlers
        for line_edit in self.comparison_param_inputs.values():
            line_edit.textChanged.connect(self.on_comparison_param_text_changed)

        # Keep editingFinished for validation
        for line_edit in self.comparison_param_inputs.values():
            line_edit.editingFinished.connect(self.on_comparison_param_edited)

        # Connect PWM end inputs
        self.pwm_end_n_input.textChanged.connect(self.on_end_pwm_text_changed)
        self.pwm_end_p_input.textChanged.connect(self.on_end_pwm_text_changed)
        self.pwm_end_n_input.editingFinished.connect(self.on_end_pwm_edited)
        self.pwm_end_p_input.editingFinished.connect(self.on_end_pwm_edited)

        self.send_curve_btn.clicked.connect(self.on_send_curve);
        self.undo_btn.clicked.connect(self.on_undo)
        self.disable_motor_btn.clicked.connect(self.on_disable_motor);
        self.restore_motor_btn.clicked.connect(self.on_restore_motor)
        self.restore_history_btn.clicked.connect(self.on_restore_history)

        for axis, slider in self.motion_sliders.items():
            slider.valueChanged.connect(
                lambda value, a=axis: self._on_slider_value_changed(value, a))
        for axis, line_edit in self.motion_lineedits.items():
            line_edit.editingFinished.connect(
                lambda a=axis: self._on_lineedit_value_changed(a))
        self.send_motion_btn.clicked.connect(self.on_send_motion);
        self.zero_motion_btn.clicked.connect(self.on_zero_motion)

        self.too_high_btn.clicked.connect(lambda: self.on_evaluate_curve(is_high=True))
        self.too_low_btn.clicked.connect(lambda: self.on_evaluate_curve(is_high=False));
        self.suggest_next_btn.clicked.connect(self.on_suggest_next)

    # --- Slot Functions ---
    def on_plot_drag_finished(self):
        # 如果在双曲线视图中，需要将比较参数同步回motor_data
        if self.dual_view_active and hasattr(self.plot_canvas, 'comparison_params'):
            if self.comparison_motor and self.comparison_motor in self.motor_data:
                # 将DraggablePointPlot中的comparison_params同步到motor_data
                self.motor_data[self.comparison_motor].update(self.plot_canvas.comparison_params)

                # 更新比较电机参数输入框
                comparison_params = self.motor_data[self.comparison_motor]
                for key, line_edit in self.comparison_param_inputs.items():
                    line_edit.setText(f"{comparison_params.get(key, 0.0):.2f}")

        # 更新主电机参数输入框
        if self.current_motor and self.current_motor in self.motor_data:
            params = self.motor_data[self.current_motor]
            for key, line_edit in self.param_inputs.items():
                line_edit.setText(f"{params.get(key, 0.0):.2f}")

        # 更新其他UI元素
        self._update_all_motor_statuses()
        self._update_history_list()

    def on_param_text_changed(self, text):
        """实时处理参数输入变化"""
        try:
            if not self.current_motor: return

            # 找出是哪个输入框触发了事件
            sender = self.sender()
            for key, line_edit in self.param_inputs.items():
                if line_edit == sender:
                    # 尝试将文本转换为浮点数
                    try:
                        value = float(text)
                        # 更新数据模型
                        self.motor_data[self.current_motor][key] = value
                        # 更新曲线图但不更新其他输入框
                        self._update_curve_only()
                    except ValueError:
                        # 如果输入不是有效的数字，不更新
                        pass
                    break
        except Exception:
            # 忽略任何其他错误
            pass

    def on_param_edited(self):
        """完成编辑后的验证和完整更新"""
        try:
            if not self.current_motor: return
            for key, line_edit in self.param_inputs.items():
                try:
                    self.motor_data[self.current_motor][key] = float(line_edit.text())
                except ValueError:
                    # 如果值无效，重置为上一个有效值
                    line_edit.setText(f"{self.motor_data[self.current_motor].get(key, 0.0):.2f}")
            # 完整更新UI
            self._update_ui_for_motor()
        except (ValueError, KeyError):
            pass

    def on_end_pwm_text_changed(self, text):
        """实时处理PWM端点输入变化"""
        try:
            sender = self.sender()
            if sender == self.pwm_end_n_input:
                try:
                    self.pwm_end_n = float(text)
                    self._update_curve_only()
                except ValueError:
                    pass
            elif sender == self.pwm_end_p_input:
                try:
                    self.pwm_end_p = float(text)
                    self._update_curve_only()
                except ValueError:
                    pass
        except Exception:
            pass

    def on_end_pwm_edited(self):
        """完成PWM端点编辑后的验证和完整更新"""
        try:
            try:
                self.pwm_end_n = float(self.pwm_end_n_input.text())
            except ValueError:
                self.pwm_end_n_input.setText(f"{self.pwm_end_n:.2f}")

            try:
                self.pwm_end_p = float(self.pwm_end_p_input.text())
            except ValueError:
                self.pwm_end_p_input.setText(f"{self.pwm_end_p:.2f}")

            self._update_ui_for_motor()
        except Exception:
            pass

    def on_comparison_param_text_changed(self, text):
        """实时处理比较电机参数输入变化"""
        try:
            if not self.comparison_motor: return

            # 找出是哪个输入框触发了事件
            sender = self.sender()
            for key, line_edit in self.comparison_param_inputs.items():
                if line_edit == sender:
                    # 尝试将文本转换为浮点数
                    try:
                        value = float(text)
                        # 更新数据模型
                        self.motor_data[self.comparison_motor][key] = value
                        # 更新曲线图但不更新其他输入框
                        self._update_curve_only()
                    except ValueError:
                        # 如果输入不是有效的数字，不更新
                        pass
                    break
        except Exception:
            # 忽略任何其他错误
            pass

    def on_comparison_param_edited(self):
        """完成比较电机参数编辑后的验证和完整更新"""
        try:
            if not self.comparison_motor: return
            for key, line_edit in self.comparison_param_inputs.items():
                try:
                    self.motor_data[self.comparison_motor][key] = float(line_edit.text())
                except ValueError:
                    # 如果值无效，重置为上一个有效值
                    line_edit.setText(f"{self.motor_data[self.comparison_motor].get(key, 0.0):.2f}")
            # 更新曲线图
            self._update_curve_only()
        except (ValueError, KeyError):
            pass

    def toggle_dual_view(self, checked):
        """切换双曲线视图模式"""
        self.dual_view_active = checked
        self.comparison_params_group.setVisible(checked)

        # 启用/禁用切换调整电机按钮
        self.switch_motor_btn.setEnabled(checked)

        # 添加当前正在编辑的电机标识
        self.editing_primary_motor = True  # 默认编辑主电机

        if checked:
            # 检查是否已经通过按钮选择了比较电机
            has_selected_comparison = False
            for name, btn in self.motor_buttons.items():
                if btn.isChecked() and name != self.current_motor:
                    self.comparison_motor = name
                    self.comparison_motor_combo.setCurrentText(name)
                    # 设置比较电机按钮样式
                    btn.setStyleSheet("background-color: #D6E9F1;")  # 浅蓝色
                    has_selected_comparison = True
                    break

            # 如果没有通过按钮选择比较电机，不自动选择，而是提示用户
            if not has_selected_comparison and not self.comparison_motor:
                QMessageBox.information(self, "选择比较电机",
                                        "请在电机选择与操作区域中选择一个电机作为比较电机。")

            # 更新比较电机参数显示
            if self.comparison_motor:
                self._update_comparison_params()

                # 更新UI以显示当前正在编辑的电机
                self._update_editing_motor_ui()
        else:
            # 关闭双曲线视图时，取消比较电机的选中状态
            if self.comparison_motor and self.comparison_motor in self.motor_buttons:
                self.motor_buttons[self.comparison_motor].setChecked(False)
                self.motor_buttons[self.comparison_motor].setStyleSheet("")
            self.comparison_motor = None

        # 更新曲线显示
        self._update_curve_only()

    def switch_editing_motor(self):
        """切换当前正在编辑的电机（主电机/比较电机）"""
        if not self.dual_view_active:
            return

        # 切换编辑状态
        self.editing_primary_motor = not self.editing_primary_motor

        # 更新UI以反映当前编辑的电机
        self._update_editing_motor_ui()

        # 更新曲线显示以改变实线/虚线
        self._update_curve_only()

    def _update_editing_motor_ui(self):
        """更新UI以显示当前正在编辑的电机"""
        if self.editing_primary_motor:
            # 编辑主电机
            self.curve_params_group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #f0f0ff; }")
            self.comparison_params_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0066cc; }")
            self.switch_motor_btn.setText(f"当前编辑: {self.current_motor} (点击切换)")

            # 更新按钮样式，主电机使用实线边框
            if self.current_motor in self.motor_buttons:
                self.motor_buttons[self.current_motor].setStyleSheet(
                    "background-color: #AED6F1; border: 2px solid #2980B9;")
            if self.comparison_motor in self.motor_buttons:
                self.motor_buttons[self.comparison_motor].setStyleSheet(
                    "background-color: #D6E9F1; border: 1px dashed #5DADE2;")
        else:
            # 编辑比较电机
            self.curve_params_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            self.comparison_params_group.setStyleSheet(
                "QGroupBox { font-weight: bold; color: #0066cc; background-color: #f0f0ff; }")
            self.switch_motor_btn.setText(f"当前编辑: {self.comparison_motor} (点击切换)")

            # 更新按钮样式，比较电机使用实线边框
            if self.current_motor in self.motor_buttons:
                self.motor_buttons[self.current_motor].setStyleSheet(
                    "background-color: #AED6F1; border: 1px dashed #2980B9;")
            if self.comparison_motor in self.motor_buttons:
                self.motor_buttons[self.comparison_motor].setStyleSheet(
                    "background-color: #D6E9F1; border: 2px solid #5DADE2;")

    def on_comparison_motor_changed(self, index):
        """处理比较电机选择变化"""
        if index >= 0:
            new_comparison_motor = self.comparison_motor_combo.itemText(index)

            # 如果选择了与当前电机相同的电机，则忽略
            if new_comparison_motor == self.current_motor:
                # 恢复下拉框到之前的选择
                if self.comparison_motor:
                    self.comparison_motor_combo.setCurrentText(self.comparison_motor)
                return

            # 清除旧的比较电机按钮选中状态
            if self.comparison_motor and self.comparison_motor in self.motor_buttons:
                self.motor_buttons[self.comparison_motor].setChecked(False)
                self.motor_buttons[self.comparison_motor].setStyleSheet("")

            # 更新比较电机
            self.comparison_motor = new_comparison_motor

            # 更新按钮选中状态
            if self.comparison_motor in self.motor_buttons:
                self.motor_buttons[self.comparison_motor].setChecked(True)
                self.motor_buttons[self.comparison_motor].setStyleSheet("background-color: #D6E9F1;")  # 浅蓝色

            # 更新参数和曲线
            self._update_comparison_params()
            self._update_curve_only()

            # 如果当前正在编辑比较电机，更新UI以显示新的比较电机名称
            if self.dual_view_active and not self.editing_primary_motor:
                self._update_editing_motor_ui()

    def _update_comparison_params(self):
        """更新比较电机参数显示"""
        if not self.comparison_motor or self.comparison_motor not in self.motor_data:
            return

        params = self.motor_data[self.comparison_motor]
        for key, input_field in self.comparison_param_inputs.items():
            input_field.setText(f"{params.get(key, 0.0):.2f}")

    def _update_curve_only(self):
        """只更新曲线图，不更新其他输入框"""
        if not self.current_motor or self.current_motor not in self.motor_data:
            return

        params = self.motor_data[self.current_motor]

        if self.dual_view_active and self.comparison_motor and self.comparison_motor in self.motor_data:
            # 双曲线模式 - 显示当前电机和比较电机的曲线
            comparison_params = self.motor_data[self.comparison_motor]
            self.plot_canvas.plot_dual_curves(
                params,
                comparison_params,
                self.pwm_end_p,
                self.pwm_end_n,
                self.current_motor,
                self.comparison_motor,
                self.editing_primary_motor  # 传递当前正在编辑的是哪个电机
            )
        else:
            # 单曲线模式 - 只显示当前电机的曲线
            self.plot_canvas.plot_curve(params, self.pwm_end_p, self.pwm_end_n)

    def on_point_selected_for_bisect(self, name):
        self.bisection_target_info['name'] = name;
        self.bisection_bounds = {'low': None, 'high': None}
        self.bisect_target_label.setText(f"目标点: {name} (PWM)");
        self.bisect_target_label.setStyleSheet("color: blue;")
        self.bisect_low_bound_display.clear()
        self.bisect_high_bound_display.clear()

    def on_evaluate_curve(self, is_high):
        if not self.current_motor: return
        name = self.bisection_target_info['name']
        if not name: QMessageBox.warning(self, "错误", "请先在图上点击一个点作为二分查找的目标。"); return
        key_map = {'nt_mid': 'np_mid', 'np_ini': 'np_ini', 'pp_ini': 'pp_ini', 'pt_mid': 'pp_mid'}
        pwm_key = key_map.get(name)
        if not pwm_key: QMessageBox.warning(self, "错误", "此点PWM值不可用于二分搜索，请选择其他点。"); return
        current_value = self.motor_data[self.current_motor][pwm_key]
        bound_display = self.bisect_high_bound_display if is_high else self.bisect_low_bound_display

        if is_high:
            self.bisection_bounds['high'] = current_value
        else:
            self.bisection_bounds['low'] = current_value

        bound_display.setText(f"{current_value:.2f}")
        QMessageBox.information(self, "边界设置",
                                f"已将 {pwm_key} 的 {'上限' if is_high else '下限'} 设置为: {current_value:.2f}")

    def on_suggest_next(self):
        if not self.current_motor: return
        if self.bisection_bounds['low'] is None or self.bisection_bounds['high'] is None: QMessageBox.warning(self,
                                                                                                              "错误",
                                                                                                              "请先设置推力过大和过小的边界。"); return
        name = self.bisection_target_info['name']
        key_map = {'nt_mid': 'np_mid', 'np_ini': 'np_ini', 'pp_ini': 'pp_ini', 'pt_mid': 'pp_mid'}
        pwm_key = key_map.get(name)
        if not pwm_key: return
        mid_value = (self.bisection_bounds['low'] + self.bisection_bounds['high']) / 2.0
        self.motor_data[self.current_motor][pwm_key] = mid_value;
        self._update_ui_for_motor()
        QMessageBox.information(self, "建议值", f"已将 {pwm_key} 更新为建议值: {mid_value:.2f}\n请下发曲线以测试效果。")

    def on_motor_button_clicked(self, motor_name):
        # 检查电机按钮的当前状态
        is_checked = self.motor_buttons[motor_name].isChecked()

        # 如果按钮被取消选中
        if not is_checked:
            # 如果是当前主电机，不允许取消选中
            if motor_name == self.current_motor:
                self.motor_buttons[motor_name].setChecked(True)
                return

            # 如果是比较电机，则移除它
            if motor_name == self.comparison_motor:
                self.comparison_motor = None
                self.motor_buttons[motor_name].setStyleSheet("")

                # 从队列中移除
                if motor_name in self.motor_selection_queue:
                    self.motor_selection_queue.remove(motor_name)

                # 更新UI
                self._update_comparison_params()
                self._update_curve_only()
            return

        # 如果按钮被选中
        # 将电机添加到选择队列
        if motor_name not in self.motor_selection_queue:
            self.motor_selection_queue.append(motor_name)

        # 如果队列超过2个，移除最早的一个（不是当前主电机）
        if len(self.motor_selection_queue) > 2:
            # 找到要移除的电机（不是当前选中的电机）
            to_remove = None
            for m in self.motor_selection_queue:
                if m != motor_name and m != self.current_motor:
                    to_remove = m
                    break

            # 如果没有找到可移除的（说明队列中只有当前电机和主电机），移除最早的一个
            if to_remove is None and len(self.motor_selection_queue) > 0:
                to_remove = self.motor_selection_queue[0]

            # 移除电机
            if to_remove is not None:
                self.motor_selection_queue.remove(to_remove)

                # 更新UI状态
                if to_remove in self.motor_buttons:
                    self.motor_buttons[to_remove].setChecked(False)
                    self.motor_buttons[to_remove].setStyleSheet("")

                # 如果移除的是比较电机，清除比较电机
                if to_remove == self.comparison_motor:
                    self.comparison_motor = None

        # 检查是否在双曲线视图模式下且已有主电机选择
        if self.dual_view_active and self.current_motor and self.current_motor != motor_name:
            # 设置为比较电机
            self.comparison_motor = motor_name
            # 更新下拉框中的比较电机
            self.comparison_motor_combo.setCurrentText(motor_name)
            # 高亮显示为比较电机
            self.motor_buttons[motor_name].setStyleSheet("background-color: #D6E9F1;")  # 比较电机使用浅蓝色

            # 更新UI
            self._update_comparison_params()
            self._update_curve_only()
            return

        # 标准单电机选择行为
        self.current_motor = motor_name

        # 如果有比较电机被选中，在更改主电机时清除它
        if self.comparison_motor:
            old_comp = self.comparison_motor
            self.comparison_motor = None
            self.motor_buttons[old_comp].setChecked(False)
            self.motor_buttons[old_comp].setStyleSheet("")

            # 从队列中移除
            if old_comp in self.motor_selection_queue:
                self.motor_selection_queue.remove(old_comp)

        # 更新按钮状态（高亮显示选中的电机）
        for name, btn in self.motor_buttons.items():
            if name == motor_name:
                btn.setStyleSheet("background-color: #AED6F1;")  # 主电机颜色
            elif name != self.comparison_motor:  # 不取消选中比较电机
                btn.setChecked(False)
                btn.setStyleSheet("")

        # 确保当前电机在队列中
        if motor_name not in self.motor_selection_queue:
            self.motor_selection_queue.append(motor_name)

        # 更新UI以显示选中的电机数据
        self._update_ui_for_motor()

    def on_send_curve(self, curve_to_send=None):
        if not self.current_motor: return
        params_to_log = self.motor_data[self.current_motor].copy()
        history_entry = {'timestamp': datetime.now(), 'data': params_to_log}
        self.history_log[self.current_motor].append(history_entry)

        self.target_address = (self.ip_input.text(), int(self.port_input.text()))
        motor_params = curve_to_send if curve_to_send else self.motor_data[self.current_motor]

        data_to_send = {
            "cmd": "thrust_init", "motor": motor_params.get('num', 0),
            "np_mid": motor_params.get('np_mid'), "np_ini": motor_params.get('np_ini'),
            "pp_ini": motor_params.get('pp_ini'), "pp_mid": motor_params.get('pp_mid'),
            "nt_end": motor_params.get('nt_end'), "nt_mid": motor_params.get('nt_mid'),
            "pt_mid": motor_params.get('pt_mid'), "pt_end": motor_params.get('pt_end')
        }

        json_str_with_newline = json.dumps(data_to_send) + "\n"
        threading.Thread(target=self._send_udp_worker, args=(json_str_with_newline.encode(), 5, 0.05)).start()
        QMessageBox.information(self, "发送中", f"正在下发电机 {self.current_motor} 的曲线...")
        self._update_history_list()

    def on_undo(self):
        if self.history_log.get(self.current_motor):
            history_entry = self.history_log[self.current_motor].pop()
            self.motor_data[self.current_motor] = history_entry['data']
            self._update_ui_for_motor()
        else:
            QMessageBox.warning(self, "无法撤回", "没有可撤回的操作。")

    def on_restore_history(self):
        selected_items = self.history_list_widget.selectedItems()
        if not selected_items: QMessageBox.warning(self, "错误", "请先在历史列表中选择一个记录。"); return
        history_entry = selected_items[0].data(Qt.UserRole)
        self.motor_data[self.current_motor] = history_entry['data']
        self._update_ui_for_motor()

    def on_disable_motor(self):
        if not self.current_motor: return
        self.disabled_curves[self.current_motor] = self.motor_data[self.current_motor].copy()

        # *** NEW LOGIC FOR DISABLING MOTOR ***
        flat_curve = self.motor_data[self.current_motor].copy()
        flat_curve.update({
            'nt_end': -10000.0, 'nt_mid': -10000.0, 'pt_mid': 10000.0, 'pt_end': 10000.0,  # Set all thrust points to 0
            'np_mid': 3000.0, 'pp_mid': 3000.0,  # Set mid PWMs to neutral
            'np_ini': 3000.0, 'pp_ini': 3000.0  # Set deadzone PWMs to neutral
        })
        self.on_send_curve(curve_to_send=flat_curve);
        self._update_all_motor_statuses()

    def on_restore_motor(self):
        if self.current_motor in self.disabled_curves:
            self.motor_data[self.current_motor] = self.disabled_curves.pop(self.current_motor)
            self._update_ui_for_motor();
            self.on_send_curve()
        else:
            QMessageBox.warning(self, "无法恢复", "该电机没有被禁用的记录。")

    def load_curve_data(self, filepath, is_initial_load=False):
        try:
            with open(filepath, 'r') as f:
                loaded_data = json.load(f)

            # Standardize the keys from the loaded data
            self.motor_data = {}
            for original_key, params in loaded_data.items():
                match = re.search(r'\d+', original_key)
                if match:
                    motor_id = int(match.group(0))
                    standard_key = f'm{motor_id}'
                    params['num'] = motor_id
                    self.motor_data[standard_key] = params

            if is_initial_load:
                self.initial_motor_data = self.motor_data.copy()
                self.history_log = {key: [] for key in self.motor_data.keys()}

            # Keep track of current selection
            current_selection = self.current_motor

            # If current selection is not in the loaded data, select the first motor
            if current_selection not in self.motor_data:
                self.current_motor = next(iter(sorted(self.motor_data.keys()))) if self.motor_data else ""

            # Update motor buttons based on loaded data
            for motor_name, btn in self.motor_buttons.items():
                if motor_name in self.motor_data:
                    btn.setEnabled(True)
                    btn.setChecked(motor_name == self.current_motor)
                    if motor_name == self.current_motor:
                        btn.setStyleSheet("background-color: #AED6F1;")
                    else:
                        btn.setStyleSheet("")
                else:
                    btn.setEnabled(False)
                    btn.setChecked(False)
                    btn.setStyleSheet("background-color: #F2F2F2;")

            # Update the current JSON path display
            self.current_json_path = filepath
            self.current_json_display.setText(filepath)

            self._update_ui_for_motor()

        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"无法加载或解析JSON文件: {e}")

    def save_curve_data(self, filepath):
        try:
            with open(filepath, 'w') as f:
                json.dump(self.motor_data, f, indent=4)
            self.initial_motor_data = self.motor_data.copy()

            # Update the current JSON path display
            self.current_json_path = filepath
            self.current_json_display.setText(filepath)

            self._update_all_motor_statuses()
            QMessageBox.information(self, "成功", f"数据已保存到 {filepath}。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存文件: {e}")

    def on_load_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "导入JSON", "", "*.json");
        if filepath:
            self.load_curve_data(filepath, is_initial_load=True)

    def on_save_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "导出JSON", "", "*.json");
        if filepath:
            self.save_curve_data(filepath)

    def on_send_motion(self):
        self.target_address = (self.ip_input.text(), int(self.port_input.text()));
        mc = {a: float(le.text()) for a, le in self.motion_lineedits.items()};
        mc.update({"s0": 0.0, "s1": 0.0});
        self.udp_socket.sendto((json.dumps(mc) + "\n").encode(), self.target_address)

        # 更新推力状态可视化
        self.update_thrust_visualization()

    def on_zero_motion(self):
        [s.setValue(0) for s in self.motion_sliders.values()]

        # 更新推力状态可视化
        self.update_thrust_visualization()

    def _on_slider_value_changed(self, value, axis):
        """处理滑块值变化"""
        # 更新对应的文本框
        self.motion_lineedits[axis].setText(str(value))

        # 更新推力状态可视化
        self.update_thrust_visualization()

    def _on_lineedit_value_changed(self, axis):
        """处理文本框值变化"""
        try:
            # 更新对应的滑块
            value = int(self.motion_lineedits[axis].text() or "0")
            self.motion_sliders[axis].setValue(value)

            # 推力状态可视化会在滑块值变化时自动更新
        except ValueError:
            # 如果输入不是有效的数字，重置为0
            self.motion_lineedits[axis].setText("0")
            self.motion_sliders[axis].setValue(0)
            self.update_thrust_visualization()

    def update_thrust_visualization(self):
        """更新推力状态可视化"""
        # 获取当前的X, Y, Z, Yaw值
        x_thrust = float(self.motion_lineedits.get('x', QLineEdit("0")).text() or "0")
        y_thrust = float(self.motion_lineedits.get('y', QLineEdit("0")).text() or "0")
        z_thrust = float(self.motion_lineedits.get('z', QLineEdit("0")).text() or "0")
        yaw_thrust = float(self.motion_lineedits.get('yaw', QLineEdit("0")).text() or "0")

        # 更新推力状态可视化
        self.thrust_viz_canvas.update_thrust(x_thrust, y_thrust, z_thrust, yaw_thrust)

    # --- UI Update & Helper Methods ---
    def _update_ui_for_motor(self):
        if self.current_motor and self.current_motor in self.motor_data:
            # 更新主电机参数输入框
            params = self.motor_data[self.current_motor]
            for key, line_edit in self.param_inputs.items():
                line_edit.setText(f"{params.get(key, 0.0):.2f}")

            # 如果在双曲线视图模式下，也更新比较电机参数输入框
            if self.dual_view_active and self.comparison_motor and self.comparison_motor in self.motor_data:
                comparison_params = self.motor_data[self.comparison_motor]
                for key, line_edit in self.comparison_param_inputs.items():
                    line_edit.setText(f"{comparison_params.get(key, 0.0):.2f}")

            # 使用_update_curve_only代替plot_curve以保持双曲线视图状态
            self._update_curve_only()
            self._update_all_motor_statuses();
            self._update_history_list()

    def _update_all_motor_statuses(self):
        for name, label in self.all_motor_status_labels.items():
            if name in self.disabled_curves:
                label.setText("[已禁用]");
                label.setStyleSheet("color: orange;")
            elif self.motor_data.get(name) != self.initial_motor_data.get(name):
                label.setText("[已修改]");
                label.setStyleSheet("color: red;")
            else:
                label.setText("[正常]");
                label.setStyleSheet("color: green;")

    def _update_history_list(self):
        if not self.current_motor: return
        self.history_list_widget.clear()
        motor_history = self.history_log.get(self.current_motor, [])
        for entry in reversed(motor_history):
            item = QListWidgetItem(entry['timestamp'].strftime("%H:%M:%S - Curve Sent"))
            item.setData(Qt.UserRole, entry)
            self.history_list_widget.addItem(item)

    def _send_udp_worker(self, data, count, interval):
        for i in range(count):
            try:
                self.udp_socket.sendto(data, self.target_address);
                print(f"Sent ({i + 1}/{count}): {data.decode().strip()}");
                time.sleep(interval)
            except Exception as e:
                print(f"UDP发送错误: {e}")


def run_performance_test():
    """运行性能测试，验证拖拽刷新速度和双曲线编辑功能"""
    print("开始性能测试...")

    # 创建应用程序和主窗口
    app = QApplication(sys.argv)
    main_win = MainWindow()

    # 显示窗口
    main_win.show()

    # 等待窗口完全加载
    QTimer.singleShot(1000, lambda: _run_test_steps(main_win))

    return app.exec_()


def _run_test_steps(main_win):
    """执行测试步骤"""
    # 步骤1: 启用双曲线视图
    print("步骤1: 启用双曲线视图")
    main_win.dual_view_btn.click()

    # 步骤2: 选择不同的比较电机
    print("步骤2: 选择不同的比较电机")
    if main_win.current_motor != "m1":
        main_win.comparison_motor_combo.setCurrentText("m1")
    else:
        main_win.comparison_motor_combo.setCurrentText("m2")

    # 步骤3: 切换编辑电机
    print("步骤3: 切换编辑电机")
    main_win.switch_motor_btn.click()

    # 步骤4: 修改比较电机参数
    print("步骤4: 修改比较电机参数")
    for key, input_field in main_win.comparison_param_inputs.items():
        if key == "nt_mid":
            current_value = float(input_field.text())
            input_field.setText(str(current_value - 50))
            break

    # 步骤5: 切换回主电机
    print("步骤5: 切换回主电机")
    main_win.switch_motor_btn.click()

    # 步骤6: 修改主电机参数
    print("步骤6: 修改主电机参数")
    for key, input_field in main_win.param_inputs.items():
        if key == "pt_mid":
            current_value = float(input_field.text())
            input_field.setText(str(current_value + 50))
            break

    print("测试完成! 请检查UI响应速度和双曲线编辑功能是否正常工作。")


if __name__ == '__main__':
    # 正常启动应用程序
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 运行性能测试
        sys.exit(run_performance_test())
    else:
        # 正常启动
        app = QApplication(sys.argv)
        main_win = MainWindow()
        main_win.show()
        sys.exit(app.exec_())
