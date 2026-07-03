@echo off
rem Watch a folder and auto-transcribe new recordings
setlocal
set "VENV=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
"%VENV%" "%~dp0watch.py" %*
