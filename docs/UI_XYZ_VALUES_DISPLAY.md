# UI界面XYZ值显示修改说明

## 问题描述

在推力曲线调试工具（thrust_curve_debugger.py）的UI界面中，XYZ轴的值显示为0-1范围的归一化值，而不是实际下发到电机的缩放值（如X=3000,
Y=5000, Z=6000）。这使得用户无法直观地看到实际发送给ROV的命令值。

## 修改内容

1. 修改了`CombinedMotorTestPanel`类中的`on_value_changed`方法，使其计算并显示实际下发的缩放值：
    - X轴：3000 * controller_curve(normalized_value)
    - Y轴：5000 * controller_curve(normalized_value)
    - Z轴：6000 * controller_curve(normalized_value)

2. 更新了"当前值"组框中的标签，使其清晰地表明显示的是实际值：
    - "X:" 改为 "X (实际值):"
    - "Y:" 改为 "Y (实际值):"
    - "Z:" 改为 "Z (实际值):"

3. 调整了值标签的格式，使用更适合大数值的格式（从"0.00"改为"0.0"）

## 修改前后对比

### 修改前

```python
def on_value_changed(self, axis, value):
    """处理轴值变化"""
    # 转换为-1.0到1.0范围
    normalized_value = value / 100.0

    # 更新标签
    if axis == "x":
        self.x_value = normalized_value
        self.x_label.setText(f"{normalized_value:.2f}")
        self.x_value_label.setText(f"{normalized_value:.2f}")
    elif axis == "y":
        self.y_value = normalized_value
        self.y_label.setText(f"{normalized_value:.2f}")
        self.y_value_label.setText(f"{normalized_value:.2f}")
    elif axis == "z":
        self.z_value = normalized_value
        self.z_label.setText(f"{normalized_value:.2f}")
        self.z_value_label.setText(f"{normalized_value:.2f}")
```

标签定义：

```python
values_layout.addWidget(QLabel("X:"), 0, 0)
values_layout.addWidget(QLabel("Y:"), 1, 0)
values_layout.addWidget(QLabel("Z:"), 2, 0)

self.x_value_label = QLabel("0.00")
self.y_value_label = QLabel("0.00")
self.z_value_label = QLabel("0.00")
```

### 修改后

```python
def on_value_changed(self, axis, value):
    """处理轴值变化"""
    # 转换为-1.0到1.0范围
    normalized_value = value / 100.0

    # 计算实际下发的缩放值
    scaled_value = 0.0
    if axis == "x":
        scaled_value = 3000 * controller_curve(normalized_value)
    elif axis == "y":
        scaled_value = 5000 * controller_curve(normalized_value)
    elif axis == "z":
        scaled_value = 6000 * controller_curve(normalized_value)

    # 更新标签
    if axis == "x":
        self.x_value = normalized_value
        self.x_label.setText(f"{normalized_value:.2f}")
        self.x_value_label.setText(f"{scaled_value:.1f}")
    elif axis == "y":
        self.y_value = normalized_value
        self.y_label.setText(f"{normalized_value:.2f}")
        self.y_value_label.setText(f"{scaled_value:.1f}")
    elif axis == "z":
        self.z_value = normalized_value
        self.z_label.setText(f"{normalized_value:.2f}")
        self.z_value_label.setText(f"{scaled_value:.1f}")
```

标签定义：

```python
values_layout.addWidget(QLabel("X (实际值):"), 0, 0)
values_layout.addWidget(QLabel("Y (实际值):"), 1, 0)
values_layout.addWidget(QLabel("Z (实际值):"), 2, 0)

self.x_value_label = QLabel("0.0")
self.y_value_label = QLabel("0.0")
self.z_value_label = QLabel("0.0")
```

## 效果说明

修改后，UI界面中的"当前值"组框现在显示的是实际下发到ROV的缩放值：

- X轴：范围约为±3000
- Y轴：范围约为±5000
- Z轴：范围约为±6000

同时，滑块旁边的标签仍然显示归一化值（-1.0到1.0范围），以便用户了解输入值。

## 验证方法

1. 运行`tools/thrust_curve_debugger.py`脚本
2. 移动X、Y、Z轴的滑块
3. 观察"当前值"组框中显示的值是否为实际缩放值
4. 确认调试信息面板中记录的日志显示了原始值、曲线后值和缩放后值

## 总结

此修改使UI界面能够直观地显示实际下发到ROV的XYZ值，而不仅仅是0-1范围的归一化值，提高了调试工具的实用性和直观性。