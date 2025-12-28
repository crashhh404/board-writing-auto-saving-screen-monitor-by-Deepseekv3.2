# -*- coding: utf-8 -*-
# logger.py
"""
日志管理模块
"""

import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class LogManager(QObject):
    """日志管理器"""
    
    log_updated = pyqtSignal()  # 日志更新信号
    
    def __init__(self, max_logs=1000):
        super().__init__()
        self.logs = []
        self.max_logs = max_logs
    
    def add_log(self, level, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (timestamp, level, message)
        self.logs.append(log_entry)
        
        # 限制日志数量
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        # 发射更新信号
        self.log_updated.emit()
    
    def get_logs(self):
        """获取所有日志"""
        return self.logs.copy()
    
    def clear_logs(self):
        """清空日志"""
        self.logs.clear()
        self.log_updated.emit()
    
    def save_to_file(self, filepath):
        """保存日志到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for timestamp, level, message in self.logs:
                    f.write(f"[{timestamp}] {level}: {message}\n")
            return True
        except Exception as e:
            self.add_log("ERROR", f"保存日志失败: {str(e)}")
            return False
    
    def get_recent_logs(self, count=50):
        """获取最近的日志"""
        return self.logs[-count:] if len(self.logs) > count else self.logs
