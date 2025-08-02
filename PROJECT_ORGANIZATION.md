# 项目文件整理说明

## 整理目的

为了提高项目的可维护性和可读性，对项目文件进行了重新组织和整理。这种组织结构使项目更加清晰，便于维护和扩展。

## 主要变更

### 1. 创建了逻辑目录结构

将项目文件按照功能和类型分类到不同的目录中：

- **assets/**：存放所有资源文件
    - 图像文件（default_image.jpg, EV.jpg）
    - 相机校准图像（calibration_images/）
    - 捕获的图像将保存在此目录

- **config/**：集中存放所有配置文件
    - 主配置文件（config_beyond.ini）
    - 备用配置文件（config_hailing.ini）
    - 电机曲线参数（curve.json）

- **docs/**：存放项目文档
    - 变更日志（CHANGES.md）
    - 中文字体修复说明（CHINESE_FONT_FIX.md）
    - 需求文档（requirements.md）

- **modules/**：存放所有Python模块
    - 保持原有的模块结构不变

- **scripts/**：存放启动和工具脚本
    - 启动脚本（start.bat）

- **tests/**：存放测试文件
    - 中文字体测试（test_chinese_font.py）
    - 最小化测试（test_minimal.py）

### 2. 更新了代码中的文件路径

修改了以下文件中的路径引用，以适应新的目录结构：

- **modules/config_manager.py**：
    - 更新了配置文件路径（config_beyond.ini）
    - 更新了电机曲线参数文件路径（curve.json）

- **modules/video_processor.py**：
    - 更新了图像保存路径，现在保存到assets目录

- **modules/ui_controller.py**：
    - 更新了默认图像加载路径（default_image.jpg）

- **scripts/start.bat**：
    - 更新了启动脚本，添加了返回上级目录的命令

### 3. 更新了文档

- 更新了README.md中的项目结构描述
- 更新了README.md中的启动说明
- 更新了README.md中的配置文件路径
- 添加了项目组织说明部分

## 优势

1. **提高可维护性**：相关文件集中存放，便于查找和修改
2. **提高可读性**：目录结构清晰，新开发人员可以快速理解项目组织
3. **便于扩展**：为不同类型的文件预留了专门的目录，便于添加新文件
4. **减少混乱**：避免所有文件都放在根目录，减少混乱

## 后续建议

1. 继续保持这种组织结构，新增文件时放入对应目录
2. 考虑为不同类型的测试创建子目录（如单元测试、集成测试等）
3. 可以考虑添加自动化脚本，确保项目结构保持一致