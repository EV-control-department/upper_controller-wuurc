from modules.config_manager import ConfigManager


def test_mode_params():
    """测试模式参数加载"""
    cm = ConfigManager()
    modes = cm.get_catch_modes()

    print("模式参数测试:")
    for i, mode in enumerate(modes):
        print(f"\n模式 {i + 1}: {mode['name']}")
        print("  基本参数:")
        print(f"    servoX: {mode['servoX']}")
        print(f"    servoY: {mode['servoY']}")
        print(f"    color: {mode['color']}")

        print("  轴最大值:")
        print(f"    x_max: {mode.get('x_max', '未设置')}")
        print(f"    y_max: {mode.get('y_max', '未设置')}")
        print(f"    z_max: {mode.get('z_max', '未设置')}")

        print("  触发器参数:")
        print(f"    left_threshold: {mode.get('left_threshold', '未设置')}")
        print(f"    x_reduction: {mode.get('x_reduction', '未设置')}")
        print(f"    y_reduction: {mode.get('y_reduction', '未设置')}")
        print(f"    z_reduction: {mode.get('z_reduction', '未设置')}")


if __name__ == "__main__":
    test_mode_params()
