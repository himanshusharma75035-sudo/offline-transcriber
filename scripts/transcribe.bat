@echo off
rem Command-line transcription.
rem   transcribe.bat <file/folder> [--speakers --srt --docx --cloud ...]
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.transcribe %*
