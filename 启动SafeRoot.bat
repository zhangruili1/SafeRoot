@echo off
chcp 65001 >nul 2>&1
title SafeRoot 启动

:: 直接启动，不显示命令行窗口
cd /d "%~dp0"
pythonw main.py
