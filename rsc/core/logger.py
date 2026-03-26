#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块 - 提供统一的日志记录功能
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

# 导入常量
try:
    from constants import LOG_PATH, APP_NAME
except ImportError:
    try:
        from src.constants import LOG_PATH, APP_NAME
    except ImportError:
        # 默认值
        LOG_PATH = os.path.expandvars(r"%APPDATA%\SafeRoot\logs")
        APP_NAME = "SafeRoot"


class Logger:
    """应用程序日志管理器"""
    
    def __init__(self, log_level: str = "INFO", max_log_days: int = 30):
        """
        初始化日志管理器
        
        Args:
            log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_log_days: 日志保留天数
        """
        self.log_level = log_level
        self.max_log_days = max_log_days
        
        # 确保日志目录存在
        os.makedirs(LOG_PATH, exist_ok=True)
        
        # 设置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # 创建根日志记录器
        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(self._get_log_level(log_level))
        
        # 清除现有处理器
        self.logger.handlers = []
        
        # 创建文件处理器（按日期滚动）
        log_file = os.path.join(LOG_PATH, f"{APP_NAME}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        self.logger.addHandler(file_handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        self.logger.addHandler(console_handler)
        
        # 记录初始化信息
        self.info(f"日志系统初始化完成，日志级别: {log_level}")
    
    def _get_log_level(self, level_str: str) -> int:
        """将字符串日志级别转换为logging级别"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str.upper(), logging.INFO)
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试信息"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录普通信息"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告信息"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误信息"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误信息"""
        self.logger.critical(message, *args, **kwargs)
    
    def log_operation(self, operation: str, details: str = "", success: bool = True):
        """记录操作日志"""
        status = "成功" if success else "失败"
        message = f"操作: {operation} - {status}"
        if details:
            message += f" - 详情: {details}"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_exception(self, operation: str, exception: Exception):
        """记录异常日志"""
        self.error(f"操作: {operation} - 异常: {type(exception).__name__}: {str(exception)}")
    
    def cleanup_old_logs(self):
        """清理过期日志文件"""
        try:
            log_files = []
            for filename in os.listdir(LOG_PATH):
                if filename.endswith('.log'):
                    log_files.append(os.path.join(LOG_PATH, filename))
            
            # 按修改时间排序
            log_files.sort(key=lambda x: os.path.getmtime(x))
            
            # 保留最近 max_log_days 天的日志文件
            # 这里简单实现：只保留最新的5个备份文件（RotatingFileHandler已处理）
            # 如果需要按天数清理，可以扩展此功能
            self.info(f"日志清理完成，当前日志文件数: {len(log_files)}")
            
        except Exception as e:
            self.error(f"清理日志文件失败: {e}")
    
    def get_log_file_path(self) -> str:
        """获取当前日志文件路径"""
        return os.path.join(LOG_PATH, f"{APP_NAME}.log")


# 全局日志实例
_global_logger: Optional[Logger] = None


def get_logger(log_level: str = "INFO", max_log_days: int = 30) -> Logger:
    """
    获取全局日志实例
    
    Args:
        log_level: 日志级别
        max_log_days: 日志保留天数
        
    Returns:
        Logger实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(log_level, max_log_days)
    return _global_logger


def init_logger(log_level: str = "INFO", max_log_days: int = 30) -> Logger:
    """
    初始化全局日志实例
    
    Args:
        log_level: 日志级别
        max_log_days: 日志保留天数
        
    Returns:
        Logger实例
    """
    global _global_logger
    _global_logger = Logger(log_level, max_log_days)
    return _global_logger


if __name__ == "__main__":
    # 测试日志功能
    logger = init_logger("DEBUG")
    logger.debug("调试信息")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.critical("严重错误")
    logger.log_operation("测试操作", "这是一个测试操作", True)
    logger.log_operation("测试操作", "这是一个失败的操作", False)
    
    try:
        raise ValueError("测试异常")
    except ValueError as e:
        logger.log_exception("测试异常操作", e)
    
    print(f"日志文件路径: {logger.get_log_file_path()}")