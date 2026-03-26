#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeRoot 应用程序主入口文件
"""

import sys
import os
import ctypes
import traceback

# 导入常量
try:
    from constants import APP_NAME, APP_VERSION, create_directories
except ImportError:
    # 如果直接运行，尝试从当前目录导入
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from constants import APP_NAME, APP_VERSION, create_directories


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin_restart():
    """请求管理员权限重新启动应用程序"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return True
    except Exception as e:
        print(f"请求管理员权限失败: {e}")
        return False


def main():
    """应用程序主函数"""
    # 检查管理员权限
    if not is_admin():
        print("未以管理员权限运行，正在请求权限...")
        if request_admin_restart():
            print("正在重新启动应用程序...")
            sys.exit(0)
        else:
            print("无法获取管理员权限，应用程序将退出")
            # 显示错误消息框（如果可能）
            try:
                from PyQt5.QtWidgets import QApplication, QMessageBox
                app = QApplication(sys.argv)
                QMessageBox.critical(
                    None,
                    "权限错误",
                    "需要管理员权限运行此应用程序。\n请右键点击程序图标，选择'以管理员身份运行'。"
                )
            except:
                pass
            return 1
    
    # 创建应用程序数据目录
    try:
        create_directories()
        print("应用程序目录创建成功")
    except Exception as e:
        print(f"创建目录失败: {e}")
    
    # 初始化Qt应用程序
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # 设置全局异常处理
    def exception_handler(exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"未捕获的异常:\n{error_msg}")
        
        # 在GUI中显示错误
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("应用程序错误")
            msg_box.setText(f"发生未预期的错误:\n{exc_type.__name__}: {exc_value}")
            msg_box.setDetailedText(error_msg)
            msg_box.exec_()
        except:
            pass
        
        # 退出应用程序
        sys.exit(1)
    
    sys.excepthook = exception_handler
    
    # 创建并显示主窗口
    try:
        # 尝试导入完整的主窗口
        try:
            from src.ui.main_window import MainWindow
        except ImportError:
            # 如果导入失败，使用占位符
            print("导入完整主窗口失败，使用占位符界面")
            from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
            from PyQt5.QtCore import Qt
            
            class MainWindow(QMainWindow):
                """主窗口（占位符，当导入失败时使用）"""
                
                def __init__(self):
                    super().__init__()
                    self.init_ui()
                    self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
                    
                def init_ui(self):
                    """初始化用户界面"""
                    central_widget = QWidget()
                    self.setCentralWidget(central_widget)
                    
                    layout = QVBoxLayout()
                    central_widget.setLayout(layout)
                    
                    # 欢迎标签
                    welcome_label = QLabel(f"欢迎使用 {APP_NAME} v{APP_VERSION}")
                    welcome_label.setAlignment(Qt.AlignCenter)
                    welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
                    layout.addWidget(welcome_label)
                    
                    # 状态标签
                    status_label = QLabel("应用程序已启动，请检查依赖项是否完整安装")
                    status_label.setAlignment(Qt.AlignCenter)
                    status_label.setStyleSheet("font-size: 14px; margin: 10px;")
                    layout.addWidget(status_label)
                    
                    # 错误信息标签
                    error_label = QLabel("注意：完整UI导入失败，请确保所有模块已正确安装")
                    error_label.setAlignment(Qt.AlignCenter)
                    error_label.setStyleSheet("font-size: 12px; color: red; margin: 10px;")
                    layout.addWidget(error_label)
                    
                    # 设置窗口大小
                    self.resize(600, 400)
        
        window = MainWindow()
        window.show()
        print("应用程序启动成功")
        
        # 运行应用程序
        return app.exec_()
    except Exception as e:
        print(f"启动应用程序失败: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())