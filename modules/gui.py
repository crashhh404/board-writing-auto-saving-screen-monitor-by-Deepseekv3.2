# -*- coding: utf-8 -*-
# gui.py
"""
GUI界面模块
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox, 
                             QGroupBox, QFileDialog, QComboBox, QTimeEdit, QListWidget, 
                             QListWidgetItem, QProgressBar, QTabWidget, QGridLayout, 
                             QFrame, QMessageBox, QApplication, QDesktopWidget,
                             QTextEdit, QTextBrowser, QSplitter, QSizePolicy)
from PyQt5.QtCore import Qt, QTime, QTimer, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor
import psutil
import json
import os

class SmartBoardGUI(QMainWindow):
    """智能板书自动保存系统 - 最初版本UI界面"""
    
    # 定义信号
    start_monitor_signal = pyqtSignal()
    stop_monitor_signal = pyqtSignal()
    auto_start_changed = pyqtSignal(bool, bool)  # 自启动设置改变信号
    update_volume_estimate = pyqtSignal()  # 更新体积估计信号
    process_changed = pyqtSignal(str)  # 进程设置改变信号
    settings_changed = pyqtSignal(dict)  # 设置改变信号（新增）
    
    def __init__(self, log_manager=None, process_history=None):
        super().__init__()
        self.setWindowTitle("智能板书自动保存系统v6.5（Made By DeepSeek-V3.2）")
        
        # 日志管理器
        self.log_manager = log_manager
        
        # 进程历史记录
        self.process_history = process_history if process_history is not None else []
        if not self.process_history:
            self.load_process_history()
        
        # 设置窗口大小和居中
        self.resize(1000, 750)  # 增加高度以容纳日志页面
        self.center_window()
        
        # 设置全局样式
        self.setup_styles()
        
        # 初始化UI组件
        self.init_ui()
        
        # 连接信号
        self.connect_signals()
        
        # 初始化配置
        self.config = {}
        
        # 监控状态标志
        self.is_monitoring = False
        
        # 日志更新定时器
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log_display)
        self.log_timer.start(1000)  # 每秒更新一次日志
        
        # 进程检测定时器
        self.process_check_timer = QTimer()
        self.process_check_timer.timeout.connect(self.check_processes)
        self.process_check_timer.start(2000)  # 每2秒检查一次进程
    
    def center_window(self):
        """将窗口居中显示"""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, 
                  (screen.height() - size.height()) // 6)
    
    def setup_styles(self):
        """设置应用程序样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
            QPushButton:disabled {
                background-color: #d9d9d9;
                color: #8c8c8c;
            }
            QLineEdit, QSpinBox, QTimeEdit, QComboBox {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 3px 5px;
                min-height: 25px;
            }
            QListWidget {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
            }
            QProgressBar {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #52c41a;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 5px 10px;
                border: 1px solid #d9d9d9;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                background-color: #f5f5f5;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
                margin-bottom: -1px;
            }
            QTextBrowser, QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
                font-size: 10pt;
            }
            #title_label {
                color: #1890ff;
                font-size: 18px;
                font-weight: bold;
            }
            #status_label {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                border-radius: 4px;
                text-align: center;
            }
            #log_browser {
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
                font-size: 10pt;
            }
            .process-valid {
                color: #52c41a;
                font-weight: bold;
            }
            .process-invalid {
                color: #ff4d4f;
                font-weight: bold;
            }
            .process-info {
                color: #1890ff;
                font-weight: bold;
            }
        """)
    
    def load_process_history(self):
        """加载进程历史记录"""
        try:
            config_file = "process_history.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.process_history = json.load(f)
        except Exception as e:
            print(f"加载进程历史记录失败: {e}")
            self.process_history = []
    
    def save_process_history(self):
        """保存进程历史记录"""
        try:
            config_file = "process_history.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.process_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存进程历史记录失败: {e}")
    
    def add_to_process_history(self, process_name):
        """添加到进程历史记录"""
        process_name = process_name.strip()
        if process_name and process_name not in self.process_history:
            self.process_history.append(process_name)
            # 只保留最近20个记录
            if len(self.process_history) > 20:
                self.process_history = self.process_history[-20:]
            self.save_process_history()
            self.update_process_history_list()
    
    def update_process_history_list(self):
        """更新进程历史记录列表"""
        if hasattr(self, 'history_list'):
            self.history_list.clear()
            for process in self.process_history:
                self.history_list.addItem(process)
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题栏
        self.create_title_bar(main_layout)
        
        # 状态显示区域
        self.create_status_section(main_layout)
        
        # 控制按钮区域
        self.create_control_section(main_layout)
        
        # 设置区域（选项卡）
        self.create_settings_section(main_layout)
        
        # 状态栏
        self.create_status_bar(main_layout)
    
    def create_title_bar(self, parent_layout):
        """创建标题栏"""
        title_label = QLabel("📝📝 智能板书自动保存系统v6.5（Made By DeepSeek-V3.2）")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 16, QFont.Bold)
        title_label.setFont(title_font)
        parent_layout.addWidget(title_label)
    
    def create_status_section(self, parent_layout):
        """创建状态显示区域"""
        status_grid = QGridLayout()
        status_grid.setSpacing(10)
        
        # 监控状态
        status_card1 = QGroupBox("监控状态")
        layout1 = QVBoxLayout(status_card1)
        self.status_label = QLabel("已停止")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ff4d4f;
                color: white;
                border: 1px solid #ff7875;
            }
        """)
        layout1.addWidget(self.status_label)
        
        # 截图模式
        status_card2 = QGroupBox("截图模式")
        layout2 = QVBoxLayout(status_card2)
        self.activity_label = QLabel("固定间隔")
        self.activity_label.setObjectName("status_label")
        self.activity_label.setAlignment(Qt.AlignCenter)
        self.activity_label.setStyleSheet("""
            QLabel {
                background-color: #1890ff;
                color: white;
                border: 1px solid #40a9ff;
            }
        """)
        layout2.addWidget(self.activity_label)
        
        # 截图统计
        status_card3 = QGroupBox("截图统计")
        layout3 = QVBoxLayout(status_card3)
        self.capture_count_label = QLabel("0")
        self.capture_count_label.setAlignment(Qt.AlignCenter)
        self.capture_count_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1890ff;
            }
        """)
        layout3.addWidget(self.capture_count_label)
        
        # 缓冲区状态
        status_card4 = QGroupBox("缓冲区")
        layout4 = QVBoxLayout(status_card4)
        self.buffer_label = QLabel("0/100")
        self.buffer_label.setAlignment(Qt.AlignCenter)
        self.buffer_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #52c41a;
            }
        """)
        layout4.addWidget(self.buffer_label)
        
        status_grid.addWidget(status_card1, 0, 0)
        status_grid.addWidget(status_card2, 0, 1)
        status_grid.addWidget(status_card3, 1, 0)
        status_grid.addWidget(status_card4, 1, 1)
        
        parent_layout.addLayout(status_grid)
    
    def create_control_section(self, parent_layout):
        """创建控制按钮区域"""
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        # 开始按钮
        self.start_btn = QPushButton("▶ 开始监控")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setMinimumHeight(40)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止监控")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        
        # 缓冲区进度条
        self.buffer_progress = QProgressBar()
        self.buffer_progress.setRange(0, 100)
        self.buffer_progress.setValue(0)
        self.buffer_progress.setFormat("缓冲区使用率: %p%")
        self.buffer_progress.setMinimumHeight(35)
        
        # 体积估计标签
        self.volume_estimate_label = QLabel("估计体积: 0.0 MB")
        self.volume_estimate_label.setAlignment(Qt.AlignCenter)
        self.volume_estimate_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #8c8c8c;
                padding: 5px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        control_layout.addWidget(self.start_btn, 1)
        control_layout.addWidget(self.stop_btn, 1)
        control_layout.addWidget(self.buffer_progress, 3)
        control_layout.addWidget(self.volume_estimate_label, 1)
        
        parent_layout.addWidget(control_frame)
    
    def create_settings_section(self, parent_layout):
        """创建设置区域"""
        self.settings_tabs = QTabWidget()
        
        # 基本设置选项卡
        self.create_basic_settings_tab()
        
        # 高级设置选项卡
        self.create_advanced_settings_tab()
        
        # 系统设置选项卡
        self.create_system_settings_tab()
        
        # 日志页面选项卡
        self.create_log_tab()
        
        # 程序说明页面
        self.create_help_tab()
        
        parent_layout.addWidget(self.settings_tabs)
    
    def create_basic_settings_tab(self):
        """创建基本设置选项卡"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel
        
        basic_tab = QWidget()
        layout = QVBoxLayout(basic_tab)
        layout.setSpacing(15)
        
        # 保存路径设置
        path_group = QGroupBox("保存路径设置")
        path_layout = QHBoxLayout(path_group)
        self.path_edit = QLineEdit("./screenshots")
        self.path_edit.setPlaceholderText("请选择截图保存路径...")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(80)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        layout.addWidget(path_group)
        
        # 截图间隔设置
        interval_group = QGroupBox("截图间隔设置")
        interval_layout = QHBoxLayout(interval_group)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 300)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setMaximumWidth(150)
        interval_layout.addWidget(QLabel("活动时截图间隔:"))
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        layout.addWidget(interval_group)
        
        # 内存缓冲区设置
        buffer_group = QGroupBox("内存缓冲区设置")
        buffer_layout = QHBoxLayout(buffer_group)
        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setRange(10, 1000)
        self.buffer_size_spin.setValue(100)
        self.buffer_size_spin.setSuffix(" 张截图")
        self.buffer_size_spin.setMaximumWidth(180)
        buffer_layout.addWidget(QLabel("缓冲区大小:"))
        buffer_layout.addWidget(self.buffer_size_spin)
        buffer_layout.addStretch()
        layout.addWidget(buffer_group)
        
        layout.addStretch()
        self.settings_tabs.addTab(basic_tab, "⚙ 基本设置")
    
    def create_advanced_settings_tab(self):
        """创建高级设置选项卡"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget
        
        advanced_tab = QWidget()
        layout = QVBoxLayout(advanced_tab)
        layout.setSpacing(15)
        
        # 窗口检测设置
        window_group = QGroupBox("窗口检测设置")
        window_layout = QVBoxLayout(window_group)
        
        self.foreground_check = QCheckBox("仅截取前台窗口")
        self.foreground_check.setChecked(True)
        window_layout.addWidget(self.foreground_check)
        
        # 进程输入区域
        process_input_layout = QHBoxLayout()
        process_input_layout.addWidget(QLabel("监控进程:"))
        self.process_edit = QLineEdit()
        self.process_edit.setPlaceholderText("如: notepad.exe, chrome.exe")
        process_input_layout.addWidget(self.process_edit, 1)
        
        # 添加历史按钮
        self.add_history_btn = QPushButton("添加到历史")
        self.add_history_btn.setMaximumWidth(80)
        process_input_layout.addWidget(self.add_history_btn)
        
        window_layout.addLayout(process_input_layout)
        
        # 进程状态提示
        self.process_status_label = QLabel("未设置进程，将监控整个显示器")
        self.process_status_label.setWordWrap(True)
        self.process_status_label.setStyleSheet("""
            QLabel {
                color: #1890ff;
                font-weight: bold;
                padding: 5px;
                border-radius: 4px;
                background-color: #f0f2f5;
            }
        """)
        window_layout.addWidget(self.process_status_label)
        
        # 进程历史记录
        history_group = QGroupBox("进程历史记录")
        history_layout = QVBoxLayout(history_group)
        
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(120)
        history_layout.addWidget(self.history_list)
        
        # 更新历史记录列表
        self.update_process_history_list()
        
        window_layout.addWidget(history_group)
        
        layout.addWidget(window_group)
        
        # Windows Ink设置
        ink_group = QGroupBox("Windows Ink设置")
        ink_layout = QVBoxLayout(ink_group)
        self.ink_check = QCheckBox("启用手写笔/触摸屏检测")
        self.ink_check.setChecked(True)
        ink_layout.addWidget(self.ink_check)
        layout.addWidget(ink_group)
        
        # 自动保存时间设置
        time_group = QGroupBox("自动保存时间点")
        time_layout = QVBoxLayout(time_group)
        
        time_edit_layout = QHBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        self.add_time_btn = QPushButton("添加")
        self.remove_time_btn = QPushButton("删除")
        time_edit_layout.addWidget(QLabel("时间:"))
        time_edit_layout.addWidget(self.time_edit)
        time_edit_layout.addWidget(self.add_time_btn)
        time_edit_layout.addWidget(self.remove_time_btn)
        time_edit_layout.addStretch()
        time_layout.addLayout(time_edit_layout)
        
        self.time_list = QListWidget()
        self.time_list.setMaximumHeight(120)
        time_layout.addWidget(self.time_list)
        
        # 初始化默认时间
        default_times = ["09:00", "12:00", "15:00", "18:00"]
        for time_str in default_times:
            self.time_list.addItem(time_str)
        
        layout.addWidget(time_group)
        
        layout.addStretch()
        self.settings_tabs.addTab(advanced_tab, "⚡ 高级设置")
    
    def create_system_settings_tab(self):
        """创建系统设置选项卡"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLabel
        
        system_tab = QWidget()
        layout = QVBoxLayout(system_tab)
        layout.setSpacing(15)
        
        # 启动设置
        startup_group = QGroupBox("启动设置")
        startup_layout = QVBoxLayout(startup_group)
        
        # 开机自启动
        self.auto_start_check = QCheckBox("开机自启动")
        self.auto_start_check.setChecked(False)
        startup_layout.addWidget(self.auto_start_check)
        
        # 静默启动
        self.silent_start_check = QCheckBox("静默启动（启动时最小化到系统托盘）")
        self.silent_start_check.setChecked(False)
        startup_layout.addWidget(self.silent_start_check)
        
        # 提示信息
        info_label = QLabel("注意：开机自启动需要管理员权限，首次设置时可能会弹出UAC确认窗口。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #ff4d4f; font-size: 12px;")
        startup_layout.addWidget(info_label)
        
        layout.addWidget(startup_group)
        
        # 托盘设置
        tray_group = QGroupBox("托盘设置")
        tray_layout = QVBoxLayout(tray_group)
        
        self.minimize_to_tray_check = QCheckBox("最小化时隐藏到系统托盘")
        self.minimize_to_tray_check.setChecked(True)
        tray_layout.addWidget(self.minimize_to_tray_check)
        
        layout.addWidget(tray_group)
        
        layout.addStretch()
        self.settings_tabs.addTab(system_tab, "🖥️ 系统设置")
    
    def create_log_tab(self):
        """创建日志页面"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser
        
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        layout.setSpacing(10)
        
        # 日志操作按钮
        log_control_layout = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("清空日志")
        self.save_log_btn = QPushButton("保存日志")
        self.refresh_log_btn = QPushButton("刷新")
        
        log_control_layout.addWidget(self.clear_log_btn)
        log_control_layout.addWidget(self.save_log_btn)
        log_control_layout.addWidget(self.refresh_log_btn)
        log_control_layout.addStretch()
        
        # 日志显示区域
        self.log_browser = QTextBrowser()
        self.log_browser.setObjectName("log_browser")
        self.log_browser.setReadOnly(True)
        self.log_browser.setMinimumHeight(300)
        
        layout.addLayout(log_control_layout)
        layout.addWidget(self.log_browser)
        
        self.settings_tabs.addTab(log_tab, "📝 运行日志")
    
    def create_help_tab(self):
        """创建程序说明页面"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser, QPushButton, QHBoxLayout
        
        help_tab = QWidget()
        layout = QVBoxLayout(help_tab)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("📘 智能板书监控系统 - 使用说明")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1890ff;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 说明文本区域
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        self.help_browser.setMinimumHeight(400)
        
        # 加载说明文档
        self.load_help_content()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新说明文档")
        refresh_btn.setMaximumWidth(120)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)
        
        layout.addWidget(self.help_browser)
        layout.addLayout(btn_layout)
        
        self.settings_tabs.addTab(help_tab, "📘 程序说明")
    
    def load_help_content(self):
        """加载说明文档"""
        help_file = "HELP.md"
        default_content = """
        <h2>📘 智能板书监控系统 v6.0</h2>
        <h3>使用说明</h3>
        
        <h4>一、快速开始</h4>
        <ol>
        <li><b>启动程序</b>: 双击 SmartBoardMonitor.exe 或运行 python main.py</li>
        <li><b>基本设置</b>: 在"基本设置"标签页配置保存路径和截图间隔</li>
        <li><b>开始监控</b>: 点击主界面的"开始监控"按钮</li>
        </ol>
        
        <h4>二、核心功能</h4>
        <ul>
        <li><b>固定间隔监控</b>: 按设定间隔自动截图，不依赖用户活动</li>
        <li><b>进程监控</b>: 可指定只截取特定程序窗口（如 ppt.exe, notepad.exe）</li>
        <li><b>自动保存</b>: 截图按日期分文件夹保存，文件名包含精确时间</li>
        <li><b>计划任务</b>: 可设置每日固定时间自动保存截图</li>
        </ul>
        
        <h4>三、高级功能</h4>
        <ul>
        <li><b>开机自启</b>: 在"系统设置"中开启，启动后自动开始监控</li>
        <li><b>静默运行</b>: 启动时最小化到系统托盘，不显示主窗口</li>
        <li><b>实时设置</b>: 更改设置后无需重启监控立即生效</li>
        </ul>
        
        <h4>四、注意事项</h4>
        <ul>
        <li>程序需要管理员权限设置开机自启动</li>
        <li>建议将保存路径设置在非系统盘</li>
        <li>缓冲区大小根据内存情况合理设置</li>
        <li>从托盘右键菜单可快速退出程序</li>
        </ul>
        
        <hr>
        <p><i>提示: 要自定义此说明，请编辑项目根目录下的 HELP.md 文件。</i></p>
        """
        
        try:
            if os.path.exists(help_file):
                with open(help_file, 'r', encoding='utf-8') as f:
                    help_text = f.read()
                if not help_text.strip().startswith('<'):
                    help_text = f"<pre>{help_text}</pre>"
            else:
                help_text = default_content
        except Exception as e:
            help_text = f"<p style='color: red'>加载说明文档失败: {str(e)}</p>" + default_content
        
        self.help_browser.setHtml(help_text)
    
    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel
        
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.system_info_label = QLabel("系统就绪")
        self.system_info_label.setStyleSheet("color: #595959;")
        
        self.last_capture_label = QLabel("最后截图: 无")
        self.last_capture_label.setStyleSheet("color: #595959;")
        
        self.monitor_target_label = QLabel("监控目标: 整个显示器")
        self.monitor_target_label.setStyleSheet("color: #1890ff; font-weight: bold;")
        
        self.memory_usage_label = QLabel("内存使用: --")
        self.memory_usage_label.setStyleSheet("color: #595959;")
        
        status_layout.addWidget(self.system_info_label)
        status_layout.addStretch()
        status_layout.addWidget(self.last_capture_label)
        status_layout.addStretch()
        status_layout.addWidget(self.monitor_target_label)
        status_layout.addStretch()
        status_layout.addWidget(self.memory_usage_label)
        
        parent_layout.addWidget(status_frame)
    
    def connect_signals(self):
        """连接信号和槽"""
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.browse_btn.clicked.connect(self.on_browse_clicked)
        self.add_time_btn.clicked.connect(self.on_add_time_clicked)
        self.remove_time_btn.clicked.connect(self.on_remove_time_clicked)
        self.process_changed.connect(self.update_monitor_target)
        self.add_history_btn.clicked.connect(self.on_add_to_history)
        if hasattr(self, 'history_list'):
            self.history_list.itemClicked.connect(self.on_history_item_clicked)
        if hasattr(self, 'clear_log_btn'):
            self.clear_log_btn.clicked.connect(self.clear_log)
        if hasattr(self, 'save_log_btn'):
            self.save_log_btn.clicked.connect(self.save_log)
        if hasattr(self, 'refresh_log_btn'):
            self.refresh_log_btn.clicked.connect(self.update_log_display)
        
        # 实时设置变更连接
        self.interval_spin.valueChanged.connect(self.on_settings_changed)
        self.foreground_check.stateChanged.connect(self.on_settings_changed)
        self.ink_check.stateChanged.connect(self.on_settings_changed)
        self.process_edit.textChanged.connect(self.on_process_text_changed)
        self.auto_start_check.stateChanged.connect(self.on_auto_start_changed)
        self.silent_start_check.stateChanged.connect(self.on_silent_start_changed)
        self.minimize_to_tray_check.stateChanged.connect(self.on_minimize_to_tray_changed)
    
    def on_foreground_changed(self, state):
        """前台窗口检测状态改变"""
        is_enabled = (state == Qt.Checked)
        if is_enabled:
            self.process_status_label.setText("已启用前台窗口检测")
        else:
            self.process_status_label.setText("未启用前台窗口检测")
        self.update_monitor_target(self.process_edit.text())
    
    def on_process_text_changed(self, text):
        """进程输入文本改变"""
        self.process_changed.emit(text)
        self.check_processes()
    
    def on_add_to_history(self):
        """添加到历史记录"""
        process_text = self.process_edit.text().strip()
        if process_text:
            self.add_to_process_history(process_text)
            if self.log_manager:
                self.log_manager.add_log("INFO", f"已添加进程到历史记录: {process_text}")
    
    def on_history_item_clicked(self, item):
        """历史记录项被点击"""
        process_name = item.text()
        self.process_edit.setText(process_name)
        self.process_changed.emit(process_name)
    
    def check_processes(self):
        """检查输入的进程是否存在"""
        process_text = self.process_edit.text().strip()
        if not process_text:
            self.process_status_label.setText("未设置进程，将监控整个显示器")
            self.process_status_label.setStyleSheet("""
                QLabel {
                    color: #1890ff;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 4px;
                    background-color: #f0f2f5;
                }
            """)
            return
        
        # 分割进程名
        process_names = [name.strip() for name in process_text.split(',') if name.strip()]
        
        existing_processes = []
        missing_processes = []
        
        for process_name in process_names:
            if self.is_process_running(process_name):
                existing_processes.append(process_name)
            else:
                missing_processes.append(process_name)
        
        if not existing_processes and missing_processes:
            # 所有进程都不存在
            self.process_status_label.setText(f"进程不存在: {', '.join(missing_processes)}")
            self.process_status_label.setStyleSheet("""
                QLabel {
                    color: #ff4d4f;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 4px;
                    background-color: #fff2f0;
                }
            """)
        elif existing_processes and not missing_processes:
            # 所有进程都存在
            self.process_status_label.setText(f"进程存在: {', '.join(existing_processes)}")
            self.process_status_label.setStyleSheet("""
                QLabel {
                    color: #52c41a;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 4px;
                    background-color: #f6ffed;
                }
            """)
        else:
            # 部分存在
            status_text = f"存在: {', '.join(existing_processes)}"
            if missing_processes:
                status_text += f" | 不存在: {', '.join(missing_processes)}"
            self.process_status_label.setText(status_text)
            self.process_status_label.setStyleSheet("""
                QLabel {
                    color: #faad14;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 4px;
                    background-color: #fffbe6;
                }
            """)
    
    def is_process_running(self, process_name):
        """检查进程是否在运行"""
        try:
            # 确保进程名有.exe后缀
            if not process_name.lower().endswith('.exe'):
                process_name = f"{process_name}.exe"
            
            process_name = process_name.lower()
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_name:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return False
        except Exception as e:
            print(f"检查进程失败: {e}")
            return False
    
    def update_monitor_target(self, process_text):
        """更新监控目标显示"""
        process_text = process_text.strip()
        if not process_text or not self.foreground_check.isChecked():
            self.monitor_target_label.setText("监控目标: 整个显示器")
        else:
            process_names = [name.strip() for name in process_text.split(',') if name.strip()]
            if len(process_names) == 1:
                self.monitor_target_label.setText(f"监控目标: {process_names[0]}")
            else:
                self.monitor_target_label.setText(f"监控目标: {len(process_names)}个进程")
    
    def on_interval_changed(self, value):
        """截图间隔改变"""
        self.update_volume_estimate.emit()
        self.on_settings_changed()
    
    def on_buffer_size_changed(self, value):
        """缓冲区大小改变"""
        self.update_volume_estimate.emit()
    
    def on_auto_start_changed(self, state):
        """开机自启动设置改变"""
        is_enabled = (state == Qt.Checked)
        self.auto_start_changed.emit(is_enabled, self.silent_start_check.isChecked())
    
    def on_silent_start_changed(self, state):
        """静默启动设置改变"""
        is_enabled = (state == Qt.Checked)
        self.auto_start_changed.emit(self.auto_start_check.isChecked(), is_enabled)
    
    def on_minimize_to_tray_changed(self, state):
        """最小化到托盘设置改变"""
        pass
    
    def on_start_clicked(self):
        """开始监控按钮点击事件"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("运行中")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #52c41a;
                color: white;
                border: 1px solid #73d13d;
            }
        """)
        self.is_monitoring = True
        self.start_monitor_signal.emit()
        
        # 更新监控目标显示
        process_text = self.process_edit.text().strip()
        self.update_monitor_target(process_text)
    
    def on_stop_clicked(self):
        """停止监控按钮点击事件"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ff4d4f;
                color: white;
                border: 1px solid #ff7875;
            }
        """)
        self.is_monitoring = False
        self.stop_monitor_signal.emit()
    
    def on_browse_clicked(self):
        """浏览按钮点击事件"""
        path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if path:
            self.path_edit.setText(path)
    
    def on_add_time_clicked(self):
        """添加时间点按钮点击事件"""
        time_str = self.time_edit.time().toString("HH:mm")
        
        # 检查是否已存在
        for i in range(self.time_list.count()):
            if self.time_list.item(i).text() == time_str:
                return
        
        # 添加新时间点
        self.time_list.addItem(time_str)
        
        # 按时间排序
        self.sort_time_list()
    
    def on_remove_time_clicked(self):
        """移除时间点按钮点击事件"""
        current_row = self.time_list.currentRow()
        if current_row >= 0:
            self.time_list.takeItem(current_row)
    
    def sort_time_list(self):
        """对时间列表进行排序"""
        items = []
        for i in range(self.time_list.count()):
            items.append(self.time_list.item(i).text())
        
        items.sort()
        self.time_list.clear()
        for item in items:
            self.time_list.addItem(item)
    
    def on_settings_changed(self):
        """设置变更处理函数"""
        # 收集所有设置
        settings = self.get_settings()
        # 发射设置变更信号
        self.settings_changed.emit(settings)
    
    def get_settings(self):
        """获取所有设置"""
        settings = {
            'save_path': self.path_edit.text(),
            'capture_interval': self.interval_spin.value(),
            'buffer_size': self.buffer_size_spin.value(),
            'save_times': [self.time_list.item(i).text() 
                          for i in range(self.time_list.count())],
            'foreground_detection': self.foreground_check.isChecked(),
            'process_names': self.process_edit.text(),
            'ink_detection': self.ink_check.isChecked(),
            'auto_start': self.auto_start_check.isChecked(),
            'silent_start': self.silent_start_check.isChecked(),
            'minimize_to_tray': self.minimize_to_tray_check.isChecked()
        }
        return settings
    
    def load_settings(self, config):
        """从配置加载设置到GUI"""
        # 基本设置
        if 'save_path' in config:
            self.path_edit.setText(config['save_path'])
        
        if 'capture_interval' in config:
            self.interval_spin.setValue(int(config['capture_interval']))
        
        if 'buffer_size' in config:
            self.buffer_size_spin.setValue(int(config['buffer_size']))
        
        # 高级设置
        if 'foreground_detection' in config:
            self.foreground_check.setChecked(config['foreground_detection'])
        
        if 'ink_detection' in config:
            self.ink_check.setChecked(config['ink_detection'])
        
        if 'process_names' in config:
            self.process_edit.setText(config['process_names'])
            self.update_monitor_target(config['process_names'])
        
        # 时间设置
        if 'save_times' in config:
            self.time_list.clear()
            for time_str in config['save_times']:
                self.time_list.addItem(time_str)
        
        # 系统设置
        if 'auto_start' in config:
            self.auto_start_check.setChecked(config['auto_start'])
        
        if 'silent_start' in config:
            self.silent_start_check.setChecked(config['silent_start'])
        
        if 'minimize_to_tray' in config:
            self.minimize_to_tray_check.setChecked(config['minimize_to_tray'])
        
        # 更新体积估计
        self.update_volume_estimate.emit()
        # 检查进程
        self.check_processes()
    
    def update_buffer_progress(self, current, maximum=100):
        """更新缓冲区进度条"""
        if maximum <= 0:
            return
            
        current_int = int(current)
        maximum_int = int(maximum)
        
        percentage = int((current_int / maximum_int) * 100) if maximum_int > 0 else 0
        self.buffer_progress.setValue(percentage)
        self.buffer_progress.setFormat(f"缓冲区: {current_int}/{maximum_int}")
        self.buffer_label.setText(f"{current_int}/{maximum_int}")
        
        # 缓冲区超过80%显示警告
        if current_int / maximum_int >= 0.8:
            self.buffer_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #faad14;
                    border-radius: 3px;
                }
            """)
        else:
            self.buffer_progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #52c41a;
                    border-radius: 3px;
                }
            """)
    
    def update_capture_count(self, count):
        """更新截图数量"""
        self.capture_count_label.setText(str(count))
    
    def update_activity_status(self, is_active):
        """更新截图状态（保持方法兼容性）"""
        # 不再需要活动检测，但保持方法以兼容现有代码
        self.activity_label.setText("固定间隔")
        self.activity_label.setStyleSheet("""
            QLabel {
                background-color: #1890ff;
                color: white;
                border: 1px solid #40a9ff;
            }
        """)
    
    def update_last_capture(self, timestamp):
        """更新最后截图时间"""
        self.last_capture_label.setText(f"最后截图: {timestamp}")
    
    def update_memory_usage(self, usage):
        """更新内存使用情况"""
        self.memory_usage_label.setText(f"内存使用: {usage}")
    
    def update_next_save_time(self, time_str):
        """更新下次保存时间"""
        pass
    
    def update_log_display(self):
        """更新日志显示"""
        if self.log_manager:
            logs = self.log_manager.get_logs()
            self.log_browser.clear()
            
            for log in logs:
                timestamp, level, message = log
                color = "#52c41a" if level == "INFO" else "#ff4d4f" if level == "ERROR" else "#1890ff"
                self.log_browser.append(f'<span style="color:#8c8c8c">[{timestamp}]</span> '
                                       f'<span style="color:{color}"><b>{level}</b></span>: {message}')
            
            # 滚动到底部
            cursor = self.log_browser.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_browser.setTextCursor(cursor)
    
    def clear_log(self):
        """清空日志"""
        if self.log_manager:
            self.log_manager.clear_logs()
            self.update_log_display()
    
    def save_log(self):
        """保存日志到文件"""
        if self.log_manager:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存日志文件", "", "文本文件 (*.txt);;所有文件 (*)"
            )
            if file_path:
                success = self.log_manager.save_to_file(file_path)
                if success:
                    QMessageBox.information(self, "提示", "日志保存成功！")
                else:
                    QMessageBox.warning(self, "警告", "日志保存失败！")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.config.get('minimize_to_tray', True):
            self.hide()
            event.ignore()
        else:
            event.accept()
