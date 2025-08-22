# 模块说明（modules/）

本文件介绍上位机的核心模块、主要类/函数与交互关系，便于二次开发与排障。

## 总览与数据流

输入（Xbox/键盘） → JoystickHandler / UIController → JoystickController 生成控制量
→ ControllerMonitor 汇总控制/状态 → HardwareController 打包并通过 UDP 发送
→ ROV 返回传感器数据（深度/温度等）→ HardwareController → ControllerMonitor
→ UIController 显示视频与状态；VideoThread 负责 RTSP 视频帧获取。

主要线程：

- VideoThread（独立线程）：拉取与解码视频帧
- NetworkWorker（独立线程）：周期性/被触发的网络通信与心跳
- 主线程：UI 渲染、输入处理与协调

## config_manager.py — 配置管理

- 类：ConfigManager
    - 读取 INI（默认 config/config_beyond.ini，UTF-8）
    - 加载曲线 JSON：由 INI 的 [curve].location 指定，相对项目根
    - 提供统一的读取接口：
        - get_rtsp_url()：根据 camera.username/password/host 组装
        - get_camera_dimensions()：返回 (width, height)
        - get_server_address()：从 [serial] 读取 (host, remote_port)
        - get_local_port()：读取 [serial].local_port
        - get_interface_settings(), get_joystick_settings()
        - get_axis_config(axis_name)、get_speed_modes()、get_lock_modes() 等
        - get_catch_modes()：从 config/modes/*.ini 加载，带默认回退
        - get_keyboard_bindings(), get_key_cooldowns()

注意：部分旧式 has_option 调用已替换为 'key' in section 以兼容不同解析器实现。

## hardware_controller.py — 硬件/网络

- 类：HardwareController
    - 负责 UDP 套接字、控制指令/推力曲线数据打包与发送
    - 提供 hwinit()、setup_socket(local_port)、deploy thrust 等方法（视实现）
- 类：ControllerMonitor
    - 维护当前控制量（x/y/z/yaw、servo 等）与传感器数据（depth/temperature）
    - 提供 update_sensor_data() 以处理来自 ROV 的 JSON 数据
- 类：NetworkWorker（线程）
    - 负责心跳/命令发送与接收循环，可通过触发机制即时发送
- 函数：controller_curve(x)
    - 控制曲线映射函数，供 Z 轴等通道处理时使用

## video_processor.py — 视频线程

- 类：VideoThread（线程）
    - 使用 FFmpeg/OpenCV 拉取 RTSP 视频帧
    - get_latest_frame(undistorted: bool) 返回最新帧（RGB），支持无畸变显示模式

## ui_controller.py — UI 与输入

- 类：UIController
    - 窗口/字体初始化、文本与帧渲染、全屏/旋转/无畸变切换
    - 键盘快捷键与冷却：从 ConfigManager 注入并在非阻塞轮询中处理
    - 温度显示模式：默认“always”（糊弄模式），可用 I 键切换为“real”（真实数据）
    - 静态工具启动：
        - open_xbox_debugger() → tools/utilities/xbox_debugger.py
        - open_controller_visualizer() → tools/visualizers/controller_visualizer.py
        - open_controller_mapping_editor() → tools/config_editors/controller_mapping_editor.py
- 类：JoystickHandler
    - 负责 pygame.joystick 初始化与按钮状态机维护（短按/长按/双击等）

## joystick_controller.py — 手柄逻辑

- 类：JoystickController
    - 读取 JoystickHandler 状态，结合配置（轴、死区、模式等）生成控制量
    - 与 ControllerMonitor 协作，更新 x/y/z/yaw/servo 等输出
    - 辅助功能：手柄辅助修正（toggle_joystick_correction_key）

## depth_temperature_controller.py — 深度/温度记录

- 典型实现为独立线程或定时器任务：采集并保存 depth/temperature
- 与 ControllerMonitor 交互读取最新传感器数据

## 与 main.py 的关系

- main.py 负责：
    - 实例化 ConfigManager
    - 构造 UIController / JoystickHandler / ControllerMonitor
    - 初始化 HardwareController 并建立 socket
    - 启动 NetworkWorker 与 VideoThread
    - 构造 JoystickController 并在主循环中调用 process/input、刷新 UI

## 开发建议

- 修改配置优先通过 INI/JSON；新增功能时为新键添加合理默认值与出错回退
- 工具脚本放入 tools/ 下对应子目录；UI 内部快捷键已指向正确路径
- 交互密集或硬件/网络依赖强的脚本不要放入 tests/；单元测试使用 unittest 风格

## 参考

- 项目结构与约定：PROJECT_ORGANIZATION.md
- 打包：docs/PACKAGING.md
- 工具说明：tools/README.md
