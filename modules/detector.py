# -*- coding: utf-8 -*-
# detector.py
"""
输入检测模块 - 检测键盘、鼠标和Windows Ink活动
"""

import time
import ctypes
from ctypes import wintypes
from PyQt5.QtCore import QObject, pyqtSignal

class InputDetector(QObject):
    """检测用户输入活动（键盘、鼠标）"""
    
    activity_detected = pyqtSignal()  # 输入活动信号
    
    def __init__(self):
        super().__init__()
        self.last_input_time = time.time()
        self.is_detecting = False
        
        # Windows API 结构体
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', ctypes.c_uint),
                ('dwTime', ctypes.c_uint)
            ]
        
        self.last_input_info = LASTINPUTINFO()
        self.last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        
    def get_idle_time(self):
        """获取系统空闲时间（秒）"""
        try:
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(self.last_input_info))
            current_time = ctypes.windll.kernel32.GetTickCount()
            idle_time = (current_time - self.last_input_info.dwTime) / 1000.0
            return idle_time
        except Exception as e:
            print(f"获取空闲时间失败: {e}")
            return 0.0
    
    def start_detection(self):
        """开始检测输入活动"""
        self.is_detecting = True
        self.last_input_time = time.time()
    
    def stop_detection(self):
        """停止检测输入活动"""
        self.is_detecting = False
    
    def check_activity(self):
        """检查是否有输入活动"""
        idle_time = self.get_idle_time()
        
        # 如果空闲时间很短（小于2秒），认为有活动
        if idle_time < 2.0:
            current_time = time.time()
            if current_time - self.last_input_time > 1.0:  # 每秒最多发射一次信号
                self.activity_detected.emit()
                self.last_input_time = current_time
                return True
        return False


class WindowsInkDetector:
    """检测 Windows Ink 活动"""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.is_detecting = False
        
    def setup_ink_detection(self):
        """设置 Ink 检测"""
        self.is_detecting = True
    
    def check_ink_activity(self):
        """检查 Ink 活动"""
        try:
            return self._check_tablet_input()
        except Exception as e:
            print(f"Ink检测失败: {e}")
            return False
    
    def _check_tablet_input(self):
        """检测平板输入"""
        # 简化的实现，实际可能需要使用 Windows Ink API
        # 这里返回 False 作为占位符
        return False