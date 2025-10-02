# ROV上位机控制系统 V2.1.0

## 项目简介

本项目是ROV（远程操作潜水器）控制上位机软件，用于通过Xbox手柄控制ROV的运动和操作。软件支持视频流显示、深度温度监控、舵机控制等功能，采用模块化设计，具有非阻塞模式的线程处理机制，提高了系统的响应性和稳定性。

## 发布信息

**最新版本**: V2.1.0 (2025-08-22)

此版本进行了全面的模块化重构，将阻塞操作改为非阻塞模式，显著提高了系统响应性和稳定性。详细发布说明请参阅 [发布说明文档](docs/RELEASE_NOTES.md)。

## 项目构建

### 环境要求

- **操作系统**：Windows 10/11、Linux或macOS
- **Python版本**：Python 3.8+
- **外部依赖**：FFmpeg（用于视频流处理；打包版已内置 Windows FFmpeg，可直接运行）
- **硬件要求**：Xbox控制器（推荐使用Xbox One或Xbox Series控制器）

### 安装步骤

1. **克隆或下载项目**：
   ```
   git clone git@github.com:exp-049/upper_controller-wuurc.git
   cd upper_controller-wuurc
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
upper_controller-wuurc/
├── assets/                    # 资源文件目录
│   ├── calibration_images/    # 相机校准图像
│   ├── default_image.jpg      # 默认图像
│   └── EV.jpg                 # 项目图像
├── config/                    # 配置文件目录
│   ├── config_beyond.ini      # 主配置文件
│   ├── config_hailing.ini     # 备用配置文件
│   ├── modes/                 # 各作业模式配置
│   └── curve.json             # 电机曲线参数（或由 INI 的 [curve] location 指定）
├── docs/                      # 文档目录
│   ├── PACKAGING.md           # 打包说明文档
│   ├── RELEASE_NOTES.md       # 发布说明
│   └── notes/                 # 内部技术笔记
├── modules/                   # 模块目录
│   ├── config_manager.py      # 配置管理模块
│   ├── depth_temperature_controller.py # 深度温度控制模块
│   ├── hardware_controller.py # 硬件控制模块
│   ├── joystick_controller.py # 手柄控制模块
│   ├── ui_controller.py       # 用户界面控制模块
│   └── video_processor.py     # 视频处理模块
├── tools/                     # 开发/调试工具
│   ├── config_editors/        # 配置编辑器
│   ├── visualizers/           # 可视化工具
│   └── utilities/             # 实用工具（包含 xbox_debugger.py）
├── build/                     # 打包与spec文件
│   ├── build_exe.bat          # 打包批处理文件
│   └── build_exe.py           # 打包Python脚本
├── scripts/                   # 脚本目录
│   └── start.bat              # 启动脚本（Windows）
├── tests/                     # 测试目录（精简，保留快速单测）
│   └── test_controller_mapping_editor.py
├── main.py                    # 主程序
└── requirements.txt           # 依赖列表
```

## 运行说明

### 启动程序

1. **确保Xbox控制器已连接**到电脑
2. **安装依赖**：
   运行`scripts/setup_and_test.py`脚本，将自动安装依赖到当前环境并测试
3. **启动方式**（三种方法）：
    - **Windows**：双击`scripts/start.bat`
    - **命令行**：`python main.py`
   - **可执行文件**：（如已打包），双击`ROV_Controller.exe`

4. **使用自定义配置**：
    - 修改`modules/config_manager.py`中的默认配置路径
    - 或在命令行中指定：`python main.py --config config/your_custom_config.ini`

### 打包为可执行文件

可以将程序打包为可执行文件，方便分发和使用：

1. **打包方法**：
    - 双击`build\\build_exe.bat`启动打包过程
    - 或运行命令：`python build\\build_exe.py`

2. **打包结果**：
    - 打包完成后，可执行文件位于`dist/ROV_Controller`目录中
    - 使用了目录模式而非单文件模式，大幅减小了文件大小
    - 运行时请执行目录中的`ROV_Controller.exe`文件

3. **优化说明**：
    - 采用了多种技术优化打包大小，避免生成过大的可执行文件
    - 排除了不必要的库和模块，仅包含程序运行所需的组件
    - 详细的优化说明请参阅`docs/PACKAGING.md`中的"文件大小优化"部分

