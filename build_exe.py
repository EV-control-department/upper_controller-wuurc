"""
打包ROV控制上位机软件为可执行文件
使用PyInstaller将Python应用程序打包为独立的可执行文件
"""

import datetime
import logging
import os
import shutil
import subprocess
import sys
import time


def kill_process(process_name):
    """尝试终止指定名称的进程"""
    try:
        # 使用taskkill命令终止进程
        result = subprocess.run(['taskkill', '/F', '/IM', process_name],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)

        if result.returncode == 0:
            logging.info(f"成功终止进程: {process_name}")
        else:
            logging.warning(f"终止进程返回代码: {result.returncode}")
            if result.stderr:
                logging.warning(f"终止进程错误输出: {result.stderr}")

        return result.returncode == 0
    except Exception as e:
        logging.error(f"尝试终止进程时出错: {str(e)}")
        return False


def setup_logging():
    """设置日志系统"""
    # 创建logs目录（如果不存在）
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # 生成日志文件名，包含时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"build_log_{timestamp}.txt")

    # 配置日志系统
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )

    logging.info(f"日志文件创建于: {log_file}")
    return log_file


def get_system_encoding():
    """
    获取系统编码并返回一个安全的编码选项
    
    在中文Windows系统上，默认编码通常是GBK或GB2312，这可能导致在处理
    包含非ASCII字符的输出时出现UnicodeDecodeError。此函数检测系统编码
    并返回一个安全的替代编码（UTF-8）以确保兼容性。
    """
    import locale
    try:
        # 尝试获取系统默认编码
        system_encoding = locale.getpreferredencoding()
        logging.info(f"系统默认编码: {system_encoding}")

        # 检查是否为常见的中文编码
        if system_encoding.lower() in ['gbk', 'gb2312', 'gb18030', 'cp936']:
            logging.info("检测到中文系统编码，将使用UTF-8作为替代")
            return 'utf-8'

        # 对于其他编码，仍然使用UTF-8作为安全选择
        return 'utf-8'
    except Exception as e:
        logging.warning(f"获取系统编码时出错: {e}，将使用UTF-8")
        return 'utf-8'


