"""
测试双曲线视图修复

此脚本用于测试thrust_curve_debugger.py中双曲线视图的修复：
1. 测试打开双曲线视图时是否立即显示两条曲线
2. 测试在拖拽过程中是否保持双曲线视图状态
3. 测试拖拽比较曲线的点时参数是否正确更新

使用方法：
python test_dual_view_fixes.py
"""

import os
import sys

from PyQt5.QtCore import QTimer
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
            print("步骤 1: 检查曲线数据加载")
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
            # 记录当前状态
            self.initial_is_dual_view = getattr(self.main_window.plot_canvas, 'is_dual_view', False)
            print(f"初始双曲线状态: {self.initial_is_dual_view}")

            # 点击双曲线视图按钮
            self.main_window.dual_view_btn.click()

            # 检查是否成功切换到双曲线视图
            is_dual_view = getattr(self.main_window.plot_canvas, 'is_dual_view', False)
            if not is_dual_view:
                print("错误: 未能切换到双曲线视图")
                self.app.quit()
                return

            print(f"切换后双曲线状态: {is_dual_view}")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 2:
            print("步骤 3: 测试拖拽主曲线点")
            # 保存当前参数
            self.current_motor = self.main_window.current_motor
            self.original_params = self.main_window.motor_data[self.current_motor].copy()

            # 模拟拖拽主曲线的一个点
            # 这里我们直接修改参数并触发更新，因为无法直接模拟拖拽
            key = 'nt_mid'
            original_value = self.original_params[key]
            new_value = original_value - 50

            # 修改参数
            self.main_window.motor_data[self.current_motor][key] = new_value

            # 触发更新
            self.main_window.on_plot_drag_finished()

            # 检查是否仍然处于双曲线视图
            is_dual_view = getattr(self.main_window.plot_canvas, 'is_dual_view', False)
            if not is_dual_view:
                print("错误: 拖拽主曲线点后双曲线视图状态丢失")
                self.app.quit()
                return

            print(f"拖拽主曲线点后双曲线状态: {is_dual_view}")
            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 3:
            print("步骤 4: 测试拖拽比较曲线点")
            # 保存当前比较电机参数
            self.comparison_motor = self.main_window.comparison_motor
            if not self.comparison_motor:
                print("错误: 未设置比较电机")
                self.app.quit()
                return

            self.original_comparison_params = self.main_window.motor_data[self.comparison_motor].copy()

            # 模拟拖拽比较曲线的一个点
            key = 'pt_mid'
            original_value = self.original_comparison_params[key]
            new_value = original_value + 50

            # 直接修改DraggablePointPlot中的comparison_params
            if hasattr(self.main_window.plot_canvas, 'comparison_params'):
                self.main_window.plot_canvas.comparison_params[key] = new_value
            else:
                print("错误: plot_canvas没有comparison_params属性")
                self.app.quit()
                return

            # 触发更新
            self.main_window.on_plot_drag_finished()

            # 检查比较电机参数是否已更新
            current_comparison_params = self.main_window.motor_data[self.comparison_motor]
            if abs(current_comparison_params[key] - new_value) > 0.1:
                print(f"错误: 比较电机参数未正确更新。预期: {new_value}, 实际: {current_comparison_params[key]}")
                self.app.quit()
                return

            # 检查是否仍然处于双曲线视图
            is_dual_view = getattr(self.main_window.plot_canvas, 'is_dual_view', False)
            if not is_dual_view:
                print("错误: 拖拽比较曲线点后双曲线视图状态丢失")
                self.app.quit()
                return

            print(f"拖拽比较曲线点后双曲线状态: {is_dual_view}")
            print(f"比较电机参数已正确更新: {key} = {current_comparison_params[key]}")

            self.test_step += 1
            self.timer.start(500)

        elif self.test_step == 4:
            print("测试完成! 所有修复已验证:")
            print("1. 双曲线视图正确初始化 ✓")
            print("2. 拖拽主曲线点时保持双曲线视图 ✓")
            print("3. 拖拽比较曲线点时参数正确更新 ✓")
            self.app.quit()

    def run(self):
        """运行测试"""
        return self.app.exec_()


if __name__ == "__main__":
    test_runner = TestRunner()
    sys.exit(test_runner.run())
