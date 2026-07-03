@echo off
rem Transcribe audio/video files from the command line
setlocal
set "VENV=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
"%VENV%" "%~dp0transcribe.py" %*
