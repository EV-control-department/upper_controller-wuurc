"""
键盘绑定编辑器
用于检查和修改ROV控制系统的键盘绑定
"""

import os
import sys
from configparser import ConfigParser

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QDialog
)


class KeyboardBindingEditor(QMainWindow):
    """键盘绑定编辑器主窗口"""

    def __init__(self):
        """初始化键盘绑定编辑器"""
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("ROV键盘绑定编辑器")
        self.setMinimumSize(600, 500)

        # 初始化配置
        self.config = ConfigParser()
        self.config_path = None

        # 初始化UI
        self.init_ui()

        # 尝试加载默认配置
        self.load_default_config()

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

        config_layout.addWidget(config_label)
        config_layout.addWidget(self.config_combo)
        config_layout.addWidget(self.browse_button)

        # 添加配置文件选择部分到主布局
        main_layout.addLayout(config_layout)

        # 创建键盘绑定表格
        self.binding_table = QTableWidget()
        self.binding_table.setColumnCount(3)
        self.binding_table.setHorizontalHeaderLabels(["功能", "当前按键", "修改"])
        self.binding_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.binding_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.binding_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # 添加表格到主布局
        main_layout.addWidget(self.binding_table)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存更改")
        self.save_button.clicked.connect(self.save_changes)
        self.reload_button = QPushButton("重新加载")
        self.reload_button.clicked.connect(self.reload_config)

        button_layout.addStretch()
        button_layout.addWidget(self.reload_button)
        button_layout.addWidget(self.save_button)

        # 添加按钮布局到主布局
        main_layout.addLayout(button_layout)

        # 创建冷却时间表格
        cooldown_label = QLabel("按键冷却时间设置:")
        main_layout.addWidget(cooldown_label)

        self.cooldown_table = QTableWidget()
        self.cooldown_table.setColumnCount(2)
        self.cooldown_table.setHorizontalHeaderLabels(["功能", "冷却时间(秒)"])
        self.cooldown_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cooldown_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # 添加冷却时间表格到主布局
        main_layout.addWidget(self.cooldown_table)

        # 设置状态栏
        self.statusBar().showMessage("准备就绪")

    def load_default_config(self):
        """加载默认配置文件"""
        # 获取可能的配置文件路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                  "config")
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
            self.config.read(config_path, encoding='utf-8')

            # 检查配置文件是否包含必要的部分
            if not self.config.has_section('keyboard_bindings') or not self.config.has_section('key_cooldowns'):
                QMessageBox.warning(self, "配置错误", "所选配置文件缺少必要的键盘绑定部分。")
                return

            # 更新表格
            self.update_binding_table()
            self.update_cooldown_table()

            self.statusBar().showMessage(f"已加载配置: {os.path.basename(config_path)}")
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载配置文件时出错: {str(e)}")

    def update_binding_table(self):
        """更新键盘绑定表格"""
        self.binding_table.setRowCount(0)

        # 功能描述映射
        function_descriptions = {
            'quit_key': '退出程序',
            'xbox_debugger_key': '打开Xbox调试器',
            'toggle_rotation_key': '切换屏幕方向',
            'toggle_undistorted_key': '切换无失真视图',
            'toggle_fullscreen_key': '切换全屏',
            'capture_frame_key': '捕获当前帧',
            'controller_visualizer_key': '控制器可视化工具',
            'controller_mapping_key': '控制器映射编辑器',
            'deploy_thrust_curves_key': '部署推力曲线',
            'toggle_joystick_correction_key': '切换手柄辅助修正'
        }

        # 添加键盘绑定
        row = 0
        for key, value in self.config.items('keyboard_bindings'):
            self.binding_table.insertRow(row)

            # 功能描述
            description = function_descriptions.get(key, key)
            self.binding_table.setItem(row, 0, QTableWidgetItem(description))

            # 当前按键
            self.binding_table.setItem(row, 1, QTableWidgetItem(value))

            # 修改按钮
            change_button = QPushButton("修改")
            change_button.clicked.connect(lambda checked, r=row, k=key: self.change_key_binding(r, k))
            self.binding_table.setCellWidget(row, 2, change_button)

            row += 1

    def update_cooldown_table(self):
        """更新冷却时间表格"""
        self.cooldown_table.setRowCount(0)

        # 功能描述映射
        function_descriptions = {
            'xbox_debugger_cooldown': 'Xbox调试器',
            'toggle_rotation_cooldown': '切换屏幕方向',
            'toggle_undistorted_cooldown': '切换无失真视图',
            'toggle_fullscreen_cooldown': '切换全屏',
            'capture_frame_cooldown': '捕获当前帧',
            'button7_cooldown': '手柄按钮7',
            'controller_visualizer_cooldown': '控制器可视化工具',
            'controller_mapping_cooldown': '控制器映射编辑器',
            'deploy_thrust_curves_cooldown': '部署推力曲线',
            'toggle_joystick_correction_cooldown': '切换手柄辅助修正'
        }

        # 添加冷却时间
        row = 0
        for key, value in self.config.items('key_cooldowns'):
            self.cooldown_table.insertRow(row)

            # 功能描述
            description = function_descriptions.get(key, key)
            self.cooldown_table.setItem(row, 0, QTableWidgetItem(description))

            # 冷却时间
            cooldown_item = QTableWidgetItem(value)
            cooldown_item.setData(Qt.UserRole, key)  # 存储原始键名
            self.cooldown_table.setItem(row, 1, cooldown_item)

            row += 1

        # 允许编辑冷却时间
        self.cooldown_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

    def change_key_binding(self, row, key):
        """更改键盘绑定"""
        # 创建一个按键捕获对话框
        key_capture_dialog = KeyCaptureDialog(self, key)
        if key_capture_dialog.exec_():
            new_key = key_capture_dialog.captured_key
            if new_key:
                # 更新表格
                self.binding_table.item(row, 1).setText(new_key)
                # 更新配置（但不保存到文件）
                self.config.set('keyboard_bindings', key, new_key)
                self.statusBar().showMessage(f"已更改 {key} 为 {new_key}，点击保存以应用更改")

    def save_changes(self):
        """保存更改到配置文件"""
        try:
            # 更新冷却时间
            for row in range(self.cooldown_table.rowCount()):
                key = self.cooldown_table.item(row, 1).data(Qt.UserRole)
                value = self.cooldown_table.item(row, 1).text()
                try:
                    # 验证值是否为有效的浮点数
                    float_value = float(value)
                    if float_value < 0:
                        raise ValueError("冷却时间不能为负数")
                    self.config.set('key_cooldowns', key, value)
                except ValueError:
                    QMessageBox.warning(self, "输入错误", f"'{value}' 不是有效的冷却时间值。请输入有效的数字。")
                    return

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)

            QMessageBox.information(self, "保存成功", "配置已成功保存。")
            self.statusBar().showMessage(f"已保存更改到 {os.path.basename(self.config_path)}")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存配置时出错: {str(e)}")

    def reload_config(self):
        """重新加载当前配置文件"""
        if self.config_path:
            self.load_config(self.config_path)


class KeyCaptureDialog(QDialog):
    """按键捕获对话框"""

    def __init__(self, parent=None, key_name=None):
        """初始化按键捕获对话框"""
        super().__init__(parent)

        self.key_name = key_name
        self.captured_key = None

        # 设置窗口属性
        self.setWindowTitle("按键捕获")
        self.setFixedSize(400, 200)
        self.setWindowModality(Qt.ApplicationModal)

        # 创建布局
        layout = QVBoxLayout(self)

        # 添加说明标签
        instruction_label = QLabel(f"请按下要用于 '{key_name}' 的键...")
        instruction_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruction_label)

        # 添加当前按键显示
        self.key_label = QLabel("等待按键...")
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.key_label)

        # 添加按钮
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        ok_button.setEnabled(False)
        self.ok_button = ok_button

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)

        layout.addStretch()
        layout.addLayout(button_layout)

        # 安装事件过滤器以捕获按键
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获按键"""
        if event.type() == QEvent.KeyPress:
            # 获取按键文本
            key_text = event.text()
            if key_text and key_text.isprintable():
                self.captured_key = key_text
                self.key_label.setText(key_text)
                self.ok_button.setEnabled(True)
            return True
        return super().eventFilter(obj, event)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = KeyboardBindingEditor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
