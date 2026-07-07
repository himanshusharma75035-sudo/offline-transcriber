# Builds a standalone OfflineTranscriber.exe (no Python needed on the
# target PC). Run from the project folder:  .\build_exe.ps1
#
# Notes:
# - The output is a FOLDER (dist\OfflineTranscriber\) ~2 GB because it
#   bundles the ML runtimes; zip it to share.
# - Speech models still download on first use on the target machine
#   (or copy %USERPROFILE%\.cache\huggingface across for full offline).
# - The IndicConformer engine (indic.bat) is not included in the exe
#   (transformers is excluded to keep the size sane); everything else works.
#   torchaudio must stay bundled — speechbrain imports it at load, so
#   excluding it silently breaks speaker labels and voice memory.
# - Build artifacts are written OUTSIDE synced folders on purpose.

$ErrorActionPreference = "Stop"

$venv = Join-Path $PSScriptRoot ".venv\Scripts"
if (-not (Test-Path (Join-Path $venv "python.exe"))) {
    $venv = Join-Path $env:USERPROFILE ".venvs\transcriber\Scripts"
}
$work = Join-Path $env:LOCALAPPDATA "OfflineTranscriber-build"

& (Join-Path $venv "pyinstaller.exe") `
    --noconfirm --clean --windowed `
    --name OfflineTranscriber `
    --workpath (Join-Path $work "build") `
    --distpath (Join-Path $work "dist") `
    --specpath $work `
    --collect-all customtkinter `
    --collect-all tkinterdnd2 `
    --collect-all speechbrain `
    --collect-all faster_whisper `
    --copy-metadata torch `
    --exclude-module transformers `
    --exclude-module PIL.ImageQt `
    --add-data "$PSScriptRoot\vocabulary.txt;." `
    (Join-Path $PSScriptRoot "gui.py")

Write-Host ""
Write-Host "Done. The app folder is: $work\dist\OfflineTranscriber"
Write-Host "Run OfflineTranscriber.exe inside it, or zip the folder to share."
