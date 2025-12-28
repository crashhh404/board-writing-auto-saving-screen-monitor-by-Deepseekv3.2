# -*- coding: utf-8 -*-
# __init__.py
"""
智能板书监控系统模块包
"""

__version__ = "1.0.0"
__author__ = "SmartBoardMonitor Team"

from .gui import SmartBoardGUI
from .detector import InputDetector, WindowsInkDetector
from .screenshot import ScreenshotManager
from .buffer import BufferManager
from .config import ConfigManager
from .tray import SystemTrayManager
from .logger import LogManager

__all__ = [
    'SmartBoardGUI',
    'InputDetector',
    'WindowsInkDetector',
    'ScreenshotManager',
    'BufferManager',
    'ConfigManager',
    'SystemTrayManager',
    'LogManager'
]
