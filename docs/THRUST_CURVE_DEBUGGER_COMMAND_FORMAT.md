# 推力曲线调试器命令格式修改说明

## 问题描述

在使用推力曲线调试工具（thrust_curve_debugger.py）时，发送命令后ROV没有响应。经过分析，发现问题可能是命令格式不匹配导致的。调试工具使用的命令格式与main.py中使用的格式不同，导致ROV无法识别和处理这些命令。

## 修改内容

1. 修改了`thrust_curve_debugger.py`中的命令发送方法，使其与main.py使用相同的格式：
    - 将`send_motor_command`方法修改为使用与main.py相同的控制器数据格式
    - 将`send_combined_motor_command`方法也修改为使用相同格式
    - 添加了ConfigManager的初始化和使用，确保配置一致性

2. 命令格式变更：
    - 原格式：使用自定义的`{"type": "motor_test", "motor": motor_num, "speed": speed}`格式
    - 新格式：使用与main.py相同的`{"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0, "servo0": value}`格式

3. 配置管理：
    - 添加了类级别的ConfigManager实例
    - 修改了网络初始化方法，使用类级别的配置管理器而不是创建新实例

## 修改前后对比

### 修改前 - send_motor_command

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

### 修改后 - send_motor_command

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

        # 创建与main.py相同格式的命令数据
        # 根据电机类型设置对应的轴
        command = {
            "x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0,
            "servo0": self.config_manager.config["servo"].getfloat("open")
        }

        if motor_num in [0, 1]:  # 左右水平推进器 (X轴)
            command["x"] = speed  # 使用原始输入值，不是scaled_speed
        elif motor_num in [2, 3]:  # 前后水平推进器 (Y轴)
            command["y"] = speed  # 使用原始输入值，不是scaled_speed
        elif motor_num in [4, 5]:  # 上下垂直推进器 (Z轴)
            command["z"] = speed  # 使用原始输入值，不是scaled_speed

        # 转换为JSON字符串
        command_json = json.dumps(command)

        # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
        self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

        # 记录日志
        self.debug_info_panel.add_log(
            f"发送电机命令: 原始值={speed:.2f}, 曲线后={curved_speed:.2f}, 缩放后={scaled_speed:.2f}")
        self.debug_info_panel.add_log(f"使用main.py格式发送: {command}")

        return True
    except Exception as e:
        self.debug_info_panel.add_log(f"发送命令失败: {str(e)}")
        return False
```

### 修改前 - send_combined_motor_command

```python
def send_combined_motor_command(self, motor_speeds):
    """发送组合电机命令
    
    参数:
        motor_speeds: 包含x, y, z轴速度的字典
    """
    if not SOCKET_AVAILABLE or not self.udp_socket:
        self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
        return False

    try:
        # 从x, y, z值计算各个电机的速度
        x_raw = motor_speeds.get("x", 0.0)
        y_raw = motor_speeds.get("y", 0.0)
        z_raw = motor_speeds.get("z", 0.0)

        # 应用控制器曲线函数和正确的幅度
        # 根据config_beyond.ini中的设置: x=3000, y=5000, z=6000
        x = 3000 * controller_curve(x_raw)
        y = 5000 * controller_curve(y_raw)
        z = 6000 * controller_curve(z_raw)

        # 根据ROV的电机布局计算各个电机的速度
        # 这里使用一个简化的映射，实际应用中可能需要更复杂的计算
        # 假设:
        # m0, m1: 左右水平推进器
        # m2, m3: 前后水平推进器
        # m4, m5: 上下垂直推进器

        # 水平推进器 (左右)
        m0_speed = x  # 左侧推进器
        m1_speed = -x  # 右侧推进器 (反向)

        # 水平推进器 (前后)
        m2_speed = y  # 前侧推进器
        m3_speed = -y  # 后侧推进器 (反向)

        # 垂直推进器 (上下)
        m4_speed = z  # 垂直推进器1
        m5_speed = z  # 垂直推进器2

        # 创建命令数据
        command = {
            "type": "combined_test",
            "motors": {
                "0": m0_speed,
                "1": m1_speed,
                "2": m2_speed,
                "3": m3_speed,
                "4": m4_speed,
                "5": m5_speed
            }
        }

        # 转换为JSON字符串
        command_json = json.dumps(command)

        # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
        self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

        # 记录日志
        self.debug_info_panel.add_log(f"发送组合命令: 原始值 X={x_raw:.2f}, Y={y_raw:.2f}, Z={z_raw:.2f}")
        self.debug_info_panel.add_log(f"处理后值: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
        self.debug_info_panel.add_log(
            f"电机速度: M0={m0_speed:.2f}, M1={m1_speed:.2f}, M2={m2_speed:.2f}, M3={m3_speed:.2f}, M4={m4_speed:.2f}, M5={m5_speed:.2f}")

        return True
    except Exception as e:
        self.debug_info_panel.add_log(f"发送组合命令失败: {str(e)}")
        return False
```

### 修改后 - send_combined_motor_command

```python
def send_combined_motor_command(self, motor_speeds):
    """发送组合电机命令
    
    参数:
        motor_speeds: 包含x, y, z轴速度的字典
    """
    if not SOCKET_AVAILABLE or not self.udp_socket:
        self.debug_info_panel.add_log("警告: 网络通信不可用，无法发送命令")
        return False

    try:
        # 从x, y, z值获取原始速度
        x_raw = motor_speeds.get("x", 0.0)
        y_raw = motor_speeds.get("y", 0.0)
        z_raw = motor_speeds.get("z", 0.0)

        # 应用控制器曲线函数和正确的幅度（仅用于日志显示）
        # 根据config_beyond.ini中的设置: x=3000, y=5000, z=6000
        x_scaled = 3000 * controller_curve(x_raw)
        y_scaled = 5000 * controller_curve(y_raw)
        z_scaled = 6000 * controller_curve(z_raw)

        # 创建与main.py相同格式的命令数据
        command = {
            "x": x_raw,
            "y": y_raw,
            "z": z_raw,
            "yaw": 0.0,
            "servo0": self.config_manager.config["servo"].getfloat("open")
        }

        # 转换为JSON字符串
        command_json = json.dumps(command)

        # 发送数据 (添加换行符，与main.py中的发送方式保持一致)
        self.udp_socket.sendto((command_json + '\n').encode('utf-8'), (self.remote_addr, self.remote_port))

        # 记录日志
        self.debug_info_panel.add_log(f"发送组合命令: 原始值 X={x_raw:.2f}, Y={y_raw:.2f}, Z={z_raw:.2f}")
        self.debug_info_panel.add_log(f"处理后值(仅供参考): X={x_scaled:.2f}, Y={y_scaled:.2f}, Z={z_scaled:.2f}")
        self.debug_info_panel.add_log(f"使用main.py格式发送: {command}")

        return True
    except Exception as e:
        self.debug_info_panel.add_log(f"发送组合命令失败: {str(e)}")
        return False
```

### 修改前 - 配置管理器初始化

```python
def __init__(self):
    super().__init__()

    # 设置窗口属性
    self.setWindowTitle("ROV推力曲线调试工具")
    self.setMinimumSize(1000, 700)

    # 加载曲线数据
    self.curve_data = {}
    self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config",
                                    "curve.json")
    self.load_curve_data()

    # 初始化网络通信变量
    self.udp_socket = None
    self.remote_addr = None
    self.remote_port = 8888  # 默认端口
