"""
测试Z轴非对称限制处理
此脚本模拟不同的手柄输入值，并测试修改后的Z轴处理逻辑
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hardware_controller import controller_curve


def test_z_axis_processing():
    """测试Z轴处理逻辑"""
    print("测试Z轴非对称限制处理")
    print("=" * 50)

    # 测试不同的z_max和z_min配置
    test_configs = [
        {"z_max": 8000, "z_min": -8000, "name": "对称配置"},
        {"z_max": 8000, "z_min": -6000, "name": "非对称配置1 (|z_min| < z_max)"},
        {"z_max": 6000, "z_min": -8000, "name": "非对称配置2 (|z_min| > z_max)"}
    ]

    # 测试不同的输入值
    test_inputs = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]

    for config in test_configs:
        z_max = config["z_max"]
        z_min = config["z_min"]
        print(f"\n配置: {config['name']}")
        print(f"z_max = {z_max}, z_min = {z_min}")
        print("-" * 50)
        print("输入值\t原始曲线输出\t修改后曲线输出\t最终输出")
        print("-" * 50)

        for corrected_z in test_inputs:
            # 原始处理方法
            z_limit_original = z_max if corrected_z >= 0 else z_min
            original_output = abs(z_limit_original) * controller_curve(corrected_z)

            # 修改后的处理方法
            z_limit_new = z_max if corrected_z >= 0 else z_min
            z_sign = 1 if corrected_z >= 0 else -1
            z_abs = abs(corrected_z)
            curved_input = z_sign * controller_curve(z_abs)
            new_output = abs(z_limit_new) * curved_input

            # 计算最终输出（假设speed_mode_rate=1.0，trigger_reduction=1.0）
            final_output = new_output

            print(f"{corrected_z:+.2f}\t{controller_curve(corrected_z):+.6f}\t{curved_input:+.6f}\t{final_output:+.1f}")


def test_extreme_values():
    """测试极端值情况"""
    print("\n\n测试极端值情况")
    print("=" * 50)

    # 极端配置
    extreme_configs = [
        {"z_max": 10000, "z_min": -1000, "name": "极端非对称 (10:1)"},
        {"z_max": 1000, "z_min": -10000, "name": "极端非对称 (1:10)"}
    ]

    # 测试满量程输入
    test_inputs = [-1.0, 1.0]

    for config in extreme_configs:
        z_max = config["z_max"]
        z_min = config["z_min"]
        print(f"\n配置: {config['name']}")
        print(f"z_max = {z_max}, z_min = {z_min}")
        print("-" * 50)
        print("输入值\t最终输出\t预期输出\t比例")
        print("-" * 50)

        for corrected_z in test_inputs:
            # 修改后的处理方法
            z_limit = z_max if corrected_z >= 0 else z_min
            z_sign = 1 if corrected_z >= 0 else -1
            z_abs = abs(corrected_z)
            curved_input = z_sign * controller_curve(z_abs)
            output = abs(z_limit) * curved_input

            # 预期输出（满量程应该达到极限值）
            expected = z_max if corrected_z > 0 else z_min

            # 计算实际输出与预期的比例
            ratio = abs(output / expected) if expected != 0 else 0

            print(f"{corrected_z:+.2f}\t{output:+.1f}\t{expected:+.1f}\t{ratio:.2%}")


if __name__ == "__main__":
    test_z_axis_processing()
    test_extreme_values()
