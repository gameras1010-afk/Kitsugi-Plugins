@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONPATH=..;%PYTHONPATH%
where py >nul 2>nul
if %errorlevel% equ 0 (
    start "" py -3.11 "manual_gui.py"
) else (
    start "" pythonw "manual_gui.py"
)
exit
