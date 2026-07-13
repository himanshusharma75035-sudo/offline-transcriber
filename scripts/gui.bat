@echo off
rem Opens the Offline Transcriber GUI (no console window).
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\pythonw.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\pythonw.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
start "" "%VENV%" -m transcriber.gui
