@echo off
rem AI4Bharat IndicConformer engine (Indian languages, --language required).
rem   indic.bat recording.mp3 --language hi
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.transcribe_indic %*
