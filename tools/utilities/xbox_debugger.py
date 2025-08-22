import sys

import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel


class JoystickMonitor(QWidget):
    def __init__(self):
        super().__init__()

        # 初始化pygame
        pygame.init()
        pygame.joystick.init()

        # 创建一个窗口
        self.setWindowTitle('Joystick Debugger')
        self.setGeometry(100, 100, 600, 400)  # 增加窗口大小

        # 创建一个布局和标签显示
        self.layout = QVBoxLayout()

        # 创建一个标签并调整字体大小
        self.joystick_status_label = QLabel("Joystick Status:")
        font = self.joystick_status_label.font()
        font.setPointSize(14)  # 设置字体大小为14
        self.joystick_status_label.setFont(font)

        self.layout.addWidget(self.joystick_status_label)
        self.setLayout(self.layout)

        # 打开第一个手柄
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        else:
            self.joystick = None

        # 启动更新定时器
        self.timer = self.startTimer(100)  # 每100毫秒更新一次

    def timerEvent(self, event):
        """定时更新手柄输入状态"""
        if self.joystick:
            pygame.event.pump()  # 必须调用这个方法来更新手柄输入

            # 获取手柄的轴和按钮数据
            axis_0 = self.joystick.get_axis(0)
            axis_1 = self.joystick.get_axis(1)
            axis_2 = self.joystick.get_axis(2)
            axis_3 = self.joystick.get_axis(3)
            axis_4 = self.joystick.get_axis(4)
            axis_5 = self.joystick.get_axis(5)
            button_0 = self.joystick.get_button(0)
            button_1 = self.joystick.get_button(1)
            button_2 = self.joystick.get_button(2)
            button_3 = self.joystick.get_button(3)
            button_4 = self.joystick.get_button(4)
            button_5 = self.joystick.get_button(5)
            hat_x, hat_y = self.joystick.get_hat(0)
            # 格式化轴值
            joystick_input = (
                f"Axis 0: {axis_0:.2f}, Axis 1: {axis_1:.2f}, Axis 2: {axis_2:.2f}, Axis 3: {axis_3:.2f}\n"
                f"Axis 4: {axis_4:.2f}, Axis 5: {axis_5:.2f}\n"
                f"Button 0: {button_0}, Button 1: {button_1}, Button 2: {button_2}, Button 3: {button_3}, Button 4: {button_4}, Button 5: {button_5}\n"
                f"Hat X: {hat_x}, Hat Y: {hat_y}")
        else:
            joystick_input = "No joystick detected!"

        for button in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(button):
                print(f"Button {button} is pressed")
        # 更新GUI中的标签
        self.joystick_status_label.setText(f"Joystick Status:\n{joystick_input}")


def main():
    app = QApplication(sys.argv)

    # 创建并显示窗口
    window = JoystickMonitor()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
