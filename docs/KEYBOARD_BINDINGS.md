# 键盘绑定系统文档

## 概述

ROV控制系统支持可配置的键盘绑定，允许用户自定义各种功能的快捷键。本文档介绍了键盘绑定系统的设计、配置方法以及键盘绑定编辑器的使用方法。

## 键盘绑定配置

### 配置文件结构

键盘绑定配置存储在配置文件（如`config_beyond.ini`）中的以下两个部分：

1. **keyboard_bindings** - 定义各功能的键盘绑定
   ```ini
   [keyboard_bindings]
   ; 键盘快捷键设置
   quit_key = q
   xbox_debugger_key = d
   toggle_rotation_key = t
   toggle_undistorted_key = s
   toggle_fullscreen_key = f
   capture_frame_key = p
   ```

2. **key_cooldowns** - 定义按键冷却时间（防止按键重复触发）
   ```ini
   [key_cooldowns]
   ; 按键冷却时间（秒）
   xbox_debugger_cooldown = 0.5
   toggle_rotation_cooldown = 0.5
   toggle_undistorted_cooldown = 0.5
   toggle_fullscreen_cooldown = 0.5
   capture_frame_cooldown = 0.2
   button7_cooldown = 0.2
   ```

### 可配置的键盘功能

| 配置键名                   | 默认值 | 功能描述          |
|------------------------|-----|---------------|
| quit_key               | q   | 退出程序          |
| xbox_debugger_key      | d   | 打开Xbox调试器     |
| toggle_rotation_key    | t   | 切换屏幕方向（横屏/竖屏） |
| toggle_undistorted_key | s   | 切换无失真视图       |
| toggle_fullscreen_key  | f   | 切换全屏模式        |
| capture_frame_key      | p   | 捕获当前视频帧       |

### 手动修改配置

您可以通过直接编辑配置文件来修改键盘绑定：

1. 打开配置文件（`config/config_beyond.ini`或`config/config_hailing.ini`）
2. 找到`[keyboard_bindings]`部分
3. 修改相应的键值
4. 保存文件并重启应用程序

## 键盘绑定编辑器

为了方便修改键盘绑定，系统提供了一个图形化的键盘绑定编辑器。

### 启动编辑器

有两种方式启动键盘绑定编辑器：

1. 运行`tools/start_keyboard_editor.bat`批处理文件
2. 直接运行`python tools/keyboard_binding_editor.py`

### 使用编辑器

1. **选择配置文件**：
    - 启动后，编辑器会自动加载`config`目录中的配置文件
    - 使用顶部的下拉框选择要编辑的配置文件
    - 也可以点击"浏览..."按钮选择其他位置的配置文件

2. **查看当前绑定**：
    - 上方表格显示当前的键盘绑定
    - 下方表格显示按键冷却时间设置

3. **修改键盘绑定**：
    - 点击要修改的绑定旁边的"修改"按钮
    - 在弹出的对话框中按下新的按键
    - 点击"确定"确认更改

4. **修改冷却时间**：
    - 双击冷却时间单元格
    - 输入新的冷却时间值（秒）
    - 按Enter确认

5. **保存更改**：
    - 点击"保存更改"按钮将修改保存到配置文件
    - 保存成功后会显示确认消息

6. **重新加载**：
    - 点击"重新加载"按钮可以放弃未保存的更改并重新加载配置文件

### 注意事项

- 修改键盘绑定后，需要重启主应用程序才能生效
- 冷却时间必须是有效的数字，且不能为负数
- 建议在修改配置前备份原始配置文件

## 开发信息

### 相关文件

- `config/config_beyond.ini`和`config/config_hailing.ini`：配置文件
- `modules/config_manager.py`：配置管理器，包含读取键盘绑定的方法
- `modules/ui_controller.py`：UI控制器，使用键盘绑定处理键盘输入
- `tools/keyboard_binding_editor.py`：键盘绑定编辑器

### 添加新的键盘绑定

如需添加新的键盘绑定，需要：

1. 在配置文件的`[keyboard_bindings]`部分添加新的键值对
2. 在`ConfigManager`类中的`get_keyboard_bindings`方法中添加新的键
3. 在使用该绑定的代码中获取并使用新的绑定
4. 更新键盘绑定编辑器中的功能描述映射

### 技术实现

键盘绑定系统的实现基于以下组件：

1. **ConfigManager**：负责从配置文件加载键盘绑定和冷却时间
2. **UIController**：使用加载的键盘绑定处理键盘输入
3. **KeyboardBindingEditor**：提供图形界面编辑键盘绑定

键盘输入处理使用`keyboard`库实现非阻塞式按键检测，并使用冷却时间机制防止按键重复触发。