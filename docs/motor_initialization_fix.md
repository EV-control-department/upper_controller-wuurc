# 电机初始化错误修复文档

## 问题描述

在启动ROV控制系统时，出现以下错误：

```
程序异常: 'HardwareController' object has no attribute 'get_failed_motors'
```

这个错误是由于在之前的简化优化过程中，移除了电机初始化状态跟踪和相关方法，但主程序（main.py）仍然在使用这些方法。

## 修复措施

为了解决这个问题，我们重新实现了以下功能：

### 1. 添加电机初始化状态跟踪

在 `HardwareController` 类中添加了电机初始化状态跟踪：

```python
# 导入所需的模块
import json
import time

# HardwareController类的__init__方法
def __init__(self, server_address, motor_params):
    self.server_address = server_address
    self.motor_params = motor_params
    self.client_socket = None
    
    # 初始化电机状态字典，用于跟踪每个电机的初始化状态
    self.motor_init_status = {
        "m0": False,
        "m1": False,
        "m2": False,
        "m3": False,
        "m4": False,
        "m5": False
    }
```

### 2. 实现 get_failed_motors 方法

添加了 `get_failed_motors` 方法，用于获取初始化失败的电机列表：

```python
def get_failed_motors(self):
    """
    获取初始化失败的电机列表
    
    返回:
        list: 初始化失败的电机名称列表
    """
    failed_motors = []
    for motor_name, status in self.motor_init_status.items():
        if not status:
            failed_motors.append(motor_name)
    return failed_motors
```

### 3. 实现 all_motors_initialized 方法

添加了 `all_motors_initialized` 方法，用于检查所有电机是否都已成功初始化：

```python
def all_motors_initialized(self):
    """
    检查所有电机是否都已成功初始化
    
    返回:
        bool: 如果所有电机都已初始化则返回True，否则返回False
    """
    return all(self.motor_init_status.values())
```

### 4. 实现 retry_failed_motors 方法

添加了 `retry_failed_motors` 方法，用于重试初始化失败的电机：

```python
# 导入所需的模块
import time

def retry_failed_motors(self):
    """
    重试初始化失败的电机
    
    返回:
        list: 重试后仍然失败的电机列表
    """
    failed_motors = self.get_failed_motors()
    still_failed = []
    
    # 优先重试主电机（m0-m3）
    main_motors = [m for m in failed_motors if m in ["m0", "m1", "m2", "m3"]]
    other_motors = [m for m in failed_motors if m in ["m4", "m5"]]
    
    # 重试主电机
    for motor_name in main_motors:
        success = self.send_thrust_data(motor_name)
        if not success:
            still_failed.append(motor_name)
        time.sleep(0.1)
    
    # 重试其他电机
    for motor_name in other_motors:
        success = self.send_thrust_data(motor_name)
        if not success:
            still_failed.append(motor_name)
        time.sleep(0.05)
    
    return still_failed
```

### 5. 更新 send_thrust_data 方法

更新了 `send_thrust_data` 方法，使其跟踪电机初始化状态并返回发送是否成功：

```python
# 导入所需的模块
import json

def send_thrust_data(self, motor_name):
    """
    发送单个电机的推力参数到网络 - 简化版
    
    参数:
        motor_name: 电机名称 (m0-m5)
        
    返回:
        bool: 发送是否成功
    """
    if motor_name in self.motor_params and self.client_socket:
        # 简化的数据结构 - 只包含必要字段
        data = {
            "cmd": "thrust_init",
            "motor": self.motor_params[motor_name]['num'],
            "np_mid": self.motor_params[motor_name]['np_mid'],
            "np_ini": self.motor_params[motor_name]['np_ini'],
            "pp_ini": self.motor_params[motor_name]['pp_ini'],
            "pp_mid": self.motor_params[motor_name]['pp_mid'],
            "nt_end": self.motor_params[motor_name]['nt_end'],
            "nt_mid": self.motor_params[motor_name]['nt_mid'],
            "pt_mid": self.motor_params[motor_name]['pt_mid'],
            "pt_end": self.motor_params[motor_name]['pt_end']
        }
        # 移除换行符，减少数据大小
        json_str = json.dumps(data)
        
        try:
            # 简化的发送逻辑 - 无重试机制
            self.client_socket.sendto(json_str.encode(), self.server_address)
            # 更新电机初始化状态为成功
            self.motor_init_status[motor_name] = True
            return True
        except Exception:
            # 简化的错误处理 - 不记录详细错误
            # 更新电机初始化状态为失败
            self.motor_init_status[motor_name] = False
            return False
            
    # 如果参数无效或套接字未初始化，返回失败
    return False
```

### 6. 更新 hwinit 方法

更新了 `hwinit` 方法，使其重置电机初始化状态并返回是否所有电机都成功初始化：

```python
def hwinit(self):
    """
    初始化所有电机参数 - 简化版
    
    返回:
        bool: 如果所有电机都成功初始化则返回True，否则返回False
    """
    if not self.client_socket:
        return False
        
    # 重置所有电机的初始化状态
    for motor_name in self.motor_init_status:
        self.motor_init_status[motor_name] = False

    # 一次性发送所有电机参数，无需延迟
    for motor_name in ["m0", "m1", "m2", "m3", "m4", "m5"]:
        self.send_thrust_data(motor_name)
        
    # 返回是否所有电机都成功初始化
    return self.all_motors_initialized()
```

## 预期效果

这些修复措施应该能够解决启动时出现的 `'HardwareController' object has no attribute 'get_failed_motors'`
错误，同时保持电机初始化的功能完整。具体来说：

1. 系统将能够正常启动，不再出现属性错误
2. 电机初始化状态跟踪功能将正常工作
3. 用户仍然可以通过按下手柄按键强制进入系统，即使部分电机初始化失败
4. 系统将显示详细的电机初始化状态信息

## 测试建议

建议进行以下测试以验证修复效果：

1. 正常启动系统，确认不再出现错误
2. 测试电机初始化功能，包括重试机制和强制进入选项
3. 检查电机初始化状态显示是否正确
4. 测试电机控制功能，确保所有电机都能正常工作

## 后续优化建议

1. 考虑将电机初始化状态跟踪功能设计为可选功能，通过配置文件控制是否启用
2. 优化电机初始化过程，减少不必要的延迟
3. 改进错误处理，提供更详细的错误信息
4. 考虑添加电机初始化状态的持久化存储，以便在系统重启后恢复