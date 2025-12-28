# -*- coding: utf-8 -*-
# screenshot.py
"""
截图管理模块 - 管理截图功能
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QScreen
from PyQt5.QtCore import QBuffer, QIODevice
import win32gui
import win32process
import psutil

class ScreenshotManager:
    """管理截图功能"""
    
    def __init__(self):
        self.screens = QApplication.screens()
    
    def capture_screen(self):
        """截取整个屏幕"""
        try:
            screen = self.screens[0]  # 主屏幕
            pixmap = screen.grabWindow(0)
            return pixmap
        except Exception as e:
            print(f"截图失败: {e}")
            return None
    
    def capture_foreground_window(self, process_names=None):
        """截取前台窗口"""
        try:
            # 获取前台窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            
            # 如果指定了进程名，检查是否匹配
            if process_names:
                if not self._is_target_process(hwnd, process_names):
                    return None
            
            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            x, y, width, height = rect
            
            # 截取窗口
            screen = self.screens[0]
            pixmap = screen.grabWindow(0, x, y, width, height)
            return pixmap
            
        except Exception as e:
            print(f"窗口截图失败: {e}")
            return None
    
    def _is_target_process(self, hwnd, process_names):
        """检查窗口是否属于目标进程"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name().lower()
            
            for target_name in process_names:
                # 清理进程名，确保有.exe后缀
                target_name = target_name.strip().lower()
                if not target_name.endswith('.exe'):
                    target_name = f"{target_name}.exe"
                
                if target_name in process_name:
                    return True
            return False
        except Exception as e:
            print(f"检查进程失败: {e}")
            return False
    
    def save_to_memory(self, pixmap):
        """将截图保存到内存"""
        try:
            buffer = QBuffer()
            buffer.open(QIODevice.ReadWrite)
            pixmap.save(buffer, "PNG")
            return buffer.data()
        except Exception as e:
            print(f"保存到内存失败: {e}")
            return None
    
    def save_to_file(self, pixmap, filepath):
        """将截图保存到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now()
            filename = timestamp.strftime("%Y-%m-%d-%H-%M-%S.png")
            full_path = os.path.join(filepath, filename)
            
            pixmap.save(full_path, "PNG")
            return True
        except Exception as e:
            print(f"保存到文件失败: {e}")
            return False
    
    def get_timestamp(self):
        """获取当前时间戳"""
        return datetime.now()
    
    def get_date_folder_name(self):
        """获取带星期的日期文件夹名称"""
        now = datetime.now()
        # 星期映射
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[now.weekday()]
        
        # 格式: 2023-10-01_周日
        return f"{now.strftime('%Y-%m-%d')}_{weekday}"
