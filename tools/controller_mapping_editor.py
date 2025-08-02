"""
控制器映射编辑器
用于检查和修改ROV控制系统的控制器映射
"""

import os
import sys
from configparser import ConfigParser

import pygame
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QMessageBox, QFileDialog, QGroupBox,
    QSpinBox, QDoubleSpinBox, QFormLayout, QTabWidget
)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.config_manager import ConfigManager


class AxisMappingWidget(QWidget):
    """轴映射编辑组件"""

    def __init__(self, config_manager, axis_name, parent=None):
        """初始化轴映射编辑组件"""
        super().__init__(parent)
        self.config_manager = config_manager
        self.axis_name = axis_name

        # 获取当前配置
        self.axis_config = self.config_manager.get_axis_config(axis_name)

        # 创建布局
        layout = QFormLayout(self)

        # 创建轴选择下拉框
        self.axis_combo = QSpinBox()
        self.axis_combo.setMinimum(0)
        self.axis_combo.setMaximum(10)  # 假设最多11个轴
        self.axis_combo.setValue(self.axis_config["axis"])
        layout.addRow("轴编号:", self.axis_combo)

        # 创建死区设置
        self.deadzone_spin = QDoubleSpinBox()
        self.deadzone_spin.setMinimum(0.0)
        self.deadzone_spin.setMaximum(1.0)
        self.deadzone_spin.setSingleStep(0.01)
        self.deadzone_spin.setValue(self.axis_config["deadzone"])
        layout.addRow("死区值:", self.deadzone_spin)

        # 创建最大值设置
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setMinimum(-10000.0)
        self.max_spin.setMaximum(10000.0)
        self.max_spin.setSingleStep(100.0)
        self.max_spin.setValue(self.axis_config["max"])
        layout.addRow("最大值:", self.max_spin)

        # 创建测试区域
        self.test_label = QLabel("未检测到控制器")
        layout.addRow("当前值:", self.test_label)

        # 创建应用按钮
        self.apply_button = QPushButton("应用更改")
        self.apply_button.clicked.connect(self.apply_changes)
        layout.addRow("", self.apply_button)

    def update_test_value(self, joystick):
        """更新测试值显示"""
        if joystick and self.axis_combo.value() < joystick.get_numaxes():
            value = joystick.get_axis(self.axis_combo.value())
            self.test_label.setText(f"{value:.2f}")
        else:
            self.test_label.setText("轴不可用")

    def apply_changes(self):
        """应用更改到配置"""
        try:
            # 更新配置
            self.config_manager.config[self.axis_name]["axis"] = str(self.axis_combo.value())
            self.config_manager.config[self.axis_name]["deadzone"] = str(self.deadzone_spin.value())
            self.config_manager.config[self.axis_name]["max"] = str(self.max_spin.value())

            # 更新本地配置
            self.axis_config = self.config_manager.get_axis_config(self.axis_name)

            QMessageBox.information(self, "更改已应用",
                                    f"{self.axis_name}轴映射已更新。\n注意：需要保存配置文件才能永久保存更改。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用更改时出错: {str(e)}")


class ButtonMappingWidget(QWidget):
    """按钮映射编辑组件"""

    def __init__(self, config_manager, section, key, description, parent=None):
        """初始化按钮映射编辑组件"""
        super().__init__(parent)
        self.config_manager = config_manager
        self.section = section
        self.key = key
        self.description = description

        # 获取当前配置
        self.button_value = self.config_manager.config[section].getint(key)

        # 创建布局
        layout = QFormLayout(self)

        # 创建描述标签
        desc_label = QLabel(description)
        font = desc_label.font()
        font.setBold(True)
        desc_label.setFont(font)
        layout.addRow(desc_label)

        # 创建按钮选择下拉框
        self.button_combo = QSpinBox()
        self.button_combo.setMinimum(0)
        self.button_combo.setMaximum(15)  # 假设最多16个按钮
        self.button_combo.setValue(self.button_value)
        layout.addRow("按钮编号:", self.button_combo)

        # 创建测试区域
        self.test_label = QLabel("未检测到控制器")
        layout.addRow("状态:", self.test_label)

        # 创建应用按钮
        self.apply_button = QPushButton("应用更改")
        self.apply_button.clicked.connect(self.apply_changes)
        layout.addRow("", self.apply_button)

    def update_test_value(self, joystick):
        """更新测试值显示"""
        if joystick and self.button_combo.value() < joystick.get_numbuttons():
            value = joystick.get_button(self.button_combo.value())
            self.test_label.setText("按下" if value else "未按下")
            self.test_label.setStyleSheet("color: red;" if value else "color: black;")
        else:
            self.test_label.setText("按钮不可用")
            self.test_label.setStyleSheet("color: gray;")

    def apply_changes(self):
        """应用更改到配置"""
        try:
            # 更新配置
            self.config_manager.config[self.section][self.key] = str(self.button_combo.value())

            # 更新本地值
            self.button_value = self.button_combo.value()

            QMessageBox.information(self, "更改已应用",
                                    f"{self.description}按钮映射已更新。\n注意：需要保存配置文件才能永久保存更改。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用更改时出错: {str(e)}")


