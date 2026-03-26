#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeRoot 常量定义文件
"""

import os
import sys

# Hosts 文件路径
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

# 应用程序数据目录
APP_DATA_PATH = os.path.expandvars(r"%APPDATA%\SafeRoot")

# 备份目录
BACKUP_PATH = os.path.join(APP_DATA_PATH, "backups")

# 配置文件路径
CONFIG_PATH = os.path.join(APP_DATA_PATH, "config.json")

# 日志文件路径
LOG_PATH = os.path.join(APP_DATA_PATH, "logs")

# 支持的网站列表文件
SITES_LIST_PATH = os.path.join(APP_DATA_PATH, "sites.json")

# 应用程序信息
APP_NAME = "SafeRoot"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Windows hosts 文件管理工具"

# 更新检查配置
UPDATE_CHECK_URL = "https://api.github.com/repos/saferoot/saferoot/releases/latest"
UPDATE_CHECK_ENABLED = True

# 创建必要的目录
def create_directories():
    """创建应用程序所需的所有目录"""
    directories = [APP_DATA_PATH, BACKUP_PATH, LOG_PATH]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

if __name__ == "__main__":
    # 测试目录创建
    create_directories()
    print("常量文件加载成功")
    print(f"HOSTS_PATH: {HOSTS_PATH}")
    print(f"APP_DATA_PATH: {APP_DATA_PATH}")