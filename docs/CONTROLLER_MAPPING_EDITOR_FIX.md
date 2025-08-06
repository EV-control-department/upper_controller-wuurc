# Controller Mapping Editor Path Fix

## 问题描述

在运行 `controller_mapping_editor.py` 脚本时，出现以下错误：

```
FileNotFoundError: [WinError 3] 系统找不到指定的路径。: 'C:\\Users\\Zhang\\OneDrive\\Desktop\\upper_controller-wuurc\\tools\\config'
```

这个错误发生在 `load_default_config` 方法中，脚本尝试访问不存在的配置目录。

## 错误原因

错误的根本原因是在工具目录重构过程中，`controller_mapping_editor.py` 脚本被移动到了 `tools/config_editors/`
目录，但脚本中的路径计算没有相应更新：

1. 在 `load_default_config` 方法中，配置目录路径计算错误：
   ```python
   config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
   ```
   这个计算只向上导航两级目录（到 `tools/`），而不是三级（到项目根目录）。

2. 在导入部分，项目根目录添加到 Python 路径的代码也有同样的问题：
   ```python
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
   这导致了 `ModuleNotFoundError: No module named 'modules'` 错误。

## 修复方案

修复方案是更新路径计算，确保正确导航到项目根目录：

1. 在 `load_default_config` 方法中更新配置目录路径计算：
   ```python
   config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")
   ```

2. 更新 Python 路径添加代码：
   ```python
   sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
   ```

这两处修改确保了脚本可以正确找到配置目录和导入必要的模块。

## 测试结果

修复后，脚本能够正常运行，成功加载电机参数，不再出现路径错误或模块导入错误。

## 预防措施

为了防止类似的错误再次发生，建议：

1. 在移动脚本文件时，仔细检查和更新所有路径计算
2. 考虑使用相对于项目根目录的绝对路径，而不是相对路径
3. 添加路径验证代码，在路径不存在时提供更明确的错误信息
4. 在重构目录结构后进行全面测试，确保所有工具正常工作