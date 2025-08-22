# 键盘绑定配置加载错误修复

## 问题描述

在加载配置文件时出现错误：`invalid literal for int() with base 10:'j'`

这个错误发生在尝试将字符串 'j' 转换为整数时。具体来说，当 `controller_mapping_editor.py` 脚本尝试加载
`toggle_joystick_correction_key` 配置项时，它错误地尝试将值 'j' 转换为整数。

## 根本原因

在 `ButtonMappingWidget` 类的 `__init__` 方法中，所有配置值都使用 `getint()` 方法进行处理：

```python
self.button_value = self.config_manager.config[section].getint(key)
```

然而，在 `config_beyond.ini` 文件中，`toggle_joystick_correction_key` 被设置为字符 'j'：

```ini
[keyboard_bindings]
toggle_joystick_correction_key = j
```

由于 'j' 不是有效的整数，所以当尝试将其转换为整数时会引发错误。

## 解决方案

修改 `ButtonMappingWidget` 类，使其能够区分按钮映射（需要整数值）和键盘绑定（使用字符值）：

1. 在 `__init__` 方法中检查 section 是否为 "keyboard_bindings"：

```python
if section == "keyboard_bindings":
    self.button_value = self.config_manager.config[section].get(key)
    self.is_keyboard_binding = True
else:
    self.button_value = self.config_manager.config[section].getint(key)
    self.is_keyboard_binding = False
```

2. 为键盘绑定创建不同的 UI 组件：

```python
if self.is_keyboard_binding:
    # 对于键盘绑定，使用文本标签显示当前值
    self.key_label = QLabel(self.button_value)
    self.change_button = QPushButton("更改按键")
    self.change_button.clicked.connect(self.change_key)
    key_layout = QHBoxLayout()
    key_layout.addWidget(self.key_label)
    key_layout.addWidget(self.change_button)
    layout.addRow("按键:", key_layout)
    # 隐藏按钮编号控件
    self.button_combo = None
else:
    # 对于按钮映射，使用数字选择框
    self.button_combo = QSpinBox()
    self.button_combo.setMinimum(0)
    self.button_combo.setMaximum(15)  # 假设最多16个按钮
    self.button_combo.setValue(self.button_value)
    layout.addRow("按钮编号:", self.button_combo)
```

3. 添加 `change_key` 方法来处理键盘绑定的更改：

```python
def change_key(self):
    """更改键盘绑定按键"""
    # 创建一个简单的对话框来捕获按键
    # ...
    if dialog.exec_() == QDialog.Accepted and captured_key[0]:
        # 更新UI和配置
        self.key_label.setText(captured_key[0])
        self.button_value = captured_key[0]
        self.config_manager.config[self.section][self.key] = captured_key[0]
        # ...
```

4. 更新 `update_test_value` 和 `apply_changes` 方法以处理键盘绑定：

```python
def update_test_value(self, joystick):
    if self.is_keyboard_binding:
        # 键盘绑定不需要实时测试
        self.test_label.setText("键盘按键")
        self.test_label.setStyleSheet("color: blue;")
    elif joystick and self.button_combo and self.button_combo.value() < joystick.get_numbuttons():
# ...
```

```python
def apply_changes(self):
    try:
        # 对于键盘绑定，更改按键已经在change_key方法中处理
        if not self.is_keyboard_binding and self.button_combo:
        # 更新配置
        # ...
        elif self.is_keyboard_binding:
    # 对于键盘绑定，提示用户使用"更改按键"按钮
    # ...
    except Exception as e:
# ...
```

## 测试

修复后，controller_mapping_editor.py 脚本应该能够正确加载配置文件，包括键盘绑定部分，而不会出现 "invalid literal for int()"
错误。

## 未来改进

为了使代码更加健壮，可以考虑以下改进：

1. 在 ConfigManager 类中添加专门的方法来获取键盘绑定
2. 为不同类型的配置项（按钮、轴、键盘按键等）创建专门的 UI 组件
3. 添加更多的错误处理和用户反馈