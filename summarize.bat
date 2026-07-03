@echo off
rem Summarize a transcript into notes + action items (needs Ollama)
setlocal
set "VENV=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
"%VENV%" "%~dp0summarize.py" %*
