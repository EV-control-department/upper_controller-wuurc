# ConfigParser 兼容性修复

## 问题描述

程序启动时出现以下错误：

```
成功加载默认图片: C:\Users\Zhang\OneDrive\Desktop\upper_controller-wuurc\assets\default_image.jpg
错误: 无法加载模式配置文件 mode_conch_harvesting.ini: 'SectionProxy' object has no attribute 'has_option'
错误: 无法加载模式配置文件 mode_feed_distribution.ini: 'SectionProxy' object has no attribute 'has_option'
错误: 无法加载模式配置文件 mode_net_recovery.ini: 'SectionProxy' object has no attribute 'has_option'
错误: 无法加载模式配置文件 mode_precision_operation.ini: 'SectionProxy' object has no attribute 'has_option'
警告: 未能成功加载任何模式配置，使用默认值
程序异常: 'SectionProxy' object has no attribute 'has_option'
```

这个错误表明在尝试加载模式配置文件时，程序使用了 `has_option` 方法，但该方法在当前使用的 ConfigParser 版本中不可用或不适用于
SectionProxy 对象。

## 解决方案

修改了 `config_manager.py` 文件中的两处代码，将 `has_option` 方法替换为使用 `in` 运算符来检查配置选项是否存在：

1. 在 `get_axis_config` 方法中：
   ```python
   # 修改前
   if self.config[axis_name].has_option("min"):
       config_dict["min"] = self.config[axis_name].getfloat("min")
   
   # 修改后
   if "min" in self.config[axis_name]:
       config_dict["min"] = self.config[axis_name].getfloat("min")
   ```

2. 在 `get_catch_modes` 方法中：
   ```python
   # 修改前
   if mode_config['axis_max'].has_option('z_min'):
       mode_data["z_min"] = mode_config['axis_max'].getfloat('z_min', -8000)
   
   # 修改后
   if 'z_min' in mode_config['axis_max']:
       mode_data["z_min"] = mode_config['axis_max'].getfloat('z_min', -8000)
   ```

## 技术说明

在 Python 的 ConfigParser 模块中，检查配置选项是否存在有两种主要方法：

1. 使用 `ConfigParser.has_option(section, option)` 方法，这是在 ConfigParser 对象上调用的。
2. 使用 `in` 运算符检查选项是否在 section 中，如 `option in config[section]`。

第二种方法更加通用，并且在不同版本的 Python 和 ConfigParser 实现中更加一致。我们的修改使用了这种更兼容的方法，应该能够解决配置加载错误。

## 预期结果

这些更改应该能够解决模式配置文件加载失败的问题，使程序能够正确读取所有模式配置，而不是回退到默认值。程序应该能够正常启动和运行，不再出现
`'SectionProxy' object has no attribute 'has_option'` 错误。