class ControllerMappingEditor(QMainWindow):
    """控制器映射编辑器主窗口"""

    def __init__(self):
        """初始化控制器映射编辑器"""
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("ROV控制器映射编辑器")
        self.setMinimumSize(800, 600)

        # 初始化pygame
        pygame.init()
        pygame.joystick.init()

        # 初始化配置
        self.config = ConfigParser()
        self.config_path = None
        self.config_manager = None

        # 初始化UI
        self.init_ui()

        # 尝试加载默认配置
        self.load_default_config()

        # 初始化控制器
        self.joystick = None
        self.init_joystick()

        # 创建定时器更新控制器状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller_state)
        self.timer.start(50)  # 每50毫秒更新一次

    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建配置文件选择部分
        config_layout = QHBoxLayout()
        config_label = QLabel("配置文件:")
        self.config_combo = QComboBox()
        self.config_combo.setMinimumWidth(300)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_config)
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)

        config_layout.addWidget(config_label)
        config_layout.addWidget(self.config_combo)
        config_layout.addWidget(self.browse_button)
        config_layout.addWidget(self.save_button)

        # 添加配置文件选择部分到主布局
        main_layout.addLayout(config_layout)

        # 创建控制器状态标签
        self.status_label = QLabel("未检测到控制器")
        main_layout.addWidget(self.status_label)

        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 轴映射选项卡
        self.axes_tab = QWidget()
        axes_layout = QVBoxLayout(self.axes_tab)

        # 创建轴映射组
        self.axis_widgets = {}

        # 添加轴映射选项卡
        self.tab_widget.addTab(self.axes_tab, "轴映射")

        # 按钮映射选项卡
        self.buttons_tab = QWidget()
        buttons_layout = QVBoxLayout(self.buttons_tab)

        # 创建按钮映射组
        self.button_widgets = {}

        # 添加按钮映射选项卡
        self.tab_widget.addTab(self.buttons_tab, "按钮映射")

    def load_default_config(self):
        """加载默认配置文件"""
        # 获取可能的配置文件路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.ini')]

        # 添加到下拉框
        for config_file in config_files:
            self.config_combo.addItem(config_file, os.path.join(config_dir, config_file))

        # 如果有配置文件，加载第一个
        if config_files:
            self.config_path = os.path.join(config_dir, config_files[0])
            self.load_config(self.config_path)
            self.config_combo.setCurrentIndex(0)

            # 连接下拉框变更事件
            self.config_combo.currentIndexChanged.connect(self.on_config_changed)

    def on_config_changed(self, index):
        """处理配置文件选择变更"""
        if index >= 0:
            self.config_path = self.config_combo.itemData(index)
            self.load_config(self.config_path)

    def browse_config(self):
        """浏览并选择配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "INI文件 (*.ini);;所有文件 (*.*)"
        )

        if file_path:
            # 检查是否已在下拉框中
            found = False
            for i in range(self.config_combo.count()):
                if self.config_combo.itemData(i) == file_path:
                    self.config_combo.setCurrentIndex(i)
                    found = True
                    break

            # 如果不在下拉框中，添加它
            if not found:
                self.config_combo.addItem(os.path.basename(file_path), file_path)
                self.config_combo.setCurrentIndex(self.config_combo.count() - 1)

            self.config_path = file_path
            self.load_config(file_path)

    def load_config(self, config_path):
        """加载配置文件"""
        try:
            # 创建新的配置管理器
            self.config_manager = ConfigManager(config_path)

            # 清空现有的轴映射组件
            self.clear_mapping_widgets()

            # 创建轴映射组件
            self.create_axis_mapping_widgets()

            # 创建按钮映射组件
            self.create_button_mapping_widgets()

            self.statusBar().showMessage(f"已加载配置: {os.path.basename(config_path)}")
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载配置文件时出错: {str(e)}")

    def clear_mapping_widgets(self):
        """清空映射组件"""
        # 清空轴映射选项卡
        if hasattr(self, 'axes_tab'):
            # 删除所有子部件
            layout = self.axes_tab.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()

        # 清空按钮映射选项卡
        if hasattr(self, 'buttons_tab'):
            # 删除所有子部件
            layout = self.buttons_tab.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()

        # 清空组件字典
        self.axis_widgets = {}
        self.button_widgets = {}

    def create_axis_mapping_widgets(self):
        """创建轴映射组件"""
        if not self.config_manager:
            return

        # 获取轴选项卡布局
        axes_layout = self.axes_tab.layout()

        # 创建X轴映射组件
        x_group = QGroupBox("X轴 (左右)")
        x_layout = QVBoxLayout(x_group)
        x_widget = AxisMappingWidget(self.config_manager, "x")
        x_layout.addWidget(x_widget)
        self.axis_widgets["x"] = x_widget
        axes_layout.addWidget(x_group)

        # 创建Y轴映射组件
        y_group = QGroupBox("Y轴 (前后)")
        y_layout = QVBoxLayout(y_group)
        y_widget = AxisMappingWidget(self.config_manager, "y")
        y_layout.addWidget(y_widget)
        self.axis_widgets["y"] = y_widget
        axes_layout.addWidget(y_group)

        # 创建Z轴映射组件
        z_group = QGroupBox("Z轴 (上下)")
        z_layout = QVBoxLayout(z_group)
        z_widget = AxisMappingWidget(self.config_manager, "z")
        z_layout.addWidget(z_widget)
        self.axis_widgets["z"] = z_widget
        axes_layout.addWidget(z_group)

        # 创建偏航轴映射组件
        yaw_group = QGroupBox("偏航轴 (旋转)")
        yaw_layout = QVBoxLayout(yaw_group)
        yaw_widget = AxisMappingWidget(self.config_manager, "yaw")
        yaw_layout.addWidget(yaw_widget)
        self.axis_widgets["yaw"] = yaw_widget
        axes_layout.addWidget(yaw_group)

        # 添加弹性空间
        axes_layout.addStretch()

    def create_button_mapping_widgets(self):
        """创建按钮映射组件"""
        if not self.config_manager:
            return

        # 获取按钮选项卡布局
        buttons_layout = self.buttons_tab.layout()

        # 创建舵机按钮映射组
        servo_group = QGroupBox("舵机控制按钮")
        servo_layout = QVBoxLayout(servo_group)

        # 打开舵机按钮
        open_widget = ButtonMappingWidget(
            self.config_manager, "servo", "open_button", "打开舵机"
        )
        servo_layout.addWidget(open_widget)
        self.button_widgets["open_button"] = open_widget

        # 关闭舵机按钮
        close_widget = ButtonMappingWidget(
            self.config_manager, "servo", "close_button", "关闭舵机"
        )
        servo_layout.addWidget(close_widget)
        self.button_widgets["close_button"] = close_widget

        # 中间位置1按钮
        mid1_widget = ButtonMappingWidget(
            self.config_manager, "servo", "mid1_button", "中间位置1"
        )
        servo_layout.addWidget(mid1_widget)
        self.button_widgets["mid1_button"] = mid1_widget

        # 中间位置2按钮
        mid2_widget = ButtonMappingWidget(
            self.config_manager, "servo", "mid2_button", "中间位置2"
        )
        servo_layout.addWidget(mid2_widget)
        self.button_widgets["mid2_button"] = mid2_widget

        buttons_layout.addWidget(servo_group)

        # 创建模式按钮映射组
        mode_group = QGroupBox("模式控制按钮")
        mode_layout = QVBoxLayout(mode_group)

        # 速度模式按钮
        speed_widget = ButtonMappingWidget(
            self.config_manager, "speed_mode", "button", "速度模式切换"
        )
        mode_layout.addWidget(speed_widget)
        self.button_widgets["speed_mode_button"] = speed_widget

        # 锁定模式按钮
        lock_widget = ButtonMappingWidget(
            self.config_manager, "lock_mode", "button", "锁定模式切换"
        )
        mode_layout.addWidget(lock_widget)
        self.button_widgets["lock_mode_button"] = lock_widget

        # 循环模式按钮
        loop_widget = ButtonMappingWidget(
            self.config_manager, "loop_mode", "button", "循环模式切换"
        )
        mode_layout.addWidget(loop_widget)
        self.button_widgets["loop_mode_button"] = loop_widget

        buttons_layout.addWidget(mode_group)

        # 添加弹性空间
        buttons_layout.addStretch()

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
                f"已检测到控制器: {joystick_name} | "
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

        # 更新轴映射组件
        for axis_name, widget in self.axis_widgets.items():
            widget.update_test_value(self.joystick)

        # 更新按钮映射组件
        for button_name, widget in self.button_widgets.items():
            widget.update_test_value(self.joystick)

    def save_config(self):
        """保存配置到文件"""
        if not self.config_manager or not self.config_path:
            QMessageBox.warning(self, "保存错误", "没有加载配置文件")
            return

        try:
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config_manager.config.write(f)

            QMessageBox.information(self, "保存成功", f"配置已成功保存到 {os.path.basename(self.config_path)}")
            self.statusBar().showMessage(f"已保存配置到 {os.path.basename(self.config_path)}")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存配置时出错: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ControllerMappingEditor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
