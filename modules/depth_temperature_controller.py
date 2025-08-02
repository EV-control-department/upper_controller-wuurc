"""
深度温度控制器模块
用于非阻塞方式记录深度和温度数据
"""

import json
import threading
import time


class DepthTemperatureController(threading.Thread):
    """深度温度记录线程，以非阻塞方式记录深度和温度数据"""

    def __init__(self, monitor, log_interval=5.0, sample_interval=0.5):
        """
        初始化深度温度记录线程
        
        参数:
            monitor: 控制器监控器实例
            log_interval: 日志记录间隔（秒）
            sample_interval: 采样间隔（秒）
        """
        super().__init__()
        self.daemon = True  # 设置为守护线程，主线程退出时自动退出
        self.monitor = monitor  # 共享传感器数据
        self.log_interval = log_interval  # 记录间隔（秒）
        self.sample_interval = sample_interval  # 采样间隔（秒）
        self.running = False  # 线程运行状态
        self.json_file = "F:\\data\\qsensor_log.json"  # 日志文件路径
        self.depths = []  # 深度数据列表
        self.temperatures = []  # 温度数据列表

        # 用于非阻塞操作的事件和定时器
        self.sample_event = threading.Event()
        self.sample_timer = None
        self.log_timer = None

    def get_depth_temperature(self):
        """采集单次深度和温度数据"""
        # 根据实际传感器调整深度判断条件
        if self.monitor.depth > 0.0:
            self.depths.append(-self.monitor.depth)
            self.temperatures.append(self.monitor.temperature)

        # 如果线程仍在运行，安排下一次采样
        if self.running:
            self.schedule_next_sample()

    def schedule_next_sample(self):
        """安排下一次采样（非阻塞）"""
        if self.sample_timer:
            self.sample_timer.cancel()

        self.sample_timer = threading.Timer(self.sample_interval, self.get_depth_temperature)
        self.sample_timer.daemon = True
        self.sample_timer.start()

    def log_current_data(self):
        """记录当前数据到控制台"""
        if self.running:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp},{self.monitor.depth:.3f},{self.monitor.temperature:.2f}")

            # 安排下一次日志记录
            self.schedule_next_log()

    def schedule_next_log(self):
        """安排下一次日志记录（非阻塞）"""
        if self.log_timer:
            self.log_timer.cancel()

        self.log_timer = threading.Timer(self.log_interval, self.log_current_data)
        self.log_timer.daemon = True
        self.log_timer.start()

    def run(self):
        """线程主循环：启动非阻塞定时器"""
        # 立即开始第一次采样
        if self.running:
            self.get_depth_temperature()

            # 立即开始第一次日志记录
            self.log_current_data()

            # 等待停止信号
            while self.running:
                time.sleep(0.1)  # 短暂休眠，减少CPU使用

            # 线程停止时保存数据
            self.save_to_json()

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
        # 取消所有定时器
        if self.sample_timer:
            self.sample_timer.cancel()

        if self.log_timer:
            self.log_timer.cancel()

        # 设置停止标志
        self.running = False

        # 保存数据（在run方法中会自动调用）
        # 不需要阻塞等待线程结束