def main():
    """主函数，执行打包过程"""
    # 设置日志系统
    log_file = setup_logging()

    # 获取安全的编码选项
    safe_encoding = get_system_encoding()

    logging.info("开始打包ROV控制上位机软件...")

    # 确保PyInstaller已安装
    try:
        import PyInstaller
        logging.info(f"PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        logging.info("正在安装PyInstaller...")
        try:
            # 捕获安装输出
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logging.info("PyInstaller安装完成")
            logging.debug(f"安装输出: {result.stdout}")
            if result.stderr:
                logging.warning(f"安装警告: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"安装PyInstaller失败: {e}")
            logging.error(f"错误输出: {e.stderr}")
            return

    # 创建build和dist目录（如果不存在）
    os.makedirs("build", exist_ok=True)
    os.makedirs("dist", exist_ok=True)

    # 检查并删除已存在的可执行文件
    exe_path = os.path.join("dist", "ROV_Controller.exe")
    if os.path.exists(exe_path):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logging.info(f"正在删除已存在的可执行文件: {exe_path}")
                os.remove(exe_path)
                logging.info("删除成功")
                break
            except PermissionError:
                logging.warning(f"无法删除已存在的可执行文件，可能正在被使用 (尝试 {attempt + 1}/{max_attempts})")

                # 尝试终止可能正在运行的进程
                logging.info("尝试终止可能正在运行的ROV_Controller.exe进程...")
                kill_process("ROV_Controller.exe")

                # 等待一段时间后重试
                if attempt < max_attempts - 1:
                    wait_time = 2 * (attempt + 1)  # 逐渐增加等待时间
                    logging.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logging.error("无法删除文件，请手动关闭所有ROV_Controller.exe实例后重试")
                    return
            except Exception as e:
                logging.error(f"删除文件时出错: {str(e)}")
                return

    # 定义需要包含的数据文件
    data_files = [
        ("assets", "assets"),
        ("config", "config"),
    ]

    # 检查Pygame版本并处理SDL3依赖问题
    possible_paths = []
    major, minor, patch = 0, 0, 0  # 默认版本号

    try:
        import pygame
        import site
        pygame_version = pygame.__version__
        logging.info(f"检测到Pygame版本: {pygame_version}")

        # 如果是使用SDL3的Pygame版本(2.5.0+)，添加特殊处理
        version_parts = pygame_version.split('.')
        if len(version_parts) >= 3:
            major, minor, patch = map(int, version_parts)
        elif len(version_parts) == 2:
            major, minor = map(int, version_parts)
            patch = 0

        if major >= 2 and minor >= 5:
            logging.info("检测到Pygame 2.5.0+版本，添加SDL3库处理...")

            # 可能的SDL3库路径

            # 检查site-packages目录
            for site_dir in site.getsitepackages():
                sdl_path = os.path.join(site_dir, 'pygame', '_sdl3')
                if os.path.exists(sdl_path):
                    possible_paths.append(sdl_path)
                    logging.debug(f"找到SDL3路径: {sdl_path}")

                lib_path = os.path.join(site_dir, 'Library', 'bin')
                if os.path.exists(lib_path):
                    possible_paths.append(lib_path)
                    logging.debug(f"找到可能的SDL3库路径: {lib_path}")

            # 检查Python安装目录下的库
            python_lib = os.path.join(os.path.dirname(sys.executable), 'Library', 'bin')
            if os.path.exists(python_lib):
                possible_paths.append(python_lib)
                logging.debug(f"找到Python库路径: {python_lib}")

            logging.info(f"可能的SDL3库路径: {possible_paths}")
    except Exception as e:
        logging.error(f"检查Pygame版本时出错: {str(e)}")

    # 检查Python DLL是否存在
    python_version = sys.version_info
    python_dll = f'python{python_version.major}{python_version.minor}.dll'
    python_path = os.path.dirname(sys.executable)
    python_dll_path = os.path.join(python_path, python_dll)

    if os.path.exists(python_dll_path):
        logging.info(f"找到Python DLL: {python_dll_path}")
    else:
        logging.warning(f"警告: 无法找到Python DLL: {python_dll_path}")
        logging.warning("这可能导致打包后的应用程序无法加载Python DLL")
        logging.warning("尝试在其他位置查找Python DLL...")

        # 尝试在其他可能的位置查找
        possible_dll_locations = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', python_dll),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'SysWOW64', python_dll),
            os.path.join(python_path, 'DLLs', python_dll)
        ]

        found = False
        for loc in possible_dll_locations:
            if os.path.exists(loc):
                logging.info(f"在替代位置找到Python DLL: {loc}")
                python_dll_path = loc
                found = True
                break

        if not found:
            logging.warning("无法找到Python DLL，打包可能会失败或生成的可执行文件可能无法运行")
            user_input = input("是否继续打包过程? (y/n): ")
            if user_input.lower() != 'y':
                logging.info("用户取消打包过程")
                return

    # 使用优化的spec文件进行打包
    spec_file = "ROV_Controller_optimized.spec"

    # 检查spec文件是否存在
    if not os.path.exists(spec_file):
        logging.error(f"错误: 找不到spec文件 '{spec_file}'")
        logging.error("请确保该文件存在于当前目录中")
        return

    # 手动清理build目录，避免权限问题
    build_dir = os.path.join("build", "ROV_Controller_optimized")
    if os.path.exists(build_dir):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logging.info(f"手动清理build目录: {build_dir} (尝试 {attempt + 1}/{max_attempts})")

                # 先尝试终止可能正在使用build目录中文件的进程
                build_exe_path = os.path.join(build_dir, "ROV_Controller.exe")
                if os.path.exists(build_exe_path):
                    logging.info("尝试终止可能正在运行的ROV_Controller.exe进程...")
                    kill_process("ROV_Controller.exe")

                # 使用系统命令强制删除目录
                if os.name == 'nt':  # Windows系统
                    try:
                        # 使用rd命令强制删除目录
                        subprocess.run(['rd', '/s', '/q', build_dir],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       check=False)
                        logging.info("使用系统命令删除build目录")
                    except Exception as cmd_error:
                        logging.warning(f"使用系统命令删除目录失败: {cmd_error}")

                # 如果系统命令失败，尝试使用Python的方法
                if os.path.exists(build_dir):
                    # 先尝试修改文件权限
                    for root, dirs, files in os.walk(build_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                os.chmod(file_path, 0o777)  # 赋予所有权限
                            except Exception:
                                pass

                    # 然后尝试删除
                    shutil.rmtree(build_dir, ignore_errors=True)

                # 检查是否成功删除
                if not os.path.exists(build_dir):
                    logging.info("成功清理build目录")
                    break

                # 如果目录仍然存在，等待一段时间后重试
                if attempt < max_attempts - 1:
                    wait_time = 3 * (attempt + 1)  # 逐渐增加等待时间
                    logging.info(f"build目录仍然存在，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logging.warning("无法完全清理build目录，将尝试继续打包过程")
            except Exception as e:
                logging.warning(f"清理build目录时出错: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                else:
                    logging.warning("多次尝试清理build目录失败，将尝试继续打包过程")

    # 构建PyInstaller命令，使用优化的spec文件
    cmd = [
        "pyinstaller",
        "--clean",  # 在构建前清理PyInstaller缓存
        "-y",  # 自动覆盖输出目录，不询问确认
        spec_file
    ]

    # 执行PyInstaller命令
    logging.info("正在执行PyInstaller...")

    # 最多尝试运行PyInstaller的次数
    max_pyinstaller_attempts = 2
    pyinstaller_attempt = 0
    permission_error_detected = False

    # 创建编译信息目录
    build_info_dir = "build_info"
    os.makedirs(build_info_dir, exist_ok=True)

    # 生成编译信息文件名，包含时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    build_info_file = os.path.join(build_info_dir, f"pyinstaller_output_{timestamp}.txt")

    try:
        # 使用subprocess.run捕获输出
        with open(build_info_file, 'w', encoding='utf-8') as f:
            logging.info(f"PyInstaller输出将保存到: {build_info_file}")

            # 执行命令并实时捕获输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding=safe_encoding  # 使用安全的编码选项，避免使用系统默认编码
            )

            # 实时读取并记录输出
            try:
                for line in process.stdout:
                    try:
                        # 写入文件
                        f.write(line)
                        f.flush()  # 确保立即写入文件

                        # 处理日志输出
                        line = line.strip()
                        if line:
                            # 检测权限错误
                            if "PermissionError" in line or "拒绝访问" in line or "Access is denied" in line:
                                permission_error_detected = True
                                logging.error(f"检测到权限错误: {line}")

                            if "ERROR" in line or "Error" in line or "error" in line:
                                logging.error(line)
                            elif "WARNING" in line or "Warning" in line or "warning" in line:
                                logging.warning(line)
                            else:
                                logging.debug(line)
                    except UnicodeError as ue:
                        # 处理编码错误
                        logging.warning(f"处理PyInstaller输出时遇到编码错误: {ue}")
                        # 尝试使用替代字符处理无法解码的字节
                        safe_line = line.encode('utf-8', errors='replace').decode('utf-8')
                        f.write(safe_line)
                        f.flush()
                        logging.debug(f"使用替代字符处理后的输出: {safe_line.strip()}")
            except Exception as e:
                logging.error(f"读取PyInstaller输出时出错: {e}")

            # 等待进程完成
            return_code = process.wait()

            if return_code != 0:
                logging.error(f"PyInstaller返回非零退出码: {return_code}")

                # 检查是否是权限错误
                if permission_error_detected:
                    logging.warning("检测到权限错误，尝试重新运行...")

                    # 等待一段时间
                    time.sleep(5)

                    # 再次尝试清理build目录
                    if os.path.exists(build_dir):
                        logging.info("尝试再次清理build目录...")
                        try:
                            # 使用系统命令强制删除
                            if os.name == 'nt':
                                subprocess.run(['rd', '/s', '/q', build_dir],
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               check=False)
                                time.sleep(2)  # 等待系统命令完成
                        except Exception as e:
                            logging.warning(f"使用系统命令清理build目录失败: {e}")

                        # 如果系统命令失败，尝试使用Python方法
                        if os.path.exists(build_dir):
                            try:
                                shutil.rmtree(build_dir, ignore_errors=True)
                                time.sleep(2)  # 等待删除操作完成
                            except Exception as e:
                                logging.warning(f"使用Python方法清理build目录失败: {e}")

                    # 再次尝试运行PyInstaller
                    logging.info("正在重新运行PyInstaller...")
                    try:
                        # 使用subprocess.run而不是Popen，简化重试逻辑
                        retry_result = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding=safe_encoding,
                            check=True
                        )
                        logging.info("重试成功！")
                        return  # 如果重试成功，直接返回
                    except subprocess.CalledProcessError as retry_error:
                        logging.error(f"重试失败: {retry_error}")
                        # 继续抛出原始异常

                raise subprocess.CalledProcessError(return_code, cmd)

            logging.info("打包完成！可执行文件位于 dist/ROV_Controller目录")

            # 检查输出目录中是否包含Python DLL
            output_dir = os.path.join("dist", "ROV_Controller", "_internal")
            output_dll_path = os.path.join(output_dir, python_dll)

            if os.path.exists(output_dll_path):
                logging.info(f"输出目录中已包含Python DLL: {output_dll_path}")
            else:
                logging.warning(f"输出目录中未找到Python DLL: {output_dll_path}")
                if os.path.exists(python_dll_path):
                    try:
                        logging.info(f"正在复制Python DLL到输出目录: {python_dll_path} -> {output_dll_path}")
                        shutil.copy2(python_dll_path, output_dll_path)
                        logging.info("Python DLL复制成功")
                    except Exception as copy_error:
                        logging.error(f"复制Python DLL时出错: {str(copy_error)}")
                        logging.warning("可能需要手动复制Python DLL到输出目录")

            logging.info("请确保在运行可执行文件前已安装FFmpeg并添加到系统PATH")

            # 计算打包后的文件大小
            try:
                total_size = 0
                exe_dir = os.path.join("dist", "ROV_Controller")
                if os.path.exists(exe_dir):
                    for dirpath, dirnames, filenames in os.walk(exe_dir):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            total_size += os.path.getsize(fp)

                    # 转换为MB
                    size_mb = total_size / (1024 * 1024)
                    logging.info(f"打包后的总大小: {size_mb:.2f} MB")
            except Exception as size_error:
                logging.warning(f"计算文件大小时出错: {size_error}")

    except subprocess.CalledProcessError as e:
        logging.error(f"打包过程中出错: {str(e)}")

        # 如果是SDL3相关错误，提供降级Pygame的选项
        if major >= 2 and minor >= 5:
            logging.warning("\n可能是由于SDL3库问题导致打包失败。")
            logging.warning("建议尝试降级到Pygame 2.4.0版本，该版本使用SDL2而非SDL3。")

            user_input = input("是否要降级Pygame到2.4.0版本? (y/n): ")
            if user_input.lower() == 'y':
                logging.info("正在降级Pygame...")
                try:
                    downgrade_result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "pygame==2.4.0", "--force-reinstall"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                    )
                    logging.info("Pygame已降级到2.4.0版本。请重新运行打包脚本。")
                    logging.debug(f"降级输出: {downgrade_result.stdout}")
                    if downgrade_result.stderr:
                        logging.warning(f"降级警告: {downgrade_result.stderr}")
                except Exception as downgrade_error:
                    logging.error(f"降级Pygame时出错: {str(downgrade_error)}")
            else:
                logging.info("未降级Pygame。您可以手动尝试以下解决方案:")
                logging.info("1. 手动安装Pygame 2.4.0: pip install pygame==2.4.0 --force-reinstall")
                logging.info("2. 确保SDL3库文件在系统PATH中")
                logging.info("3. 使用--debug=all选项运行PyInstaller获取更多信息")
        else:
            logging.error("请检查错误信息并解决相关问题后重试。")


def test_encoding_handling():
    """
    测试编码处理功能
    
    此函数用于测试脚本的编码处理机制是否正常工作。
    它尝试使用不同的编码解码一个包含中文和特殊字符的字符串，
    以验证错误处理机制是否能正确捕获和处理编码错误。
    """
    test_string = "测试字符串 with special chars: ©®™€£¥§¶†‡"
    encodings = ['utf-8', 'gbk', 'ascii']

    print("\n===== 编码处理测试 =====")
    for enc in encodings:
        try:
            # 先编码为bytes，然后尝试用不同编码解码
            encoded = test_string.encode('utf-8')
            decoded = encoded.decode(enc)
            print(f"使用 {enc} 编码解码成功: {decoded[:20]}...")
        except UnicodeError as e:
            print(f"使用 {enc} 编码解码失败: {e}")
            # 尝试使用替代字符
            try:
                safe_decoded = encoded.decode(enc, errors='replace')
                print(f"使用替代字符后: {safe_decoded[:20]}...")
            except Exception as e2:
                print(f"即使使用替代字符也失败: {e2}")

    # 测试系统编码检测
    safe_encoding = get_system_encoding()
    print(f"\n系统编码检测结果: {safe_encoding}")
    print("===== 测试完成 =====\n")


if __name__ == "__main__":
    # 如果使用--test参数运行，则执行测试
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_encoding_handling()
    else:
        main()
