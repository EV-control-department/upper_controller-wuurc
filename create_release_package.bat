@echo off
echo 正在创建ROV控制系统 V2.0.0 发布包...

REM 设置变量
set RELEASE_NAME=ROV_Controller_V2.0.0
set RELEASE_DIR=release
set DIST_DIR=dist\ROV_Controller
set DOCS_DIR=docs

REM 创建发布目录
if exist %RELEASE_DIR% (
    echo 清理旧的发布目录...
    rd /s /q %RELEASE_DIR%
)
mkdir %RELEASE_DIR%
mkdir %RELEASE_DIR%\docs

REM 复制可执行文件和依赖
echo 复制可执行文件和依赖...
xcopy /E /I /Y %DIST_DIR% %RELEASE_DIR%\ROV_Controller

REM 复制文档
echo 复制文档...
copy %DOCS_DIR%\RELEASE_NOTES.md %RELEASE_DIR%\docs\
copy %DOCS_DIR%\CHANGES.md %RELEASE_DIR%\docs\
copy %DOCS_DIR%\PACKAGING.md %RELEASE_DIR%\docs\
copy %DOCS_DIR%\KEYBOARD_BINDINGS.md %RELEASE_DIR%\docs\
copy %DOCS_DIR%\CONTROLLER_TOOLS.md %RELEASE_DIR%\docs\
copy %DOCS_DIR%\CHINESE_FONT_FIX.md %RELEASE_DIR%\docs\
copy README.md %RELEASE_DIR%\

REM 复制版本文件
echo 复制版本文件...
copy version.txt %RELEASE_DIR%\

REM 创建ZIP文件
echo 创建ZIP文件...
powershell -command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%RELEASE_NAME%.zip' -Force"

echo 发布包创建完成: %RELEASE_NAME%.zip
echo.
echo 发布包内容:
echo - ROV_Controller 可执行文件和依赖
echo - 文档 (README.md, RELEASE_NOTES.md, 等)
echo - 版本信息 (version.txt)

pause