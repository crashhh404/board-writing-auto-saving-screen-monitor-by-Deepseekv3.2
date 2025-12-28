# -*- coding: utf-8 -*-
# config.py
"""
配置管理模块 - 管理应用程序配置
"""

import os
import json
import sys
from pathlib import Path
from PyQt5.QtCore import QSettings

class ConfigManager:
    def __init__(self, config_file="config.ini"):
        # 获取程序的真实路径，解决开机自启时的路径问题
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe，使用exe所在目录
            base_dir = os.path.dirname(sys.executable)
        else:
            # 如果是源码运行，使用当前文件所在目录
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 确保配置文件路径是绝对路径
        if not os.path.isabs(config_file):
            config_file = os.path.join(base_dir, config_file)
        
        self.config_file = config_file
        self.base_dir = base_dir  # 保存基础目录
        self.settings = QSettings(config_file, QSettings.IniFormat)
        
        self.default_config = {
            'auto_start': False,
            'silent_start': False,
            'minimize_to_tray': True,
            'buffer_size': 100,           # 确保是整数
            'capture_interval': 60,        # 默认改为60秒
            'save_times': ['09:00', '12:00', '15:00', '18:00'],
            'foreground_detection': True,
            'ink_detection': True,
            'process_names': '',
            'save_path': 'screenshots'
        }
    
    def get_absolute_path(self, path):
        """将相对路径转换为绝对路径"""
        if not path:
            return path
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(path):
            return path
        
        # 相对于程序目录的路径
        return os.path.join(self.base_dir, path)
    
    def load_config(self):
        """加载配置文件 - 确保类型转换正确"""
        config = {}
        for key, default_value in self.default_config.items():
            try:
                if isinstance(default_value, bool):
                    value = self.settings.value(key, default_value)
                    # 处理字符串形式的布尔值
                    if isinstance(value, str):
                        config[key] = value.lower() in ('true', '1', 'yes')
                    else:
                        config[key] = bool(value) if value is not None else default_value
                
                elif isinstance(default_value, int):
                    value = self.settings.value(key, default_value)
                    # 确保转换为整数
                    if value is not None:
                        try:
                            config[key] = int(float(value))  # 先转float再转int，处理"5.0"这种情况
                        except (ValueError, TypeError):
                            config[key] = default_value
                    else:
                        config[key] = default_value
                
                elif isinstance(default_value, float):
                    value = self.settings.value(key, default_value)
                    if value is not None:
                        try:
                            config[key] = float(value)
                        except (ValueError, TypeError):
                            config[key] = default_value
                    else:
                        config[key] = default_value
                
                elif isinstance(default_value, list):
                    # 处理时间列表
                    value = self.settings.value(key, '')
                    if value and isinstance(value, str):
                        config[key] = value.split(',')
                    else:
                        config[key] = default_value
                
                else:
                    value = self.settings.value(key, default_value)
                    config[key] = str(value) if value is not None else default_value
                    
            except Exception as e:
                print(f"加载配置项 {key} 时出错: {e}")
                config[key] = default_value
        
        # 特殊处理：将保存路径转换为绝对路径
        if 'save_path' in config:
            config['save_path'] = self.get_absolute_path(config['save_path'])
        
        return config
    
    def save_config(self, config):
        """保存配置文件 - 确保类型正确"""
        # 创建配置副本，避免修改原始配置
        save_config = config.copy()
        
        # 将绝对路径转换为相对路径保存（如果是相对于程序目录的路径）
        if 'save_path' in save_config and os.path.isabs(save_config['save_path']):
            try:
                # 尝试转换为相对路径
                relative_path = os.path.relpath(save_config['save_path'], self.base_dir)
                # 如果相对路径不以..开头（表示在程序目录内或子目录下）
                if not relative_path.startswith('..'):
                    save_config['save_path'] = relative_path
            except:
                # 转换失败，保持绝对路径
                pass
        
        for key, value in save_config.items():
            try:
                if isinstance(value, list):
                    # 将列表转换为逗号分隔的字符串
                    self.settings.setValue(key, ','.join(value))
                else:
                    self.settings.setValue(key, value)
            except Exception as e:
                print(f"保存配置项 {key} 时出错: {e}")
        
        # 立即同步到磁盘
        self.settings.sync()
        print("配置文件已保存并同步到磁盘")
    
    def set_auto_start(self, enable=True, silent=False):
        """设置开机自启动"""
        if os.name == 'nt':  # Windows
            self._set_windows_auto_start(enable, silent)
    
    def _set_windows_auto_start(self, enable, silent):
        """Windows系统开机自启动设置"""
        try:
            import winreg
            import sys
            
            # 获取当前脚本路径
            if getattr(sys, 'frozen', False):
                # 打包后的exe文件路径
                app_path = sys.executable
            else:
                # 开发环境下的脚本路径
                app_path = os.path.abspath(sys.argv[0])
            
            # 启动参数
            startup_args = ""
            if silent:
                startup_args = " --silent"
            
            # 确保工作目录正确（非常重要！）
            work_dir = os.path.dirname(app_path)
            
            # 注册表路径
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "SmartBoardMonitor"
            
            if enable:
                # 创建注册表项，包含工作目录
                command_line = f'"{app_path}"{startup_args}'
                
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command_line)
                winreg.CloseKey(key)
                print(f"开机自启动已启用，工作目录: {work_dir}")
            else:
                # 删除注册表项
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, app_name)
                    winreg.CloseKey(key)
                    print("开机自启动已禁用")
                except FileNotFoundError:
                    pass
                    
        except Exception as e:
            print(f"设置开机自启动失败: {e}")