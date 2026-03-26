#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeRoot 主窗口类
"""

import os
import sys
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QCheckBox,
    QLineEdit, QLabel, QMessageBox, QFileDialog, QInputDialog,
    QHeaderView, QSplitter, QToolBar, QStatusBar, QComboBox,
    QSpinBox, QGroupBox, QFrame, QProgressBar, QAbstractItemView,
    QDialog, QDialogButtonBox, QFormLayout, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

# 导入核心管理器 - 处理导入路径问题
try:
    # 首先尝试从src.core导入
    from src.core.hosts_manager import HostsManager
    from src.core.rule_manager import RuleManager, validate_domain
    from src.core.logger import get_logger
except ImportError:
    try:
        # 如果失败，尝试将项目根目录添加到sys.path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core.hosts_manager import HostsManager
        from src.core.rule_manager import RuleManager, validate_domain
        from src.core.logger import get_logger
    except ImportError:
        try:
            # 最后尝试直接从core导入（如果src在路径中）
            from core.hosts_manager import HostsManager
            from core.rule_manager import RuleManager, validate_domain
            from core.logger import get_logger
        except ImportError as e:
            print(f"导入核心模块失败: {e}")
            # 创建虚拟管理器以允许UI加载
            class DummyHostsManager:
                def __init__(self): pass
                def read_hosts(self): return "# Dummy hosts file\n"
                def write_hosts(self, content): return True
                def backup(self): return "/tmp/dummy.bak"
                def restore_from_backup(self, path): return True
                def get_backup_list(self): return []
                def clean_old_backups(self, count): pass
                def add_rule(self, domain, redirect_to): return True
                def remove_rule(self, domain): return True
                def disable_rule(self, domain): return True
                def enable_rule(self, domain): return True
                def get_rules(self): return []
            
            class DummyRuleManager:
                def __init__(self): pass
                def get_all_rules(self, enabled_only=False): return []
                def add_rule(self, domain, redirect_to, remark): return True
                def remove_rule(self, rule_id): return True
                def update_rule(self, rule_id, **kwargs): return True
                def enable_rule(self, rule_id): return True
                def disable_rule(self, rule_id): return True
                def batch_delete(self, rule_ids): return 0
                def batch_enable(self, rule_ids): return 0
                def batch_disable(self, rule_ids): return 0
                def clear_all_rules(self): return 0
                def get_rule_count(self, enabled_only=False): return 0
                def close(self): pass
            
            HostsManager = DummyHostsManager
            RuleManager = DummyRuleManager
            validate_domain = lambda x: bool(x and isinstance(x, str))
            
            # 创建虚拟日志函数
            class DummyLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
                def log_operation(self, op, details="", success=True): pass
                def log_exception(self, op, exc): pass
            
            def get_logger():
                return DummyLogger()

# 导入对话框
try:
    from src.ui.add_rule_dialog import AddRuleDialog
except ImportError:
    try:
        from ui.add_rule_dialog import AddRuleDialog
    except ImportError:
        from add_rule_dialog import AddRuleDialog

# 导入备份标签页
try:
    from src.ui.backup_tab import BackupTab
except ImportError:
    try:
        from ui.backup_tab import BackupTab
    except ImportError:
        from backup_tab import BackupTab

# 导入设置标签页
try:
    from src.ui.settings_tab import SettingsTab
except ImportError:
    try:
        from ui.settings_tab import SettingsTab
    except ImportError:
        from settings_tab import SettingsTab















class AddRuleWorker(QThread):
    """后台添加规则工作线程"""

    finished = pyqtSignal(int, list, bool)  # success_count, failed_domains, is_batch
    error = pyqtSignal(str)  # 错误消息

    def __init__(self, rule_manager, hosts_manager, rules_data, is_batch=False):
        super().__init__()
        self.rule_manager = rule_manager
        self.hosts_manager = hosts_manager
        self.rules_data = rules_data
        self.is_batch = is_batch

    def run(self):
        success_count = 0
        failed_domains = []

        try:
            for rule_data in self.rules_data:
                domain = rule_data['domain']
                redirect_to = rule_data['redirect_to'] or '127.0.0.1'
                remark = rule_data['remark']

                if not validate_domain(domain):
                    failed_domains.append(f"{domain} (格式无效)")
                    continue

                success = self.rule_manager.add_rule(
                    domain, redirect_to, remark
                )

                if success:
                    hosts_success = self.hosts_manager.add_rule(
                        domain, redirect_to
                    )
                    if hosts_success:
                        success_count += 1
                    else:
                        failed_domains.append(f"{domain} (hosts写入失败)")
                else:
                    failed_domains.append(f"{domain} (已存在)")

            self.finished.emit(success_count, failed_domains, self.is_batch)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(success_count, failed_domains, self.is_batch)


class BatchOperationWorker(QThread):
    """后台批量操作工作线程"""
    
    # 定义信号
    progress = pyqtSignal(int, int)  # 当前进度，总数量
    finished = pyqtSignal(int, bool, str)  # 成功数量，是否完全成功，操作类型
    error = pyqtSignal(str)  # 错误消息
    
    def __init__(self, rule_manager, hosts_manager, rule_ids, operation_type):
        """初始化工作线程
        
        Args:
            rule_manager: 规则管理器
            hosts_manager: hosts文件管理器
            rule_ids: 规则ID列表
            operation_type: 操作类型 ('enable', 'disable', 'delete')
        """
        super().__init__()
        self.rule_manager = rule_manager
        self.hosts_manager = hosts_manager
        self.rule_ids = rule_ids
        self.operation_type = operation_type
        self.success_count = 0
    
    def run(self):
        """执行后台操作"""
        try:
            total = len(self.rule_ids)
            
            # 发送初始进度
            self.progress.emit(0, total)
            
            if self.operation_type == 'enable':
                # 批量启用规则
                self.success_count = self.rule_manager.batch_enable(self.rule_ids)
                
                if self.success_count > 0:
                    # 同步 hosts 文件
                    self._sync_hosts_with_db()
                
            elif self.operation_type == 'disable':
                # 批量禁用规则
                self.success_count = self.rule_manager.batch_disable(self.rule_ids)
                
                if self.success_count > 0:
                    # 同步 hosts 文件
                    self._sync_hosts_with_db()
                    
            elif self.operation_type == 'delete':
                # 批量删除规则
                self.success_count = self.rule_manager.batch_delete(self.rule_ids)
                
                if self.success_count > 0:
                    # 同步 hosts 文件
                    self._sync_hosts_with_db()
            
            # 发送完成进度
            self.progress.emit(total, total)
            
            # 操作完成，发送成功信号
            self.finished.emit(self.success_count, True, self.operation_type)
            
        except Exception as e:
            # 发生错误，发送错误信号
            self.error.emit(str(e))
            self.finished.emit(self.success_count, False, self.operation_type)
    
    def _sync_hosts_with_db(self):
        """同步 hosts 文件与数据库（后台线程中执行）"""
        try:
            # 读取当前 hosts 文件
            current_content = self.hosts_manager.read_hosts()
            lines = current_content.splitlines()
            
            # 获取所有启用的规则
            enabled_rules = self.rule_manager.get_all_rules(enabled_only=True)
            
            # 构建新的 hosts 文件内容
            new_lines = []
            
            # 首先添加系统默认内容（注释和空行）
            for line in lines:
                if (line.strip().startswith('#') and 
                    ('localhost' in line.lower() or 
                     'example' in line.lower() or
                     len(line.strip()) < 30)):
                    new_lines.append(line)
                elif not line.strip():
                    new_lines.append(line)
                else:
                    # 跳过用户添加的规则，我们将从数据库重新添加
                    continue
            
            # 添加启用的规则
            for rule in enabled_rules:
                new_lines.append(f"{rule['redirect_to']} {rule['domain']}")
            
            # 写入新的 hosts 文件
            new_content = '\n'.join(new_lines)
            self.hosts_manager.write_hosts(new_content)
            
        except Exception as e:
            raise Exception(f"同步 hosts 文件失败: {str(e)}")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化管理器
        self.hosts_manager = HostsManager()
        self.rule_manager = RuleManager()
        self.logger = get_logger("DEBUG")
        
        # 当前显示的规则
        self.current_rules = []
        self.selected_rules = set()
        
        # 后台操作相关
        self.current_worker = None
        self.operation_in_progress = False
        
        # 初始化UI
        self.init_ui()
        self.apply_styles()
        
        # 加载数据
        QTimer.singleShot(100, self.load_rules)
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("SafeRoot")
        self.resize(900, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加标签页
        self.tab_shield = self.create_shield_tab()
        self.tab_backup = self.create_backup_tab()
        self.tab_settings = self.create_settings_tab()
        
        self.tab_widget.addTab(self.tab_shield, "屏蔽列表")
        self.tab_widget.addTab(self.tab_backup, "备份管理")
        self.tab_widget.addTab(self.tab_settings, "系统设置")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def create_shield_tab(self) -> QWidget:
        """创建屏蔽列表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 工具栏
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_add = QPushButton("添加网址")
        self.btn_add.clicked.connect(self.on_add_rule)
        
        self.btn_import = QPushButton("批量导入")
        self.btn_import.clicked.connect(self.on_batch_import)
        
        self.btn_export = QPushButton("批量导出")
        self.btn_export.clicked.connect(self.on_batch_export)
        
        self.btn_restore_all = QPushButton("全部恢复")
        self.btn_restore_all.clicked.connect(self.on_clear_all)
        
        toolbar_layout.addWidget(self.btn_add)
        toolbar_layout.addWidget(self.btn_import)
        toolbar_layout.addWidget(self.btn_export)
        toolbar_layout.addWidget(self.btn_restore_all)
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar)
        
        # 统计信息
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        
        self.lbl_stats = QLabel("生效规则: 0")
        stats_layout.addWidget(self.lbl_stats)
        stats_layout.addStretch()
        
        layout.addWidget(stats_widget)
        
        # 搜索框
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索域名...")
        self.search_edit.textChanged.connect(self.filter_rules)
        
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_edit)
        search_layout.addStretch()
        
        layout.addWidget(search_widget)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "域名", "指向地址", "状态", "操作"])
        
        # 设置表格属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        # 批量操作工具栏
        batch_widget = QWidget()
        batch_layout = QHBoxLayout(batch_widget)
        
        self.btn_select_all = QCheckBox("全选")
        self.btn_select_all.stateChanged.connect(self.on_select_all)
        
        self.btn_batch_delete = QPushButton("批量删除")
        self.btn_batch_delete.clicked.connect(self.on_batch_delete)
        
        self.btn_batch_enable = QPushButton("批量启用")
        self.btn_batch_enable.clicked.connect(self.on_batch_enable)
        
        self.btn_batch_disable = QPushButton("批量禁用")
        self.btn_batch_disable.clicked.connect(self.on_batch_disable)
        
        batch_layout.addWidget(self.btn_select_all)
        batch_layout.addWidget(self.btn_batch_delete)
        batch_layout.addWidget(self.btn_batch_enable)
        batch_layout.addWidget(self.btn_batch_disable)
        batch_layout.addStretch()
        
        layout.addWidget(batch_widget)
        
        return tab
    
    def create_backup_tab(self) -> QWidget:
        """创建备份管理标签页"""
        # 创建BackupTab实例
        self.backup_tab = BackupTab(self.hosts_manager, self.rule_manager, self)
        
        # 连接信号到槽函数
        self.backup_tab.backup_created.connect(self.on_backup_created)
        self.backup_tab.backup_restored.connect(self.on_backup_restored)
        self.backup_tab.backup_deleted.connect(self.on_backup_deleted)
        self.backup_tab.hosts_reset_to_default.connect(self.on_hosts_reset_to_default)
        
        return self.backup_tab
    
    def create_settings_tab(self) -> QWidget:
        """创建系统设置标签页"""
        # 创建SettingsTab实例
        self.settings_tab = SettingsTab(self.hosts_manager, self.rule_manager, self)
        
        # 连接信号到槽函数
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        self.settings_tab.auto_start_changed.connect(self.on_auto_start_changed)
        self.settings_tab.notification_changed.connect(self.on_notification_changed)
        
        return self.settings_tab
    
    def apply_styles(self):
        """应用样式表"""
        style_sheet = """
        /* 主窗口 */
        QMainWindow {
            background-color: #F5F5F5;
        }
        
        /* 标签页 */
        QTabWidget::pane {
            border: 1px solid #CCCCCC;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #E8E8E8;
            border: 1px solid #CCCCCC;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #2D5F9E;
            color: white;
        }
        
        QTabBar::tab:hover {
            background-color: #4A7FC1;
            color: white;
        }
        
        /* 按钮 */
        QPushButton {
            background-color: #2D5F9E;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #4A7FC1;
        }
        
        QPushButton:pressed {
            background-color: #1A4A7D;
        }
        
        QPushButton:disabled {
            background-color: #CCCCCC;
            color: #666666;
        }
        
        /* 表格 */
        QTableWidget {
            border: 1px solid #CCCCCC;
            alternate-background-color: #F9F9F9;
            selection-background-color: #E8F0FE;
            selection-color: #2D5F9E;
        }
        
        QTableWidget::item {
            padding: 4px;
        }
        
        QHeaderView::section {
            background-color: #2D5F9E;
            color: white;
            padding: 6px;
            border: none;
            font-weight: bold;
        }
        
        /* 输入框 */
        QLineEdit {
            border: 1px solid #CCCCCC;
            padding: 4px;
            border-radius: 3px;
        }
        
        QLineEdit:focus {
            border-color: #2D5F9E;
        }
        
        /* 复选框 */
        QCheckBox {
            spacing: 5px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        
        /* 组合框 */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #CCCCCC;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: #2D5F9E;
            color: white;
        }
        """
        
        self.setStyleSheet(style_sheet)
    
    # === 屏蔽列表页功能 ===
    
    def load_rules(self):
        """加载规则到表格"""
        try:
            # 从数据库获取所有规则
            self.current_rules = self.rule_manager.get_all_rules()
            
            # 清空表格
            self.table.setRowCount(0)
            
            # 添加规则到表格
            for i, rule in enumerate(self.current_rules):
                self.table.insertRow(i)
                
                # 选择列 - 复选框
                check_widget = QWidget()
                check_layout = QHBoxLayout(check_widget)
                check_layout.setAlignment(Qt.AlignCenter)
                check_layout.setContentsMargins(0, 0, 0, 0)
                
                checkbox = QCheckBox()
                checkbox.setProperty("rule_id", rule['id'])
                checkbox.stateChanged.connect(self.on_rule_selected)
                check_layout.addWidget(checkbox)
                
                self.table.setCellWidget(i, 0, check_widget)
                
                # 域名列
                domain_item = QTableWidgetItem(rule['domain'])
                domain_item.setFlags(domain_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 1, domain_item)
                
                # 指向地址列
                ip_item = QTableWidgetItem(rule['redirect_to'])
                ip_item.setFlags(ip_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 2, ip_item)
                
                # 状态列 - 开关按钮
                status_widget = QWidget()
                status_layout = QHBoxLayout(status_widget)
                status_layout.setAlignment(Qt.AlignCenter)
                status_layout.setContentsMargins(0, 0, 0, 0)
                
                status_checkbox = QCheckBox()
                status_checkbox.setChecked(bool(rule['enabled']))
                status_checkbox.setProperty("rule_id", rule['id'])
                status_checkbox.stateChanged.connect(self.on_toggle_rule_ui)
                status_layout.addWidget(status_checkbox)
                
                self.table.setCellWidget(i, 3, status_widget)
                
                # 操作列 - 删除按钮
                delete_widget = QWidget()
                delete_layout = QHBoxLayout(delete_widget)
                delete_layout.setAlignment(Qt.AlignCenter)
                delete_layout.setContentsMargins(0, 0, 0, 0)
                
                delete_btn = QPushButton("删除")
                delete_btn.setProperty("rule_id", rule['id'])
                delete_btn.clicked.connect(self.on_delete_rule_ui)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #DC3545;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #C82333;
                    }
                """)
                delete_layout.addWidget(delete_btn)
                
                self.table.setCellWidget(i, 4, delete_widget)
            
            # 刷新统计信息
            self.refresh_stats()
            self.status_bar.showMessage(f"已加载 {len(self.current_rules)} 条规则", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载规则失败: {str(e)}")
    
    def filter_rules(self, keyword: str):
        """搜索过滤规则"""
        keyword = keyword.strip().lower()
        
        if not keyword:
            # 显示所有行
            for i in range(self.table.rowCount()):
                self.table.setRowHidden(i, False)
            return
        
        # 隐藏不匹配的行
        for i in range(self.table.rowCount()):
            domain_item = self.table.item(i, 1)
            if domain_item and keyword in domain_item.text().lower():
                self.table.setRowHidden(i, False)
            else:
                self.table.setRowHidden(i, True)
    
    def refresh_stats(self):
        """刷新统计信息"""
        try:
            # 获取生效规则数量
            enabled_count = self.rule_manager.get_rule_count(enabled_only=True)
            total_count = self.rule_manager.get_rule_count()
            
            self.lbl_stats.setText(f"生效规则: {enabled_count} / 总计: {total_count}")
            
        except Exception as e:
            self.lbl_stats.setText("统计信息加载失败")
    
    def on_add_rule(self):
        """添加规则"""
        self.logger.info("开始添加规则流程")
        # 获取现有域名列表用于重复检查
        existing_rules = self.rule_manager.get_all_rules()
        existing_domains = [rule['domain'] for rule in existing_rules]
        self.logger.debug(f"现有规则数量: {len(existing_rules)}，域名列表: {existing_domains}")
        
        # 创建对话框
        dialog = AddRuleDialog(self, existing_domains)
        self.logger.info("创建添加规则对话框")
        if dialog.exec_() == QDialog.Accepted:
            self.logger.info("用户确认添加规则")
            is_batch, rules_data = dialog.get_result()
            self.logger.info(f"获取规则结果: 批量模式={is_batch}, 规则数据数量={len(rules_data)}")
            
            if not rules_data:
                self.logger.warning("没有有效的规则数据")
                QMessageBox.warning(self, "输入错误", "没有有效的规则数据")
                return
            
            # 如果已经有操作在进行中，不执行新操作
            if self.operation_in_progress:
                QMessageBox.warning(self, "操作进行中", "当前有操作正在进行，请稍候")
                return
            
            # 创建后台工作线程
            worker = AddRuleWorker(
                self.rule_manager,
                self.hosts_manager,
                rules_data,
                is_batch
            )
            
            # 连接信号与槽
            worker.finished.connect(self._on_add_rule_finished)
            worker.error.connect(self._on_add_rule_error)
            
            # 设置当前工作线程和状态
            self.current_worker = worker
            self.operation_in_progress = True
            
            # 禁用相关按钮，避免重复操作
            self._set_batch_buttons_enabled(False)
            
            # 更新状态栏
            total = len(rules_data)
            if is_batch:
                self.status_bar.showMessage(f"正在批量添加 {total} 条规则...")
            else:
                self.status_bar.showMessage("正在添加规则...")
            
            # 启动后台线程
            worker.start()

    def _on_add_rule_finished(self, success_count: int, failed_domains: list, is_batch: bool):
        """添加规则完成回调（主线程执行）"""
        # 重新启用按钮
        self._set_batch_buttons_enabled(True)
        
        if success_count > 0:
            self.logger.info(f"成功添加 {success_count} 条规则")
            # 重新加载规则
            self.load_rules()
            
            if is_batch:
                self.status_bar.showMessage(
                    f"批量添加完成: {success_count} 条成功, {len(failed_domains)} 条失败", 5000
                )
        else:
            self.logger.warning("没有规则添加成功")
        
        # 如果有失败的域名，显示警告
        if failed_domains:
            self.logger.warning(f"有 {len(failed_domains)} 条规则添加失败: {failed_domains}")
            if is_batch:
                warning_msg = f"以下域名添加失败:\n" + "\n".join(failed_domains)
                QMessageBox.warning(self, "部分失败", warning_msg)
            else:
                QMessageBox.warning(self, "添加失败", failed_domains[0])
        else:
            self.logger.info("所有规则添加成功")

        # 安全清理后台线程
        if self.current_worker:
            worker = self.current_worker
            self.current_worker = None
            self.operation_in_progress = False
            worker.deleteLater()

    def _on_add_rule_error(self, error_message: str):
        """添加规则错误回调（主线程执行）"""
        # 重新启用按钮
        self._set_batch_buttons_enabled(True)
        
        # 安全清理后台线程
        if self.current_worker:
            worker = self.current_worker
            self.current_worker = None
            self.operation_in_progress = False
            worker.deleteLater()
        
        # 显示错误消息
        self.logger.error(f"添加规则发生异常: {error_message}")
        QMessageBox.critical(self, "添加失败", f"添加规则失败: {error_message}")
        self.status_bar.showMessage("添加规则失败", 3000)
    
    def on_delete_rule(self, rule_id: str):
        """删除规则"""
        try:
            # 从数据库获取规则信息
            rules = self.rule_manager.get_all_rules()
            rule = next((r for r in rules if r['id'] == rule_id), None)
            
            if not rule:
                return False
            
            # 从数据库删除
            success = self.rule_manager.remove_rule(rule_id)
            
            if success:
                # 从 hosts 文件删除
                self.hosts_manager.remove_rule(rule['domain'])
            
            return success
            
        except Exception as e:
            raise Exception(f"删除规则失败: {str(e)}")
    
    def on_delete_rule_ui(self):
        """删除规则（UI触发）"""
        rule_id = self.sender().property("rule_id")
        
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除此规则吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.on_delete_rule(rule_id)
                
                if success:
                    # 重新加载规则
                    self.load_rules()
                    self.status_bar.showMessage("规则已删除", 3000)
                else:
                    QMessageBox.warning(self, "删除失败", "规则删除失败")
                    
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除规则失败: {str(e)}")
    
    def on_toggle_rule(self, rule_id: str, enabled: bool):
        """切换规则状态"""
        try:
            # 从数据库获取规则信息
            rules = self.rule_manager.get_all_rules()
            rule = next((r for r in rules if r['id'] == rule_id), None)
            
            if not rule:
                return False
            
            # 更新数据库
            if enabled:
                db_success = self.rule_manager.enable_rule(rule_id)
                if db_success:
                    # 添加到 hosts 文件
                    hosts_success = self.hosts_manager.add_rule(
                        rule['domain'],
                        rule['redirect_to']
                    )
                    return hosts_success
            else:
                db_success = self.rule_manager.disable_rule(rule_id)
                if db_success:
                    # 从 hosts 文件禁用
                    hosts_success = self.hosts_manager.disable_rule(rule['domain'])
                    return hosts_success
            
            return False
            
        except Exception as e:
            raise Exception(f"切换规则状态失败: {str(e)}")
    
    def on_toggle_rule_ui(self, state: int):
        """切换规则状态（UI触发）"""
        checkbox = self.sender()
        rule_id = checkbox.property("rule_id")
        enabled = state == Qt.Checked
        
        try:
            success = self.on_toggle_rule(rule_id, enabled)
            
            if success:
                self.status_bar.showMessage(
                    f"规则已{'启用' if enabled else '禁用'}", 
                    3000
                )
                self.refresh_stats()
            else:
                # 恢复原来的状态
                checkbox.blockSignals(True)
                checkbox.setChecked(not enabled)
                checkbox.blockSignals(False)
                QMessageBox.warning(self, "操作失败", "切换规则状态失败")
                
        except Exception as e:
            # 恢复原来的状态
            checkbox.blockSignals(True)
            checkbox.setChecked(not enabled)
            checkbox.blockSignals(False)
            QMessageBox.critical(self, "操作失败", f"切换规则状态失败: {str(e)}")
    
    def on_select_all(self, state: int):
        """全选/取消全选"""
        checked = state == Qt.Checked
        
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(checked)
                    checkbox.blockSignals(False)
                    
                    rule_id = checkbox.property("rule_id")
                    if checked:
                        self.selected_rules.add(rule_id)
                    else:
                        self.selected_rules.discard(rule_id)
    
    def on_rule_selected(self, state: int):
        """规则选中状态变化"""
        checkbox = self.sender()
        rule_id = checkbox.property("rule_id")
        
        if state == Qt.Checked:
            self.selected_rules.add(rule_id)
        else:
            self.selected_rules.discard(rule_id)
    
    def on_batch_delete(self):
        """批量删除"""
        if not self.selected_rules:
            QMessageBox.warning(self, "操作失败", "请先选择要删除的规则")
            return
        
        # 如果已经有操作在进行中，不执行新操作
        if self.operation_in_progress:
            QMessageBox.warning(self, "操作进行中", "当前有批量操作正在进行，请稍候")
            return
        
        reply = QMessageBox.question(
            self, "确认批量删除",
            f"确定要删除选中的 {len(self.selected_rules)} 条规则吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 创建后台工作线程
            worker = BatchOperationWorker(
                self.rule_manager,
                self.hosts_manager,
                list(self.selected_rules),
                'delete'
            )
            
            # 连接信号与槽
            worker.progress.connect(self._on_batch_operation_progress)
            worker.finished.connect(self._on_batch_operation_finished)
            worker.error.connect(self._on_batch_operation_error)
            
            # 设置当前工作线程和状态
            self.current_worker = worker
            self.operation_in_progress = True
            
            # 禁用相关按钮，避免重复操作
            self._set_batch_buttons_enabled(False)
            
            # 更新状态栏
            total = len(self.selected_rules)
            self.status_bar.showMessage(f"正在批量删除 {total} 条规则... (0/{total})")
            
            # 启动后台线程
            worker.start()
    
    def on_batch_enable(self):
        """批量启用"""
        if not self.selected_rules:
            QMessageBox.warning(self, "操作失败", "请先选择要启用的规则")
            return
        
        # 如果已经有操作在进行中，不执行新操作
        if self.operation_in_progress:
            QMessageBox.warning(self, "操作进行中", "当前有批量操作正在进行，请稍候")
            return
        
        # 创建后台工作线程
        worker = BatchOperationWorker(
            self.rule_manager,
            self.hosts_manager,
            list(self.selected_rules),
            'enable'
        )
        
        # 连接信号与槽
        worker.progress.connect(self._on_batch_operation_progress)
        worker.finished.connect(self._on_batch_operation_finished)
        worker.error.connect(self._on_batch_operation_error)
        
        # 设置当前工作线程和状态
        self.current_worker = worker
        self.operation_in_progress = True
        
        # 禁用相关按钮，避免重复操作
        self._set_batch_buttons_enabled(False)
        
        # 更新状态栏
        self.status_bar.showMessage("正在批量启用规则...")
        
        # 启动后台线程
        worker.start()
        
        # 显示进度提示
        total = len(self.selected_rules)
        self.status_bar.showMessage(f"正在批量启用 {total} 条规则... (0/{total})")
    
    def _on_batch_operation_progress(self, current: int, total: int):
        """处理批量操作进度更新"""
        self.status_bar.showMessage(f"正在批量操作... ({current}/{total})")
    
    def _on_batch_operation_finished(self, success_count: int, success: bool, operation_type: str):
        """处理批量操作完成信号"""
        # 重新启用按钮
        self._set_batch_buttons_enabled(True)
        
        if success and success_count > 0:
            # 操作成功，刷新UI
            if operation_type in ['enable', 'disable']:
                # 刷新统计信息
                self.refresh_stats()
            
            # 重新加载规则列表
            self.load_rules()
            
            # 显示成功消息
            operation_name = {'enable': '启用', 'disable': '禁用', 'delete': '删除'}.get(operation_type, '操作')
            self.status_bar.showMessage(f"已{operation_name} {success_count} 条规则", 5000)
            
            # 清空选择（如果是删除操作）
            if operation_type == 'delete':
                self.selected_rules.clear()
                self.btn_select_all.setChecked(False)
                
        else:
            # 操作失败或没有规则被处理
            if success_count == 0:
                QMessageBox.warning(self, "操作失败", f"批量{operation_type}失败，没有规则被处理")
            else:
                QMessageBox.warning(self, "操作失败", f"批量{operation_type}操作完成，但部分规则处理失败")
        
        # 安全清理后台线程
        if self.current_worker:
            worker = self.current_worker
            self.current_worker = None
            self.operation_in_progress = False
            worker.deleteLater()
    
    def _on_batch_operation_error(self, error_message: str):
        """处理批量操作错误信号"""
        # 重新启用按钮
        self._set_batch_buttons_enabled(True)
        
        # 安全清理后台线程
        if self.current_worker:
            worker = self.current_worker
            self.current_worker = None
            self.operation_in_progress = False
            worker.deleteLater()
        
        # 显示错误消息
        QMessageBox.critical(self, "操作错误", f"批量操作发生错误: {error_message}")
        
        # 更新状态栏
        self.status_bar.showMessage("批量操作失败", 3000)
    
    def _set_batch_buttons_enabled(self, enabled: bool):
        """启用或禁用批量操作按钮"""
        if hasattr(self, 'btn_batch_enable'):
            self.btn_batch_enable.setEnabled(enabled)
        if hasattr(self, 'btn_batch_disable'):
            self.btn_batch_disable.setEnabled(enabled)
        if hasattr(self, 'btn_batch_delete'):
            self.btn_batch_delete.setEnabled(enabled)
        if hasattr(self, 'btn_select_all'):
            self.btn_select_all.setEnabled(enabled)
    
    def on_batch_disable(self):
        """批量禁用"""
        if not self.selected_rules:
            QMessageBox.warning(self, "操作失败", "请先选择要禁用的规则")
            return
        
        # 如果已经有操作在进行中，不执行新操作
        if self.operation_in_progress:
            QMessageBox.warning(self, "操作进行中", "当前有批量操作正在进行，请稍候")
            return
        
        # 创建后台工作线程
        worker = BatchOperationWorker(
            self.rule_manager,
            self.hosts_manager,
            list(self.selected_rules),
            'disable'
        )
        
        # 连接信号与槽
        worker.progress.connect(self._on_batch_operation_progress)
        worker.finished.connect(self._on_batch_operation_finished)
        worker.error.connect(self._on_batch_operation_error)
        
        # 设置当前工作线程和状态
        self.current_worker = worker
        self.operation_in_progress = True
        
        # 禁用相关按钮，避免重复操作
        self._set_batch_buttons_enabled(False)
        
        # 更新状态栏
        total = len(self.selected_rules)
        self.status_bar.showMessage(f"正在批量禁用 {total} 条规则... (0/{total})")
        
        # 启动后台线程
        worker.start()
    
    def on_batch_import(self):
        """批量导入"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "",
            "文本文件 (*.txt);;CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                success_count, failed_domains = self.rule_manager.import_from_file(file_path)
                
                if success_count > 0:
                    # 重新加载 hosts 文件
                    self.sync_hosts_with_db()
                    
                    # 重新加载规则
                    self.load_rules()
                    
                    msg = f"成功导入 {success_count} 条规则"
                    if failed_domains:
                        msg += f"，失败 {len(failed_domains)} 条"
                    
                    QMessageBox.information(self, "导入成功", msg)
                    self.status_bar.showMessage(msg, 5000)
                else:
                    QMessageBox.warning(self, "导入失败", "没有规则被导入")
                    
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入规则失败: {str(e)}")
    
    def on_batch_export(self):
        """批量导出"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出文件", "",
            "文本文件 (*.txt);;CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                # 如果选择了规则，导出选中的，否则导出所有
                if self.selected_rules:
                    rule_ids = list(self.selected_rules)
                else:
                    rule_ids = None
                
                success = self.rule_manager.export_to_file(file_path, rule_ids)
                
                if success:
                    QMessageBox.information(self, "导出成功", "规则导出成功")
                    self.status_bar.showMessage("规则已导出", 3000)
                else:
                    QMessageBox.warning(self, "导出失败", "规则导出失败")
                    
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出规则失败: {str(e)}")
    
    def on_clear_all(self):
        """全部恢复（清空所有规则）"""
        reply = QMessageBox.question(
            self, "确认全部恢复",
            "确定要清空所有规则并恢复 hosts 文件吗？\n此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QDialog.Accepted:
            try:
                # 备份当前 hosts 文件
                backup_path = self.hosts_manager.backup()
                
                # 清空数据库
                deleted_count = self.rule_manager.clear_all_rules()
                
                # 重新读取 hosts 文件内容，只保留系统默认内容
                content = self.hosts_manager.read_hosts()
                lines = content.splitlines()
                
                # 保留系统默认的注释和空行
                keep_lines = []
                for line in lines:
                    # 保留系统默认注释和空行
                    if (line.strip().startswith('#') and 
                        ('localhost' in line.lower() or 
                         'example' in line.lower() or
                         len(line.strip()) < 30)):
                        keep_lines.append(line)
                    elif not line.strip():
                        keep_lines.append(line)
                
                # 写入清理后的 hosts 文件
                new_content = '\n'.join(keep_lines)
                self.hosts_manager.write_hosts(new_content)
                
                # 重新加载规则
                self.load_rules()
                
                msg = f"已清空 {deleted_count} 条规则，hosts 文件已恢复"
                QMessageBox.information(self, "操作成功", msg)
                self.status_bar.showMessage(msg, 5000)
                
            except Exception as e:
                QMessageBox.critical(self, "操作失败", f"全部恢复失败: {str(e)}")
    
    def sync_hosts_with_db(self):
        """同步 hosts 文件与数据库"""
        try:
            # 读取当前 hosts 文件
            current_content = self.hosts_manager.read_hosts()
            lines = current_content.splitlines()
            
            # 获取所有启用的规则
            enabled_rules = self.rule_manager.get_all_rules(enabled_only=True)
            
            # 构建新的 hosts 文件内容
            new_lines = []
            
            # 首先添加系统默认内容（注释和空行）
            for line in lines:
                if (line.strip().startswith('#') and 
                    ('localhost' in line.lower() or 
                     'example' in line.lower() or
                     len(line.strip()) < 30)):
                    new_lines.append(line)
                elif not line.strip():
                    new_lines.append(line)
                else:
                    # 跳过用户添加的规则，我们将从数据库重新添加
                    continue
            
            # 添加启用的规则
            for rule in enabled_rules:
                new_lines.append(f"{rule['redirect_to']} {rule['domain']}")
            
            # 写入新的 hosts 文件
            new_content = '\n'.join(new_lines)
            self.hosts_manager.write_hosts(new_content)
            
        except Exception as e:
            raise Exception(f"同步 hosts 文件失败: {str(e)}")
    
    # === 备份管理页功能 ===
    
    def on_backup_created(self, backup_path: str):
        """备份创建信号处理"""
        self.status_bar.showMessage(f"备份已创建: {backup_path}", 3000)
        # 刷新规则列表
        self.load_rules()
    
    def on_backup_restored(self, backup_path: str):
        """备份恢复信号处理"""
        self.status_bar.showMessage(f"已从备份恢复: {backup_path}", 3000)
        # 重新解析 hosts 文件，更新数据库
        self.sync_db_with_hosts()
        # 刷新规则列表
        self.load_rules()
    
    def on_backup_deleted(self, backup_path: str):
        """备份删除信号处理"""
        self.status_bar.showMessage(f"备份已删除: {backup_path}", 3000)
    
    def on_hosts_reset_to_default(self):
        """hosts文件重置为默认信号处理"""
        self.status_bar.showMessage("hosts文件已重置为系统默认", 3000)
        # 清空数据库中的所有规则
        self.rule_manager.clear_all_rules()
        # 刷新规则列表
        self.load_rules()
    
    def load_backups(self):
        """加载备份列表（兼容性方法，调用BackupTab的加载方法）"""
        if hasattr(self, 'backup_tab') and self.backup_tab:
            try:
                self.backup_tab.load_backup_list()
                self.status_bar.showMessage("备份列表已刷新", 3000)
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载备份列表失败: {str(e)}")
        else:
            # 如果BackupTab不存在，使用旧逻辑（兼容性）
            try:
                backups = self.hosts_manager.get_backup_list()
                self.status_bar.showMessage(f"已加载 {len(backups)} 个备份", 3000)
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载备份列表失败: {str(e)}")
    
    def on_create_backup(self):
        """创建备份（兼容性方法，调用BackupTab的创建方法）"""
        if hasattr(self, 'backup_tab') and self.backup_tab:
            self.backup_tab.create_backup()
        else:
            # 如果BackupTab不存在，使用旧逻辑（兼容性）
            try:
                backup_path = self.hosts_manager.backup()
                QMessageBox.information(self, "备份成功", f"备份已创建: {backup_path}")
                self.status_bar.showMessage("备份创建成功", 3000)
                self.load_backups()
            except Exception as e:
                QMessageBox.critical(self, "备份失败", f"创建备份失败: {str(e)}")
    
    def on_restore_backup(self):
        """恢复选中备份（兼容性方法，调用BackupTab的恢复方法）"""
        if hasattr(self, 'backup_tab') and self.backup_tab:
            self.backup_tab.restore_selected_backup()
        else:
            # 如果BackupTab不存在，使用旧逻辑（兼容性）
            # 注意：旧逻辑依赖于self.backup_table，可能不存在
            QMessageBox.warning(self, "操作失败", "备份管理功能不可用，请重启应用")
    
    def on_delete_backup(self):
        """删除选中备份（兼容性方法，调用BackupTab的删除方法）"""
        if hasattr(self, 'backup_tab') and self.backup_tab:
            self.backup_tab.delete_selected_backup()
        else:
            # 如果BackupTab不存在，使用旧逻辑（兼容性）
            # 注意：旧逻辑依赖于self.backup_table，可能不存在
            QMessageBox.warning(self, "操作失败", "备份管理功能不可用，请重启应用")
    
    def on_clean_backups(self):
        """清理旧备份（兼容性方法，暂时保留旧逻辑）"""
        # 注意：BackupTab中没有清理旧备份的UI，所以保留旧逻辑
        keep_count, ok = QInputDialog.getInt(
            self, "清理备份",
            "保留最新备份数量:", 10, 1, 100
        )
        
        if ok:
            try:
                self.hosts_manager.clean_old_backups(keep_count)
                
                QMessageBox.information(self, "清理成功", f"已清理旧备份，保留 {keep_count} 个最新备份")
                
                # 刷新备份列表
                self.load_backups()
                
            except Exception as e:
                QMessageBox.critical(self, "清理失败", f"清理备份失败: {str(e)}")
    
    def sync_db_with_hosts(self):
        """根据 hosts 文件更新数据库"""
        try:
            # 获取 hosts 文件中的所有规则
            hosts_rules = self.hosts_manager.get_rules()
            
            # 获取数据库中的所有规则
            db_rules = self.rule_manager.get_all_rules()
            
            # 更新数据库中的启用状态
            for db_rule in db_rules:
                # 在 hosts 文件中查找对应的规则
                hosts_rule = next(
                    (r for r in hosts_rules if r['domain'] == db_rule['domain']),
                    None
                )
                
                if hosts_rule:
                    # 如果存在，更新启用状态
                    if hosts_rule['enabled'] != bool(db_rule['enabled']):
                        if hosts_rule['enabled']:
                            self.rule_manager.enable_rule(db_rule['id'])
                        else:
                            self.rule_manager.disable_rule(db_rule['id'])
                else:
                    # 如果在 hosts 文件中不存在，禁用数据库中的规则
                    if db_rule['enabled']:
                        self.rule_manager.disable_rule(db_rule['id'])
            
        except Exception as e:
            raise Exception(f"更新数据库失败: {str(e)}")
    
    # === 系统设置页功能 ===
    
    def on_settings_changed(self, config: dict):
        """设置变更信号处理"""
        # 更新主窗口中的配置引用
        self.current_config = config
        self.status_bar.showMessage("设置已应用", 3000)
    
    def on_auto_start_changed(self, enabled: bool):
        """开机自启动状态变更信号处理"""
        self.status_bar.showMessage(f"开机自启动 {'已启用' if enabled else '已禁用'}", 3000)
    
    def on_notification_changed(self, enabled: bool):
        """通知开关状态变更信号处理"""
        self.status_bar.showMessage(f"通知 {'已启用' if enabled else '已禁用'}", 3000)
    
    def on_save_settings(self):
        """保存设置（兼容性方法，调用SettingsTab的保存方法）"""
        if hasattr(self, 'settings_tab') and self.settings_tab:
            self.settings_tab.save_config()
        else:
            # 如果SettingsTab不存在，使用旧逻辑（兼容性）
            try:
                QMessageBox.information(self, "保存成功", "设置已保存")
                self.status_bar.showMessage("设置已保存", 3000)
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存设置失败: {str(e)}")
    
    def on_reset_settings(self):
        """恢复默认设置（兼容性方法，调用SettingsTab的恢复方法）"""
        if hasattr(self, 'settings_tab') and self.settings_tab:
            self.settings_tab.reset_config()
        else:
            # 如果SettingsTab不存在，使用旧逻辑（兼容性）
            reply = QMessageBox.question(
                self, "确认恢复默认",
                "确定要恢复默认设置吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QDialog.Accepted:
                try:
                    # 恢复默认值
                    self.cb_auto_backup.setChecked(True)
                    self.spin_keep_backups.setValue(10)
                    self.cb_check_update.setChecked(True)
                    self.edit_default_ip.setText("127.0.0.1")
                    self.combo_log_level.setCurrentText("INFO")
                    
                    QMessageBox.information(self, "恢复成功", "设置已恢复为默认值")
                    self.status_bar.showMessage("设置已恢复", 3000)
                    
                except Exception as e:
                    QMessageBox.critical(self, "恢复失败", f"恢复设置失败: {str(e)}")
    
    # === 标签页切换事件 ===
    
    def tab_changed(self, index: int):
        """标签页切换事件"""
        if index == 0:  # 屏蔽列表
            self.load_rules()
        elif index == 1:  # 备份管理
            self.load_backups()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 等待后台操作完成
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.quit()
            self.current_worker.wait(3000)  # 最多等待3秒
        
        # 清理资源
        if hasattr(self, 'rule_manager'):
            self.rule_manager.close()
        
        event.accept()


if __name__ == "__main__":
    # 测试代码
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())