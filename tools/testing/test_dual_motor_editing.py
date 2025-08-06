"""
测试双电机编辑功能

此脚本用于测试推力曲线调试器中的双电机编辑功能。
它会启动推力曲线调试器，并自动执行以下步骤：
1. 加载曲线数据
2. 切换到双曲线视图
3. 选择比较电机
4. 修改主电机和比较电机的参数
5. 验证两个电机的参数是否正确更新

使用方法：
python test_dual_motor_editing.py
"""

import os
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

# 添加父目录到路径，以便导入thrust_curve_debugger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.thrust_curve_debugger import MainWindow


class TestRunner:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.main_window.show()

        # 设置测试计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_test_steps)
        self.timer.setSingleShot(True)
        self.timer.start(1000)  # 1秒后开始测试

        self.test_step = 0

    def run_test_steps(self):
        """执行测试步骤"""
        if self.test_step == 0:
            print("步骤 1: 加载曲线数据")
            # 确保已加载曲线数据
            if not self.main_window.motor_data:
                print("错误: 未加载曲线数据")
                self.app.quit()
                return
            print(f"已加载 {len(self.main_window.motor_data)} 个电机的数据")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 1:
            print("步骤 2: 切换到双曲线视图")
            # 点击双曲线视图按钮
            self.main_window.dual_view_btn.click()
            if not self.main_window.dual_view_active:
                print("错误: 未能切换到双曲线视图")
                self.app.quit()
                return
            print("成功切换到双曲线视图")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 2:
            print("步骤 3: 选择比较电机")
            # 选择一个不同于当前电机的电机作为比较
            current_motor = self.main_window.current_motor
            comparison_motor = None
            for i in range(6):
                motor_name = f"m{i}"
                if motor_name != current_motor:
                    comparison_motor = motor_name
                    break

            if not comparison_motor:
                print("错误: 未能找到合适的比较电机")
                self.app.quit()
                return

            # 设置比较电机
            index = self.main_window.comparison_motor_combo.findText(comparison_motor)
            self.main_window.comparison_motor_combo.setCurrentIndex(index)

            print(f"当前电机: {current_motor}, 比较电机: {comparison_motor}")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 3:
            print("步骤 4: 修改主电机参数")
            # 保存原始参数值
            self.original_primary_params = self.main_window.motor_data[self.main_window.current_motor].copy()

            # 修改主电机的nt_mid参数
            primary_input = self.main_window.param_inputs['nt_mid']
            original_value = float(primary_input.text())
            new_value = original_value - 100  # 减少100
            primary_input.setText(str(new_value))

            # 触发editingFinished信号
            QTest.keyClick(primary_input, Qt.Key_Return)

            print(f"主电机 nt_mid 参数从 {original_value} 修改为 {new_value}")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 4:
            print("步骤 5: 修改比较电机参数")
            # 保存原始参数值
            self.original_comparison_params = self.main_window.motor_data[self.main_window.comparison_motor].copy()

            # 修改比较电机的pt_mid参数
            comparison_input = self.main_window.comparison_param_inputs['pt_mid']
            original_value = float(comparison_input.text())
            new_value = original_value + 100  # 增加100
            comparison_input.setText(str(new_value))

            # 触发editingFinished信号
            QTest.keyClick(comparison_input, Qt.Key_Return)

            print(f"比较电机 pt_mid 参数从 {original_value} 修改为 {new_value}")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 5:
            print("步骤 6: 验证参数更新")
            # 验证主电机参数是否更新
            current_primary_params = self.main_window.motor_data[self.main_window.current_motor]
            if abs(current_primary_params['nt_mid'] - (self.original_primary_params['nt_mid'] - 100)) > 0.1:
                print(
                    f"错误: 主电机参数未正确更新。预期: {self.original_primary_params['nt_mid'] - 100}, 实际: {current_primary_params['nt_mid']}")
            else:
                print("主电机参数更新成功")

            # 验证比较电机参数是否更新
            current_comparison_params = self.main_window.motor_data[self.main_window.comparison_motor]
            if abs(current_comparison_params['pt_mid'] - (self.original_comparison_params['pt_mid'] + 100)) > 0.1:
                print(
                    f"错误: 比较电机参数未正确更新。预期: {self.original_comparison_params['pt_mid'] + 100}, 实际: {current_comparison_params['pt_mid']}")
            else:
                print("比较电机参数更新成功")

            print("测试完成")
            self.app.quit()

    def run(self):
        """运行测试"""
        return self.app.exec_()


if __name__ == "__main__":
    test_runner = TestRunner()
    sys.exit(test_runner.run())
