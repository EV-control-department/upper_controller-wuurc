"""
硬件控制模块
用于管理与ROV硬件的通信
"""

import json
import math
import socket
import struct
import threading
import time


# 下位机协议帧常量
FRAME_HEADER = b"\xFA\xAF"
FRAME_FOOTER = b"\xFB\xBF"
CMD_MOTION_CTRL = 0x01
CMD_THRUST_CONFIG = 0x02
CMD_DEPTH_TEMP = 0x03
CMD_THRUST_ACK = 0x04


class GimbalController:
    """云台 TOP Protocol UDP 控制器。"""

    def __init__(self, server_address=("192.168.0.38", 5000)):
        self.server_address = server_address
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setblocking(False)

    @staticmethod
    def calculate_crc(payload):
        """计算 TOP 协议 ASCII 特征累加和。"""
        return f"{sum(ord(char) for char in payload) & 0xFF:02X}"

    @classmethod
    def build_packet(cls, command, data):
        """构造 TOP 协议云台控制报文。"""
        data = str(data)
        len_char = f"{len(data):X}"[-1].upper()
        packet = f"#TPUG{len_char}w{command}{data}"
        return packet + cls.calculate_crc(packet)

    def send_command(self, command, data):
        """发送一个 TOP Protocol 命令。"""
        try:
            packet = self.build_packet(command, data)
            self.client_socket.sendto(packet.encode("ascii"), self.server_address)
            return True
        except (OSError, ValueError) as exc:
            print(f"发送云台指令失败: {exc}")
            return False

    def send_ptz(self, direction):
        """
        发送云台 PTZ 指令。

        direction:
            00 - 停止
            01 - 向上
            02 - 向下
        """
        return self.send_command("PTZ", direction)

    def send_pitch_speed(self, direction, speed_rad_s):
        """
        按固定速度控制云台俯仰。

        GSP 的协议字段为有符号 8 位整数，单位为度/秒；配置接口使用
        rad/s，向下方向通过补码发送负速度。
        """
        try:
            speed_rad_s = abs(float(speed_rad_s))
            if not math.isfinite(speed_rad_s) or speed_rad_s <= 0:
                return self.send_command("GSP", "00")

            speed_deg_s = min(127, max(1, int(round(speed_rad_s * 180.0 / math.pi))))
            if direction == "02":
                speed_value = (-speed_deg_s) & 0xFF
            elif direction == "01":
                speed_value = speed_deg_s
            else:
                return self.send_command("GSP", "00")

            return self.send_command("GSP", f"{speed_value:02X}")
        except (TypeError, ValueError):
            return self.send_command("GSP", "00")

    def stop(self):
        """停止云台运动并关闭 UDP socket。"""
        try:
            self.send_pitch_speed("00", 0)
        finally:
            self.client_socket.close()


