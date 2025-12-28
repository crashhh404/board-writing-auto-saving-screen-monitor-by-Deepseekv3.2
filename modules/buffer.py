# -*- coding: utf-8 -*-
# buffer.py
"""
缓冲区管理模块 - 管理内存缓冲区
"""

import os
import time
import hashlib
from datetime import datetime
from queue import Queue
from threading import Thread, Event, Lock
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPixmap

class BufferManager(QObject):
    """管理内存缓冲区"""
    
    buffer_updated = pyqtSignal(int, int)  # 缓冲区更新信号 (当前大小, 最大大小)
    buffer_full_signal = pyqtSignal()  # 缓冲区满信号
    
    def __init__(self, log_manager=None, screenshot_manager=None):
        super().__init__()
        self.max_size = 100  # 最大100张截图
        self.ram_buffer = Queue(maxsize=self.max_size)
        self.save_interval = 300  # 默认5分钟
        self.save_path = "./screenshots"
        self.auto_save_thread = None
        self.stop_event = Event()
        self.log_manager = log_manager
        self.screenshot_manager = screenshot_manager
        self.lock = Lock()
        self.buffer_count = 0
        self.image_hashes = set()  # 用于存储已存在的图片哈希值
        
        # 确保保存目录存在（解决权限问题）
        self.ensure_save_directory()
    
    def ensure_save_directory(self):
        """确保保存目录存在且有写入权限"""
        try:
            os.makedirs(self.save_path, exist_ok=True)
            
            # 测试目录写入权限
            test_file = os.path.join(self.save_path, "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            if self.log_manager:
                self.log_manager.add_log("INFO", f"保存目录已准备就绪: {self.save_path}")
        except PermissionError as e:
            # 如果权限错误，尝试使用用户文档目录
            user_docs = os.path.join(os.path.expanduser("~"), "Documents", "SmartBoardScreenshots")
            self.save_path = user_docs
            os.makedirs(self.save_path, exist_ok=True)
            
            error_msg = f"原始保存目录无写入权限，已切换到: {self.save_path}"
            if self.log_manager:
                self.log_manager.add_log("ERROR", error_msg)
            print(error_msg)
        except Exception as e:
            error_msg = f"准备保存目录失败: {e}"
            if self.log_manager:
                self.log_manager.add_log("ERROR", error_msg)
            print(error_msg)
    
    def set_buffer_size(self, size):
        """设置缓冲区大小"""
        with self.lock:
            self.max_size = size
            # 重新创建队列
            old_buffer = list(self.ram_buffer.queue)
            self.ram_buffer = Queue(maxsize=size)
            for item in old_buffer[:size]:  # 只保留前size个
                self.ram_buffer.put(item)
    
    def add_to_buffer(self, image_data, screenshot_manager=None):
        """添加截图到缓冲区，自动去重"""
        with self.lock:
            # 计算图片哈希值
            image_hash = self.calculate_image_hash(image_data)
            
            # 检查是否重复
            if image_hash and image_hash in self.image_hashes:
                if self.log_manager:
                    self.log_manager.add_log("INFO", "检测到重复截图，已跳过")
                return  # 重复截图，直接返回
            
            # 如果是新截图，添加到哈希集合
            if image_hash:
                self.image_hashes.add(image_hash)
            
            # 检查缓冲区是否已满
            if self.ram_buffer.full():
                # 缓冲区满时启动保存
                self.buffer_full_signal.emit()
                self._save_worker()
            
            timestamp = time.time()
            
            # 使用screenshot_manager获取带星期的文件夹名
            if screenshot_manager and hasattr(screenshot_manager, 'get_date_folder_name'):
                date_str = screenshot_manager.get_date_folder_name()
            else:
                # 备用方法
                now = datetime.fromtimestamp(timestamp)
                weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = weekdays[now.weekday()]
                date_str = f"{now.strftime('%Y-%m-%d')}_{weekday}"
            
            # 创建日期目录
            date_dir = os.path.join(self.save_path, date_str)
            try:
                os.makedirs(date_dir, exist_ok=True)
            except PermissionError:
                # 如果无法创建目录，使用备用路径
                user_docs = os.path.join(os.path.expanduser("~"), "Documents", "SmartBoardScreenshots", date_str)
                date_dir = user_docs
                os.makedirs(date_dir, exist_ok=True)
            
            # 生成文件名
            filename = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H-%M-%S.png")
            filepath = os.path.join(date_dir, filename)
            
            self.ram_buffer.put({
                'data': image_data,
                'timestamp': timestamp,
                'filepath': filepath,
                'date_str': date_str,
                'filename': filename,
                'hash': image_hash  # 保存哈希值
            })
            
            self.buffer_count = self.ram_buffer.qsize()
            
            # 发射更新信号
            self.buffer_updated.emit(self.buffer_count, self.max_size)
            
            if self.log_manager:
                self.log_manager.add_log("INFO", f"截图已添加到缓冲区 ({self.buffer_count}/{self.max_size})")
    
    def start_auto_save(self):
        """启动自动保存线程"""
        self.stop_event.clear()
        self.auto_save_thread = Thread(target=self._auto_save_worker)
        self.auto_save_thread.daemon = True
        self.auto_save_thread.start()
        
        if self.log_manager:
            self.log_manager.add_log("INFO", "自动保存已启动")
    
    def stop_auto_save(self):
        """停止自动保存"""
        self.stop_event.set()
        if self.auto_save_thread:
            self.auto_save_thread.join(timeout=5)
        
        if self.log_manager:
            self.log_manager.add_log("INFO", "自动保存已停止")
    
    def _auto_save_worker(self):
        """自动保存工作线程"""
        while not self.stop_event.is_set():
            self._save_worker()
            self.stop_event.wait(self.save_interval)
    
    def _save_worker(self):
        """保存缓冲区内容到文件"""
        if self.ram_buffer.empty():
            return
        
        saved_count = 0
        # 保存所有缓冲区内容
        while not self.ram_buffer.empty():
            try:
                item = self.ram_buffer.get()
                filepath = item['filepath']
                date_str = item['date_str']
                
                # 确保日期目录存在
                try:
                    date_dir = os.path.dirname(filepath)
                    os.makedirs(date_dir, exist_ok=True)
                except PermissionError:
                    # 如果无法创建目录，使用备用路径
                    user_docs = os.path.join(os.path.expanduser("~"), "Documents", "SmartBoardScreenshots", date_str)
                    filepath = os.path.join(user_docs, os.path.basename(filepath))
                    os.makedirs(user_docs, exist_ok=True)
                
                # 从内存数据创建QPixmap并保存
                pixmap = QPixmap()
                pixmap.loadFromData(item['data'])
                if not pixmap.isNull():
                    # 尝试保存，如果失败则尝试备用路径
                    try:
                        pixmap.save(filepath, "PNG")
                    except Exception as save_error:
                        # 使用用户文档目录作为备用
                        user_docs = os.path.join(os.path.expanduser("~"), "Documents", "SmartBoardScreenshots", date_str)
                        backup_path = os.path.join(user_docs, os.path.basename(filepath))
                        os.makedirs(user_docs, exist_ok=True)
                        pixmap.save(backup_path, "PNG")
                        filepath = backup_path
                    
                    saved_count += 1
                    
                    if self.log_manager:
                        self.log_manager.add_log("INFO", f"已保存截图: {os.path.basename(filepath)}")
                    
            except Exception as e:
                error_msg = f"保存截图时出错: {e}"
                print(error_msg)
                if self.log_manager:
                    self.log_manager.add_log("ERROR", error_msg)
        
        # 更新缓冲区计数
        self.buffer_count = self.ram_buffer.qsize()
        self.buffer_updated.emit(self.buffer_count, self.max_size)
        
        # 清理已保存图片的哈希值
        self.image_hashes.clear()
        
        if saved_count > 0 and self.log_manager:
            self.log_manager.add_log("INFO", f"已保存 {saved_count} 张截图")
    
    def set_save_path(self, path):
        """设置保存路径"""
        self.save_path = path
        self.ensure_save_directory()
        
        if self.log_manager:
            self.log_manager.add_log("INFO", f"保存路径设置为: {path}")
    
    def calculate_image_hash(self, image_data):
        """计算图片的哈希值用于去重"""
        try:
            # 使用MD5哈希算法
            md5_hash = hashlib.md5(image_data).hexdigest()
            return md5_hash
        except Exception as e:
            print(f"计算图片哈希失败: {e}")
            return None

    def get_buffer_info(self):
        """获取缓冲区信息"""
        with self.lock:
            return {
                'current_size': self.buffer_count,
                'max_size': self.max_size,
                'estimated_size_mb': self.buffer_count * 0.5  # 每张截图约0.5MB
            }