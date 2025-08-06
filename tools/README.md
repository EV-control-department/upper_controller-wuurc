# ROV 控制系统工具目录

本目录包含 ROV 控制系统的各种工具，按功能分类组织。

## 目录结构

```
tools/
├── config_editors/     # 配置编辑工具
│   ├── keyboard_binding_editor.py    # 键盘绑定编辑器
│   ├── controller_mapping_editor.py  # 控制器映射编辑器
│   ├── start_keyboard_editor.bat     # 启动键盘绑定编辑器的批处理文件
│   └── start_controller_mapping_editor.bat  # 启动控制器映射编辑器的批处理文件
│
├── visualizers/        # 可视化工具
│   ├── controller_visualizer.py      # 控制器可视化工具
│   ├── thrust_curve_debugger.py      # 推力曲线调试器
│   ├── start_controller_visualizer.bat  # 启动控制器可视化工具的批处理文件
│   └── start_thrust_curve_debugger.bat  # 启动推力曲线调试器的批处理文件
│
├── testing/            # 测试工具
│   ├── test_joystick_correction.py   # 手柄辅助修正测试工具
│   ├── test_dual_motor_editing.py    # 双电机编辑测试
│   ├── test_dual_view_fixes.py       # 双视图修复测试
│   ├── run_dual_view_test.bat        # 运行双视图测试的批处理文件
│   └── run_performance_test.bat      # 运行性能测试的批处理文件
│
└── utilities/          # 实用工具
    ├── modified_on_motion.py         # 运动修改工具
    └── temp_draggable_plot.py        # 可拖动图表工具
```

## 工具说明

### 配置编辑工具

- **键盘绑定编辑器** (keyboard_binding_editor.py)：用于编辑 ROV 控制系统的键盘绑定配置。
- **控制器映射编辑器** (controller_mapping_editor.py)：用于编辑控制器按钮和轴的映射配置。

### 可视化工具

- **控制器可视化工具** (controller_visualizer.py)：实时显示控制器输入状态的可视化工具。
- **推力曲线调试器** (thrust_curve_debugger.py)：用于调试和可视化电机推力曲线的工具。

### 测试工具

- **手柄辅助修正测试工具** (test_joystick_correction.py)：测试手柄辅助修正功能的工具。
- **双电机编辑测试** (test_dual_motor_editing.py)：测试双电机编辑功能的工具。
- **双视图修复测试** (test_dual_view_fixes.py)：测试双视图修复功能的工具。

### 实用工具

- **运动修改工具** (modified_on_motion.py)：用于修改运动参数的工具。
- **可拖动图表工具** (temp_draggable_plot.py)：提供可交互拖动的图表功能。

## 使用方法

1. 使用批处理文件启动工具：
    - 双击对应的批处理文件即可启动相应的工具。

2. 直接运行 Python 脚本：
   ```
   python config_editors/keyboard_binding_editor.py
   ```

## 注意事项

- 部分工具需要先连接控制器才能正常工作。
- 配置编辑工具修改的配置文件位于项目根目录的 `config` 文件夹中。
- 测试工具主要用于开发和调试，普通用户可能不需要使用。