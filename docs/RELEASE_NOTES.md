# ROV 控制系统 V2.1.0 发布说明

## 发布日期

2025年8月22日

## 版本信息

- **版本号**: 2.1.0
- **构建日期**: 2025-08-22

## 本次更新亮点

1. 打包与体积优化
    - 使用优化的 spec 与目录模式（onedir）
    - Windows 发行版内置 FFmpeg（dist/ROV_Controller/_internal/ffmpeg.exe），无需再额外安装 FFmpeg
    - 构建日志与 PyInstaller 输出分别保存于 logs/ 与 build_info/

2. 运行时兼容性改进
    - 视频模块自动优先使用内置 ffmpeg.exe（冻结环境下），开发环境继续从 PATH 查找
    - 针对 Pygame 2.5+ 的 SDL3 依赖增加处理与降级选项提示（可降级到 2.4.0 使用 SDL2）

3. 目录与工具整理
    - 统一工具路径至 tools/ 子目录（config_editors、visualizers、utilities）
    - UI 内快捷键启动路径修复：
        - 控制器可视化 → tools/visualizers/controller_visualizer.py
        - 控制器映射编辑器 → tools/config_editors/controller_mapping_editor.py
        - Xbox 调试器 → tools/utilities/xbox_debugger.py

4. 文档与脚本
    - 更新 README、PROJECT_ORGANIZATION.md、modules/README.md
    - 新增 docs/PACKAGING.md 与 docs/AUDIT_REPORT.md
    - 新增一键依赖安装与测试脚本：scripts/setup_and_test.(py|bat)

## 使用与安装说明（Windows 发行包）

1. 解压发布包到任意目录
2. 双击 dist/ROV_Controller/ROV_Controller.exe 运行
3. 无需单独安装 FFmpeg（已内置）。若从源码运行，请自行安装 FFmpeg 并确保在 PATH 中

## 已知问题

1. SDL3 库加载失败（仅在某些环境/打包方式下）
    - 方案 A：使用本仓库 build/build_exe.py 打包（内含处理）
    - 方案 B：降级 Pygame 到 2.4.0（SDL2）
    - 详见 docs/PACKAGING.md

## 相关文档

- 打包与问题排查：docs/PACKAGING.md
- 项目结构与路径：PROJECT_ORGANIZATION.md
- 本次审计摘要：docs/AUDIT_REPORT.md
