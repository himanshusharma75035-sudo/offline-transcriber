# Removes the "Transcribe (offline)" right-click menu entry.
foreach ($type in "audio", "video") {
    $key = "HKCU:\Software\Classes\SystemFileAssociations\$type\shell\TranscribeOffline"
    if (Test-Path $key) { Remove-Item -Path $key -Recurse -Force }
}
Write-Host "Removed."