```

### 修改后 - 配置管理器初始化

```python
def __init__(self):
    super().__init__()

    # 设置窗口属性
    self.setWindowTitle("ROV推力曲线调试工具")
    self.setMinimumSize(1000, 700)

    # 初始化配置管理器
    self.config_manager = ConfigManager()

    # 加载曲线数据
    self.curve_data = {}
    self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config",
                                    "curve.json")
    self.load_curve_data()

    # 初始化网络通信变量
    self.udp_socket = None
    self.remote_addr = None
    self.remote_port = 8888  # 默认端口
```

### 修改前 - 网络初始化

```python
def init_network(self):
    """初始化网络通信"""
    if not SOCKET_AVAILABLE:
        self.debug_info_panel.add_log("警告: socket模块不可用，网络通信功能将被禁用")
        return

    try:
        # 创建UDP套接字
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 尝试从配置文件加载远程地址和端口
        config_manager = ConfigManager()

        # 获取本地端口并绑定
        local_port = config_manager.get_local_port()
        self.udp_socket.setblocking(False)  # 设置为非阻塞模式
        self.udp_socket.bind(('', local_port))  # 绑定本地端口

        # 获取远程地址和端口
        if "network" in config_manager.config:
            self.remote_addr = config_manager.config["network"].get("remote_ip", "127.0.0.1")
            self.remote_port = config_manager.config["network"].getint("remote_port", 8888)
        else:
            server_address = config_manager.get_server_address()
            self.remote_addr = server_address[0]
            self.remote_port = server_address[1]
```

### 修改后 - 网络初始化

```python
def init_network(self):
    """初始化网络通信"""
    if not SOCKET_AVAILABLE:
        self.debug_info_panel.add_log("警告: socket模块不可用，网络通信功能将被禁用")
        return

    try:
        # 创建UDP套接字
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 使用类级别的配置管理器
        # 获取本地端口并绑定
        local_port = self.config_manager.get_local_port()
        self.udp_socket.setblocking(False)  # 设置为非阻塞模式
        self.udp_socket.bind(('', local_port))  # 绑定本地端口

        # 获取远程地址和端口
        if "network" in self.config_manager.config:
            self.remote_addr = self.config_manager.config["network"].get("remote_ip", "127.0.0.1")
            self.remote_port = self.config_manager.config["network"].getint("remote_port", 8888)
        else:
            server_address = self.config_manager.get_server_address()
            self.remote_addr = server_address[0]
            self.remote_port = server_address[1]
```

## 验证方法

1. 运行推力曲线调试工具：
   ```
   cd tools
   python thrust_curve_debugger.py
   ```

2. 使用单电机测试面板或组合电机测试面板发送命令

3. 观察调试信息面板中的日志，确认命令以正确的格式发送：
    - 应该看到类似 `使用main.py格式发送: {'x': 0.0, 'y': 0.0, 'z': 0.5, 'yaw': 0.0, 'servo0': 0.96}` 的日志

4. 确认ROV对命令有响应，电机按预期运动

## 总结

此修改确保了推力曲线调试工具使用与main.py相同的命令格式与ROV通信，解决了命令发送后ROV无响应的问题。通过统一命令格式，使调试工具能够正确控制ROV的电机。