class HardwareController:
    """硬件控制类，负责与ROV硬件通信"""

    def __init__(self, server_address, motor_params):
        """
        初始化硬件控制器
        
        参数:
            server_address: 服务器地址元组 (host, port)
            motor_params: 电机参数字典
        """
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

    @staticmethod
    def _xor_checksum(data):
        """计算协议定义的 XOR 校验值。"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    @classmethod
    def _build_frame(cls, command, payload=b""):
        """构造带帧头、XOR 校验和帧尾的协议帧。"""
        body = bytes((command,)) + payload
        checksum = cls._xor_checksum(body)
        return FRAME_HEADER + body + bytes((checksum,)) + FRAME_FOOTER

    @classmethod
    def _parse_frame(cls, frame):
        """
        解析一个下位机协议帧。

        返回 (command, payload)，帧格式错误时返回 None。
        CMD_THRUST_ACK 是协议中唯一不带 XOR 校验的应答帧。
        """
        if len(frame) < 6:
            return None
        if not frame.startswith(FRAME_HEADER) or not frame.endswith(FRAME_FOOTER):
            return None

        command = frame[2]
        if command == CMD_THRUST_ACK:
            if len(frame) != 6:
                return None
            return command, frame[3:4]

        expected_lengths = {
            CMD_DEPTH_TEMP: 14,
        }
        if len(frame) != expected_lengths.get(command, -1):
            return None

        # frame[2:-3] 覆盖命令字和全部数据，不包含校验字节及帧尾。
        if frame[-3] != cls._xor_checksum(frame[2:-3]):
            return None
        return command, frame[3:-3]

    def setup_socket(self, local_port):
        """设置UDP套接字"""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setblocking(False)
        self.client_socket.bind(('', local_port))  # 绑定本地端口
        return self.client_socket

    def send_thrust_data(self, motor_name):
        """
        发送单个电机的推力参数到网络
        
        参数:
            motor_name: 电机名称 (m0-m5)
            
        返回:
            bool: 是否发送成功
        """
        if motor_name not in self.motor_params:
            print(f"错误: 未找到电机参数 {motor_name}")
            return False

        if not self.client_socket:
            print("错误: 套接字未初始化")
            return False

        try:
            params = self.motor_params[motor_name]
            payload = struct.pack(
                '<B8f',
                int(params['num']),
                float(params['np_mid']),
                float(params['np_ini']),
                float(params['pp_ini']),
                float(params['pp_mid']),
                float(params['nt_end']),
                float(params['nt_mid']),
                float(params['pt_mid']),
                float(params['pt_end']),
            )
            frame = self._build_frame(CMD_THRUST_CONFIG, payload)
            self.client_socket.sendto(frame, self.server_address)
            # 更新电机初始化状态为成功
            self.motor_init_status[motor_name] = True
            return True
        except Exception as e:
            print(f"发送电机 {motor_name} 参数失败: {str(e)}")
            # 更新电机初始化状态为失败
            self.motor_init_status[motor_name] = False
            return False

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

    def all_motors_initialized(self):
        """
        检查所有电机是否都已成功初始化
        
        返回:
            bool: 如果所有电机都已初始化则返回True，否则返回False
        """
        return all(self.motor_init_status.values())

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

    def hwinit(self, max_retries=3):
        """
        初始化所有电机参数
        
        参数:
            max_retries: 每个电机的最大重试次数
            
        返回:
            bool: 是否所有电机都成功初始化
        """
        if not self.client_socket:
            raise RuntimeError("套接字未初始化，请先调用setup_socket方法")

        # 重置所有电机的初始化状态
        for motor_name in self.motor_init_status:
            self.motor_init_status[motor_name] = False

        all_success = True
        
        for motor_name in ["m0", "m1", "m2", "m3", "m4", "m5"]:
            motor_success = False

            # 尝试发送电机参数，最多重试max_retries次
            for attempt in range(max_retries + 1):
                success = self.send_thrust_data(motor_name)
                if success:
                    motor_success = True
                    break

                if attempt < max_retries:
                    # 指数退避重试
                    wait_time = 0.1 * (2 ** attempt)
                    print(f"初始化电机 {motor_name} 失败，{wait_time:.2f}秒后重试 ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"初始化电机 {motor_name} 失败，已达到最大重试次数")

            if motor_success:
                print(f"电机 {motor_name} 初始化成功")
            else:
                all_success = False

            # 电机初始化之间的延迟
            time.sleep(0.1)

        return self.all_motors_initialized()

    def send_controller_data(self, controller_data):
        """
        发送控制器数据到ROV（二进制帧格式）

        帧格式:
            帧头: 0xFA 0xAF (2 bytes)
            命令: 0x01 (1 byte)
            数据: x, y, z, roll, pitch, yaw, servo0 (7 个小端 float)
            校验: 从命令字到 servo0 末尾的 XOR (1 byte)
            帧尾: 0xFB 0xBF (2 bytes)
            总计: 34 bytes

        参数:
            controller_data: 控制器数据字典

        返回:
            bool: 是否发送成功
        """
        if not self.client_socket:
            print("错误: 套接字未初始化")
            return False

        try:
            x = float(controller_data.get("y", 0.0))
            y = float(controller_data.get("x", 0.0))
            z = float(controller_data.get("z", 0.0))
            roll = float(controller_data.get("roll", controller_data.get("rx", 0.0)))
            pitch = float(controller_data.get("pitch", controller_data.get("ry", 0.0)))
            yaw = -float(controller_data.get("yaw", controller_data.get("rz", 0.0)))
            servo = float(controller_data.get("servo0", 0.0))

            payload = struct.pack('<7f', x, y, z, roll, pitch, yaw, servo)
            frame = self._build_frame(CMD_MOTION_CTRL, payload)
            self.client_socket.sendto(frame, self.server_address)
            return True
        except Exception as e:
            print(f"发送控制器数据失败: {str(e)}")
            return False

    def receive_sensor_data(self):
        """
        接收传感器数据
        
        返回:
            sensor_data: 传感器数据字典，如果没有数据则返回None
        """
        if not self.client_socket:
            print("错误: 套接字未初始化")
            return None

        try:
            data, addr = self.client_socket.recvfrom(1024)
            parsed = self._parse_frame(data)
            if parsed is None:
                return None

            command, payload = parsed
            if command == CMD_DEPTH_TEMP:
                depth, temperature = struct.unpack('<2f', payload)
                return {"depth": depth, "temperature": temperature}

            if command == CMD_THRUST_ACK:
                motor_num = payload[0]
                motor_name = f"m{motor_num}"
                if motor_name in self.motor_init_status:
                    self.motor_init_status[motor_name] = True
                # 应答不是传感器数据，不能交给 ControllerMonitor 处理。
                return None
        except BlockingIOError:
            # 非阻塞模式下没有数据可读，这是正常的
            pass
        except ConnectionError as e:
            # 连接错误
            print(f"接收数据时连接错误: {str(e)}")
        except Exception as e:
            # 捕获其他所有异常
            print(f"接收传感器数据时发生错误: {str(e)}")

        return None


class ControllerMonitor:
    """控制器监控类，跟踪控制器状态和传感器数据"""

    def __init__(self, controller_init):
        """
        初始化控制器监控器
        
        参数:
            controller_init: 控制器初始状态字典
        """
        self.controller = controller_init.copy()
        self.depth = 0.0  # 深度数据
        self.temperature = 0.0  # 温度数据

    def update_sensor_data(self, sensor_data):
        """
        更新传感器数据
        
        参数:
            sensor_data: 传感器数据字典
        """
        if sensor_data:
            # 检查是否是错误数据
            if "_error" in sensor_data:
                # 如果是错误数据，保持当前值不变
                # 这样在JSON解析错误时不会重置深度和温度值
                pass
            else:
                # 正常数据，更新深度和温度
                self.depth = sensor_data.get("depth", 0.0) + 0.24  # 深度偏移校正
                self.temperature = sensor_data.get("temperature", 0.0)


class NetworkWorker(threading.Thread):
    """网络工作线程，处理网络通信"""

    def __init__(self, hardware_controller, controller_monitor):
        """
        初始化网络工作线程
        
        参数:
            hardware_controller: 硬件控制器实例
            controller_monitor: 控制器监控器实例
        """
        super().__init__(daemon=True)
        self.hardware_controller = hardware_controller
        self.controller_monitor = controller_monitor
        self.task_in_progress = False
        self.task_event = threading.Event()
        self.running = True

        # 连接状态跟踪
        self.connection_status = True
        self.last_successful_comm = time.time()
        self.comm_failures = 0
        self.max_retries = 3

        # 心跳和电机重初始化计时器
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 2.0  # 心跳间隔（秒）
        self.last_motor_reinit = time.time()
        self.motor_reinit_interval = 30.0  # 电机重初始化间隔（秒）

    def run(self):
        """线程主循环"""
        # 检查必要的属性是否存在
        if not hasattr(self, 'task_event') or not hasattr(self, 'hardware_controller') or not hasattr(self,
                                                                                                      'controller_monitor'):
            print("NetworkWorker初始化不完整")
            return

        while self.running:
            # 检查是否需要发送心跳
            current_time = time.time()
            if current_time - self.last_heartbeat >= self.heartbeat_interval:
                self.send_heartbeat()
                self.last_heartbeat = current_time

            # 注意：根据需求，推力曲线只在初始化时发送，运行过程中不再定期发送

            self.task_event.wait(timeout=0.5)  # 等待被设置，但最多等待0.5秒
            self.task_event.clear()  # 重置事件，避免重复处理

            # 检查线程是否仍在运行
            if not self.running:
                break

            self.task_in_progress = True

            try:
                # 发送控制器数据
                success = self.send_with_retry(self.hardware_controller.send_controller_data,
                                               self.controller_monitor.controller)

                if success:
                    # 更新最后成功通信时间
                    self.last_successful_comm = time.time()
                    self.comm_failures = 0
                    if not self.connection_status:
                        print("电调连接已恢复")
                        self.connection_status = True

                # 接收并解析深度/温度协议帧；电机应答由控制器内部消费
                sensor_data = self.hardware_controller.receive_sensor_data()
                if sensor_data:
                    self.controller_monitor.update_sensor_data(sensor_data)
            except Exception as e:
                self.comm_failures += 1
                print(f"网络通信错误: {str(e)}")

                # 如果连续失败次数过多，标记连接状态为断开
                if self.comm_failures > 5 and self.connection_status:
                    self.connection_status = False
                    print("电调连接已断开，等待自动恢复...")
            finally:
                # 任务完成
                self.task_in_progress = False

    def send_with_retry(self, send_func, data, retries=None):
        """
        使用重试机制发送数据
        
        参数:
            send_func: 发送函数
            data: 要发送的数据
            retries: 重试次数，如果为None则使用默认值
            
        返回:
            bool: 是否发送成功
        """
        if retries is None:
            retries = self.max_retries

        for attempt in range(retries + 1):
            try:
                if send_func(data):
                    return True
                raise RuntimeError("发送函数返回失败")
            except Exception as e:
                if attempt < retries:
                    # 指数退避重试
                    wait_time = 0.1 * (2 ** attempt)
                    print(f"发送失败，{wait_time:.2f}秒后重试 ({attempt + 1}/{retries}): {str(e)}")
                    time.sleep(wait_time)
                else:
                    print(f"发送失败，已达到最大重试次数: {str(e)}")
                    return False

    def send_heartbeat(self):
        """新协议未定义心跳命令，保留接口但不发送未定义帧。"""
        return False

    def reinitialize_motors(self):
        """
        重新初始化电机
        
        注意：根据需求，此方法仅用于系统初始化时，不再用于运行过程中的定期重初始化。
        保留此方法仅用于手动调试或特殊情况下的手动重初始化。
        """
        try:
            print("手动重新初始化电机...")
            self.hardware_controller.hwinit()
            print("电机重新初始化完成")
        except Exception as e:
            print(f"电机重新初始化失败: {str(e)}")

    def send_thrust_curves(self):
        """
        仅发送推力曲线数据，不执行完整的电机初始化
        
        注意：根据需求，此方法仅用于系统初始化时，不再用于运行过程中的定期发送。
        保留此方法仅用于手动调试或特殊情况下的手动发送。
        """
        print("手动发送推力曲线数据...")
        success_count = 0

        # 为每个电机单独发送推力曲线，并单独处理错误
        for motor_name in ["m0", "m1", "m2", "m3", "m4", "m5"]:
            try:
                if self.hardware_controller.send_thrust_data(motor_name):
                    success_count += 1
                # 短暂延迟，避免发送过快
                time.sleep(0.05)
            except Exception as e:
                print(f"发送电机 {motor_name} 推力曲线失败: {str(e)}")

        print(f"推力曲线发送完成: {success_count}/6 个电机成功")
        return success_count > 0

    def trigger_communication(self):
        """触发通信任务"""
        if not self.task_in_progress:
            self.task_event.set()

    def stop(self):
        """停止线程"""
        self.running = False
        self.task_event.set()  # 确保线程不会卡在wait()


class DepthTemperatureThread(threading.Thread):
    """深度温度记录线程，记录深度和温度数据"""

    def __init__(self, monitor, log_interval=5.0, log_time=0.5):
        """
        初始化深度温度记录线程
        
        参数:
            monitor: 控制器监控器实例
            log_interval: 日志记录间隔（秒）
            log_time: 采样间隔（秒）
        """
        super().__init__()
        self.monitor = monitor  # 共享传感器数据
        self.log_interval = log_interval  # 记录间隔（秒）
        self.log_time = log_time
        self.running = False  # 线程运行状态
        self.json_file = "F:\\data\\qsensor_log.json"  # 日志文件路径
        self.depths = []  # 深度数据列表
        self.temperatures = []  # 温度数据列表

    def get_depth_temperature(self):
        """采集单次深度和温度数据"""
        # 根据实际传感器调整深度判断条件
        if self.monitor.depth > 0.0:
            self.depths.append(-self.monitor.depth)
            self.temperatures.append(self.monitor.temperature)

    def run(self):
        """线程主循环：仅在running为True时执行"""
        current_time = time.time()
        while self.running:
            self.get_depth_temperature()
            time.sleep(self.log_time)  # 间隔采集
            time_gap = time.time() - current_time
            if time_gap >= self.log_interval:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"{timestamp},{self.monitor.depth:.3f},{self.monitor.temperature:.2f}")
                current_time = time.time()

    def save_to_json(self):
        """保存数据到JSON文件"""
        min_length = min(len(self.temperatures), len(self.depths))
        data = {
            "temperature": self.temperatures[:min_length],
            "depth": self.depths[:min_length]
        }
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {self.json_file}，共{min_length}条")
        except Exception as e:
            print(f"保存失败：{str(e)}")

    def start_log(self):
        """启动线程（设置运行状态）"""
        self.running = True
        if not self.is_alive():
            self.start()

    def stop_log(self):
        """停止线程（重置运行状态并保存数据）"""
        self.running = False
        self.save_to_json()
        # 清空数据列表，避免下次启动累积历史数据
        self.depths.clear()
        self.temperatures.clear()


def controller_curve(curve_input):
    """
    控制器曲线函数，将输入值映射为更适合控制的输出值
    
    参数:
        curve_input: 输入值（通常是-1到1之间的浮点数）
        
    返回:
        映射后的输出值
    """
    return curve_input ** 5 if curve_input >= 0 else -((-curve_input) ** 3)
