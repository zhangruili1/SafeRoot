@echo off
chcp 65001 >nul 2>&1
title SafeRoot - 创建桌面快捷方式

echo.
echo ========================================================
echo     SafeRoot - 创建桌面快捷方式
echo ========================================================
echo.

:: 获取脚本所在目录（即程序安装目录）
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"

:: 获取桌面路径
set "DESKTOP="
for /f "usebackq tokens=3*" %%a in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop 2^>nul`) do (
    set "DESKTOP=%%a %%b"
)
:: 展开环境变量
set "DESKTOP=%DESKTOP%"

if "%DESKTOP%"=="" (
    echo [!] 无法获取桌面路径，尝试使用默认路径...
    set "DESKTOP=%USERPROFILE%\Desktop"
)

echo     程序路径: %APP_DIR%
echo     桌面路径: %DESKTOP%
echo.

:: 使用 PowerShell 创建快捷方式
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $sc = $ws.CreateShortcut('%DESKTOP%\SafeRoot 网址屏蔽器.lnk'); ^
     $sc.TargetPath = '%APP_DIR%\安装并启动.bat'; ^
     $sc.WorkingDirectory = '%APP_DIR%'; ^
     $sc.Description = 'SafeRoot 网址屏蔽器 - Windows Hosts 文件管理工具'; ^
     $sc.IconLocation = 'shell32.dll,14'; ^
     $sc.Save()" 2>nul

if %errorlevel% equ 0 (
    echo     √ 桌面快捷方式创建成功！
    echo.
    echo     您可以在桌面上找到 "SafeRoot 网址屏蔽器" 快捷方式。
    echo     双击即可一键启动程序。
) else (
    echo.
    echo [!] 快捷方式创建失败，您可以手动创建：
    echo.
    echo     1. 右键桌面 → 新建 → 快捷方式
    echo     2. 位置输入: %APP_DIR%\安装并启动.bat
    echo     3. 名称输入: SafeRoot 网址屏蔽器
)

echo.
pause
