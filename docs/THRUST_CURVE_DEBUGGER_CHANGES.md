# 推力曲线调试器更新文档

## 更新内容概述

本次更新解决了推力曲线调试器 (`thrust_curve_debugger.py`) 中的以下问题：

1. 在双曲线视图模式下，确保只有当前正在编辑的电机曲线可以被拖动，另一个电机曲线不可拖动
2. 实现了电机选择队列机制，解决了选择三个以上电机按钮的情况
3. 增强了UI反馈，使用户更容易识别当前正在编辑的电机

## 详细更改

### 1. 防止非编辑电机的点被拖动

修改了 `DraggablePointPlot` 类的 `on_press` 方法，添加了检查逻辑，确保在双曲线视图模式下，只有当前正在编辑的电机的点可以被拖动：

```python
def on_press(self, event):
    if event.inaxes != self.axes: return
    for artist in self.points_artists:
        contains, _ = artist.contains(event)
        if contains:
            name = artist.get_gid()

            # 检查是否是比较曲线的点
            is_comparison_point = name.endswith('_comp')

            # 在双曲线视图模式下，只允许拖动当前正在编辑的电机的点
            if self.is_dual_view:
                if (is_comparison_point and self.editing_primary_motor) or
                        (not is_comparison_point and not self.editing_primary_motor):
                    # 不允许拖动非编辑电机的点
                    return

            self._drag_point_info = (artist, name)
            self.point_selected.emit(name);
            return
```

### 2. 实现电机选择队列机制

添加了电机选择队列属性，并修改了 `on_motor_button_clicked` 方法，实现了队列机制：

1. 添加了 `motor_selection_queue` 属性，用于存储选中的电机队列
2. 修改了 `on_motor_button_clicked` 方法，实现了以下逻辑：
    - 当选择新电机时，将其添加到队列中
    - 如果队列超过2个电机，移除最早的一个（不是当前主电机）
    - 更新UI以反映队列变化

```python
# 在MainWindow类的__init__方法中添加队列属性
# self.motor_selection_queue = []  # 用于存储选中的电机队列，最多保留两个

# 在on_motor_button_clicked方法中实现队列管理逻辑
# 当选择新电机时，将其添加到队列
# if motor_name not in self.motor_selection_queue:
#     self.motor_selection_queue.append(motor_name)

# 如果队列超过2个，移除最早的一个（不是当前主电机）
# if len(self.motor_selection_queue) > 2:
#     # 找到要移除的电机（不是当前选中的电机）
#     to_remove = None
#     for m in self.motor_selection_queue:
#         if m != motor_name and m != self.current_motor:
#             to_remove = m
#             break

#     # 如果没有找到可移除的，移除最早的一个
#     if to_remove is None and len(self.motor_selection_queue) > 0:
#         to_remove = self.motor_selection_queue[0]

#     # 移除电机并更新UI
#     if to_remove is not None:
#         self.motor_selection_queue.remove(to_remove)
#         self.motor_buttons[to_remove].setChecked(False)
#         self.motor_buttons[to_remove].setStyleSheet("")

#         # 如果移除的是比较电机，清除比较电机
#         if to_remove == self.comparison_motor:
#             self.comparison_motor = None
```

队列管理的主要逻辑：

1. 维护一个最多包含两个电机的队列
2. 当选择新电机时，将其添加到队列
3. 如果队列超过2个，移除最早的非主电机
4. 更新UI以反映队列变化

### 3. 增强UI反馈

修改了 `_update_editing_motor_ui` 方法，增强了视觉反馈，使用户更容易识别当前正在编辑的电机：

```python
# 修改_update_editing_motor_ui方法以增强视觉反馈
# def _update_editing_motor_ui(self):
#     """更新UI以显示当前正在编辑的电机"""
#     if self.editing_primary_motor:
#         # 编辑主电机时的样式
#         self.curve_params_group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #f0f0ff; }")
#         self.comparison_params_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0066cc; }")
#         self.switch_motor_btn.setText(f"当前编辑: {self.current_motor} (点击切换)")
#         
#         # 更新按钮样式，主电机使用实线边框
#         self.motor_buttons[self.current_motor].setStyleSheet("background-color: #AED6F1; border: 2px solid #2980B9;")
#         self.motor_buttons[self.comparison_motor].setStyleSheet("background-color: #D6E9F1; border: 1px dashed #5DADE2;")
#     else:
#         # 编辑比较电机时的样式
#         self.curve_params_group.setStyleSheet("QGroupBox { font-weight: bold; }")
#         self.comparison_params_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0066cc; background-color: #f0f0ff; }")
#         self.switch_motor_btn.setText(f"当前编辑: {self.comparison_motor} (点击切换)")
#         
#         # 更新按钮样式，比较电机使用实线边框
#         self.motor_buttons[self.current_motor].setStyleSheet("background-color: #AED6F1; border: 1px dashed #2980B9;")
#         self.motor_buttons[self.comparison_motor].setStyleSheet("background-color: #D6E9F1; border: 2px solid #5DADE2;")
```

UI增强的主要改进：

1. 当前正在编辑的电机按钮使用实线边框高亮显示
2. 非编辑状态的电机按钮使用虚线边框显示
3. 参数输入区域的背景色也会相应变化，以指示当前正在编辑的是哪个电机的参数

## 使用说明

1. **电机选择**：
    - 在"电机选择与操作"区域中，最多可以同时选择两个电机
    - 如果尝试选择第三个电机，系统会自动取消选择最早选择的非主电机

2. **双曲线视图**：
    - 在双曲线视图模式下，实线表示当前正在编辑的电机曲线，虚线表示比较电机曲线
    - 只有当前正在编辑的电机曲线可以被拖动修改
    - 可以通过"当前编辑: XX (点击切换)"按钮切换当前正在编辑的电机

3. **视觉反馈**：
    - 当前正在编辑的电机按钮使用实线边框高亮显示
    - 非编辑状态的电机按钮使用虚线边框显示
    - 参数输入区域的背景色也会相应变化，以指示当前正在编辑的是哪个电机的参数