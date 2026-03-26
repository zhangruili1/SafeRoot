#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理标签页
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# 尝试导入 PyQt5，失败时创建虚拟类
try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
        QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
        QMessageBox, QAbstractItemView, QTextEdit, QFrame, QSizePolicy, QSpacerItem
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QSize
    from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
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
    
    class QGroupBox:
        def __init__(self, title=""): pass
        def setLayout(self, layout): pass
    
    class QLabel:
        def __init__(self, text=""): pass
        def setText(self, text): pass
        def setTextInteractionFlags(self, flags): pass
        def setStyleSheet(self, style): pass
    
    class QPushButton:
        def __init__(self, text=""): pass
        def setIcon(self, icon): pass
        def setMinimumWidth(self, width): pass
        def clicked(self): pass
        def setProperty(self, key, value): pass
        def setEnabled(self, flag): pass
        def setCheckable(self, flag): pass
        def setChecked(self, flag): pass
    
    class QTableWidget:
        def __init__(self): pass
        def setColumnCount(self, count): pass
        def setHorizontalHeaderLabels(self, labels): pass
        def setAlternatingRowColors(self, flag): pass
        def setSelectionBehavior(self, behavior): pass
        def setEditTriggers(self, triggers): pass
        def setRowCount(self, count): pass
        def insertRow(self, row): pass
        def setItem(self, row, col, item): pass
        def setCellWidget(self, row, col, widget): pass
        def setSpan(self, row, col, rowspan, colspan): pass
        def horizontalHeader(self): return self
        def setSectionResizeMode(self, mode): pass
        def setStretchLastSection(self, flag): pass
        def selectionModel(self): return self
        def selectedRows(self): return []
        def rowCount(self): return 0
    
    class QTableWidgetItem:
        def __init__(self, text=""): pass
        def setFlags(self, flags): pass
        def setTextAlignment(self, alignment): pass
        def setData(self, role, value): pass
        def setText(self, text): pass
    
    class QHeaderView:
        def setSectionResizeMode(self, mode): pass
        def setStretchLastSection(self, flag): pass
    
    class QMessageBox:
        @staticmethod
        def information(parent, title, text): pass
        @staticmethod
        def warning(parent, title, text): pass
        @staticmethod
        def critical(parent, title, text): pass
        @staticmethod
        def question(parent, title, text, buttons, defaultButton): return 0
    
    class QAbstractItemView:
        SelectRows = 0
        NoEditTriggers = 0
    
    class QTextEdit:
        def __init__(self): pass
        def setPlaceholderText(self, text): pass
        def setMaximumHeight(self, height): pass
    
    class QFrame:
        def __init__(self): pass
        def setFrameShape(self, shape): pass
        def setFrameShadow(self, shadow): pass
    
    class QSizePolicy:
        def __init__(self): pass
    
    class QSpacerItem:
        def __init__(self): pass
    
    class Qt:
        Horizontal = 0
        AlignCenter = 0
        TextSelectableByMouse = 0
        ItemIsEditable = 0
        UserRole = 0
        AlignLeft = 0
        AlignRight = 0
    
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

# 导入核心管理器 - 处理导入路径问题
try:
    # 首先尝试从src.core导入
    from src.core.hosts_manager import HostsManager
    from src.core.rule_manager import RuleManager
except ImportError:
    try:
        # 如果失败，尝试将项目根目录添加到sys.path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core.hosts_manager import HostsManager
        from src.core.rule_manager import RuleManager
    except ImportError:
        try:
            # 最后尝试直接从core导入（如果src在路径中）
            from core.hosts_manager import HostsManager
            from core.rule_manager import RuleManager
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


