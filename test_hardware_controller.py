"""
测试硬件控制器模块
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hardware_controller import HardwareController, ControllerMonitor, NetworkWorker


def test_hardware_controller():
    """测试硬件控制器基本功能"""
    print("开始测试硬件控制器...")

    # 模拟电机参数
    motor_params = {
        "m0": {"num": 0, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
        "m1": {"num": 1, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
        "m2": {"num": 2, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
        "m3": {"num": 3, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
        "m4": {"num": 4, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
        "m5": {"num": 5, "np_mid": 1500, "np_ini": 1400, "pp_ini": 1600, "pp_mid": 1700,
               "nt_end": 1000, "nt_mid": 1300, "pt_mid": 1700, "pt_end": 2000},
    }

    # 创建硬件控制器实例
    server_address = ('192.168.0.233', 2200)  # 使用配置文件中的地址
    hw_controller = HardwareController(server_address, motor_params)

    # 测试电机初始化状态跟踪方法
    print("\n测试电机初始化状态跟踪方法...")

    # 初始状态应该是所有电机都未初始化
    failed_motors = hw_controller.get_failed_motors()
    print(f"初始状态下失败的电机: {failed_motors}")

    # 所有电机都应该未初始化
    all_initialized = hw_controller.all_motors_initialized()
    print(f"所有电机都已初始化? {all_initialized}")

    # 模拟一些电机初始化成功
    hw_controller.motor_init_status["m0"] = True
    hw_controller.motor_init_status["m1"] = True

    # 再次检查状态
    failed_motors = hw_controller.get_failed_motors()
    print(f"部分初始化后失败的电机: {failed_motors}")

    # 所有电机仍然未全部初始化
    all_initialized = hw_controller.all_motors_initialized()
    print(f"所有电机都已初始化? {all_initialized}")

    # 测试控制器监控器
    print("\n测试控制器监控器...")
    controller_init = {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "yaw": 0.0,
        "servo0": 0.0
    }
    controller_monitor = ControllerMonitor(controller_init)

    # 模拟传感器数据
    sensor_data = {
        "depth": 1.5,
        "temperature": 25.0
    }
    controller_monitor.update_sensor_data(sensor_data)
    print(f"深度: {controller_monitor.depth}, 温度: {controller_monitor.temperature}")

    # 测试错误数据处理
    error_data = {"_error": "json_decode"}
    controller_monitor.update_sensor_data(error_data)
    print(f"错误数据后 - 深度: {controller_monitor.depth}, 温度: {controller_monitor.temperature}")

    # 测试NetworkWorker类（不实际连接网络）
    print("\n测试NetworkWorker类...")
    network_worker = NetworkWorker(hw_controller, controller_monitor)

    # 检查NetworkWorker实例是否正确创建
    print(f"NetworkWorker实例创建成功: {network_worker is not None}")
    print(f"心跳间隔: {network_worker.heartbeat_interval}秒")

    print("\n测试完成!")


if __name__ == "__main__":
    test_hardware_controller()
