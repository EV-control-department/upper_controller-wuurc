# 推力曲线调试器 (thrust_curve_debugger.py) 修复文档

## 问题描述

运行 thrust_curve_debugger.py 时出现错误：

```
thrust_curve_debugger.py无法加在或解析JSON文件 No such file or directory
```

这表明脚本无法找到或加载所需的 JSON 文件，出现了"文件不存在"错误。

## 根本原因

经过分析，发现以下问题：

1. 脚本使用相对路径尝试加载 JSON 文件，但路径解析逻辑不够健壮
2. 脚本没有检查文件是否存在就尝试打开它
3. 错误处理不够详细，无法提供有用的调试信息

具体来说，脚本在初始化时使用以下代码设置 JSON 文件路径：

```python
self.current_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "curve_beyond.json")
```

这个路径假设 config 目录位于脚本所在目录的上一级目录，但实际上 config 目录可能位于项目根目录下。

## 解决方案

修复包含以下几个方面：

### 1. 改进文件路径解析逻辑

修改后的代码会检查多个可能的文件位置：

```python
# First try to find the JSON file relative to the script location
script_relative_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config",
                                    "curve_beyond.json")

# Also check for the file relative to the current working directory
cwd_relative_path = os.path.join(os.getcwd(), "config", "curve_beyond.json")

# Use the first path that exists
if os.path.exists(script_relative_path):
    self.current_json_path = script_relative_path
elif os.path.exists(cwd_relative_path):
    self.current_json_path = cwd_relative_path
else:
    # If neither path exists, default to the script relative path but don't try to load it yet
    self.current_json_path = script_relative_path
    print(f"警告: 无法找到默认JSON文件: {script_relative_path}")
    print(f"也检查了: {cwd_relative_path}")
    print("请使用'导入JSON'按钮手动选择文件。")
```

### 2. 添加文件存在性检查

在尝试加载文件之前，先检查文件是否存在：

```python
# Only try to load the file if it exists
if os.path.exists(self.current_json_path):
    self.load_curve_data(self.current_json_path, is_initial_load=True)
else:
    # Initialize with empty data
    self.motor_data = {f"m{i}": {"num": i} for i in range(MOTOR_COUNT)}
    self.initial_motor_data = self.motor_data.copy()
    self.history_log = {key: [] for key in self.motor_data.keys()}
```

### 3. 改进错误处理

在 `load_curve_data` 方法中添加更详细的错误处理：

```python
try:
    # Check if file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # Try to open and parse the file
    try:
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
    except json.JSONDecodeError as json_err:
        raise ValueError(f"JSON格式错误: {json_err}")
    except UnicodeDecodeError:
        raise ValueError("文件编码错误，请确保文件使用UTF-8编码")
    except PermissionError:
        raise PermissionError(f"没有权限读取文件: {filepath}")

    # ... 处理加载的数据 ...

except FileNotFoundError as e:
    error_msg = f"文件不存在: {filepath}\n\n请检查文件路径是否正确，并确保文件存在。"
    print(f"错误: {error_msg}")
    QMessageBox.critical(self, "文件未找到", error_msg)
except PermissionError as e:
    error_msg = f"没有权限读取文件: {filepath}\n\n请检查文件权限。"
    print(f"错误: {error_msg}")
    QMessageBox.critical(self, "权限错误", error_msg)
except ValueError as e:
    error_msg = f"文件格式错误: {e}\n\n请确保文件是有效的JSON格式。"
    print(f"错误: {error_msg}")
    QMessageBox.critical(self, "格式错误", error_msg)
except Exception as e:
    error_msg = f"无法加载或解析JSON文件: {e}"
    print(f"错误: {error_msg}")
    QMessageBox.critical(self, "加载失败", error_msg)
```

## 测试

修复后，thrust_curve_debugger.py 脚本应该能够：

1. 正确查找并加载 curve_beyond.json 文件
2. 如果找不到文件，提供清晰的错误信息
3. 允许用户通过 UI 手动选择 JSON 文件

## 未来改进建议

1. 考虑添加配置文件，允许用户指定默认 JSON 文件位置
2. 实现自动保存功能，避免数据丢失
3. 添加文件验证功能，确保加载的 JSON 文件包含所有必需的参数