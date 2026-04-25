@echo off

REM ===== 启动器 =====
pyinstaller -F -w app_launcher.py ^
  -n AgendaXLauncher ^
  --add-data "resources;resources" ^
  -i resources/icon/icon.png

REM ===== 日志-启动器 =====
pyinstaller -F app_launcher.py ^
  -n AgendaXLauncher-log ^
  --add-data "resources;resources" ^
  -i resources/icon/icon.png

REM ===== 前端程序 =====
pyinstaller -F app_main.py ^
  -n AgendaX ^
  --add-data "resources;resources" ^
  -i resources/icon/icon.png ^
  --hiddenimport sqlalchemy

:: REM ===== 日志版本（可选）=====
::pyinstaller -F app_main.py ^
::  -n AgendaX-log ^
::  --add-data "resources;resources" ^
::  -i resources/icon/icon.png ^
::  --hiddenimport sqlalchemy

REM ===== 服务端 =====
pyinstaller -F app_server.py ^
  -n AgendaXServer ^
  --add-data "resources;resources" ^
  -i resources/icon/icon.png ^
  --hiddenimport sqlalchemy

REM ===== 清理 =====
rmdir build /s /q