#!/usr/bin/env python
# -*- coding: utf-8 -*-
# main.py
"""
智能板书自动保存系统 - 主程序
自动检测用户活动并截图保存，适用于教学、会议等场景
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex
from PyQt5.QtGui import QFont

# 导入自定义模块
from modules.gui import SmartBoardGUI
from modules.detector import InputDetector, WindowsInkDetector
from modules.screenshot import ScreenshotManager
from modules.buffer import BufferManager
from modules.config import ConfigManager
from modules.tray import SystemTrayManager
from modules.logger import LogManager

class MonitorThread(QThread):
    """监控线程，负责定时截图"""
    
    capture_signal = pyqtSignal(object)  # 截图数据信号
    status_signal = pyqtSignal(str, str)  # 状态更新信号（类型，消息）
    log_signal = pyqtSignal(str, str)  # 日志信号（级别，消息）
    
    def __init__(self):
        super().__init__()
        self.interval = 60.0  # 默认截图间隔改为60秒
        self.is_running = False
        self.stop_flag = False
        self.input_detector = None
        self.ink_detector = None
        self.screenshot_manager = None
        self.foreground_detection = True
        self.process_names = []
        self.ink_enabled = True
        self.last_activity_time = time.time()
        self.mutex = QMutex()
        self.current_monitor_target = "整个显示器"
        
        # 标志位，用于控制是否进行截图
        self.capture_enabled = False
    
    def enable_capture(self, enable=True):
        """启用/禁用截图功能"""
        self.capture_enabled = enable
    
    def set_monitor_target(self, target):
        """设置监控目标"""
        self.current_monitor_target = target
    
    def run(self):
        """线程主循环 - 固定间隔截图，不检测活动"""
        self.is_running = True
        self.stop_flag = False
        self.log_signal.emit("INFO", "监控线程启动(固定间隔模式)")
        self.status_signal.emit("info", "监控线程启动(固定间隔模式)")
        
        while not self.stop_flag:
            try:
                # 只有在启用截图时才执行截图逻辑
                if not self.capture_enabled:
                    self.msleep(100)  # 短暂休眠避免占用CPU
                    continue
                
                # 固定间隔截图，不检测活动
                self.last_activity_time = time.time()
                
                # 执行截图
                pixmap = None
                if self.screenshot_manager:
                    if self.foreground_detection and self.process_names:
                        pixmap = self.screenshot_manager.capture_foreground_window(self.process_names)
                    else:
                        pixmap = self.screenshot_manager.capture_screen()
                
                if pixmap:
                    # 发射信号传递截图数据
                    self.capture_signal.emit(pixmap)
                    self.log_signal.emit("INFO", f"固定间隔截图成功")
                
                # 检查停止标志
                if self.stop_flag:
                    break
                    
                # 等待指定的间隔时间
                for i in range(int(self.interval * 10)):  # 每0.1秒检查一次停止标志
                    if self.stop_flag:
                        break
                    self.msleep(100)
                    
            except Exception as e:
                error_msg = f"监控线程错误: {str(e)}"
                self.log_signal.emit("ERROR", error_msg)
                self.status_signal.emit("error", error_msg)
                self.msleep(1000)  # 出错时等待1秒
        
        self.is_running = False
        self.log_signal.emit("INFO", "监控线程已停止")
        self.status_signal.emit("info", "监控线程已停止")
    
    def stop(self):
        """停止监控线程"""
        self.mutex.lock()
        self.stop_flag = True
        self.mutex.unlock()
        
        # 等待线程结束，但设置超时
        if self.isRunning():
            self.wait(2000)  # 最多等待2秒

class SmartBoardApp:
    """智能板书应用主类"""
    
    def __init__(self, silent_start=False):
        # 创建应用实例
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("SmartBoardMonitor")
        self.app.setApplicationDisplayName("智能板书监控系统")
        
        # 设置全局字体
        font = QFont("Microsoft YaHei", 9)
        self.app.setFont(font)
        
        # 初始化日志管理器
        self.log_manager = LogManager()
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # 加载进程历史记录
        self.process_history = self.load_process_history()
        
        # 初始化截图管理器
        self.screenshot_manager = ScreenshotManager()
        
        # 初始化UI
        self.gui = SmartBoardGUI(self.log_manager, self.process_history)
        self.gui.config = self.config
        
        # 加载设置到GUI
        self.gui.load_settings(self.config)
        
        # 初始化后端模块
        self.input_detector = InputDetector()
        self.ink_detector = WindowsInkDetector()
        self.buffer_manager = BufferManager(self.log_manager, self.screenshot_manager)
        
        # 监控线程
        self.monitor_thread = None
        
        # 统计信息
        self.capture_count = 0
        self.last_capture_time = None
        self.next_save_time = None
        self.is_monitoring = False
        self.current_processes = []
        
        # 定时器
        self.status_timer = QTimer()
        self.save_check_timer = QTimer()
        
        # 系统托盘
        self.tray_manager = SystemTrayManager(self.gui, self)
        self.tray_manager.show_window_signal.connect(self.show_window)
        self.tray_manager.hide_window_signal.connect(self.hide_window)
        self.tray_manager.quit_app_signal.connect(self.quit_application)
        self.tray_manager.show()
        
        # 连接信号
        self.connect_signals()
        
        # 设置定时器
        self.setup_timers()
        
        # 初始化状态
        self.update_gui_status()
        
        # 设置开机自启动（根据配置）
        self.setup_auto_start()
        
        # 检查是否需要自动开始监控
        auto_start = self.config.get('auto_start', False)
        silent_start_config = self.config.get('silent_start', False)
        
        # 如果配置了开机自启动，则自动开始监控
        if auto_start:
            # 记录启动方式
            if silent_start or silent_start_config:
                start_mode = "静默启动"
            else:
                start_mode = "正常启动"
            
            msg = f"开机自启动已启用 ({start_mode})"
            self.update_status_message("info", msg)
            self.log_manager.add_log("INFO", msg)
            
            # 隐藏窗口（如果配置了静默启动）
            if silent_start or silent_start_config:
                self.gui.hide()
                # 延迟1秒后开始监控，确保系统完全初始化
                QTimer.singleShot(1000, self.start_monitoring)
            else:
                self.gui.show()
                # 延迟0.5秒后开始监控，让用户看到界面
                QTimer.singleShot(500, self.start_monitoring)
        else:
            # 不是开机自启动，正常显示窗口
            if silent_start:
                self.gui.hide()
            else:
                self.gui.show()
    
    def load_process_history(self):
        """加载进程历史记录"""
        history = []
        try:
            # 使用config管理器的base_dir来确保路径正确
            base_dir = self.config_manager.base_dir
            history_file = os.path.join(base_dir, "process_history.json")
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                print(f"✓ 已加载进程历史记录: {len(history)} 条")
                if hasattr(self, 'log_manager') and self.log_manager:
                    self.log_manager.add_log("INFO", f"已加载进程历史记录: {len(history)} 条")
            else:
                print("ℹ 未找到进程历史记录文件，将创建新文件")
                # 创建空的JSON文件
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"✗ 加载进程历史记录失败: {e}")
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.add_log("ERROR", f"加载进程历史记录失败: {e}")
        return history
    
    def setup_auto_start(self):
        """设置开机自启动"""
        auto_start = self.config.get('auto_start', False)
        silent_start = self.config.get('silent_start', False)
        
        if auto_start:
            try:
                self.config_manager.set_auto_start(True, silent_start)
            except Exception as e:
                error_msg = f"设置开机自启动失败: {e}"
                self.update_status_message("error", error_msg)
                self.log_manager.add_log("ERROR", error_msg)
    
    def update_status_message(self, msg_type, message):
        """更新状态消息"""
        if msg_type == "error":
            print(f"错误: {message}")
            self.log_manager.add_log("ERROR", message)
        elif msg_type == "info":
            print(f"信息: {message}")
            self.log_manager.add_log("INFO", message)
        
        # 更新系统信息标签
        self.gui.system_info_label.setText(message[:50])  # 限制长度
    
    def connect_signals(self):
        """连接所有信号"""
        # GUI信号
        self.gui.start_monitor_signal.connect(self.start_monitoring)
        self.gui.stop_monitor_signal.connect(self.stop_monitoring)
        self.gui.auto_start_changed.connect(self.on_auto_start_changed)
        self.gui.update_volume_estimate.connect(self.update_volume_estimate)
        self.gui.process_changed.connect(self.on_process_changed)
        self.gui.settings_changed.connect(self.on_settings_changed)  # 新增
        
        # 缓冲区管理器信号
        self.buffer_manager.buffer_updated.connect(self.on_buffer_updated)
        self.buffer_manager.buffer_full_signal.connect(self.on_buffer_full)
    
    def on_process_changed(self, process_text):
        """处理进程设置改变"""
        process_text = process_text.strip()
        if process_text:
            process_names = [name.strip() for name in process_text.split(',') if name.strip()]
            self.current_processes = process_names
            
            # 更新监控目标显示
            if len(process_names) == 1:
                monitor_text = f"监控目标: {process_names[0]}"
            else:
                monitor_text = f"监控目标: {len(process_names)}个进程"
            self.gui.monitor_target_label.setText(monitor_text)
        else:
            self.current_processes = []
            self.gui.monitor_target_label.setText("监控目标: 整个显示器")
    
    def on_auto_start_changed(self, auto_start, silent_start):
        """处理自启动设置改变"""
        try:
            self.config_manager.set_auto_start(auto_start, silent_start)
            
            # 更新配置
            self.config['auto_start'] = auto_start
            self.config['silent_start'] = silent_start
            self.config_manager.save_config(self.config)  # 立即保存配置
            
            status = "已启用" if auto_start else "已禁用"
            msg = f"开机自启动{status}"
            self.update_status_message("info", msg)
            self.log_manager.add_log("INFO", msg)
            
        except Exception as e:
            error_msg = f"设置开机自启动失败: {e}"
            self.update_status_message("error", error_msg)
            self.log_manager.add_log("ERROR", error_msg)
    
    def setup_timers(self):
        """设置定时器"""
        # 状态更新定时器
        self.status_timer.timeout.connect(self.update_gui_status)
        self.status_timer.start(1000)  # 每秒更新一次
        
        # 保存时间检查定时器
        self.save_check_timer.timeout.connect(self.check_save_times)
        self.save_check_timer.start(30000)  # 每30秒检查一次
        
        # 空闲检测定时器
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.check_idle_time)
        self.idle_timer.start(5000)  # 每5秒检查一次
    
    def load_settings_to_gui(self):
        """将配置加载到GUI"""
        # 设置基本参数
        if 'save_path' in self.config:
            self.gui.path_edit.setText(self.config['save_path'])
        
        # 修复：QSpinBox 需要整数，确保转换为 int
        if 'capture_interval' in self.config:
            self.gui.interval_spin.setValue(int(self.config['capture_interval']))
        
        if 'buffer_size' in self.config:
            self.gui.buffer_size_spin.setValue(int(self.config['buffer_size']))
        
        # 设置时间点
        if 'save_times' in self.config:
            self.gui.time_list.clear()
            for time_str in self.config['save_times']:
                self.gui.time_list.addItem(time_str)
        
        # 设置高级选项
        if 'foreground_detection' in self.config:
            self.gui.foreground_check.setChecked(self.config['foreground_detection'])
        if 'ink_detection' in self.config:
            self.gui.ink_check.setChecked(self.config['ink_detection'])
        if 'process_names' in self.config:
            self.gui.process_edit.setText(self.config['process_names'])
        
        # 设置系统选项（新增）
        if 'auto_start' in self.config:
            self.gui.auto_start_check.setChecked(self.config['auto_start'])
        if 'silent_start' in self.config:
            self.gui.silent_start_check.setChecked(self.config['silent_start'])
        if 'minimize_to_tray' in self.config:
            self.gui.minimize_to_tray_check.setChecked(self.config['minimize_to_tray'])
    
    def start_monitoring(self):
        """开始监控"""
        try:
            # 获取设置
            settings = self.gui.get_settings()
            
            # 确保数值类型正确
            settings['capture_interval'] = float(settings['capture_interval'])
            settings['buffer_size'] = int(settings['buffer_size'])
            
            # 更新配置并立即保存
            self.config.update(settings)
            self.config_manager.save_config(self.config)  # 立即保存到磁盘
            
            # 启动输入检测
            self.input_detector.start_detection()
            
            # 设置Ink检测
            if settings['ink_detection']:
                self.ink_detector.setup_ink_detection()
            
            # 设置保存路径（确保是绝对路径）
            save_path = settings['save_path']
            if not os.path.isabs(save_path):
                # 如果是相对路径，转换为绝对路径
                save_path = os.path.join(self.config_manager.base_dir, save_path)
            self.buffer_manager.set_save_path(save_path)
            
            # 设置缓冲区大小
            self.buffer_manager.set_buffer_size(settings['buffer_size'])
            
            # 创建并启动监控线程
            self.monitor_thread = MonitorThread()
            self.monitor_thread.input_detector = self.input_detector
            self.monitor_thread.ink_detector = self.ink_detector
            self.monitor_thread.screenshot_manager = self.screenshot_manager
            self.monitor_thread.foreground_detection = settings['foreground_detection']
            self.monitor_thread.ink_enabled = settings['ink_detection']
            self.monitor_thread.interval = settings['capture_interval']
            
            # 处理进程名
            if settings['process_names']:
                self.monitor_thread.process_names = [
                    name.strip() for name in settings['process_names'].split(',')
                    if name.strip()
                ]
            
            # 设置监控目标
            if settings['process_names'] and settings['foreground_detection']:
                process_names = [name.strip() for name in settings['process_names'].split(',') if name.strip()]
                if len(process_names) == 1:
                    self.monitor_thread.set_monitor_target(f"进程: {process_names[0]}")
                else:
                    self.monitor_thread.set_monitor_target(f"{len(process_names)}个进程")
            else:
                self.monitor_thread.set_monitor_target("整个显示器")
            
            # 连接监控线程信号
            self.monitor_thread.capture_signal.connect(self.handle_capture)
            self.monitor_thread.status_signal.connect(self.update_status_message)
            self.monitor_thread.log_signal.connect(self.log_manager.add_log)
            
            # 启动线程，但先不启用截图
            self.monitor_thread.start()
            
            # 等待线程启动完成
            time.sleep(0.1)
            
            # 现在启用截图功能
            self.monitor_thread.enable_capture(True)
            
            # 启动缓冲区自动保存
            self.buffer_manager.start_auto_save()
            
            # 计算下次保存时间
            self.calculate_next_save_time()
            
            # 更新状态
            self.is_monitoring = True
            self.gui.update_activity_status(False)
            
            # 更新GUI状态
            self.gui.start_btn.setEnabled(False)
            self.gui.stop_btn.setEnabled(True)
            self.gui.status_label.setText("运行中")
            self.gui.status_label.setStyleSheet("""
                QLabel {
                    background-color: #52c41a;
                    color: white;
                    border: 1px solid #73d13d;
                }
            """)
            
            # 更新托盘状态
            self.tray_manager.update_monitoring_status(True)
            
            # 更新状态栏信息
            if settings['process_names'] and settings['foreground_detection']:
                process_text = settings['process_names']
                process_names = [name.strip() for name in process_text.split(',') if name.strip()]
                if process_names:
                    monitor_text = f"正在监控: {', '.join(process_names)}"
                    self.gui.system_info_label.setText(monitor_text)
                else:
                    self.gui.system_info_label.setText("正在监控: 整个显示器")
            else:
                self.gui.system_info_label.setText("正在监控: 整个显示器")
            
            msg = "监控已启动"
            self.update_status_message("info", msg)
            self.log_manager.add_log("INFO", msg)
            
            # 更新体积估计
            self.update_volume_estimate()
            
        except Exception as e:
            error_msg = f"启动监控失败: {str(e)}"
            self.update_status_message("error", error_msg)
            self.log_manager.add_log("ERROR", error_msg)
            QMessageBox.critical(self.gui, "错误", error_msg)
    
    def stop_monitoring(self):
        """停止监控"""
        try:
            # 先禁用截图功能
            if self.monitor_thread:
                self.monitor_thread.enable_capture(False)
            
            # 停止监控线程
            if self.monitor_thread and self.monitor_thread.isRunning():
                self.monitor_thread.stop()
                self.monitor_thread = None
            
            # 停止输入检测
            self.input_detector.stop_detection()
            
            # 停止缓冲区自动保存
            self.buffer_manager.stop_auto_save()
            
            # 异步保存缓冲区剩余内容
            QTimer.singleShot(0, self.buffer_manager._save_worker)
            
            # 更新状态
            self.is_monitoring = False
            self.gui.update_activity_status(False)
            
            # 更新GUI状态
            self.gui.start_btn.setEnabled(True)
            self.gui.stop_btn.setEnabled(False)
            self.gui.status_label.setText("已停止")
            self.gui.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff4d4f;
                    color: white;
                    border: 1px solid #ff7875;
                }
            """)
            
            # 更新托盘状态
            self.tray_manager.update_monitoring_status(False)
            
            # 更新状态栏信息
            self.gui.system_info_label.setText("监控已停止")
            
            msg = "监控已停止"
            self.update_status_message("info", msg)
            self.log_manager.add_log("INFO", msg)
            
        except Exception as e:
            error_msg = f"停止监控时出错: {str(e)}"
            self.update_status_message("error", error_msg)
            self.log_manager.add_log("ERROR", error_msg)
    
    def handle_capture(self, pixmap):
        """处理截图"""
        try:
            # 只有在监控状态下才处理截图
            if not self.is_monitoring:
                return
                
            # 保存截图到内存
            image_data = self.screenshot_manager.save_to_memory(pixmap)
            if image_data:
                # 传递截图管理器用于获取时间戳
                self.buffer_manager.add_to_buffer(image_data, self.screenshot_manager)
                
                # 更新统计信息
                self.capture_count += 1
                self.last_capture_time = datetime.now()
                
                # 更新GUI
                self.gui.update_capture_count(self.capture_count)
                self.gui.update_last_capture(self.last_capture_time.strftime("%H:%M:%S"))
                self.gui.update_activity_status(True)
                
        except Exception as e:
            error_msg = f"处理截图时出错: {str(e)}"
            self.update_status_message("error", error_msg)
            self.log_manager.add_log("ERROR", error_msg)
    
    def on_buffer_updated(self, size, max_size):
        """缓冲区更新回调"""
        self.gui.update_buffer_progress(size, max_size)
        
        # 计算内存使用（估算：每张截图约0.5MB）
        estimated_mb = size * 0.5
        self.gui.update_memory_usage(f"{estimated_mb:.1f} MB")
    
    def on_settings_changed(self, settings):
        """处理设置变更（实时应用）"""
        try:
            # 立即保存配置到磁盘
            self.config.update(settings)
            self.config_manager.save_config(self.config)
            
            if self.is_monitoring and self.monitor_thread:
                # 更新截图间隔
                if 'capture_interval' in settings:
                    self.monitor_thread.interval = float(settings['capture_interval'])
                    msg = f"截图间隔已更新: {settings['capture_interval']}秒"
                    self.update_status_message("info", msg)
                    self.log_manager.add_log("INFO", msg)
                
                # 更新前台窗口检测设置
                if 'foreground_detection' in settings:
                    self.monitor_thread.foreground_detection = settings['foreground_detection']
                    status = "已启用" if settings['foreground_detection'] else "已禁用"
                    msg = f"前台窗口检测{status}"
                    self.update_status_message("info", msg)
                    self.log_manager.add_log("INFO", msg)
                
                # 更新Ink检测设置
                if 'ink_detection' in settings:
                    self.monitor_thread.ink_enabled = settings['ink_detection']
                    status = "已启用" if settings['ink_detection'] else "已禁用"
                    msg = f"手写笔检测{status}"
                    self.update_status_message("info", msg)
                    self.log_manager.add_log("INFO", msg)
                
                # 更新进程名
                if 'process_names' in settings:
                    if settings['process_names']:
                        self.monitor_thread.process_names = [
                            name.strip() for name in settings['process_names'].split(',')
                            if name.strip()
                        ]
                    else:
                        self.monitor_thread.process_names = []
                    
                    if self.monitor_thread.process_names:
                        msg = f"监控进程已更新: {', '.join(self.monitor_thread.process_names)}"
                    else:
                        msg = "监控目标已更新: 整个显示器"
                    
                    self.update_status_message("info", msg)
                    self.log_manager.add_log("INFO", msg)
            
        except Exception as e:
            error_msg = f"更新设置失败: {str(e)}"
            self.update_status_message("error", error_msg)
            self.log_manager.add_log("ERROR", error_msg)
    
    def on_buffer_full(self):
        """缓冲区满时回调"""
        msg = "缓冲区已满，正在保存..."
        self.update_status_message("info", msg)
        self.log_manager.add_log("INFO", msg)
        self.tray_manager.show_message("缓冲区满", "缓冲区已满，正在保存截图", 3000)
    
    def update_volume_estimate(self):
        """更新体积估计"""
        try:
            buffer_size = self.gui.buffer_size_spin.value()
            estimated_mb = buffer_size * 0.5  # 每张截图0.5MB
            estimated_gb = estimated_mb / 1024
            
            if estimated_mb < 1024:
                text = f"{estimated_mb:.1f} MB"
            else:
                text = f"{estimated_gb:.2f} GB"
            
            self.gui.volume_estimate_label.setText(f"估计体积: {text}")
        except Exception as e:
            print(f"更新体积估计失败: {e}")
    
    def check_save_times(self):
        """检查是否到达保存时间点"""
        if not self.is_monitoring:
            return
            
        current_time = datetime.now().strftime("%H:%M")
        settings = self.gui.get_settings()
        save_times = settings['save_times']
        
        if current_time in save_times:
            try:
                # 执行保存
                self.buffer_manager._save_worker()
                self.last_capture_time = datetime.now()
                self.calculate_next_save_time()
                
                # 显示提示
                msg = f"已自动保存截图 ({current_time})"
                self.update_status_message("info", msg)
                self.log_manager.add_log("INFO", msg)
                self.tray_manager.show_message("自动保存", msg, 3000)
                
            except Exception as e:
                error_msg = f"自动保存时出错: {str(e)}"
                self.update_status_message("error", error_msg)
                self.log_manager.add_log("ERROR", error_msg)
    
    def check_idle_time(self):
        """检查空闲时间"""
        if self.is_monitoring and self.input_detector:
            idle_time = self.input_detector.get_idle_time()
            # 如果空闲时间超过5秒，认为无活动
            self.gui.update_activity_status(idle_time < 5.0)
    
    def calculate_next_save_time(self):
        """计算下次保存时间"""
        settings = self.gui.get_settings()
        save_times = settings['save_times']
        if not save_times:
            self.gui.update_next_save_time("未设置")
            self.next_save_time = None
            return
        
        current_time = datetime.now()
        current_time_str = current_time.strftime("%H:%M")
        
        # 找到下一个保存时间点
        next_time = None
        for time_str in sorted(save_times):
            if time_str > current_time_str:
                next_time = time_str
                break
        
        # 如果今天没有下一个时间点，使用明天的第一个时间点
        if next_time is None and save_times:
            next_time = sorted(save_times)[0]
            next_save = current_time + timedelta(days=1)
        else:
            next_save = current_time
        
        # 设置具体时间
        hour, minute = map(int, next_time.split(':'))
        next_save = next_save.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        self.next_save_time = next_save
        # 注意：精简版GUI中可能没有update_next_save_time方法
        # 所以我们只更新状态栏
        self.gui.system_info_label.setText(f"下次保存: {next_save.strftime('%H:%M')}")
    
    def update_gui_status(self):
        """更新GUI状态信息"""
        # 更新下次保存时间（如果需要重新计算）
        if self.next_save_time and datetime.now() > self.next_save_time:
            self.calculate_next_save_time()
    
    def show_window(self):
        """显示主窗口"""
        self.gui.showNormal()
        self.gui.activateWindow()
        self.gui.raise_()
    
    def hide_window(self):
        """隐藏主窗口到托盘"""
        if self.config.get('minimize_to_tray', True):
            self.gui.hide()
            self.tray_manager.show_message("提示", "程序已最小化到系统托盘", 2000)
    
    def quit_application(self):
        """退出应用程序"""
        # 保存当前配置
        try:
            settings = self.gui.get_settings()
            self.config.update(settings)
            self.config_manager.save_config(self.config)
        except Exception as e:
            print(f"保存配置失败: {e}")
        
        # 异步停止监控，避免卡顿
        if self.is_monitoring:
            self.stop_monitoring()
        
        # 延迟退出，确保资源释放
        QTimer.singleShot(500, self.app.quit)
    
    def run(self):
        """运行应用程序"""
        return self.app.exec_()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='智能板书自动保存系统')
    parser.add_argument('--silent', action='store_true', help='静默启动（最小化到托盘）')
    args = parser.parse_args()
    
    try:
        app = SmartBoardApp(silent_start=args.silent)
        exit_code = app.run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"应用程序错误: {e}")
        QMessageBox.critical(None, "错误", f"应用程序启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()