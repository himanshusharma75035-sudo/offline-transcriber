# One-time setup: creates a Python virtual environment and installs
# everything. Run from the project folder:  .\scripts\setup.ps1
#
# If the project lives in a synced folder (Dropbox/OneDrive/Drive), the venv
# is created outside it instead — sync tools lock files mid-install and
# break pip.

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$inRepo = Join-Path $root ".venv"
$outside = Join-Path $env:USERPROFILE ".venvs\transcriber"
$synced = $root -match "Dropbox|OneDrive|Google Drive"

$venv = if ($synced) { $outside } else { $inRepo }
Write-Host "Creating virtual environment at $venv ..."
python -m venv $venv
if (-not $?) { throw "Python 3.10+ is required — install from python.org" }

Write-Host "Installing dependencies (first run downloads ~1 GB of packages)..."
& "$venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r (Join-Path $root "requirements.txt")

Write-Host ""
Write-Host "Done. Start the app with scripts\gui.bat, or see README.md for all modes."
Write-Host "(Speech models download automatically on first use, then everything is offline.)"
