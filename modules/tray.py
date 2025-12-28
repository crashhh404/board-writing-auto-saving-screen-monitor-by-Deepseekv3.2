# -*- coding: utf-8 -*-
# tray.py
"""
系统托盘管理模块
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                             QAction, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, pyqtSignal

class SystemTrayManager(QSystemTrayIcon):
    show_window_signal = pyqtSignal()
    hide_window_signal = pyqtSignal()
    quit_app_signal = pyqtSignal()
    
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.parent = parent
        self.app = app
        self.window_visible = True
        
        # 创建托盘图标
        self.create_icon()
        
        # 创建右键菜单
        self.create_menu()
        
        # 连接信号
        self.activated.connect(self.on_tray_activated)
    
    def create_icon(self):
        """创建托盘图标"""
        # 创建一个简单的程序图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QApplication.palette().window().color())
        
        # 添加一个简单的标识
        from PyQt5.QtGui import QPainter, QColor
        painter = QPainter(pixmap)
        painter.setBrush(QColor(24, 144, 255))  # 蓝色
        painter.drawRect(8, 8, 16, 16)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip("智能板书监控")
    
    def create_menu(self):
        """创建托盘菜单"""
        self.menu = QMenu()
        
        # 显示/隐藏窗口
        self.show_hide_action = QAction("隐藏窗口", self)
        self.show_hide_action.triggered.connect(self.toggle_window_visibility)
        self.menu.addAction(self.show_hide_action)
        
        self.menu.addSeparator()
        
        # 开始监控
        self.start_action = QAction("开始监控", self)
        self.start_action.triggered.connect(self.start_monitoring)
        self.menu.addAction(self.start_action)
        
        # 停止监控
        self.stop_action = QAction("停止监控", self)
        self.stop_action.triggered.connect(self.stop_monitoring)
        self.stop_action.setEnabled(False)
        self.menu.addAction(self.stop_action)
        
        self.menu.addSeparator()
        
        # 退出（不再显示确认窗口）
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_application_no_confirm)
        self.menu.addAction(exit_action)
        
        self.setContextMenu(self.menu)
    
    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_window_visibility()
    
    def toggle_window_visibility(self):
        """切换窗口显示/隐藏"""
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def show_window(self):
        """显示主窗口"""
        self.show_window_signal.emit()
        self.window_visible = True
        self.show_hide_action.setText("隐藏窗口")
        self.setToolTip("智能板书监控 - 窗口已显示")
    
    def hide_window(self):
        """隐藏主窗口"""
        self.hide_window_signal.emit()
        self.window_visible = False
        self.show_hide_action.setText("显示窗口")
        self.setToolTip("智能板书监控 - 窗口已隐藏")
    
    def start_monitoring(self):
        """开始监控"""
        if self.parent:
            self.parent.start_monitor_signal.emit()
            self.update_monitoring_status(True)
    
    def stop_monitoring(self):
        """停止监控"""
        if self.parent:
            self.parent.stop_monitor_signal.emit()
            self.update_monitoring_status(False)
    
    def update_monitoring_status(self, is_monitoring):
        """更新监控状态"""
        self.start_action.setEnabled(not is_monitoring)
        self.stop_action.setEnabled(is_monitoring)
        
        if is_monitoring:
            self.setToolTip("智能板书监控 - 运行中")
        else:
            self.setToolTip("智能板书监控 - 已停止")
    
    def quit_application(self):
        """退出应用程序（保留这个方法，但不再使用）"""
        # 这个方法保留，但不再从菜单调用
        self.quit_app_signal.emit()
    
    def quit_application_no_confirm(self):
        """退出应用程序（不显示确认窗口）"""
        # 直接发送退出信号，不显示确认窗口
        self.quit_app_signal.emit()
    
    def show_message(self, title, message, timeout=3000):
        """显示托盘消息"""
        self.showMessage(title, message, QSystemTrayIcon.Information, timeout)
