# Z轴非对称限制处理

## 问题描述

在ROV控制系统中，Z轴（上下方向）的控制需要支持非对称的上限和下限。例如，向下的最大推力可能是8000，而向上的最大推力可能是-6000。在这种情况下，手柄上下操作时的增幅也应该是不对称的，以确保控制的精确性和直观性。

## 解决方案

我们修改了`joystick_controller.py`中的Z轴处理逻辑，以正确处理非对称限制。主要更改如下：

1. 分离Z轴输入的符号和幅度：
   ```python
   z_sign = 1 if corrected_z >= 0 else -1
   z_abs = abs(corrected_z)
   ```

2. 对输入的绝对值应用controller_curve函数，然后恢复符号：
   ```python
   curved_input = z_sign * controller_curve(z_abs)
   ```

3. 在最终计算中使用这个修改后的曲线输入：
   ```python
   self.controller_monitor.controller["z"] = (
                                                   abs(z_limit) *
                                                   self.speed_modes[self.speed_mode_ptr]["rate"]
                                           ) * curved_input * (1 - (self.joystick_handler.get_axis(4) + 1) / z_reduction)
   ```

## 技术说明

### 原始实现的问题

在原始实现中，controller_curve函数直接应用于原始输入值（corrected_z），而没有考虑z_max和z_min之间的不对称性。这意味着如果z_max和z_min具有不同的绝对值，手柄响应将不会与这些限制成比例。

例如，如果z_max = 8000，z_min = -6000：

- 当手柄完全向上推（corrected_z = -1.0）时，输出应该达到z_min（-6000）
- 当手柄完全向下推（corrected_z = 1.0）时，输出应该达到z_max（8000）

但是，原始实现中的曲线应用不会考虑这种不对称性。

### 新实现的优势

新的实现确保：

1. controller_curve函数一致地应用于输入的幅度，无论方向如何
2. 保留输入的符号
3. 输出根据适当的限制（z_max或z_min）进行缩放

这种方法确保了当z_max和z_min具有不同的绝对值时，手柄响应将与这些限制成比例。

## 测试结果

我们创建了一个测试脚本`test_z_axis_asymmetric.py`来验证这些更改在不同的z_max和z_min配置下是否正常工作。测试结果确认：

1. 对于对称配置（z_max = 8000，z_min = -8000）：
    - 输出对称地从-8000缩放到8000
    - 曲线在两个方向上一致应用

2. 对于非对称配置，其中|z_min| < z_max（z_max = 8000，z_min = -6000）：
    - 输出从-6000缩放到8000
    - 曲线按比例应用于每个限制

3. 对于非对称配置，其中|z_min| > z_max（z_max = 6000，z_min = -8000）：
    - 输出从-8000缩放到6000
    - 曲线按比例应用于每个限制

4. 对于极端非对称配置（10:1和1:10比率）：
    - 输出正确地达到各自的限制
    - 在极端情况下，输出与预期值之间的比率为100%

## 配置说明

要配置Z轴的非对称限制，请在配置文件中设置以下参数：

1. 在主配置文件（`config_beyond.ini`）中：
   ```ini
   [z]
   max = 8000    # 向下的最大推力
   min = -8000   # 向上的最大推力（负值）
   axis = 3
   deadzone = 0.05
   ```

2. 在模式配置文件（例如`mode_conch_harvesting.ini`）中：
   ```ini
   [axis_max]
   z = 8000      # 向下的最大推力
   z_min = -8000 # 向上的最大推力（负值）
   ```

通过调整这些值，您可以为不同的操作模式配置不同的Z轴限制。