#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置标签页
"""

import os
import sys
import json
import winreg
from typing import Dict, Any, Optional

# 尝试导入 PyQt5，失败时创建虚拟类
try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
        QLabel, QPushButton, QCheckBox, QLineEdit, QSpinBox,
        QMessageBox, QFileDialog, QFrame, QSizePolicy, QSpacerItem,
        QTextEdit, QScrollArea, QGridLayout
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
    from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QDesktopServices
except ImportError:
    # 创建虚拟类以允许导入
    class QWidget:
        def __init__(self, parent=None): pass
        def setLayout(self, layout): pass
        def setVisible(self, flag): pass
    
    class QVBoxLayout:
        def __init__(self, parent=None): pass
        def setContentsMargins(self, *args): pass
        def setSpacing(self, spacing): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass
        def addStretch(self): pass
    
    class QHBoxLayout:
        def __init__(self, parent=None): pass
        def setContentsMargins(self, *args): pass
        def setSpacing(self, spacing): pass
        def addWidget(self, widget): pass
        def addStretch(self): pass
        def setAlignment(self, alignment): pass
    
    class QFormLayout:
        def __init__(self, parent=None): pass
        def addRow(self, label, widget=None): pass
        def setSpacing(self, spacing): pass
    
    class QGroupBox:
        def __init__(self, title=""): pass
        def setLayout(self, layout): pass
    
    class QLabel:
        def __init__(self, text=""): pass
        def setText(self, text): pass
        def setTextInteractionFlags(self, flags): pass
        def setStyleSheet(self, style): pass
        def setOpenExternalLinks(self, flag): pass
    
    class QPushButton:
        def __init__(self, text=""): 
            self._clicked = pyqtSignal()
        def setIcon(self, icon): pass
        def setMinimumWidth(self, width): pass
        @property
        def clicked(self):
            return self._clicked
        def setProperty(self, key, value): pass
        def setEnabled(self, flag): pass
        def setCheckable(self, flag): pass
        def setChecked(self, flag): pass
    
    class QCheckBox:
        def __init__(self, text=""): 
            self._state_changed = pyqtSignal()
        def setChecked(self, flag): pass
        def isChecked(self): return False
        @property
        def stateChanged(self):
            return self._state_changed
    
    class QLineEdit:
        def __init__(self, text=""): 
            self._text_changed = pyqtSignal()
        def setText(self, text): pass
        def text(self): return ""
        def setPlaceholderText(self, text): pass
        def setReadOnly(self, flag): pass
        @property
        def textChanged(self):
            return self._text_changed
    
    class QSpinBox:
        def __init__(self): 
            self._value_changed = pyqtSignal()
        def setRange(self, min_val, max_val): pass
        def setValue(self, value): pass
        def value(self): return 0
        def setSuffix(self, suffix): pass
        @property
        def valueChanged(self):
            return self._value_changed
    
    class QMessageBox:
        @staticmethod
        def information(parent, title, text): pass
        @staticmethod
        def warning(parent, title, text): pass
        @staticmethod
        def critical(parent, title, text): pass
        @staticmethod
        def question(parent, title, text, buttons, defaultButton): return 0
    
    class QFileDialog:
        @staticmethod
        def getOpenFileName(parent, caption, directory, filter): return ("", "")
        @staticmethod
        def getExistingDirectory(parent, caption, directory): return ""
    
    class QFrame:
        def __init__(self): pass
        def setFrameShape(self, shape): pass
        def setFrameShadow(self, shadow): pass
    
    class QSizePolicy:
        def __init__(self): pass
    
    class QSpacerItem:
        def __init__(self): pass
    
    class QTextEdit:
        def __init__(self): pass
        def setPlaceholderText(self, text): pass
        def setMaximumHeight(self, height): pass
        def setReadOnly(self, flag): pass
    
    class QScrollArea:
        def __init__(self): pass
        def setWidget(self, widget): pass
        def setWidgetResizable(self, flag): pass
    
    class QGridLayout:
        def __init__(self, parent=None): pass
        def addWidget(self, widget, row, col, rowspan=1, colspan=1): pass
        def setColumnStretch(self, col, stretch): pass
    
    class Qt:
        Horizontal = 0
        Vertical = 0
        AlignCenter = 0
        TextSelectableByMouse = 0
        ItemIsEditable = 0
        UserRole = 0
        AlignLeft = 0
        AlignRight = 0
        ScrollBarAsNeeded = 0
    
    class pyqtSignal:
        def __init__(self, *args):
            self._args = args
        def emit(self, *args):
            pass
        def connect(self, slot):
            pass
    
    class QSize:
        def __init__(self, w=0, h=0): pass
    
    class QFont:
        def __init__(self): pass
    
    class QIcon:
        @staticmethod
        def fromTheme(theme): return QIcon()
    
    class QColor:
        def __init__(self): pass
    
    class QPalette:
        def __init__(self): pass
    
    class QTimer:
        def __init__(self): pass
        def start(self, interval): pass
        def stop(self): pass
        def timeout(self): pass
    
    class QDesktopServices:
        @staticmethod
        def openUrl(url): pass

# 导入常量
try:
    from constants import CONFIG_PATH, HOSTS_PATH, APP_NAME, APP_VERSION, LOG_PATH, UPDATE_CHECK_URL, UPDATE_CHECK_ENABLED
except ImportError:
    try:
        from src.constants import CONFIG_PATH, HOSTS_PATH, APP_NAME, APP_VERSION, LOG_PATH, UPDATE_CHECK_URL, UPDATE_CHECK_ENABLED
    except ImportError:
        # 默认值
        CONFIG_PATH = os.path.expandvars(r"%APPDATA%\SafeRoot\config.json")
        HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
        APP_NAME = "SafeRoot"
        APP_VERSION = "1.0.0"
        LOG_PATH = os.path.expandvars(r"%APPDATA%\SafeRoot\logs")
        UPDATE_CHECK_URL = "https://api.github.com/repos/saferoot/saferoot/releases/latest"
        UPDATE_CHECK_ENABLED = True


class CheckUpdateWorker(QThread):
    """后台检查更新工作线程"""
    
    # 信号定义
    update_available = pyqtSignal(str, str, str)  # latest_version, release_name, release_body
    already_latest = pyqtSignal(str)  # current_version
    network_error = pyqtSignal(str)  # error_message
    parse_error = pyqtSignal(str)  # error_message
    http_error = pyqtSignal(str)  # error_message
    check_finished = pyqtSignal()  # 检查完成
    
    def __init__(self, current_version: str, api_url: str):
        super().__init__()
        self.current_version = current_version
        self.api_url = api_url
    
    def run(self):
        """执行后台更新检查"""
        import urllib.request
        import urllib.error
        import json
        import ssl
        
        try:
            req = urllib.request.Request(
                self.api_url,
                headers={
                    'User-Agent': f'{APP_NAME}/{self.current_version}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_version = data.get('tag_name', '')
                    if latest_version and latest_version.startswith('v'):
                        latest_version = latest_version[1:]
                    release_name = data.get('name', '')
                    release_url = data.get('html_url', '')
                    release_body = data.get('body', '')[:500]
                    
                    if latest_version and SettingsTab._compare_versions_static(self.current_version, latest_version) < 0:
                        self.update_available.emit(latest_version, release_name or release_url, release_body)
                    else:
                        self.already_latest.emit(self.current_version)
                else:
                    self.http_error.emit(f"HTTP {response.status}: {response.reason}")
                    
        except urllib.error.URLError as e:
            self.network_error.emit(str(e))
        except json.JSONDecodeError as e:
            self.parse_error.emit(str(e))
        except Exception as e:
            self.network_error.emit(str(e))
        finally:
            self.check_finished.emit()


class SettingsTab(QWidget):
    """系统设置标签页"""
    
    # 信号定义
    settings_changed = pyqtSignal(dict)  # 设置变更时发射，参数为变更的设置字典
    auto_start_changed = pyqtSignal(bool)  # 开机自启动状态变更
    notification_changed = pyqtSignal(bool)  # 通知开关状态变更
    
    def __init__(self, hosts_manager=None, rule_manager=None, parent_window=None):
        super().__init__()
        
        self.hosts_manager = hosts_manager
        self.rule_manager = rule_manager
        self.parent_window = parent_window
        
        # 默认配置
        self.default_config = {
            "auto_start": False,
            "tray_minimize": True,
            "enable_notification": True,
            "custom_redirect_ip": "127.0.0.1",
            "backup_keep_count": 10,
            "log_keep_days": 30,
            "hosts_path": HOSTS_PATH
        }
        
        # 当前配置
        self.config = self.default_config.copy()
        
        # 初始化UI
        self.init_ui()
        
        # 加载配置
        self.load_config()
        
        # 应用配置到UI
        self.apply_config_to_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建滚动区域，防止内容过多
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(15)
        
        # 1. 通用设置组
        self.create_general_settings_group(content_layout)
        
        # 2. 高级设置组
        self.create_advanced_settings_group(content_layout)
        
        # 3. 关于组
        self.create_about_group(content_layout)
        
        # 添加弹性空间
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # 操作按钮
        self.create_action_buttons(main_layout)
    
    def create_general_settings_group(self, parent_layout):
        """创建通用设置组"""
        group = QGroupBox("通用设置")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # 开机自动启动
        self.cb_auto_start = QCheckBox("开机自动启动")
        self.cb_auto_start.stateChanged.connect(self.on_auto_start_changed)
        layout.addRow(self.cb_auto_start)
        
        # 最小化到系统托盘
        self.cb_tray_minimize = QCheckBox("最小化到系统托盘")
        self.cb_tray_minimize.stateChanged.connect(self.on_setting_changed)
        layout.addRow(self.cb_tray_minimize)
        
        # 屏蔽规则生效时显示通知
        self.cb_enable_notification = QCheckBox("屏蔽规则生效时显示通知")
        self.cb_enable_notification.stateChanged.connect(self.on_notification_changed)
        layout.addRow(self.cb_enable_notification)
        
        parent_layout.addWidget(group)
    
    def create_advanced_settings_group(self, parent_layout):
        """创建高级设置组"""
        group = QGroupBox("高级设置")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # 自定义指向IP
        self.edit_custom_ip = QLineEdit()
        self.edit_custom_ip.setPlaceholderText("127.0.0.1")
        self.edit_custom_ip.textChanged.connect(self.on_setting_changed)
        layout.addRow("自定义指向IP:", self.edit_custom_ip)
        
        # 备份保留数量
        self.spin_backup_keep = QSpinBox()
        self.spin_backup_keep.setRange(1, 50)
        self.spin_backup_keep.setSuffix(" 个")
        self.spin_backup_keep.valueChanged.connect(self.on_setting_changed)
        layout.addRow("备份保留数量:", self.spin_backup_keep)
        
        # 日志保留天数
        self.spin_log_keep = QSpinBox()
        self.spin_log_keep.setRange(1, 365)
        self.spin_log_keep.setSuffix(" 天")
        self.spin_log_keep.valueChanged.connect(self.on_setting_changed)
        layout.addRow("日志保留天数:", self.spin_log_keep)
        
        # Hosts文件路径
        hosts_widget = QWidget()
        hosts_layout = QHBoxLayout(hosts_widget)
        hosts_layout.setContentsMargins(0, 0, 0, 0)
        
        self.label_hosts_path = QLabel(HOSTS_PATH)
        self.label_hosts_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_hosts_path.setStyleSheet("padding: 4px; background-color: #f0f0f0; border-radius: 3px;")
        
        self.btn_change_hosts = QPushButton("更改...")
        self.btn_change_hosts.setMinimumWidth(80)
        self.btn_change_hosts.clicked.connect(self.on_change_hosts_path)
        
        hosts_layout.addWidget(self.label_hosts_path, 1)
        hosts_layout.addWidget(self.btn_change_hosts)
        
        layout.addRow("Hosts文件路径:", hosts_widget)
        
        parent_layout.addWidget(group)
    
    def create_about_group(self, parent_layout):
        """创建关于组"""
        group = QGroupBox("关于")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 版本信息
        version_text = f"""
        <div style="line-height: 1.5;">
            <b>{APP_NAME}</b><br/>
            版本: {APP_VERSION}<br/>
            <br/>
            描述: Windows hosts 文件管理工具<br/>
            作者: SafeRoot Team<br/>
        </div>
        """
        version_label = QLabel(version_text)
        version_label.setTextFormat(Qt.RichText)
        version_label.setOpenExternalLinks(True)
        layout.addWidget(version_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.btn_view_logs = QPushButton("查看日志")
        self.btn_view_logs.setIcon(QIcon.fromTheme("text-x-generic"))
        self.btn_view_logs.clicked.connect(self.on_view_logs)
        
        self.btn_check_update = QPushButton("检查更新")
        self.btn_check_update.setIcon(QIcon.fromTheme("system-software-update"))
        self.btn_check_update.clicked.connect(self.on_check_update)
        
        btn_layout.addWidget(self.btn_view_logs)
        btn_layout.addWidget(self.btn_check_update)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        parent_layout.addWidget(group)
    
    def create_action_buttons(self, parent_layout):
        """创建操作按钮"""
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        
        self.btn_save = QPushButton("保存设置")
        self.btn_save.setMinimumWidth(100)
        self.btn_save.clicked.connect(self.save_config)
        
        self.btn_reset = QPushButton("恢复默认")
        self.btn_reset.setMinimumWidth(100)
        self.btn_reset.clicked.connect(self.reset_config)
        
        self.btn_apply = QPushButton("立即应用")
        self.btn_apply.setMinimumWidth(100)
        self.btn_apply.clicked.connect(self.apply_config)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_save)
        
        parent_layout.addWidget(btn_widget)
    
    def load_config(self):
        """从配置文件加载设置"""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                # 合并配置，保留默认配置中但用户配置中没有的键
                for key in self.default_config:
                    if key in loaded_config:
                        self.config[key] = loaded_config[key]
            else:
                # 配置文件不存在，使用默认配置
                self.config = self.default_config.copy()
                
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置
            self.config = self.default_config.copy()
    
    def save_config(self):
        """保存设置到配置文件"""
        try:
            # 从UI更新配置
            self.update_config_from_ui()
            
            # 确保配置目录存在
            config_dir = os.path.dirname(CONFIG_PATH)
            os.makedirs(config_dir, exist_ok=True)
            
            # 保存到文件
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            # 发射设置变更信号
            self.settings_changed.emit(self.config)
            
            QMessageBox.information(self, "保存成功", "设置已保存到配置文件")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存设置失败: {str(e)}")
            return False
    
    def apply_config(self):
        """应用当前设置（立即生效）"""
        # 从UI更新配置
        self.update_config_from_ui()
        
        # 发射设置变更信号
        self.settings_changed.emit(self.config)
        
        QMessageBox.information(self, "应用成功", "设置已立即生效")
    
    def reset_config(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, "确认恢复默认",
            "确定要恢复默认设置吗？当前设置将会丢失。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config = self.default_config.copy()
            self.apply_config_to_ui()
            
            # 保存默认配置
            self.save_config()
            
            QMessageBox.information(self, "恢复成功", "已恢复为默认设置")
    
    def update_config_from_ui(self):
        """从UI控件更新配置字典"""
        self.config["auto_start"] = self.cb_auto_start.isChecked()
        self.config["tray_minimize"] = self.cb_tray_minimize.isChecked()
        self.config["enable_notification"] = self.cb_enable_notification.isChecked()
        self.config["custom_redirect_ip"] = self.edit_custom_ip.text().strip() or "127.0.0.1"
        self.config["backup_keep_count"] = self.spin_backup_keep.value()
        self.config["log_keep_days"] = self.spin_log_keep.value()
        self.config["hosts_path"] = self.label_hosts_path.text()
    
    def apply_config_to_ui(self):
        """将配置应用到UI控件"""
        self.cb_auto_start.setChecked(self.config["auto_start"])
        self.cb_tray_minimize.setChecked(self.config["tray_minimize"])
        self.cb_enable_notification.setChecked(self.config["enable_notification"])
        self.edit_custom_ip.setText(self.config["custom_redirect_ip"])
        self.spin_backup_keep.setValue(self.config["backup_keep_count"])
        self.spin_log_keep.setValue(self.config["log_keep_days"])
        self.label_hosts_path.setText(self.config["hosts_path"])
        
        # 应用开机自启动设置
        self.apply_auto_start_setting()
    
    def apply_auto_start_setting(self):
        """应用开机自启动设置（写入/删除注册表）"""
        # 仅Windows平台支持开机自启动
        if sys.platform != 'win32':
            print("开机自启动功能仅支持Windows平台")
            if self.parent_window:
                self.parent_window.status_bar.showMessage("开机自启动仅支持Windows", 3000)
            return
        
        try:
            app_path = sys.executable  # 获取Python解释器路径
            script_path = os.path.abspath(sys.argv[0])  # 获取脚本路径
            
            # 如果通过python脚本运行，则使用python解释器 + 脚本路径
            if script_path.endswith('.py'):
                startup_cmd = f'"{app_path}" "{script_path}"'
            else:
                # 如果是可执行文件，直接使用
                startup_cmd = f'"{script_path}"'
            
            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            if self.config["auto_start"]:
                # 写入注册表
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_cmd)
                print("开机自启动已启用")
            else:
                # 删除注册表项
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("开机自启动已禁用")
                except FileNotFoundError:
                    # 注册表项不存在，忽略
                    pass
            
            winreg.CloseKey(key)
            
        except Exception as e:
            print(f"设置开机自启动失败: {e}")
            # 显示错误信息但不中断程序
            if self.parent_window:
                self.parent_window.status_bar.showMessage(f"开机自启动设置失败: {e}", 5000)
    
    # ===== 事件处理函数 =====
    
    def on_auto_start_changed(self, state):
        """开机自启动状态变更"""
        self.config["auto_start"] = (state == Qt.Checked)
        self.auto_start_changed.emit(self.config["auto_start"])
        
        # 立即应用设置
        self.apply_auto_start_setting()
    
    def on_notification_changed(self, state):
        """通知开关状态变更"""
        self.config["enable_notification"] = (state == Qt.Checked)
        self.notification_changed.emit(self.config["enable_notification"])
    
    def on_setting_changed(self):
        """设置变更（通用处理）"""
        # 标记设置已变更
        self.btn_save.setEnabled(True)
        self.btn_apply.setEnabled(True)
    
    def on_change_hosts_path(self):
        """更改Hosts文件路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Hosts文件",
            os.path.dirname(HOSTS_PATH),
            "Hosts文件 (*)"
        )
        
        if file_path:
            # 警告用户谨慎操作
            reply = QMessageBox.warning(
                self,
                "警告",
                f"确定要更改Hosts文件路径吗？\n\n"
                f"新路径: {file_path}\n\n"
                f"注意：更改后需要重新启动应用才能生效。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.label_hosts_path.setText(file_path)
                self.config["hosts_path"] = file_path
                self.on_setting_changed()
    
    def on_view_logs(self):
        """查看日志文件"""
        try:
            if os.path.exists(LOG_PATH):
                # 打开日志目录
                QDesktopServices.openUrl(f"file:///{LOG_PATH}")
            else:
                QMessageBox.information(self, "日志目录", f"日志目录不存在: {LOG_PATH}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法打开日志目录: {str(e)}")
    
    def on_check_update(self):
        """检查更新（异步，不阻塞GUI）"""
        # 检查更新功能是否启用
        if not UPDATE_CHECK_ENABLED:
            QMessageBox.information(
                self,
                "检查更新",
                f"当前版本: {APP_VERSION}\n\n"
                "更新检查功能已禁用。"
            )
            return
        
        # 禁用按钮，防止重复点击
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("检查中...")
        
        # 创建后台工作线程
        self._update_worker = CheckUpdateWorker(APP_VERSION, UPDATE_CHECK_URL)
        
        # 连接信号
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.already_latest.connect(self._on_already_latest)
        self._update_worker.network_error.connect(self._on_update_network_error)
        self._update_worker.parse_error.connect(self._on_update_parse_error)
        self._update_worker.http_error.connect(self._on_update_http_error)
        self._update_worker.check_finished.connect(self._on_check_update_finished)
        
        # 启动后台线程
        self._update_worker.start()
    
    def _on_update_available(self, latest_version: str, release_name: str, release_body: str):
        """发现新版本"""
        current_version = APP_VERSION
        message = (
            f"当前版本: v{current_version}\n"
            f"最新版本: v{latest_version}\n\n"
        )
        if release_body:
            message += f"更新内容:\n{release_body}\n\n"
        message += "是否打开下载页面？"
        
        reply = QMessageBox.information(
            self,
            "发现新版本",
            message,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes and release_name:
            import webbrowser
            webbrowser.open(release_name)
    
    def _on_already_latest(self, current_version: str):
        """已是最新版本"""
        QMessageBox.information(
            self,
            "检查更新",
            f"当前版本: v{current_version}\n\n"
            "您已经使用的是最新版本。"
        )
    
    def _on_update_network_error(self, error_message: str):
        """网络错误"""
        QMessageBox.warning(
            self,
            "检查更新失败",
            f"无法连接到更新服务器:\n{error_message}\n\n"
            "请检查网络连接后重试。"
        )
    
    def _on_update_parse_error(self, error_message: str):
        """JSON解析错误"""
        QMessageBox.warning(
            self,
            "检查更新失败",
            f"服务器响应格式错误:\n{error_message}\n\n"
            "请稍后重试或手动检查更新。"
        )
    
    def _on_update_http_error(self, error_message: str):
        """HTTP错误"""
        QMessageBox.warning(
            self,
            "检查更新失败",
            f"服务器返回错误:\n{error_message}\n\n"
            "请稍后重试或手动检查更新。"
        )
    
    def _on_check_update_finished(self):
        """更新检查完成，恢复按钮状态"""
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("检查更新")
        self._update_worker = None
    
    @staticmethod
    def _compare_versions_static(v1: str, v2: str) -> int:
        """
        比较版本号（静态方法，供后台线程使用）
        
        Args:
            v1: 版本号1 (如 "1.0.0")
            v2: 版本号2 (如 "1.0.1")
        Returns:
            -1: v1 < v2
            0: v1 == v2
            1: v1 > v2
        """
        def parse_version(v):
            parts = []
            for part in v.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    # 处理非数字部分
                    parts.append(part)
            return parts
        
        v1_parts = parse_version(v1)
        v2_parts = parse_version(v2)
        
        # 比较每个部分
        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if isinstance(p1, int) and isinstance(p2, int):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            else:
                # 如果包含非数字部分，转为字符串比较
                str_p1 = str(p1)
                str_p2 = str(p2)
                if str_p1 < str_p2:
                    return -1
                elif str_p1 > str_p2:
                    return 1
        
        return 0
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号（实例方法）"""
        return self._compare_versions_static(v1, v2)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def set_config_value(self, key: str, value: Any):
        """设置配置值并更新UI"""
        if key in self.config:
            self.config[key] = value
            self.apply_config_to_ui()


if __name__ == "__main__":
    # 测试代码
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        
        # 创建虚拟管理器
        class DummyHostsManager:
            pass
        
        class DummyRuleManager:
            pass
        
        window = SettingsTab(DummyHostsManager(), DummyRuleManager(), None)
        window.setWindowTitle("系统设置 - 测试")
        window.resize(600, 500)
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"测试失败: {e}")