4. **注意事项**：
    - Windows 打包版已内置 FFmpeg（无需用户再安装）。从源码运行时仍需按前述步骤安装 FFmpeg。
    - 详细打包说明请参阅`docs/PACKAGING.md`

### 控制说明（若未进行自定义配置，可参考如下，逻辑仅供参考，赛前改太多了懒得检查）

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
- **I键**：切换温度显示模式（默认为“糊弄模式”始终显示28.32±0.1℃；按下切换为“真实数据模式”）
- **Q键**：退出程序

## 配置文件说明

### config/config_beyond.ini（核心片段）

- [camera] 摄像头
    - username：RTSP用户名
    - password：RTSP密码
    - host：摄像头主机/IP
    - width：视频宽度
    - height：视频高度
    - buffer：帧缓冲大小（整数）
    - 说明：程序会根据 username/password/host 组合生成 RTSP URL（见 ConfigManager.get_rtsp_url）。

- [serial] 网络通信
    - host：ROV 主控的 IP（远端）
    - remote_port：远端端口（发送命令）
    - local_port：本地端口（接收数据）

- [joystick] 手柄
    - buttons, axes, long, double, tick 等基础参数

- [keyboard_bindings] 键盘快捷键
    - quit_key, xbox_debugger_key, toggle_rotation_key, toggle_undistorted_key, toggle_fullscreen_key,
      capture_frame_key, controller_visualizer_key(默认 v), controller_mapping_key(默认 m),
      deploy_thrust_curves_key(默认 c), toggle_joystick_correction_key(默认 j)

- [key_cooldowns] 按键冷却
    - 对应上述功能的冷却时间，单位秒（例如 controller_mapping_cooldown=0.5）

- [curve]
    - location：曲线 JSON 文件名（通常为 curve.json）

- 其他分节
  - [x],[y],[z],[yaw] 等轴配置；[speed_mode]、[mode_defaults]、[controller_timing]、[controller_thresholds]

### config/curve.json（或由 [curve].location 指向的文件）

- 为每个电机（m0–m5）提供曲线参数：np_mid, np_ini, pp_ini, pp_mid, nt_end, nt_mid, pt_mid, pt_end。

更多配置结构请参考源码 modules/config_manager.py 中的读取方法。

## 常见问题解决（FAQ）

1. 黑屏问题：
    - 可能原因：正在尝试接收视频流
    - 解决：等待连接；检查网络、摄像头、路由器；确认已安装 FFmpeg 并在 PATH 中

2. 控制无响应：
    - 可能原因：ROV 内部初始化延迟
    - 解决：等待或重启软件；检查网络与端口配置

3. 延迟问题：
    - 可能原因：启动时视频处理线程负载高
    - 解决：按 Xbox 键可短暂阻塞以缓解（参见“控制说明”）

4. 全屏失焦：
    - 现象：全屏模式下失焦会切换屏幕
    - 建议：比赛中避免切换窗口

5. FFmpeg 错误：
    - 原因：未安装或未加入 PATH
    - 解决：按 README 前述步骤安装并验证 ffmpeg -version

6. SDL3 库加载失败（打包后）：
    - 原因：Pygame 2.5.0+ 使用 SDL3，打包时可能缺失 DLL
    - 解决：使用仓库内 build/build_exe.py（会尝试处理SDL3），或降级 Pygame 到 2.4.0
    - 详细信息：见 docs/PACKAGING.md

## 开发与结构文档

- 模块总览与交互说明：modules/README.md
- 项目结构与路径约定：PROJECT_ORGANIZATION.md
- 工具目录说明：tools/README.md
- 打包指南：docs/PACKAGING.md

## 测试

- 一键安装依赖并运行测试（Windows 推荐）：
    - 双击 scripts\setup_and_test.bat
- 跨平台：
    - python scripts\setup_and_test.py
- 手动运行：
    - 安装依赖：pip install -r requirements.txt
    - 运行所有：python -m unittest discover
    - 运行指定：python -m unittest tests.test_controller_mapping_editor

## 制作发行包（Release）

在完成打包（生成 dist/ROV_Controller）后，可一键生成发行压缩包：

- Windows：双击 scripts\make_release.bat
- 或运行：python scripts\make_release.py

生成的发布压缩包位于 release/ROV_Controller_v{version}.zip，包含：

- ROV_Controller/ 可执行程序目录
- docs/（RELEASE_NOTES.md、PACKAGING.md）
- README_release.md（简要使用说明）
