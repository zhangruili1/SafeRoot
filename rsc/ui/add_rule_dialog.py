#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加网址弹窗 - 支持单条和批量模式
"""

import os
import sys
import re
from typing import List, Tuple, Optional, Dict, Any

# 尝试导入 PyQt5，失败时创建虚拟类
try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
        QLineEdit, QTextEdit, QPushButton, QLabel, QCheckBox, QScrollArea,
        QWidget, QMessageBox, QFrame, QSizePolicy, QSpacerItem
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
    from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor, QIntValidator
except ImportError:
    # 创建虚拟类以允许导入
    class QDialog:
        def __init__(self, parent=None): pass
        def exec_(self): return 0
        def setWindowTitle(self, title): pass
        def setFixedSize(self, w, h): pass
        def setModal(self, flag): pass
        def setLayout(self, layout): pass
    
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QFormLayout: pass
    class QGroupBox: pass
    class QLineEdit:
        def __init__(self): pass
        def setPlaceholderText(self, text): pass
        def setClearButtonEnabled(self, flag): pass
        def textChanged(self): pass
        def blockSignals(self, flag): return False
        def setText(self, text): pass
        def setProperty(self, key, value): pass
        def style(self): return self
        def polish(self, widget): pass
        def text(self): return ""
    class QTextEdit:
        def __init__(self): pass
        def setPlaceholderText(self, text): pass
        def setMaximumHeight(self, h): pass
        def setReadOnly(self, flag): pass
        def setStyleSheet(self, style): pass
        def toPlainText(self): return ""
        def textChanged(self): pass
        def setText(self, text): pass
    class QPushButton:
        def __init__(self, text=""): pass
        def setCheckable(self, flag): pass
        def setChecked(self, flag): pass
        def setMinimumWidth(self, w): pass
        def clicked(self): pass
        def setObjectName(self, name): pass
        def setEnabled(self, flag): pass
    class QLabel:
        def __init__(self, text=""): pass
        def setStyleSheet(self, style): pass
        def setText(self, text): pass
    class QCheckBox: pass
    class QScrollArea: pass
    class QWidget:
        def __init__(self, parent=None): pass
        def setVisible(self, flag): pass
        def setLayout(self, layout): pass
    class QMessageBox:
        @staticmethod
        def warning(parent, title, text): pass
    class QFrame:
        HLine = 0
        Sunken = 0
        def setFrameShape(self, shape): pass
        def setFrameShadow(self, shadow): pass
    class QSizePolicy: pass
    class QSpacerItem: pass
    
    class Qt:
        Horizontal = 0
        AlignCenter = 0
    
    class pyqtSignal:
        def __init__(self, *args):
            self._args = args
        def emit(self, *args):
            pass
        def connect(self, slot):
            pass
    
    class QSize: pass
    class QTimer: pass
    class QFont: pass
    class QPalette: pass
    class QColor: pass
    class QTextCursor: pass
    class QIntValidator: pass

# 导入验证函数和常量
try:
    from src.core.rule_manager import validate_domain
    from src.core.logger import get_logger
    from constants import APP_NAME
except ImportError:
    try:
        # 尝试将项目根目录添加到sys.path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core.rule_manager import validate_domain
        from src.core.logger import get_logger
        from constants import APP_NAME
    except ImportError:
        try:
            from core.rule_manager import validate_domain
            from core.logger import get_logger
            from constants import APP_NAME
        except ImportError:
            # 创建虚拟函数以允许UI加载
            def validate_domain(domain: str) -> bool:
                """虚拟域名验证函数"""
                if not domain or not isinstance(domain, str):
                    return False
                # 简单检查：至少包含一个点号，且不包含空格
                return '.' in domain and ' ' not in domain
            
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
            
            APP_NAME = "SafeRoot"


def extract_domain_from_url(url: str) -> str:
    """
    从URL中提取域名
    
    Args:
        url: 完整的URL或域名
        
    Returns:
        提取后的域名，如果无效则返回空字符串
    """
    if not url or not isinstance(url, str):
        return ""
    
    # 去除前后空白
    url = url.strip()
    
    # 如果已经是域名格式（不包含协议），直接返回
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$', url):
        return url
    
    # 尝试提取协议部分
    # 移除http://, https://, ftp://等
    url = re.sub(r'^[a-zA-Z]+://', '', url)
    
    # 移除路径部分
    url = re.sub(r'[/?#].*$', '', url)
    
    # 移除端口部分
    url = re.sub(r':\d+$', '', url)
    
    # 保留完整子域名（不剥离 www. 前缀，否则无法正确屏蔽 www 子域）
    
    return url if url else ""


class AddRuleDialog(QDialog):
    """添加网址规则对话框"""
    
    # 信号：当域名输入变化时发出，用于实时校验
    domain_changed = pyqtSignal(str)
    # 信号：当批量模式切换时发出
    mode_changed = pyqtSignal(bool)  # True=批量模式
    
    def __init__(self, parent=None, existing_domains: List[str] = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            existing_domains: 已存在的域名列表，用于重复检查
        """
        super().__init__(parent)
        
        self.logger = get_logger("DEBUG")
        self.logger.debug(f"AddRuleDialog 初始化，已有域名数量: {len(existing_domains or [])}")
        
        self.existing_domains = existing_domains or []
        self.is_batch_mode = False
        self.batch_domains = []  # 批量模式下解析的域名列表
        self.duplicate_domains = []  # 重复的域名列表
        
        self.init_ui()
        self.setup_signals()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f"{APP_NAME} - 添加屏蔽规则")
        self.setFixedSize(400, 300)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 模式切换区域
        mode_layout = QHBoxLayout()
        mode_label = QLabel("添加模式:")
        mode_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(mode_label)
        
        mode_layout.addStretch()
        
        self.single_mode_btn = QPushButton("单条添加")
        self.single_mode_btn.setCheckable(True)
        self.single_mode_btn.setChecked(not self.is_batch_mode)
        self.single_mode_btn.setMinimumWidth(80)
        
        self.batch_mode_btn = QPushButton("批量添加")
        self.batch_mode_btn.setCheckable(True)
        self.batch_mode_btn.setChecked(self.is_batch_mode)
        self.batch_mode_btn.setMinimumWidth(80)
        
        mode_layout.addWidget(self.single_mode_btn)
        mode_layout.addWidget(self.batch_mode_btn)
        
        main_layout.addLayout(mode_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # 单条模式容器
        self.single_container = QWidget()
        single_layout = QVBoxLayout()
        single_layout.setContentsMargins(0, 0, 0, 0)
        
        # 网站地址输入
        form_layout = QFormLayout()
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("例如: example.com 或 https://www.example.com")
        self.domain_input.setClearButtonEnabled(True)
        form_layout.addRow("网站地址:", self.domain_input)
        
        # 提示标签
        self.hint_label = QLabel("支持直接粘贴完整URL，系统会自动提取域名")
        self.hint_label.setStyleSheet("color: gray; font-size: 10pt;")
        single_layout.addWidget(self.hint_label)
        
        single_layout.addLayout(form_layout)
        
        # 校验结果标签
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #D32F2F; font-size: 10pt;")
        single_layout.addWidget(self.validation_label)
        
        # 可选配置区域（可折叠）
        self.advanced_group = QGroupBox("高级配置 (可选)")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        self.advanced_group.setStyleSheet("QGroupBox::title { subcontrol-origin: margin; }")
        
        advanced_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setText("0.0.0.0")
        self.ip_input.setPlaceholderText("指向的IP地址")
        advanced_layout.addRow("指向IP:", self.ip_input)
        
        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("备注信息（可选）")
        advanced_layout.addRow("备注:", self.remark_input)
        
        self.advanced_group.setLayout(advanced_layout)
        single_layout.addWidget(self.advanced_group)
        
        single_layout.addStretch()
        self.single_container.setLayout(single_layout)
        
        # 批量模式容器
        self.batch_container = QWidget()
        batch_layout = QVBoxLayout()
        batch_layout.setContentsMargins(0, 0, 0, 0)
        
        # 批量输入区域
        batch_input_label = QLabel("每行输入一个域名或URL:")
        batch_input_label.setStyleSheet("font-weight: bold;")
        batch_layout.addWidget(batch_input_label)
        
        self.batch_textedit = QTextEdit()
        self.batch_textedit.setPlaceholderText("每行一个域名或URL，例如:\nexample.com\nhttps://www.google.com\nfacebook.com")
        self.batch_textedit.setMaximumHeight(120)
        batch_layout.addWidget(self.batch_textedit)
        
        # 批量模式提示
        batch_hint_label = QLabel("系统会自动提取每行的域名，并过滤重复项")
        batch_hint_label.setStyleSheet("color: gray; font-size: 10pt;")
        batch_layout.addWidget(batch_hint_label)
        
        # 批量预览区域
        self.batch_preview_label = QLabel("有效域名: 0 个 | 重复域名: 0 个")
        self.batch_preview_label.setStyleSheet("font-weight: bold; color: #2D5F9E;")
        batch_layout.addWidget(self.batch_preview_label)
        
        # 预览文本框（只读）
        self.preview_textedit = QTextEdit()
        self.preview_textedit.setReadOnly(True)
        self.preview_textedit.setMaximumHeight(80)
        self.preview_textedit.setStyleSheet("background-color: #F5F5F5; border: 1px solid #DDD;")
        batch_layout.addWidget(self.preview_textedit)
        
        batch_layout.addStretch()
        self.batch_container.setLayout(batch_layout)
        
        # 初始显示单条模式
        self.batch_container.setVisible(False)
        
        main_layout.addWidget(self.single_container)
        main_layout.addWidget(self.batch_container)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(80)
        
        self.confirm_btn = QPushButton("确认添加")
        self.confirm_btn.setMinimumWidth(80)
        self.confirm_btn.setEnabled(False)  # 初始禁用
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.confirm_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 应用样式
        self.apply_styles()
        
    def apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            
            QLabel {
                color: #333333;
            }
            
            QLineEdit, QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 5px;
                background-color: #FFFFFF;
                selection-background-color: #2D5F9E;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #2D5F9E;
            }
            
            QLineEdit[error="true"] {
                border: 1px solid #D32F2F;
                background-color: #FFEBEE;
            }
            
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: normal;
            }
            
            QPushButton:hover {
                background-color: #E8E8E8;
                border-color: #999999;
            }
            
            QPushButton:pressed {
                background-color: #D5D5D5;
            }
            
            QPushButton:checked {
                background-color: #2D5F9E;
                color: white;
                border-color: #1E4A7E;
            }
            
            QPushButton#confirm_btn {
                background-color: #2D5F9E;
                color: white;
                border-color: #1E4A7E;
                font-weight: bold;
            }
            
            QPushButton#confirm_btn:hover {
                background-color: #3B6FB0;
                border-color: #2D5F9E;
            }
            
            QPushButton#confirm_btn:pressed {
                background-color: #1E4A7E;
            }
            
            QPushButton#confirm_btn:disabled {
                background-color: #CCCCCC;
                color: #666666;
                border-color: #BBBBBB;
            }
            
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 为确认按钮设置对象名以便样式生效
        self.confirm_btn.setObjectName("confirm_btn")
        
    def setup_signals(self):
        """连接信号和槽"""
        # 模式切换
        self.single_mode_btn.clicked.connect(lambda: self.switch_mode(False))
        self.batch_mode_btn.clicked.connect(lambda: self.switch_mode(True))
        
        # 单条模式输入变化
        self.domain_input.textChanged.connect(self.on_single_domain_changed)
        self.domain_input.textChanged.connect(self.update_confirm_button)
        
        # 批量模式输入变化
        self.batch_textedit.textChanged.connect(self.on_batch_text_changed)
        
        # 按钮点击
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self.accept)
        
        # 高级配置区域切换
        self.advanced_group.toggled.connect(self.on_advanced_toggled)
        
        # 初始校验
        self.on_single_domain_changed(self.domain_input.text())
        
    def switch_mode(self, is_batch: bool):
        """
        切换单条/批量模式
        
        Args:
            is_batch: 是否为批量模式
        """
        self.logger.debug(f"切换模式请求: is_batch={is_batch}, 当前模式: {self.is_batch_mode}")
        if self.is_batch_mode == is_batch:
            self.logger.debug("模式未改变，忽略")
            return
            
        self.is_batch_mode = is_batch
        self.logger.info(f"切换到{'批量' if is_batch else '单条'}模式")
        
        # 更新按钮状态
        self.single_mode_btn.setChecked(not is_batch)
        self.batch_mode_btn.setChecked(is_batch)
        
        # 显示/隐藏对应容器
        self.single_container.setVisible(not is_batch)
        self.batch_container.setVisible(is_batch)
        
        # 发出信号
        self.mode_changed.emit(is_batch)
        
        # 更新确认按钮状态
        self.update_confirm_button()
        
    def on_single_domain_changed(self, text: str):
        """
        单条模式域名输入变化处理
        
        Args:
            text: 输入的文本
        """
        self.logger.debug(f"单条模式域名输入变化: text='{text}'")
        # 如果输入为空，清除错误状态
        if not text.strip():
            self.logger.debug("输入为空，清除错误状态")
            self.domain_input.setProperty("error", False)
            self.domain_input.style().polish(self.domain_input)
            self.validation_label.setText("")
            return
            
        # 提取域名
        extracted = extract_domain_from_url(text)
        self.logger.debug(f"提取域名结果: extracted='{extracted}'")
        if extracted and extracted != text:
            # 自动更新输入框内容
            self.domain_input.blockSignals(True)
            self.domain_input.setText(extracted)
            self.domain_input.blockSignals(False)
            
        # 验证域名
        is_valid = validate_domain(extracted) if extracted else False
        self.logger.debug(f"域名验证结果: is_valid={is_valid}")
        
        # 检查重复
        is_duplicate = extracted in self.existing_domains if extracted else False
        self.logger.debug(f"重复检查结果: is_duplicate={is_duplicate}")
        
        # 更新输入框样式
        self.domain_input.setProperty("error", not is_valid or is_duplicate)
        self.domain_input.style().polish(self.domain_input)
        
        # 更新验证标签
        if not extracted:
            self.validation_label.setText("请输入有效的域名或URL")
            self.logger.debug("域名提取失败")
        elif not is_valid:
            self.validation_label.setText("域名格式无效")
            self.logger.debug("域名格式无效")
        elif is_duplicate:
            self.validation_label.setText(f"域名 '{extracted}' 已存在")
            self.logger.debug(f"域名重复: '{extracted}'")
        else:
            self.validation_label.setText("✓ 域名格式正确")
            self.validation_label.setStyleSheet("color: #388E3C; font-size: 10pt;")
            self.logger.debug(f"域名有效且不重复: '{extracted}'")
            
    def on_batch_text_changed(self):
        """批量模式文本变化处理"""
        text = self.batch_textedit.toPlainText().strip()
        self.logger.debug(f"批量模式文本变化: text长度={len(text)}")
        if not text:
            self.logger.debug("批量文本为空，清空域名列表")
            self.batch_domains = []
            self.duplicate_domains = []
            self.update_batch_preview()
            return
            
        # 按行分割
        lines = text.split('\n')
        self.logger.debug(f"批量文本行数: {len(lines)}")
        domains = []
        
        # 提取每行的域名
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            domain = extract_domain_from_url(line)
            if domain and validate_domain(domain):
                domains.append(domain)
                
        self.logger.debug(f"提取域名数量（去重前）: {len(domains)}")
        # 去重（仅保留唯一域名）
        unique_domains = []
        seen = set()
        for domain in domains:
            if domain not in seen:
                seen.add(domain)
                unique_domains.append(domain)
                
        # 检查与现有域名的重复
        self.batch_domains = unique_domains
        self.duplicate_domains = [d for d in unique_domains if d in self.existing_domains]
        self.logger.debug(f"唯一域名数量: {len(unique_domains)}，重复域名数量: {len(self.duplicate_domains)}")
        
        # 更新预览
        self.update_batch_preview()
        
    def update_batch_preview(self):
        """更新批量模式预览"""
        valid_count = len(self.batch_domains)
        duplicate_count = len(self.duplicate_domains)
        
        self.batch_preview_label.setText(
            f"有效域名: {valid_count} 个 | 重复域名: {duplicate_count} 个"
        )
        
        # 更新预览文本框
        if valid_count == 0:
            self.preview_textedit.setText("暂无有效域名")
        else:
            preview_text = "\n".join(self.batch_domains)
            if duplicate_count > 0:
                preview_text += f"\n\n重复域名 ({duplicate_count} 个):\n" + "\n".join(self.duplicate_domains)
            self.preview_textedit.setText(preview_text)
            
        # 更新确认按钮状态
        self.update_confirm_button()
        
    def update_confirm_button(self):
        """更新确认按钮的启用状态"""
        if self.is_batch_mode:
            # 批量模式：至少有一个有效域名
            has_valid_domains = len(self.batch_domains) > 0
            self.logger.debug(f"批量模式确认按钮状态: has_valid_domains={has_valid_domains}, 域名数量={len(self.batch_domains)}")
            self.confirm_btn.setEnabled(has_valid_domains)
        else:
            # 单条模式：域名有效且不重复
            text = self.domain_input.text().strip()
            extracted = extract_domain_from_url(text)
            is_valid = validate_domain(extracted) if extracted else False
            is_duplicate = extracted in self.existing_domains if extracted else False
            self.logger.debug(f"单条模式确认按钮状态: text='{text}', extracted='{extracted}', is_valid={is_valid}, is_duplicate={is_duplicate}")
            self.confirm_btn.setEnabled(is_valid and not is_duplicate)
        self.logger.debug(f"确认按钮启用状态: {self.confirm_btn.isEnabled()}")
            
    def on_advanced_toggled(self, checked: bool):
        """
        高级配置区域切换
        
        Args:
            checked: 是否展开
        """
        # 调整对话框大小
        if checked:
            self.setFixedSize(400, 380)
        else:
            self.setFixedSize(400, 300)
            
    def get_single_rule_data(self) -> Dict[str, Any]:
        """
        获取单条模式下的规则数据
        
        Returns:
            包含规则数据的字典
        """
        domain = self.domain_input.text().strip()
        extracted = extract_domain_from_url(domain)
        self.logger.debug(f"获取单条规则数据: domain='{domain}', extracted='{extracted}'")
        return {
            'domain': extracted,
            'redirect_to': self.ip_input.text().strip(),
            'remark': self.remark_input.text().strip()
        }
        
    def get_batch_rule_data(self) -> List[Dict[str, Any]]:
        """
        获取批量模式下的规则数据列表
        
        Returns:
            规则数据字典列表
        """
        rules = []
        ip = self.ip_input.text().strip()
        remark = self.remark_input.text().strip()
        self.logger.debug(f"获取批量规则数据: ip='{ip}', remark='{remark}', 域名数量={len(self.batch_domains)}")
        
        for domain in self.batch_domains:
            # 跳过重复域名
            if domain in self.duplicate_domains:
                self.logger.debug(f"跳过重复域名: {domain}")
                continue
                
            rules.append({
                'domain': domain,
                'redirect_to': ip,
                'remark': remark
            })
            
        self.logger.debug(f"批量规则数据生成完成，共 {len(rules)} 条规则")
        return rules
        
    def accept(self):
        """重写accept方法，添加日志记录"""
        self.logger.info("用户点击确认按钮，接受对话框")
        super().accept()
        
    def get_result(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        获取对话框结果
        
        Returns:
            (是否批量模式, 规则数据列表)
        """
        self.logger.info("获取对话框结果")
        if self.is_batch_mode:
            rules = self.get_batch_rule_data()
            self.logger.info(f"批量模式，返回 {len(rules)} 条规则")
            return True, rules
        else:
            rule_data = self.get_single_rule_data()
            self.logger.info(f"单条模式，返回规则: {rule_data}")
            return False, [rule_data]


if __name__ == "__main__":
    # 测试对话框
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = AddRuleDialog()
    dialog.setWindowTitle("测试添加规则对话框")
    
    if dialog.exec_() == QDialog.Accepted:
        is_batch, rules = dialog.get_result()
        print(f"批量模式: {is_batch}")
        print(f"规则数据: {rules}")
        
    sys.exit(0)