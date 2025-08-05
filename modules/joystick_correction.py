"""
手柄辅助修正模块

该模块提供了一个辅助修正系统，用于减少操作手快速拨动摇杆时的非主要方向移动。
当操作手从静止状态快速拨动摇杆时，系统会检测主要移动方向，并对次要方向应用过滤，
以减少"顺带现象"（例如推z轴附带yaw转向，推y轴带有x横移）。
"""

import time


class JoystickCorrection:
    """手柄辅助修正类，用于减少快速拨动摇杆时的非主要方向移动"""

    def __init__(self, config):
        """
        初始化手柄辅助修正
        
        参数:
            config: 配置字典，包含以下可选参数:
                - detection_threshold: 检测阈值，默认0.1
                - stationary_threshold: 静止阈值，默认0.05
                - correction_duration: 修正持续时间（秒），默认0.5
                - filter_strength: 过滤强度（指数），默认2.0
        """
        # 配置参数
        self.enabled = False  # 是否启用修正
        self.detection_threshold = config.get("detection_threshold", 0.1)  # 检测阈值
        self.stationary_threshold = config.get("stationary_threshold", 0.05)  # 静止阈值
        self.correction_duration = config.get("correction_duration", 0.5)  # 修正持续时间（秒）
        self.filter_strength = config.get("filter_strength", 2.0)  # 过滤强度（指数）

        # 状态变量
        self.left_stick_stationary = True  # 左摇杆静止状态
        self.right_stick_stationary = True  # 右摇杆静止状态
        self.left_stick_start_time = 0  # 左摇杆开始移动时间
        self.right_stick_start_time = 0  # 右摇杆开始移动时间
        self.left_primary_axis = None  # 左摇杆主要方向
        self.right_primary_axis = None  # 右摇杆主要方向

    def toggle(self):
        """
        切换辅助修正状态
        
        返回:
            bool: 切换后的状态
        """
        self.enabled = not self.enabled
        return self.enabled

    def process_axes(self, x_value, y_value, z_value, yaw_value):
        """
        处理摇杆输入值，应用辅助修正
        
        参数:
            x_value: X轴原始值
            y_value: Y轴原始值
            z_value: Z轴原始值
            yaw_value: Yaw轴原始值
            
        返回:
            修正后的(x_value, y_value, z_value, yaw_value)
        """
        if not self.enabled:
            return x_value, y_value, z_value, yaw_value

        current_time = time.time()

        # 检查左摇杆（X/Y轴）状态
        left_magnitude = (x_value ** 2 + y_value ** 2) ** 0.5

        # 检测从静止到移动的状态变化
        if self.left_stick_stationary and left_magnitude > self.detection_threshold:
            self.left_stick_stationary = False
            self.left_stick_start_time = current_time

            # 确定主要移动方向
            if abs(x_value) > abs(y_value):
                self.left_primary_axis = 'x'
            else:
                self.left_primary_axis = 'y'

        # 检测回到静止状态
        elif not self.left_stick_stationary and left_magnitude < self.stationary_threshold:
            self.left_stick_stationary = True
            self.left_primary_axis = None

        # 检查右摇杆（Z/Yaw轴）状态
        right_magnitude = (z_value ** 2 + yaw_value ** 2) ** 0.5

        # 检测从静止到移动的状态变化
        if self.right_stick_stationary and right_magnitude > self.detection_threshold:
            self.right_stick_stationary = False
            self.right_stick_start_time = current_time

            # 确定主要移动方向
            if abs(z_value) > abs(yaw_value):
                self.right_primary_axis = 'z'
            else:
                self.right_primary_axis = 'yaw'

        # 检测回到静止状态
        elif not self.right_stick_stationary and right_magnitude < self.stationary_threshold:
            self.right_stick_stationary = True
            self.right_primary_axis = None

        # 应用修正
        corrected_x, corrected_y = self._apply_correction(
            x_value, y_value,
            self.left_primary_axis,
            self.left_stick_start_time,
            current_time
        )

        corrected_z, corrected_yaw = self._apply_correction(
            z_value, yaw_value,
            self.right_primary_axis,
            self.right_stick_start_time,
            current_time,
            axes=['z', 'yaw']
        )

        return corrected_x, corrected_y, corrected_z, corrected_yaw

    def _apply_correction(self, axis1_value, axis2_value, primary_axis, start_time, current_time, axes=['x', 'y']):
        """
        应用修正到一对轴
        
        参数:
            axis1_value: 第一个轴的值
            axis2_value: 第二个轴的值
            primary_axis: 主要轴
            start_time: 开始移动时间
            current_time: 当前时间
            axes: 轴名称列表
            
        返回:
            修正后的(axis1_value, axis2_value)
        """
        # 如果没有主要方向或超过修正时间，不应用修正
        if primary_axis is None or (current_time - start_time) > self.correction_duration:
            return axis1_value, axis2_value

        # 计算修正系数（随时间衰减）
        time_factor = max(0, 1 - (current_time - start_time) / self.correction_duration)

        # 应用修正
        if primary_axis == axes[0]:  # 第一个轴是主要方向
            # 保持主要方向不变，减弱次要方向
            secondary_factor = abs(axis2_value) ** self.filter_strength * time_factor
            corrected_axis2 = axis2_value * (1 - secondary_factor)
            return axis1_value, corrected_axis2
        else:  # 第二个轴是主要方向
            # 保持主要方向不变，减弱次要方向
            secondary_factor = abs(axis1_value) ** self.filter_strength * time_factor
            corrected_axis1 = axis1_value * (1 - secondary_factor)
            return corrected_axis1, axis2_value
