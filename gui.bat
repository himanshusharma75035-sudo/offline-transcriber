@echo off
rem Opens the transcriber GUI (no console window)
setlocal
set "VENV=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\pythonw.exe"
start "" "%VENV%" "%~dp0gui.py"
