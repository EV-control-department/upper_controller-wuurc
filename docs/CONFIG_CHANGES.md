# 配置系统改进文档

## 概述

为了提高系统的可维护性和灵活性，我们对配置系统进行了重构，将所有可修订参数移至配置文件中进行集中管理。这些更改使得系统更易于配置和维护，无需修改代码即可调整系统行为。

## 主要更改

### 1. 新增配置部分

在配置文件中添加了以下新部分：

#### 模式默认值 (mode_defaults)

```ini
[mode_defaults]
; 初始模式指针
speed_mode_ptr = 2
lock_mode_ptr = 2
loop_mode_ptr = 0
catch_mode_ptr = 0
```

这些设置控制系统启动时的默认模式。

#### 控制器时间设置 (controller_timing)

```ini
[controller_timing]
; 阻塞持续时间(秒)
button10_block_duration = 3
depth_temp_block_duration = 0.2
```

这些设置控制各种操作的阻塞时间。

#### 控制器阈值设置 (controller_thresholds)

```ini
[controller_thresholds]
; 特殊功能的轴阈值
left_trigger_threshold = -0.5
right_trigger_threshold = 0.9
hat_up_value = 1
```

这些设置定义了触发特定功能的阈值。

### 2. ConfigManager 类增强

在 `ConfigManager` 类中添加了新方法以支持访问新的配置参数：

- `get_mode_defaults()`: 获取模式默认值
- `get_controller_timing()`: 获取控制器时间设置
- `get_controller_thresholds()`: 获取控制器阈值设置

### 3. 代码更新

更新了 `joystick_controller.py` 以使用新的配置方法，替换了之前的硬编码值。主要更改包括：

- 使用配置的模式默认值初始化模式指针
- 使用配置的控制器时间设置初始化阻塞持续时间
- 使用配置的控制器阈值进行条件判断

## 使用说明

### 修改配置

要修改系统行为，只需编辑配置文件中的相应参数：

1. 打开 `config/config_beyond.ini` 或 `config/config_hailing.ini`
2. 找到相应的部分并修改参数值
3. 保存文件并重启应用程序

### 添加新配置参数

如需添加新的配置参数：

1. 在适当的配置部分添加新参数，或创建新的配置部分
2. 在 `ConfigManager` 类中添加相应的访问方法
3. 更新代码以使用新的配置参数

## 注意事项

- 配置文件使用 UTF-8 编码，确保在编辑时保持此编码
- 修改配置文件时请保持正确的 INI 格式
- 建议在修改配置前备份原始配置文件