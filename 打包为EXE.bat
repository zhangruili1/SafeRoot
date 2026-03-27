@echo off
chcp 65001 >nul 2>&1
title SafeRoot - 打包为独立 EXE

echo.
echo ========================================================
echo     SafeRoot - 打包为独立可执行文件（免安装 Python）
echo ========================================================
echo.

:: 检测 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未检测到 Python，请先安装 Python 3.6+
    pause
    exit /b 1
)

echo [1/3] 正在安装打包工具...
pip install pyinstaller -q

echo [2/3] 正在打包程序（首次打包可能需要 1-3 分钟）...
echo.

cd /d "%~dp0"

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "SafeRoot" ^
    --icon "SafeRoot.ico" ^
    --add-data "src;src" ^
    --add-data "constants.py;." ^
    --hidden-import "PyQt5" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --hidden-import "PyQt5.QtCore" ^
    --hidden-import "PyQt5.QtGui" ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] 打包失败，请检查上方错误信息。
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] 清理临时文件...

if exist build rmdir /s /q build
if exist "SafeRoot.spec" del /f "SafeRoot.spec"

echo.
echo ========================================================
echo     打包完成！
echo ========================================================
echo.
echo     输出文件: dist\SafeRoot.exe
echo.
echo     用户只需双击 SafeRoot.exe 即可运行，
echo     无需安装 Python 或任何依赖。
echo.

explorer "%~dp0dist"

pause
