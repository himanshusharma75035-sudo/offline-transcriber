# Adds "Transcribe (offline)" to the right-click menu of audio and video
# files in Windows Explorer. Per-user (HKCU) — no admin rights needed.
# Remove again with: .\uninstall_context_menu.ps1

$ErrorActionPreference = "Stop"
$bat = Join-Path $PSScriptRoot "transcribe.bat"
if (-not (Test-Path $bat)) { throw "transcribe.bat not found next to this script" }

# "& pause" keeps the window open so you can read the transcript/result
$command = "cmd /c `"`"$bat`" `"%1`" & pause`""

foreach ($type in "audio", "video") {
    $key = "HKCU:\Software\Classes\SystemFileAssociations\$type\shell\TranscribeOffline"
    New-Item -Path "$key\command" -Force | Out-Null
    Set-ItemProperty -Path $key -Name "(Default)" -Value "Transcribe (offline)"
    Set-ItemProperty -Path $key -Name "Icon" -Value "imageres.dll,-5687"
    Set-ItemProperty -Path "$key\command" -Name "(Default)" -Value $command
}

Write-Host "Done. Right-click any audio/video file -> 'Transcribe (offline)'."
