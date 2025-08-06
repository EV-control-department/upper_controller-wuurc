"""
测试手柄辅助修正键绑定
用于验证'j'键绑定是否正确加载和工作
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.config_manager import ConfigManager


def test_joystick_correction_key_binding():
    """测试手柄辅助修正键绑定是否正确加载"""
    # 创建配置管理器实例
    config_manager = ConfigManager()

    # 获取键盘绑定
    keyboard_bindings = config_manager.get_keyboard_bindings()

    # 检查是否包含toggle_joystick_correction_key
    if 'toggle_joystick_correction_key' in keyboard_bindings:
        print(f"✓ 成功: toggle_joystick_correction_key 存在于键盘绑定中")
        print(f"  值: {keyboard_bindings['toggle_joystick_correction_key']}")
    else:
        print(f"✗ 错误: toggle_joystick_correction_key 不存在于键盘绑定中")

    # 获取按键冷却时间
    key_cooldowns = config_manager.get_key_cooldowns()

    # 检查是否包含toggle_joystick_correction_cooldown
    if 'toggle_joystick_correction_cooldown' in key_cooldowns:
        print(f"✓ 成功: toggle_joystick_correction_cooldown 存在于按键冷却时间中")
        print(f"  值: {key_cooldowns['toggle_joystick_correction_cooldown']}")
    else:
        print(f"✗ 错误: toggle_joystick_correction_cooldown 不存在于按键冷却时间中")

    return 'toggle_joystick_correction_key' in keyboard_bindings and 'toggle_joystick_correction_cooldown' in key_cooldowns


if __name__ == "__main__":
    print("测试手柄辅助修正键绑定...")
    success = test_joystick_correction_key_binding()

    if success:
        print("\n总结: 所有测试通过 ✓")
        sys.exit(0)
    else:
        print("\n总结: 测试失败 ✗")
        sys.exit(1)
