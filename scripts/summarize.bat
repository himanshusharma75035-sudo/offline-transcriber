@echo off
rem Meeting notes + action items from a transcript.
rem   summarize.bat "meeting.txt" [--language Hindi]
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.summarize %*
