@echo off
chcp 65001 >nul 2>&1
title SafeRoot 一键安装启动

:: 设置窗口颜色
color 0A

echo.
echo ========================================================
echo          SafeRoot 网址屏蔽器 - 一键安装启动
echo ========================================================
echo.

:: =====================
:: 1. 检测 Python 环境
:: =====================
echo [1/4] 正在检测 Python 环境...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] 未检测到 Python，正在为您自动下载安装...
    echo.
    echo 请在弹出的浏览器页面中下载 Python 安装包。
    echo.
    echo ★ 重要提示：安装时请务必勾选 "Add Python to PATH"！
    echo.
    start https://www.python.org/downloads/
    echo.
    echo 安装完成后，请重新运行此脚本。
    echo.
    pause
    exit /b 1
)

:: 获取 Python 版本
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VER=%%v
echo     √ 已找到 Python %PYTHON_VER%

:: 检查版本是否 >= 3.6
python -c "import sys; sys.exit(0 if sys.version_info >= (3,6) else 1)" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [!] Python 版本过低，需要 Python 3.6 或更高版本。
    echo     当前版本: %PYTHON_VER%
    echo.
    echo 请前往 https://www.python.org/downloads/ 下载最新版本。
    echo.
    pause
    exit /b 1
)

:: =====================
:: 2. 安装/更新依赖
:: =====================
echo.
echo [2/4] 正在安装依赖库...
echo.

:: 升级 pip
python -m pip install --upgrade pip -q 2>nul

:: 安装依赖
pip install -r "%~dp0requirements.txt" -q 2>nul
if %errorlevel% neq 0 (
    echo     ! 依赖安装遇到问题，尝试使用清华镜像源重新安装...
    pip install -r "%~dp0requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple -q 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo [!] 依赖安装失败，请检查网络连接后重试。
        echo.
        pause
        exit /b 1
    )
)

echo     √ 依赖安装完成

:: =====================
:: 3. 验证关键依赖
:: =====================
echo.
echo [3/4] 正在验证安装...
echo.

python -c "from PyQt5.QtWidgets import QApplication; print('    √ PyQt5')" 2>nul || (
    echo     ! PyQt5 未正确安装
    echo.
    pause
    exit /b 1
)

:: =====================
:: 4. 启动程序
:: =====================
echo.
echo [4/4] 正在启动 SafeRoot...
echo.
echo ========================================================
echo   启动后将自动请求管理员权限，请在弹窗中点击"是"
echo ========================================================
echo.

:: 延迟一下让用户看到提示
timeout /t 2 /nobreak >nul

:: 启动主程序
cd /d "%~dp0"
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] 程序异常退出，错误代码: %errorlevel%
    echo.
    pause
)
