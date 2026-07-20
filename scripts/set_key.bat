@echo off
rem Store the Groq API key securely (OS keyring) and off the plaintext file.
rem   set_key.bat --status    show where the key resolves from
rem   set_key.bat --set       paste a key, store it in the keyring
rem   set_key.bat --migrate   move groq_api_key.txt into the keyring + delete it
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV%" set "VENV=%USERPROFILE%\.venvs\transcriber\Scripts\python.exe"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%VENV%" -m transcriber.setup_key %*
