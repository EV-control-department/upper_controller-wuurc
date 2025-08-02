# ROV上位机控制系统 V2.0.0

## 项目简介

本项目是ROV（远程操作潜水器）控制上位机软件，用于通过Xbox手柄控制ROV的运动和操作。软件支持视频流显示、深度温度监控、舵机控制等功能，采用模块化设计，具有非阻塞模式的线程处理机制，提高了系统的响应性和稳定性。

## 发布信息

**最新版本**: V2.0.0 (2025-08-02)

此版本进行了全面的模块化重构，将阻塞操作改为非阻塞模式，显著提高了系统响应性和稳定性。详细发布说明请参阅 [发布说明文档](docs/RELEASE_NOTES.md)。

## 项目构建

### 环境要求

- **操作系统**：Windows 10/11、Linux或macOS
- **Python版本**：Python 3.8+
- **外部依赖**：FFmpeg（用于视频流处理）
- **硬件要求**：Xbox控制器（推荐使用Xbox One或Xbox Series控制器）

### 安装步骤

1. **克隆或下载项目**：
   ```
   git clone https://github.com/your-username/upper_controller-wuurc.git
   cd upper_controller-wuurc_V1.0
   ```

2. **安装FFmpeg**：
    - **Windows**：
        1. 从[FFmpeg官网](https://ffmpeg.org/download.html)下载Windows版本
        2. 解压到任意目录（如`C:\ffmpeg`）
        3. 将FFmpeg的bin目录（如`C:\ffmpeg\bin`）添加到系统环境变量PATH中
        4. 重启命令提示符或PowerShell以使更改生效
        5. 验证安装：`ffmpeg -version`

    - **Linux (Ubuntu/Debian)**：
      ```
      sudo apt update
      sudo apt install ffmpeg
      ffmpeg -version
      ```

    - **macOS**：
      ```
      brew install ffmpeg
      ffmpeg -version
      ```

3. **安装Python依赖**（**必须步骤**）：
   ```
   pip install -r requirements.txt
   ```

   > **重要提示**：必须安装所有依赖项才能运行程序。如果遇到"ModuleNotFoundError: No module named 'xxx'"
   错误，请确保已正确执行上述命令安装所有依赖。

4. **配置文件设置**：
    - 默认配置文件为`config/config_beyond.ini`
    - 如需自定义配置，请复制并重命名（如`config/config_custom.ini`）
    - 根据需要修改配置参数（摄像头URL、网络设置、控制器映射等）

### 项目结构

```
upper_controller-wuurc_V2.0/
├── assets/                    # 资源文件目录
│   ├── calibration_images/    # 相机校准图像
│   ├── default_image.jpg      # 默认图像
│   └── EV.jpg                 # 项目图像
├── config/                    # 配置文件目录
│   ├── config_beyond.ini      # 主配置文件
│   ├── config_hailing.ini     # 备用配置文件
│   └── curve.json             # 电机曲线参数
├── docs/                      # 文档目录
│   ├── CHANGES.md             # 变更日志
│   ├── CHINESE_FONT_FIX.md    # 中文字体修复说明
│   ├── PACKAGING.md           # 打包说明文档
│   └── requirements.md        # 需求文档
├── modules/                   # 模块目录
│   ├── __init__.py            # 包初始化文件
│   ├── config_manager.py      # 配置管理模块
│   ├── depth_temperature_controller.py # 深度温度控制模块
│   ├── hardware_controller.py # 硬件控制模块
│   ├── joystick_controller.py # 手柄控制模块
│   ├── main_controller.py     # 主控制器模块
│   ├── ui_controller.py       # 用户界面控制模块
│   └── video_processor.py     # 视频处理模块
├── scripts/                   # 脚本目录
│   └── start.bat              # 启动脚本（Windows）
├── tests/                     # 测试目录
│   ├── test_chinese_font.py   # 中文字体测试
│   └── test_minimal.py        # 最小化测试
├── build_exe.bat              # 打包批处理文件
├── build_exe.py               # 打包Python脚本
├── main.py                    # 主程序
└── requirements.txt           # 依赖列表
```

## 运行说明

### 启动程序

1. **确保Xbox控制器已连接**到电脑

2. **启动方式**：
    - **Windows**：双击`scripts/start.bat`
    - **命令行**：`python main.py`
    - **可执行文件**：双击`ROV_Controller.exe`（如已打包）

3. **使用自定义配置**：
    - 修改`modules/config_manager.py`中的默认配置路径
    - 或在命令行中指定：`python main.py --config config/your_custom_config.ini`

### 打包为可执行文件

可以将程序打包为可执行文件，方便分发和使用：

1. **打包方法**：
    - 双击`build_exe.bat`启动打包过程
    - 或运行命令：`python build_exe.py`

2. **打包结果**：
    - 打包完成后，可执行文件位于`dist/ROV_Controller`目录中
    - 使用了目录模式而非单文件模式，大幅减小了文件大小
    - 运行时请执行目录中的`ROV_Controller.exe`文件

3. **优化说明**：
    - 采用了多种技术优化打包大小，避免生成过大的可执行文件
    - 排除了不必要的库和模块，仅包含程序运行所需的组件
    - 详细的优化说明请参阅`docs/PACKAGING.md`中的"文件大小优化"部分

4. **注意事项**：
    - 用户计算机上仍需安装FFmpeg并添加到系统PATH
    - 详细打包说明请参阅`docs/PACKAGING.md`

### 控制说明

#### 手柄控制

- **左摇杆**：上下Y轴移动，左右X轴移动，按下切换舵机锁定状态
- **右摇杆**：上下Z轴移动，左右Yaw旋转
- **A键**：速度模式切换
- **B键**：切换抓取模式
- **Y键**：爪子切换至转换张角
- **X键**：爪子切换至特定张角
- **左肩键**：爪子切换至最大张角
- **右肩键**：爪子闭合
- **左线性扳机**：
    1. 给予所有运动速度一个随着扳机扣下1~0.25变化的附加系数
    2. 扣下过20%，自动进入轻柔模式状态，松开退回原状态
- **右线性扳机**：
    1. 在未锁定模式下扳机线性处理
    2. 在锁定模式下按到最低，切换至释放模式，释放舵机可对爪子进行从当前状态到最大闭合状态的线性控制
- **Xbox键**：按下时阻塞进程，缓解延迟问题
- **左侧按钮(6)**：启动/停止深度温度记录

#### 键盘控制

- **T键**：切换屏幕方向（横屏/竖屏）
- **F键**：切换全屏模式
- **D键**：启动Xbox调试器，用于查看键位映射
- **S键**：切换有/无畸变显示
- **P键**：捕获当前视频帧
- **Q键**：退出程序

## 配置文件说明

### config/config_beyond.ini

配置文件分为多个部分：

1. **[camera]** - 摄像头设置
    - `rtsp_url` - RTSP视频流URL
    - `width` - 视频宽度
    - `height` - 视频高度
    - `buffer` - 缓冲区大小

2. **[network]** - 网络设置
    - `remote_ip` - 远程IP地址
    - `remote_port` - 远程端口
    - `local_port` - 本地端口

3. **[joystick]** - 手柄设置
    - `deadzone` - 摇杆死区
    - `sensitivity` - 灵敏度
    - 各按键映射

### config/curve.json

电机曲线参数文件，包含：

- 每个电机（m0-m5）的参数
- 控制曲线的关键点参数

## 常见问题解决

1. **黑屏问题**：
    - 原因：软件正在尝试接收视频流
    - 解决方法：等待连接建立；检查网络连接、摄像头和路由器

2. **控制无响应**：
    - 原因：可能是ROV内部初始化延迟
    - 解决方法：耐心等待；必要时重启软件

3. **延迟问题**：
    - 原因：启动时视频处理线程负载高
    - 解决方法：按下Xbox键暂时阻塞进程

4. **全屏失焦**：
    - 问题：全屏模式下失去焦点会切换屏幕
    - 解决方法：比赛中避免切换窗口

5. **FFmpeg错误**：
    - 原因：FFmpeg未正确安装或未添加到PATH
    - 解决方法：重新安装FFmpeg并确保添加到系统PATH

6. **SDL3库加载失败**：
    - 原因：Pygame 2.5.0+使用SDL3，可能在打包后无法正确加载
    - 解决方法：
        - 使用最新版本的打包脚本，它会自动处理SDL3问题
        - 或手动降级Pygame：`pip install pygame==2.4.0 --force-reinstall`
    - 详细信息：参见`docs/PACKAGING.md`中的"SDL3相关问题说明"

## 开发指南

### 项目组织说明

项目已经进行了目录重组，以提高可维护性：

- **assets/**：存放所有资源文件，包括图像和校准数据
- **config/**：集中存放所有配置文件
- **docs/**：存放项目文档
- **modules/**：存放所有Python模块
- **scripts/**：存放启动和工具脚本
- **tests/**：存放测试文件

这种组织结构使项目更加清晰，便于维护和扩展。

### 模块说明

1. **config_manager.py**：
    - 负责加载和管理配置文件
    - 提供统一的配置访问接口

2. **hardware_controller.py**：
    - 负责与ROV硬件通信
    - 包含控制器监控和网络通信功能

3. **video_processor.py**：
    - 处理视频流和图像处理
    - 使用FFmpeg进行高效视频解码

4. **ui_controller.py**：
    - 负责用户界面显示
    - 处理键盘和手柄输入

5. **joystick_controller.py**：
    - 处理手柄输入逻辑
    - 实现各种控制模式

6. **depth_temperature_controller.py**：
    - 管理深度和温度数据记录
    - 提供数据保存功能

### 自定义开发

如需修改或扩展功能，建议按照以下步骤：

1. 首先了解各模块的职责和接口
2. 在相应模块中添加或修改功能
3. 如需添加新模块，请在modules目录下创建新文件，并在main.py中导入

## 版权信息

张殷瑞&人机交互中国水版本

![img](https://img1.baidu.com/it/u=4019763367,1639339942&fm=253&fmt=auto&app=138&f=JPEG?w=541&h=500)
