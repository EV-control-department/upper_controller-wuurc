# 推力曲线调试器修改说明

## 问题描述

thrust_curve_debugger.py 下发数据时使用的是 0-1 范围的值，而不是参考 main.py 和 config 中 x, y, z 的极值（如 6000, 4000
等）。这导致了电机控制不一致的问题。

## 修改内容

修改了 `thrust_curve_debugger.py` 文件中的 `send_motor_command` 方法，使其在发送单个电机命令时也应用与
`send_combined_motor_command` 方法相同的缩放逻辑：

1. 应用 controller_curve 函数对输入值进行非线性映射
2. 根据电机类型应用正确的幅度缩放：
    - 电机 0, 1 (X轴/左右): 3000
    - 电机 2, 3 (Y轴/前后): 5000
    - 电机 4, 5 (Z轴/上下): 6000

这些值与 config_beyond.ini 中定义的极值一致。

## 修改前后对比

### 修改前

```python
def send_motor_command(self, motor_id, speed):
    """发送单个电机命令"""
    if not SOCKET_AVAILABLE or not self.udp_socket:
        self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
        return False

    try:
        # 提取电机编号
        motor_num = int(motor_id[1:])

        # 创建命令数据
        command = {
            "type": "motor_test",
            "motor": motor_num,
            "speed": speed
        }

        # 转换为JSON字符串
        command_json = json.dumps(command)

        # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
        self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

        return True
    except Exception as e:
        self.debug_info_panel.add_log(f"发送命令失败: {str(e)}")
        return False
```

### 修改后

```python
def send_motor_command(self, motor_id, speed):
    """发送单个电机命令"""
    if not SOCKET_AVAILABLE or not self.udp_socket:
        self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
        return False

    try:
        # 提取电机编号
        motor_num = int(motor_id[1:])

        # 应用控制器曲线函数
        curved_speed = controller_curve(speed)

        # 根据电机类型应用正确的幅度
        # 根据config_beyond.ini中的设置: x=3000, y=5000, z=6000
        scaled_speed = curved_speed
        if motor_num in [0, 1]:  # 左右水平推进器 (X轴)
            scaled_speed = 3000 * curved_speed
        elif motor_num in [2, 3]:  # 前后水平推进器 (Y轴)
            scaled_speed = 5000 * curved_speed
        elif motor_num in [4, 5]:  # 上下垂直推进器 (Z轴)
            scaled_speed = 6000 * curved_speed

        # 创建命令数据
        command = {
            "type": "motor_test",
            "motor": motor_num,
            "speed": scaled_speed
        }

        # 转换为JSON字符串
        command_json = json.dumps(command)

        # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
        self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

        # 记录日志
        self.debug_info_panel.add_log(
            f"发送电机命令: 原始值={speed:.2f}, 曲线后={curved_speed:.2f}, 缩放后={scaled_speed:.2f}")

        return True
    except Exception as e:
        self.debug_info_panel.add_log(f"发送命令失败: {str(e)}")
        return False
```

## 验证方法

运行 `start_thrust_curve_debugger.bat` 脚本启动推力曲线调试工具，然后：

1. 使用单电机测试面板测试各个电机，观察日志面板中显示的原始值、曲线后值和缩放后值
2. 确认缩放后的值与预期一致：
    - 电机 0, 1: 最大约 ±3000
    - 电机 2, 3: 最大约 ±5000
    - 电机 4, 5: 最大约 ±6000
3. 使用组合电机测试面板，确认 X、Y、Z 轴的值也正确缩放

## 总结

此修改确保了 thrust_curve_debugger.py 在发送单个电机命令时也使用与 main.py 和 config 文件中相同的极值范围，使电机控制行为保持一致。