#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名智能采集对话框
"""

import os
import sys

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLineEdit, QPushButton, QLabel, QCheckBox, QTextEdit,
        QTableWidget, QTableWidgetItem, QAbstractItemView,
        QHeaderView, QWidget, QGroupBox, QProgressBar, QMessageBox,
        QSplitter, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QColor
except ImportError:
    sys.exit(0)

try:
    from src.core.domain_collector import DomainCollector
    from src.core.logger import get_logger
    from src.core.rule_manager import validate_domain
except ImportError:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.core.domain_collector import DomainCollector
    from src.core.logger import get_logger
    from src.core.rule_manager import validate_domain


class CollectWorker(QThread):
    """后台采集线程"""
    progress = pyqtSignal(str, int, int)       # message, current, total
    finished = pyqtSignal(list, list, bool)     # domains, errors, cancelled
    error = pyqtSignal(str)

    def __init__(self, keyword, options):
        super().__init__()
        self.keyword = keyword
        self.options = options

    def run(self):
        collector = DomainCollector()
        try:
            domains, errors = collector.collect(
                self.keyword,
                use_crtsh=self.options.get('crtsh', True),
                use_subdict=self.options.get('subdict', True),
                use_hosts=self.options.get('hosts', True),
                progress_callback=lambda msg, cur, total: self.progress.emit(msg, cur, total)
            )
            self.finished.emit(domains, errors, collector.is_cancelled())
        except Exception as e:
            self.error.emit(str(e))


class CollectDomainDialog(QDialog):
    """域名智能采集对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.collector = DomainCollector()
        self.logger = get_logger()
        self._worker = None
        self._collected_domains = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("智能采集域名")
        self.setFixedSize(700, 580)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ---- 搜索区域 ----
        search_group = QGroupBox("搜索")
        search_layout = QHBoxLayout(search_group)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入域名或关键词，如: 360.cn、baidu、taobao")
        self.keyword_input.setClearButtonEnabled(True)
        self.keyword_input.returnPressed.connect(self._start_collect)

        self.btn_collect = QPushButton("开始采集")
        self.btn_collect.setFixedWidth(100)
        self.btn_collect.clicked.connect(self._start_collect)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedWidth(60)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_collect)

        search_layout.addWidget(QLabel("关键词:"))
        search_layout.addWidget(self.keyword_input, 1)
        search_layout.addWidget(self.btn_collect)
        search_layout.addWidget(self.btn_cancel)
        layout.addWidget(search_group)

        # ---- 选项区域 ----
        opt_group = QGroupBox("采集来源")
        opt_layout = QHBoxLayout(opt_group)

        self.cb_crtsh = QCheckBox("证书透明度日志 (crt.sh)")
        self.cb_crtsh.setChecked(True)
        self.cb_crtsh.setToolTip("通过 SSL 证书日志发现子域名，数据最全但需要联网")

        self.cb_subdict = QCheckBox("常见子域名字典")
        self.cb_subdict.setChecked(True)
        self.cb_subdict.setToolTip("枚举 www, api, mail 等常见子域名并验证是否存在")

        self.cb_hosts = QCheckBox("本地 hosts 文件")
        self.cb_hosts.setChecked(True)
        self.cb_hosts.setToolTip("搜索当前 hosts 文件中匹配的域名")

        opt_layout.addWidget(self.cb_crtsh)
        opt_layout.addWidget(self.cb_subdict)
        opt_layout.addWidget(self.cb_hosts)
        layout.addWidget(opt_group)

        # ---- 进度区域 ----
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v 个域名")
        self.progress_bar.setValue(0)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #888;")
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # ---- 结果表格 ----
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["选择", "域名", "来源"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 120)
        layout.addWidget(self.table)

        # ---- 底部按钮 ----
        bottom_layout = QHBoxLayout()

        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setFixedWidth(60)
        self.btn_select_all.clicked.connect(self._select_all)

        self.btn_deselect_all = QPushButton("取消全选")
        self.btn_deselect_all.setFixedWidth(80)
        self.btn_deselect_all.clicked.connect(self._deselect_all)

        self.lbl_count = QLabel("已选择: 0 个域名")
        self.lbl_count.setStyleSheet("font-weight: bold;")

        bottom_layout.addWidget(self.btn_select_all)
        bottom_layout.addWidget(self.btn_deselect_all)
        bottom_layout.addWidget(self.lbl_count)
        bottom_layout.addStretch()

        self.btn_add = QPushButton("添加到屏蔽列表")
        self.btn_add.setFixedWidth(140)
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self.accept)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
        """)

        self.btn_close = QPushButton("关闭")
        self.btn_close.setFixedWidth(60)
        self.btn_close.clicked.connect(self.reject)

        bottom_layout.addWidget(self.btn_add)
        bottom_layout.addWidget(self.btn_close)
        layout.addLayout(bottom_layout)

        # 初始化表格行数为 0
        self.table.setRowCount(0)

    def _start_collect(self):
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入域名或关键词")
            return

        options = {
            'crtsh': self.cb_crtsh.isChecked(),
            'subdict': self.cb_subdict.isChecked(),
            'hosts': self.cb_hosts.isChecked(),
        }

        if not any(options.values()):
            QMessageBox.warning(self, "提示", "请至少选择一种采集来源")
            return

        # UI 状态
        self.btn_collect.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.keyword_input.setEnabled(False)
        self.cb_crtsh.setEnabled(False)
        self.cb_subdict.setEnabled(False)
        self.cb_hosts.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.status_label.setText("采集中...")

        # 启动后台线程
        self._worker = CollectWorker(keyword, options)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_collect_finished)
        self._worker.error.connect(self._on_collect_error)
        self._worker.start()

    def _cancel_collect(self):
        if self._worker and self._worker.isRunning():
            self.collector.cancel()
            self._worker.terminate()
            self._worker.wait(3000)
            self.status_label.setText("已取消")

    def _on_progress(self, message, current, total):
        self.status_label.setText(message)

    def _on_collect_finished(self, domains, errors, cancelled):
        self._collected_domains = domains

        if cancelled:
            self.status_label.setText(f"已取消，共发现 {len(domains)} 个域名")
        else:
            self.status_label.setText(f"采集完成，共发现 {len(domains)} 个域名")

        if errors:
            for err in errors[:3]:
                self.logger.warning(f"采集: {err}")

        # 填充表格
        self.table.setRowCount(len(domains))
        for i, domain in enumerate(domains):
            # 复选框
            cb = QTableWidgetItem()
            cb.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            cb.setCheckState(Qt.Checked)
            self.table.setItem(i, 0, cb)

            # 域名
            item_domain = QTableWidgetItem(domain)
            item_domain.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, 1, item_domain)

            # 来源（简化标注）
            item_src = QTableWidgetItem("多源")
            item_src.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_src.setTextAlignment(Qt.AlignCenter)
            item_src.setForeground(QColor("#7f8c8d"))
            self.table.setItem(i, 2, item_src)

        self.progress_bar.setMaximum(max(len(domains), 1))
        self.progress_bar.setValue(len(domains))
        self._update_count()

        # 恢复 UI
        self.btn_collect.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.keyword_input.setEnabled(True)
        self.cb_crtsh.setEnabled(True)
        self.cb_subdict.setEnabled(True)
        self.cb_hosts.setEnabled(True)
        self.btn_add.setEnabled(len(domains) > 0)

    def _on_collect_error(self, error_msg):
        self.status_label.setText("采集失败")
        QMessageBox.critical(self, "采集失败", error_msg)
        self._restore_ui()

    def _restore_ui(self):
        self.btn_collect.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.keyword_input.setEnabled(True)
        self.cb_crtsh.setEnabled(True)
        self.cb_subdict.setEnabled(True)
        self.cb_hosts.setEnabled(True)

    def _select_all(self):
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self._update_count()

    def _deselect_all(self):
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self._update_count()

    def _update_count(self):
        count = 0
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                count += 1
        self.lbl_count.setText(f"已选择: {count} 个域名")
        self.btn_add.setEnabled(count > 0)

    def get_selected_domains(self):
        """返回用户勾选的域名列表"""
        domains = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                domain_item = self.table.item(i, 1)
                if domain_item:
                    domains.append(domain_item.text())
        return domains
