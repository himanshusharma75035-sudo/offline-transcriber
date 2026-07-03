@echo off
rem AI4Bharat IndicConformer engine (Indian languages, --language required)
setlocal
set "VENV=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
"%VENV%" "%~dp0transcribe_indic.py" %*
