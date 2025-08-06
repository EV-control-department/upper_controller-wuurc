# 控制器映射编辑器更新

## 更新内容

在控制器映射编辑器(`controller_mapping_editor.py`)中添加了对手柄辅助修正键(`toggle_joystick_correction_key`)的支持。

## 具体修改

1. 在`create_button_mapping_widgets`方法中添加了新的"辅助功能按钮"组，包含手柄辅助修正切换按钮。
2. 新增的代码如下：

```python
# 创建辅助功能按钮映射组
aux_group = QGroupBox("辅助功能按钮")
aux_layout = QVBoxLayout(aux_group)

# 手柄辅助修正按钮
joystick_correction_widget = ButtonMappingWidget(
    self.config_manager, "keyboard_bindings", "toggle_joystick_correction_key", "手柄辅助修正切换"
)
aux_layout.addWidget(joystick_correction_widget)
self.button_widgets["toggle_joystick_correction_key"] = joystick_correction_widget

buttons_layout.addWidget(aux_group)
```

## 测试结果

创建了单元测试`test_controller_mapping_editor.py`来验证修改是否正确。测试确认：

1. 手柄辅助修正按钮已正确添加到控制器映射编辑器中
2. 按钮的属性（section, key, description）设置正确
3. 按钮被正确存储在`button_widgets`字典中

测试结果显示所有测试都通过，确认修改有效。

## 相关文件

- 修改的文件：
    - `tools/config_editors/controller_mapping_editor.py`

- 新增的文件：
    - `tests/test_controller_mapping_editor.py`（测试脚本）
    - `docs/CONTROLLER_MAPPING_EDITOR_UPDATE.md`（本文档）

## 使用说明

用户现在可以通过控制器映射编辑器查看和修改手柄辅助修正功能的键绑定。操作步骤：

1. 启动控制器映射编辑器（按`m`键或通过菜单）
2. 在"按钮映射"选项卡中，找到"辅助功能按钮"组
3. 点击"手柄辅助修正切换"旁边的"修改"按钮来更改键绑定

## 总结

此更新完成了对控制器映射编辑器的修改，使其支持手柄辅助修正键的配置。这是对之前已完成的配置管理器更新的补充，确保整个系统对该功能有完整的支持。