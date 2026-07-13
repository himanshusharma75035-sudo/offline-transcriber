@echo off
rem Search across transcript files (.txt/.md/.srt).
rem   search.bat "invoice" [folder] [--context 1]
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.search %*
