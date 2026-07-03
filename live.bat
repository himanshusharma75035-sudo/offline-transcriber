@echo off
rem Live microphone transcription (Ctrl+C to stop and save)
setlocal
set "VENV=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
"%VENV%" "%~dp0live.py" %*
