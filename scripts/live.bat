@echo off
rem Live transcription (Ctrl+C to stop and save).
rem   live.bat [--source mic^|call^|both] [--language hi]
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.live %*
