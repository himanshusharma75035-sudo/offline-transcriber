# Code-sign the built OfflineTranscriber.exe (and its DLLs).
#
# Signing is what stops Windows SmartScreen from calling the download an
# "unknown publisher". You need a code-signing certificate; this script drives
# signtool for the three ways you might have one:
#
#   1. A .pfx file        ->  .\scripts\sign_exe.ps1 -PfxPath cert.pfx -PfxPassword ****
#                             (or set env SIGN_PFX and SIGN_PFX_PASSWORD)
#   2. A cert in the store->  .\scripts\sign_exe.ps1 -Thumbprint <THUMBPRINT>
#   3. Nothing yet, just  ->  .\scripts\sign_exe.ps1 -SelfSigned
#      testing the pipeline   (creates a throwaway cert; the signature will NOT
#                             be trusted by other machines -- it only proves the
#                             signing + verify flow works)
#
# By default it signs the exe produced by build_exe.ps1. Point -Target elsewhere
# to sign a specific file.

[CmdletBinding(DefaultParameterSetName = "Pfx")]
param(
    [Parameter(ParameterSetName = "Pfx")]      [string] $PfxPath = $env:SIGN_PFX,
    [Parameter(ParameterSetName = "Pfx")]      [string] $PfxPassword = $env:SIGN_PFX_PASSWORD,
    [Parameter(ParameterSetName = "Store")]    [string] $Thumbprint,
    [Parameter(ParameterSetName = "Self")]     [switch] $SelfSigned,
    [string] $Target,
    [string] $TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

# ---- locate the target exe -------------------------------------------------
if (-not $Target) {
    $Target = Join-Path $env:LOCALAPPDATA "OfflineTranscriber-build\dist\OfflineTranscriber\OfflineTranscriber.exe"
}
if (-not (Test-Path $Target)) {
    throw "Target not found: $Target`nBuild it first with .\scripts\build_exe.ps1, or pass -Target."
}

# ---- locate signtool (prefer native x64 over arm) --------------------------
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -in @("x64", "x86") } |
    Sort-Object @{ e = { if ($_.Directory.Name -eq "x64") { 0 } else { 1 } } }, FullName -Descending:$false |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $signtool) {
    throw "signtool.exe not found. Install the Windows 10/11 SDK (the 'Windows SDK Signing Tools' component)."
}
Write-Host "signtool: $signtool"

# ---- resolve the certificate ----------------------------------------------
$tempCert = $null
$signArgs = @()

switch ($PSCmdlet.ParameterSetName) {
    "Self" {
        Write-Host "Creating a throwaway self-signed certificate (test only)..." -ForegroundColor Yellow
        $tempCert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=OfflineTranscriber Test (DO NOT TRUST)" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -KeyUsage DigitalSignature `
            -KeyExportPolicy Exportable
        $signArgs = @("/sha1", $tempCert.Thumbprint)
        Write-Host "  thumbprint: $($tempCert.Thumbprint)"
    }
    "Store" {
        if (-not $Thumbprint) { throw "Pass -Thumbprint <THUMBPRINT> of a code-signing cert in your store." }
        $signArgs = @("/sha1", $Thumbprint)
    }
    "Pfx" {
        if (-not $PfxPath) {
            throw "No certificate given. Use -PfxPath (or `$env:SIGN_PFX), -Thumbprint, or -SelfSigned. See the header for details."
        }
        if (-not (Test-Path $PfxPath)) { throw "PFX not found: $PfxPath" }
        $signArgs = @("/f", $PfxPath)
        if ($PfxPassword) { $signArgs += @("/p", $PfxPassword) }
    }
}

# ---- sign ------------------------------------------------------------------
# SHA-256 digest + RFC-3161 timestamp so the signature stays valid after the
# certificate expires. Signing the exe is what matters; DLLs are optional but
# tidy, so we sign them too when present.
$targets = @($Target)
$distDir = Split-Path $Target -Parent
$dlls = Get-ChildItem $distDir -Filter *.dll -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -gt 0 } | Select-Object -ExpandProperty FullName
# Signing every bundled DLL (thousands) is slow and unnecessary; sign only the
# app exe by default. Uncomment to also sign DLLs:  $targets += $dlls

try {
    foreach ($t in $targets) {
        Write-Host "`nsigning: $t"
        & $signtool sign /fd SHA256 /td SHA256 /tr $TimestampUrl @signArgs $t
        if ($LASTEXITCODE -ne 0) { throw "signtool failed on $t (exit $LASTEXITCODE)" }
    }

    Write-Host "`nverifying..."
    if ($PSCmdlet.ParameterSetName -eq "Self") {
        # A self-signed cert isn't in a trusted root, so signtool's trust check
        # would fail by design. Confirm the signature + timestamp were applied
        # via the signature object instead.
        $sig = Get-AuthenticodeSignature $Target
        if (-not $sig.SignerCertificate) { throw "no signature was applied" }
        $ts = if ($sig.TimeStamperCertificate) { "with RFC-3161 timestamp" } else { "WITHOUT timestamp" }
        Write-Host "  self-signed signature applied ($ts)." -ForegroundColor Yellow
        Write-Host "  (trust check skipped -- a self-signed cert is for pipeline testing only.)" -ForegroundColor Yellow
    } else {
        & $signtool verify /v /pa $Target
        if ($LASTEXITCODE -ne 0) { throw "verification failed (exit $LASTEXITCODE)" }
        Write-Host "  signature verified and trusted." -ForegroundColor Green
    }
}
finally {
    if ($tempCert) {
        Remove-Item "Cert:\CurrentUser\My\$($tempCert.Thumbprint)" -Force -ErrorAction SilentlyContinue
        Write-Host "removed throwaway test certificate."
    }
}

Write-Host "`nDone." -ForegroundColor Green
