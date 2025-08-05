"""
硬件控制模块
用于管理与ROV硬件的通信
"""

import json
import socket
import threading
import time


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
        """
        if motor_name in self.motor_params and self.client_socket:
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
            json_str = json.dumps(data) + "\n"
            self.client_socket.sendto(json_str.encode(), self.server_address)

    def hwinit(self):
        """初始化所有电机参数"""
        if not self.client_socket:
            raise RuntimeError("套接字未初始化，请先调用setup_socket方法")

        for motor_name in ["m0", "m1", "m2", "m3", "m4", "m5"]:
            self.send_thrust_data(motor_name)
            time.sleep(0.05)

    def send_controller_data(self, controller_data):
        """
        发送控制器数据到ROV
        
        参数:
            controller_data: 控制器数据字典
        """
        if self.client_socket:
            msg = json.dumps(controller_data)
            self.client_socket.sendto((msg + '\n').encode(), self.server_address)

    def receive_sensor_data(self):
        """
        接收传感器数据
        
        返回:
            sensor_data: 传感器数据字典，如果没有数据则返回None
        """
        if not self.client_socket:
            return None

        try:
            data, addr = self.client_socket.recvfrom(1024)
            if data:
                decoded_data = data.decode()
                stripped_data = decoded_data.strip()
                try:
                    sensor_data = json.loads(stripped_data)
                    return sensor_data
                except json.JSONDecodeError:
                    # 忽略JSON解析错误
                    pass
        except BlockingIOError:
            # 非阻塞模式下没有数据可读
            pass

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
        self.last_thrust_update = 0
        self.thrust_update_interval = 5.0  # 推力曲线更新间隔（秒）

    def run(self):
        """线程主循环"""
        # 检查必要的属性是否存在
        if not hasattr(self, 'task_event') or not hasattr(self, 'hardware_controller') or not hasattr(self,
                                                                                                      'controller_monitor'):
            print("NetworkWorker初始化不完整")
            return

        # 初始化时部署一次推力曲线
        try:
            self.hardware_controller.hwinit()
            self.last_thrust_update = time.time()
            print("初始化时部署推力曲线")
        except Exception as e:
            print(f"初始化部署推力曲线失败: {str(e)}")

        while self.running:
            self.task_event.wait()  # 等待被设置

            # 检查线程是否仍在运行
            if not self.running:
                break

            self.task_in_progress = True

            try:
                # 检查是否需要更新推力曲线
                # current_time = time.time()
                # time_since_last_update = current_time - self.last_thrust_update
                # if time_since_last_update > self.thrust_update_interval:
                #     # 发送控制器数据前更新推力曲线
                #     self.hardware_controller.hwinit()
                #     print(f"已更新推力曲线，间隔: {time_since_last_update:.1f}秒")
                #     self.last_thrust_update = current_time
                
                # 发送控制器数据
                self.hardware_controller.send_controller_data(self.controller_monitor.controller)

                # 接收传感器数据
                sensor_data = self.hardware_controller.receive_sensor_data()
                if sensor_data:
                    self.controller_monitor.update_sensor_data(sensor_data)
            except Exception as e:
                print(f"网络通信错误: {str(e)}")
            finally:
                # 任务完成
                self.task_in_progress = False
                self.task_event.clear()  # 重置事件，等待下一次触发

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