class BackupTab(QWidget):
    """备份管理标签页"""
    
    # 信号定义
    backup_created = pyqtSignal(str)  # 参数：备份路径
    backup_restored = pyqtSignal(str)  # 参数：备份路径
    backup_deleted = pyqtSignal(str)  # 参数：备份路径
    hosts_reset_to_default = pyqtSignal()  # hosts文件重置为默认
    
    def __init__(self, hosts_manager: HostsManager, rule_manager: RuleManager, parent=None):
        """
        初始化备份管理标签页
        
        Args:
            hosts_manager: HostsManager实例
            rule_manager: RuleManager实例
            parent: 父部件
        """
        super().__init__(parent)
        
        self.hosts_manager = hosts_manager
        self.rule_manager = rule_manager
        
        self.init_ui()
        self.load_hosts_info()
        self.load_backup_list()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 1. 当前hosts信息显示区
        hosts_info_group = QGroupBox("当前hosts文件信息")
        hosts_info_layout = QFormLayout(hosts_info_group)
        
        # 文件路径
        self.lbl_hosts_path = QLabel()
        self.lbl_hosts_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hosts_info_layout.addRow("文件路径:", self.lbl_hosts_path)
        
        # 文件大小
        self.lbl_hosts_size = QLabel()
        hosts_info_layout.addRow("文件大小:", self.lbl_hosts_size)
        
        # 最后修改时间
        self.lbl_hosts_mtime = QLabel()
        hosts_info_layout.addRow("最后修改:", self.lbl_hosts_mtime)
        
        # 规则数量
        self.lbl_rule_count = QLabel()
        hosts_info_layout.addRow("规则数量:", self.lbl_rule_count)
        
        main_layout.addWidget(hosts_info_group)
        
        # 2. 备份列表
        backup_list_group = QGroupBox("备份列表")
        backup_list_layout = QVBoxLayout(backup_list_group)
        
        # 备份列表表格
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels([
            "备份时间", "备份类型", "规则数量", "文件大小", "操作"
        ])
        
        # 设置表格属性
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.horizontalHeader().setStretchLastSection(False)
        self.backup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 设置列宽
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 备份时间自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 备份类型
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 规则数量
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 文件大小
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 操作
        
        backup_list_layout.addWidget(self.backup_table)
        
        main_layout.addWidget(backup_list_group)
        
        # 3. 操作按钮区
        buttons_layout = QHBoxLayout()
        
        # 创建备份按钮
        self.btn_create_backup = QPushButton("创建备份")
        self.btn_create_backup.setIcon(QIcon.fromTheme("document-save-as"))
        self.btn_create_backup.setMinimumWidth(100)
        self.btn_create_backup.clicked.connect(self.create_backup)
        buttons_layout.addWidget(self.btn_create_backup)
        
        # 从备份还原按钮
        self.btn_restore_backup = QPushButton("从选中备份还原")
        self.btn_restore_backup.setIcon(QIcon.fromTheme("document-open"))
        self.btn_restore_backup.setMinimumWidth(120)
        self.btn_restore_backup.clicked.connect(self.restore_selected_backup)
        buttons_layout.addWidget(self.btn_restore_backup)
        
        # 重置为系统默认按钮
        self.btn_reset_default = QPushButton("重置为系统默认")
        self.btn_reset_default.setIcon(QIcon.fromTheme("edit-clear"))
        self.btn_reset_default.setMinimumWidth(120)
        self.btn_reset_default.clicked.connect(self.restore_to_default)
        buttons_layout.addWidget(self.btn_reset_default)
        
        # 删除选中备份按钮
        self.btn_delete_backup = QPushButton("删除选中备份")
        self.btn_delete_backup.setIcon(QIcon.fromTheme("edit-delete"))
        self.btn_delete_backup.setMinimumWidth(120)
        self.btn_delete_backup.clicked.connect(self.delete_selected_backup)
        buttons_layout.addWidget(self.btn_delete_backup)
        
        # 添加弹性空间
        buttons_layout.addStretch()
        
        # 刷新按钮
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setIcon(QIcon.fromTheme("view-refresh"))
        self.btn_refresh.setMinimumWidth(80)
        self.btn_refresh.clicked.connect(self.refresh_all)
        buttons_layout.addWidget(self.btn_refresh)
        
        main_layout.addLayout(buttons_layout)
    
    def load_hosts_info(self):
        """加载当前hosts文件信息"""
        try:
            hosts_path = self.hosts_manager.hosts_path
            
            # 文件路径
            self.lbl_hosts_path.setText(hosts_path)
            
            # 文件大小和修改时间
            if os.path.exists(hosts_path):
                size = os.path.getsize(hosts_path)
                mtime = os.path.getmtime(hosts_path)
                
                # 文件大小格式化
                if size < 1024:
                    size_text = f"{size} B"
                elif size < 1024 * 1024:
                    size_text = f"{size/1024:.1f} KB"
                else:
                    size_text = f"{size/(1024*1024):.1f} MB"
                
                self.lbl_hosts_size.setText(size_text)
                
                # 修改时间格式化
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                self.lbl_hosts_mtime.setText(mtime_str)
            else:
                self.lbl_hosts_size.setText("文件不存在")
                self.lbl_hosts_mtime.setText("-")
            
            # 规则数量
            rules = self.hosts_manager.get_rules()
            self.lbl_rule_count.setText(str(len(rules)))
            
        except Exception as e:
            self.lbl_hosts_path.setText(f"错误: {str(e)}")
            self.lbl_hosts_size.setText("-")
            self.lbl_hosts_mtime.setText("-")
            self.lbl_rule_count.setText("-")
    
    def load_backup_list(self):
        """加载备份列表"""
        try:
            backups = self.hosts_manager.get_backup_list()
            
            # 清空表格
            self.backup_table.setRowCount(0)
            
            for i, backup in enumerate(backups):
                self.backup_table.insertRow(i)
                
                # 备份时间列
                backup_time = backup.get('datetime', '')
                if backup_time:
                    try:
                        # 尝试解析ISO格式时间
                        dt = datetime.fromisoformat(backup_time.replace('Z', '+00:00'))
                        display_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        display_time = backup_time
                else:
                    display_time = backup.get('timestamp', '未知时间')
                
                time_item = QTableWidgetItem(display_time)
                time_item.setData(Qt.UserRole, backup['path'])  # 存储备份路径
                self.backup_table.setItem(i, 0, time_item)
                
                # 备份类型列
                # 根据文件名判断是自动备份还是手动备份
                backup_path = backup['path']
                filename = os.path.basename(backup_path)
                # 假设自动备份文件名包含 "auto_" 前缀
                backup_type = "自动" if "auto_" in filename else "手动"
                type_item = QTableWidgetItem(backup_type)
                self.backup_table.setItem(i, 1, type_item)
                
                # 规则数量列
                rule_count = backup.get('rule_count', 0)
                count_item = QTableWidgetItem(str(rule_count))
                count_item.setTextAlignment(Qt.AlignCenter)
                self.backup_table.setItem(i, 2, count_item)
                
                # 文件大小列
                size = backup.get('size', 0)
                if size < 1024:
                    size_text = f"{size} B"
                elif size < 1024 * 1024:
                    size_text = f"{size/1024:.1f} KB"
                else:
                    size_text = f"{size/(1024*1024):.1f} MB"
                
                size_item = QTableWidgetItem(size_text)
                size_item.setTextAlignment(Qt.AlignCenter)
                self.backup_table.setItem(i, 3, size_item)
                
                # 操作列 - 还原按钮
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setAlignment(Qt.AlignCenter)
                
                restore_btn = QPushButton("还原")
                restore_btn.setMinimumWidth(60)
                restore_btn.setProperty("backup_path", backup['path'])
                restore_btn.clicked.connect(self.on_restore_clicked)
                btn_layout.addWidget(restore_btn)
                
                self.backup_table.setCellWidget(i, 4, btn_widget)
            
            # 如果没有备份，显示提示
            if len(backups) == 0:
                self.backup_table.setRowCount(1)
                item = QTableWidgetItem("暂无备份")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.backup_table.setItem(0, 0, item)
                self.backup_table.setSpan(0, 0, 1, 5)  # 合并所有列
            
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载备份列表失败: {str(e)}")
    
    def get_selected_backup_paths(self) -> List[str]:
        """获取选中的备份路径"""
        selected_paths = []
        
        # 获取所有选中行的备份路径
        selected_rows = set(self.backup_table.selectionModel().selectedRows())
        
        for row in selected_rows:
            if row.row() < self.backup_table.rowCount():
                item = self.backup_table.item(row.row(), 0)
                if item:
                    backup_path = item.data(Qt.UserRole)
                    if backup_path:
                        selected_paths.append(backup_path)
        
        return selected_paths
    
    def create_backup(self):
        """创建手动备份"""
        try:
            backup_path = self.hosts_manager.backup()
            
            QMessageBox.information(self, "备份成功", f"备份已创建:\n{backup_path}")
            
            # 发射信号
            self.backup_created.emit(backup_path)
            
            # 刷新显示
            self.load_hosts_info()
            self.load_backup_list()
            
        except Exception as e:
            QMessageBox.critical(self, "备份失败", f"创建备份失败: {str(e)}")
    
    def restore_selected_backup(self):
        """从选中备份还原"""
        selected_paths = self.get_selected_backup_paths()
        
        if not selected_paths:
            QMessageBox.warning(self, "操作失败", "请先选择一个备份")
            return
        
        if len(selected_paths) > 1:
            QMessageBox.warning(self, "操作失败", "请只选择一个备份进行恢复")
            return
        
        backup_path = selected_paths[0]
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要从备份恢复 hosts 文件吗？\n备份路径: {backup_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.restore_from_backup(backup_path)
    
    def restore_from_backup(self, backup_path: str):
        """从指定备份还原"""
        try:
            success = self.hosts_manager.restore_from_backup(backup_path)
            
            if success:
                QMessageBox.information(self, "恢复成功", "hosts 文件已从备份恢复")
                
                # 发射信号
                self.backup_restored.emit(backup_path)
                
                # 刷新显示
                self.load_hosts_info()
                self.load_backup_list()
            else:
                QMessageBox.warning(self, "恢复失败", "恢复备份失败")
                
        except Exception as e:
            QMessageBox.critical(self, "恢复失败", f"恢复备份失败: {str(e)}")
    
    def restore_to_default(self):
        """重置hosts文件为系统初始状态（清空所有用户添加的规则）"""
        # 确认对话框
        reply = QMessageBox.warning(
            self, "确认重置",
            "确定要重置 hosts 文件为系统默认状态吗？\n\n"
            "这将删除所有用户添加的规则，只保留系统默认条目。\n"
            "此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 读取当前hosts文件
                current_content = self.hosts_manager.read_hosts()
                
                # 提取系统默认部分（假设系统默认条目在文件开头）
                # 这里需要更智能的解析，但暂时简单实现
                lines = current_content.splitlines()
                
                # 保留以 '#' 开头的注释行和空行，移除规则行
                default_lines = []
                for line in lines:
                    # 如果是空行或注释行，保留
                    if not line.strip() or line.strip().startswith('#'):
                        default_lines.append(line)
                    # 如果是规则行，检查是否是系统默认规则（如 localhost）
                    else:
                        # 暂时简单处理：只保留包含 "localhost" 的行
                        if "localhost" in line.lower():
                            default_lines.append(line)
                
                default_content = '\n'.join(default_lines)
                
                # 写入默认内容
                success = self.hosts_manager.write_hosts(default_content)
                
                if success:
                    # 清空数据库中的所有规则
                    self.rule_manager.clear_all_rules()
                    
                    QMessageBox.information(self, "重置成功", "hosts 文件已重置为系统默认状态")
                    
                    # 发射信号
                    self.hosts_reset_to_default.emit()
                    
                    # 刷新显示
                    self.load_hosts_info()
                    self.load_backup_list()
                else:
                    QMessageBox.warning(self, "重置失败", "重置 hosts 文件失败")
                    
            except Exception as e:
                QMessageBox.critical(self, "重置失败", f"重置 hosts 文件失败: {str(e)}")
    
    def delete_selected_backup(self):
        """删除选中备份"""
        selected_paths = self.get_selected_backup_paths()
        
        if not selected_paths:
            QMessageBox.warning(self, "操作失败", "请先选择要删除的备份")
            return
        
        # 确认对话框
        backup_count = len(selected_paths)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {backup_count} 个备份吗？\n"
            "此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = 0
            errors = []
            
            for backup_path in selected_paths:
                try:
                    # 删除备份文件
                    if os.path.exists(backup_path):
                        os.unlink(backup_path)
                    
                    # 删除元数据文件
                    meta_path = backup_path + '.meta'
                    if os.path.exists(meta_path):
                        os.unlink(meta_path)
                    
                    deleted_count += 1
                    
                except Exception as e:
                    errors.append(f"{backup_path}: {str(e)}")
            
            # 显示结果
            if errors:
                error_msg = f"成功删除 {deleted_count} 个备份，失败 {len(errors)} 个:\n\n"
                error_msg += "\n".join(errors)
                QMessageBox.warning(self, "部分失败", error_msg)
            else:
                QMessageBox.information(self, "删除成功", f"已成功删除 {deleted_count} 个备份")
            
            # 发射信号
            for backup_path in selected_paths:
                self.backup_deleted.emit(backup_path)
            
            # 刷新列表
            self.load_backup_list()
    
    def on_restore_clicked(self):
        """还原按钮点击事件"""
        sender = self.sender()
        if sender:
            backup_path = sender.property("backup_path")
            if backup_path:
                self.restore_from_backup(backup_path)
    
    def refresh_all(self):
        """刷新所有信息"""
        self.load_hosts_info()
        self.load_backup_list()
        
        QMessageBox.information(self, "刷新完成", "备份信息已刷新")


if __name__ == "__main__":
    # 测试代码
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建虚拟管理器
    class TestHostsManager:
        def __init__(self):
            self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        
        def get_backup_list(self):
            return [
                {
                    'path': '/tmp/hosts_20250325_143000.bak',
                    'datetime': '2025-03-25T14:30:00',
                    'size': 1024,
                    'rule_count': 5
                },
                {
                    'path': '/tmp/hosts_20250325_120000.bak',
                    'datetime': '2025-03-25T12:00:00',
                    'size': 2048,
                    'rule_count': 10
                }
            ]
        
        def read_hosts(self):
            return "# Test hosts file\n"
        
        def write_hosts(self, content):
            return True
        
        def backup(self):
            return "/tmp/test.bak"
        
        def restore_from_backup(self, path):
            return True
        
        def get_rules(self):
            return []
    
    class TestRuleManager:
        def clear_all_rules(self):
            return 0
    
    window = BackupTab(TestHostsManager(), TestRuleManager())
    window.setWindowTitle("备份管理测试")
    window.resize(800, 600)
    window.show()
    
    sys.exit(app.exec_())