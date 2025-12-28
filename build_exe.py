#!/usr/bin/env python
# -*- coding: utf-8 -*-
# build_exe.py
"""
智能板书监控系统 - 编译脚本
一键将Python代码编译为Windows可执行文件
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

def get_base_dir():
    """获取脚本所在的基础目录"""
    # 如果被打包成exe，使用sys.executable的路径
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # 否则使用脚本文件所在目录
    return os.path.dirname(os.path.abspath(__file__))

def check_environment():
    """检查编译环境"""
    print("=" * 60)
    print("智能板书监控系统 - 编译工具")
    print("=" * 60)
    
    # 获取基础目录
    base_dir = get_base_dir()
    print(f"基础目录: {base_dir}")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌❌ Python版本需要3.7或更高")
        return False
    
    print(f"✓ Python版本: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # 检查必需工具
    required_tools = ['pip', 'pyinstaller']
    for tool in required_tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"✓ {tool} 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌❌ {tool} 未安装或不在PATH中")
            return False
    
    return True

def install_dependencies():
    """安装依赖包 - 使用国内镜像源"""
    print("\n" + "=" * 60)
    print("安装依赖包...")
    print("=" * 60)
    
    base_dir = get_base_dir()
    requirements_file = os.path.join(base_dir, "requirements.txt")
    
    print(f"查找requirements.txt: {requirements_file}")
    
    if not os.path.exists(requirements_file):
        print(f"❌❌ 找不到requirements.txt文件，尝试在以下位置查找:")
        print(f"  1. {requirements_file}")
        print(f"  2. {os.path.join(os.getcwd(), 'requirements.txt')}")
        print(f"  3. 项目根目录")
        
        # 尝试在当前工作目录查找
        cwd_requirements = os.path.join(os.getcwd(), "requirements.txt")
        if os.path.exists(cwd_requirements):
            print(f"✓ 在当前工作目录找到requirements.txt")
            requirements_file = cwd_requirements
        else:
            # 尝试在父目录查找（如果脚本在子目录中）
            parent_dir = os.path.dirname(base_dir)
            parent_requirements = os.path.join(parent_dir, "requirements.txt")
            if os.path.exists(parent_requirements):
                print(f"✓ 在父目录找到requirements.txt")
                requirements_file = parent_requirements
            else:
                print("❌❌ 未找到requirements.txt文件，使用默认依赖列表")
                return install_default_dependencies()
    
    print(f"✓ 使用依赖文件: {requirements_file}")
    
    # 国内镜像源列表
    mirrors = [
        "https://pypi.tuna.tsinghua.edu.cn/simple/",
        "https://mirrors.aliyun.com/pypi/simple/",
        "https://pypi.douban.com/simple/",
        "https://pypi.mirrors.ustc.edu.cn/simple/"
    ]
    
    success = False
    last_error = None
    
    for mirror in mirrors:
        try:
            print(f"正在尝试从 {mirror} 安装依赖...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file, 
                 "-i", mirror, "--trusted-host", mirror.split("//")[1].split("/")[0]],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print("✓ 依赖安装成功")
                success = True
                break
            else:
                last_error = result.stderr
                print(f"❌ 从 {mirror} 安装失败，尝试下一个镜像...")
                
        except subprocess.TimeoutExpired:
            print(f"❌ 从 {mirror} 安装超时，尝试下一个镜像...")
            last_error = "安装超时"
        except Exception as e:
            print(f"❌ 从 {mirror} 安装出错: {e}，尝试下一个镜像...")
            last_error = str(e)
    
    if not success:
        # 如果所有镜像都失败，尝试使用默认源
        print("所有镜像都失败，尝试使用默认源...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("✓ 依赖安装成功")
                success = True
            else:
                last_error = result.stderr
        except Exception as e:
            last_error = str(e)
    
    if not success:
        print("❌❌ 所有安装尝试都失败:")
        print(last_error)
        return False
    
    return True

def install_default_dependencies():
    """安装默认依赖包"""
    print("\n使用默认依赖列表安装...")
    
    default_dependencies = [
        'PyQt5>=5.15.0',
        'pywin32>=300',
        'psutil>=5.8.0',
        'Pillow>=8.3.0'
    ]
    
    mirrors = [
        "https://pypi.tuna.tsinghua.edu.cn/simple/",
        "https://mirrors.aliyun.com/pypi/simple/",
        "https://pypi.douban.com/simple/"
    ]
    
    for mirror in mirrors:
        try:
            print(f"尝试从 {mirror} 安装默认依赖...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + default_dependencies + 
                ["-i", mirror, "--trusted-host", mirror.split("//")[1].split("/")[0]],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("✓ 默认依赖安装成功")
                return True
            else:
                print(f"❌ 从 {mirror} 安装失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 安装出错: {e}")
    
    # 尝试使用默认源
    try:
        print("尝试使用默认源安装...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + default_dependencies,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✓ 默认依赖安装成功")
            return True
        else:
            print(f"❌ 默认源安装失败: {result.stderr}")
    except Exception as e:
        print(f"❌ 安装出错: {e}")
    
    return False

def install_missing_packages():
    """检查并安装缺失的必需包"""
    print("\n" + "=" * 60)
    print("检查必需包...")
    print("=" * 60)
    
    required_packages = {
        'PyQt5': 'pyqt5',
        'pywin32': 'pywin32',
        'psutil': 'psutil',
        'PIL': 'pillow'
    }
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            if package == 'PIL':
                __import__('PIL')
            else:
                __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print(f"\n正在安装缺失的包: {', '.join(missing_packages)}")
        
        # 使用国内镜像源
        mirrors = [
            "https://pypi.tuna.tsinghua.edu.cn/simple/",
            "https://mirrors.aliyun.com/pypi/simple/",
            "https://pypi.douban.com/simple/"
        ]
        
        success = False
        for mirror in mirrors:
            try:
                print(f"尝试从 {mirror} 安装...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + missing_packages + 
                    ["-i", mirror, "--trusted-host", mirror.split("//")[1].split("/")[0]],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    print("✓ 缺失包安装成功")
                    success = True
                    break
                else:
                    print(f"❌ 从 {mirror} 安装失败: {result.stderr}")
            except Exception as e:
                print(f"❌ 安装出错: {e}")
        
        if not success:
            print("❌ 尝试使用默认源安装...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + missing_packages,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    print("✓ 缺失包安装成功")
                    success = True
                else:
                    print(f"❌ 默认源安装失败: {result.stderr}")
            except Exception as e:
                print(f"❌ 安装出错: {e}")
        
        if not success:
            print("❌❌ 无法安装缺失的包，请手动安装")
            return False
    
    return True

def create_icon():
    """创建程序图标（如果不存在）"""
    base_dir = get_base_dir()
    icon_file = os.path.join(base_dir, "icon.ico")
    
    if not os.path.exists(icon_file):
        print("\n创建默认图标...")
        try:
            # 创建一个简单的图标文件（实际项目中应该提供真正的图标）
            from PIL import Image, ImageDraw
            
            # 创建32x32图标
            img = Image.new('RGBA', (32, 32), (24, 144, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle([8, 8, 24, 24], fill=(255, 255, 255, 255))
            
            # 保存为ICO格式
            img.save(icon_file, format='ICO', sizes=[(32, 32)])
            print(f"✓ 已创建默认图标: {icon_file}")
        except ImportError:
            print("⚠  无法创建图标（PIL未安装），使用默认图标")
            # 如果没有PIL，创建一个空的ICO文件占位
            with open(icon_file, 'wb') as f:
                f.write(b'')  # 空文件，编译时会忽略
    else:
        print(f"✓ 使用现有图标: {icon_file}")
    
    return icon_file

def create_config_files():
    """创建必要的配置文件"""
    base_dir = get_base_dir()
    
    # 创建config.ini如果不存在
    config_file = os.path.join(base_dir, "config.ini")
    if not os.path.exists(config_file):
        print("\n创建默认配置文件...")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write("[Settings]\n")
                f.write("save_path=screenshots\n")
                f.write("capture_interval=60\n")
                f.write("buffer_size=100\n")
                f.write("foreground_detection=true\n")
                f.write("ink_detection=true\n")
                f.write("auto_start=false\n")
                f.write("silent_start=false\n")
                f.write("minimize_to_tray=true\n")
            print(f"✓ 已创建配置文件: {config_file}")
        except Exception as e:
            print(f"⚠  创建配置文件失败: {e}")
    else:
        print(f"✓ 配置文件已存在: {config_file}")
    
    # 创建screenshots目录
    screenshots_dir = os.path.join(base_dir, "screenshots")
    if not os.path.exists(screenshots_dir):
        print("\n创建截图目录...")
        try:
            os.makedirs(screenshots_dir, exist_ok=True)
            print(f"✓ 已创建截图目录: {screenshots_dir}")
        except Exception as e:
            print(f"⚠  创建截图目录失败: {e}")
    else:
        print(f"✓ 截图目录已存在: {screenshots_dir}")
    
    return config_file, screenshots_dir

def compile_exe():
    """编译可执行文件"""
    print("\n" + "=" * 60)
    print("开始编译可执行文件...")
    print("=" * 60)
    
    base_dir = get_base_dir()
    
    # 清理之前的编译结果
    build_dirs = ['build', 'dist']
    for dir_name in build_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"✓ 清理目录: {dir_path}")
    
    # 编译命令参数
    main_script = os.path.join(base_dir, "main.py")
    app_name = "SmartBoardMonitor"
    icon_file = create_icon()
    config_file, screenshots_dir = create_config_files()
    
    # 检查主脚本是否存在
    if not os.path.exists(main_script):
        print(f"❌❌ 找不到主脚本文件: {main_script}")
        print("请确保main.py文件存在")
        return False
    
    print(f"✓ 主脚本文件: {main_script}")
    
    # 切换到基础目录
    original_cwd = os.getcwd()
    os.chdir(base_dir)
    
    try:
        pyinstaller_cmd = [
            'pyinstaller',
            '--onefile',
            '--windowed',
            '--name', app_name,
            '--add-data', 'icon.ico;.',
            '--add-data', 'config.ini;.',
            '--add-data', 'screenshots;screenshots',
            '--hidden-import', 'PyQt5.sip',
            '--hidden-import', 'PyQt5.QtCore',
            '--hidden-import', 'PyQt5.QtGui',
            '--hidden-import', 'PyQt5.QtWidgets',
            '--clean',
            '--noconfirm'
        ]
        
        if os.path.exists(icon_file):
            pyinstaller_cmd.extend(['--icon', icon_file])
        
        pyinstaller_cmd.append('main.py')
        
        print("执行编译命令...")
        print(f"命令: {' '.join(pyinstaller_cmd)}")
        
        result = subprocess.run(
            pyinstaller_cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode == 0:
            print("✓ 编译成功")
            
            # 复制生成的可执行文件到项目根目录
            exe_path = os.path.join('dist', f'{app_name}.exe')
            if os.path.exists(exe_path):
                target_path = os.path.join(base_dir, f'{app_name}.exe')
                shutil.copy(exe_path, target_path)
                print(f"✓ 已复制可执行文件到: {target_path}")
                
                # 显示文件大小
                file_size = os.path.getsize(target_path) / (1024 * 1024)
                print(f"✓ 生成文件大小: {file_size:.2f} MB")
            
            return True
        else:
            print("❌❌ 编译失败:")
            print("标准输出:")
            print(result.stdout)
            print("错误输出:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌❌ 编译超时")
        return False
    except Exception as e:
        print(f"❌❌ 编译出错: {e}")
        return False
    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)

def main():
    """主函数"""
    # 检查环境
    if not check_environment():
        return
    
    # 安装依赖
    if not install_dependencies():
        print("\n尝试继续编译，但依赖可能不完整...")
        # 继续尝试，但警告用户
    
    # 检查并安装缺失包
    if not install_missing_packages():
        print("\n警告：部分依赖包可能未正确安装")
    
    # 编译可执行文件
    if not compile_exe():
        return
    
    print("\n" + "=" * 60)
    print("✓✓✓ 编译完成 ✓✓✓")
    print("=" * 60)
    print("\n使用说明:")
    print("1. 生成的 SmartBoardMonitor.exe 可以直接运行")
    print("2. 首次运行会自动创建配置文件")
    print("3. 截图会保存在 screenshots 目录中")
    print("4. 可以在系统托盘中找到程序图标")

if __name__ == "__main__":
    main()
