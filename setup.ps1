# One-time setup: creates a Python virtual environment and installs
# everything. Run from the project folder:  .\setup.ps1
#
# If the project lives in a synced folder (Dropbox/OneDrive/Drive), the venv
# is created outside it instead — sync tools lock files mid-install and
# break pip.

$ErrorActionPreference = "Stop"

$inRepo = Join-Path $PSScriptRoot ".venv"
$outside = Join-Path $env:USERPROFILE ".venvs\transcriber"
$synced = $PSScriptRoot -match "Dropbox|OneDrive|Google Drive"

$venv = if ($synced) { $outside } else { $inRepo }
Write-Host "Creating virtual environment at $venv ..."
python -m venv $venv
if (-not $?) { throw "Python 3.10+ is required — install from python.org" }

Write-Host "Installing dependencies (first run downloads ~1 GB of packages)..."
& "$venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")

Write-Host ""
Write-Host "Done. Start the app with gui.bat, or see README.md for all modes."
Write-Host "(Speech models download automatically on first use, then everything is offline.)"
