@echo off
setlocal

REM ===== 参数 =====
set SETUP_SCRIPT=%~dp0setup.iss
set OUTPUT_DIR=..\dist

REM ===== 清理旧安装包 =====
del /q "%OUTPUT_DIR%\AgendaX_Setup.exe" 2>nul

REM ===== 编译 Inno Setup =====
echo Building Inno Setup...
iscc "%SETUP_SCRIPT%"

if errorlevel 1 (
    echo Inno Setup Error: Failed to build the installer.
    pause
    exit /b 1
)

echo.
echo generated installation package:
echo %OUTPUT_DIR%\AgendaX_Setup.exe
pause