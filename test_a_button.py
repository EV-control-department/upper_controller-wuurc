"""
测试A按钮快速上浮功能
"""

import pygame

from modules.config_manager import ConfigManager
from modules.hardware_controller import ControllerMonitor
from modules.joystick_controller import JoystickController
from modules.ui_controller import JoystickHandler


def test_a_button():
    """测试A按钮快速上浮功能"""
    # 初始化pygame
    pygame.init()

    # 加载配置
    config_manager = ConfigManager()

    # 初始化手柄处理器
    joystick_handler = JoystickHandler(config_manager.get_joystick_settings())

    # 初始化控制器监控
    controller_monitor = ControllerMonitor(config_manager.get_controller_init())

    # 初始化手柄控制器
    joystick_controller = JoystickController(
        joystick_handler,
        config_manager,
        controller_monitor
    )

    print("测试A按钮快速上浮功能")
    print("请按下A按钮并保持，观察Z轴值是否持续为-10000")
    print("按下Esc键退出测试")

    running = True
    clock = pygame.time.Clock()

    while running:
        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # 更新手柄状态
        joystick_handler.update_button_states()

        # 处理手柄输入
        joystick_controller.process_input()

        # 显示Z轴值
        z_value = controller_monitor.controller["z"]
        a_button_state = "按下" if joystick_handler.buttons[0]["new"] else "释放"
        print(f"A按钮状态: {a_button_state}, Z轴值: {z_value}")

        # 控制循环频率
        clock.tick(10)  # 10 FPS，便于观察

    # 清理资源
    pygame.quit()


if __name__ == "__main__":
    test_a_button()
