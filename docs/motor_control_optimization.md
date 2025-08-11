# 电机控制优化文档

## 问题描述

电调（控制四个电机的）经常断连，大约3秒左右不听使唤，但后面又可以恢复正常，视频流保持稳定。这些问题在老软件中不存在。

## 优化措施

为了解决电机控制断连问题，实施了以下优化措施：

### 1. 重新启用周期性推力曲线更新

在 `NetworkWorker` 类中，重新启用了周期性推力曲线更新功能，该功能在之前的代码中被注释掉了。这确保了电机参数会定期重新初始化，有助于维持与电调的稳定连接。

```python
# 检查是否需要更新推力曲线
current_time = time.time()
time_since_last_update = current_time - self.last_thrust_update
if time_since_last_update > self.thrust_update_interval:
    # 发送控制器数据前更新推力曲线
    self.hardware_controller.hwinit()
    print(f"已更新推力曲线，间隔: {time_since_last_update:.1f}秒")
    self.last_thrust_update = current_time
```

### 2. 减少推力曲线更新间隔

将推力曲线更新间隔从5.0秒减少到2.0秒，以确保更频繁地更新电机参数，防止出现3秒左右的断连情况。

```python
self.thrust_update_interval = 2.0  # 推力曲线更新间隔（秒）
```

### 3. 添加网络通信重试机制

为 `send_controller_data` 和 `send_thrust_data` 方法添加了重试机制，确保即使在网络不稳定的情况下，命令也能可靠地发送到ROV。

```python
max_retries = 3
retry_delay = 0.01  # 10毫秒

for attempt in range(max_retries):
    try:
        self.client_socket.sendto(json_str.encode(), self.server_address)
        break  # 发送成功，跳出循环
    except Exception as e:
        if attempt < max_retries - 1:  # 如果不是最后一次尝试
            time.sleep(retry_delay)  # 短暂延迟后重试
        else:
            print(f"发送失败: {str(e)}")  # 所有重试都失败后记录错误
```

### 4. 改进错误处理

在 `NetworkWorker` 的 `run` 方法中，为每个主要操作（更新推力曲线、发送控制器数据、接收传感器数据）添加了单独的错误处理，确保即使某个操作失败，其他操作仍能继续执行。

```python
try:
    # 发送控制器数据
    self.hardware_controller.send_controller_data(self.controller_monitor.controller)
except Exception as e:
    print(f"发送控制器数据失败: {str(e)}")
```

### 5. 优化电机参数发送延迟

优化了 `hwinit` 方法中发送电机参数之间的延迟，特别是增加了主电机（m0-m3）的延迟时间，确保每个电机参数都能被正确接收。

```python
# 优先初始化控制四个主电机的参数（m0-m3）
for motor_name in ["m0", "m1", "m2", "m3"]:
    self.send_thrust_data(motor_name)
    # 增加延迟以确保每个电机参数都能被正确接收
    time.sleep(0.1)

# 然后初始化其他电机参数
for motor_name in ["m4", "m5"]:
    self.send_thrust_data(motor_name)
    time.sleep(0.05)
```

## 预期效果

这些优化措施应该能够显著提高电机控制的稳定性，减少或消除电调断连的问题。具体来说：

1. 周期性推力曲线更新确保电机参数定期刷新
2. 更短的更新间隔（2秒）防止出现3秒左右的断连
3. 重试机制和改进的错误处理提高了通信的可靠性
4. 优化的延迟确保电机参数能被正确接收

## 测试建议

建议进行以下测试以验证优化效果：

1. 长时间运行ROV，观察是否仍有电调断连现象
2. 在不同的操作条件下测试（如快速转向、快速上升/下降等）
3. 在网络条件不佳的情况下测试系统稳定性

## 后续优化方向

如果上述优化措施仍不能完全解决问题，可以考虑以下进一步的优化：

1. 实现电机命令的缓冲机制，在通信中断时使用最后的有效命令
2. 添加心跳信号机制，定期检测与ROV的连接状态
3. 优化网络通信协议，减少数据包大小或使用更可靠的传输方式