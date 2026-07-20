# 🔏 Code-signing the Windows build

An unsigned `.exe` makes Windows **SmartScreen** show a red "Windows protected
your PC — unknown publisher" warning on first run. Signing replaces that with
your verified name and, over time, builds the reputation that removes the
warning entirely. This page explains what you need and how to sign.

## The honest reality first

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WHAT SIGNING DOES — AND DOESN'T                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  standard OV certificate   ->  your name shows instead of "unknown",    │
│  (~$100-400 / year)            but SmartScreen still warns until your   │
│                                download earns reputation (days-weeks)   │
│                                                                         │
│  EV certificate            ->  SmartScreen trusts you IMMEDIATELY,      │
│  (~$250-600 / year,            no reputation wait; needs a hardware     │
│   hardware token)              token or cloud HSM                       │
│                                                                         │
│  self-signed               ->  ZERO trust on other machines. Only for   │
│  (free)                        testing that the signing pipeline runs   │
└─────────────────────────────────────────────────────────────────────────┘
```

There is **no free way** to remove the SmartScreen warning for the public — a
trusted certificate is issued by a Certificate Authority and always costs money.
Self-signing is only useful to prove your build/sign steps work.

## Getting a certificate

1. Buy a **code-signing certificate** from a CA (DigiCert, Sectigo, SSL.com,
   Certum, and others). Choose **OV** (cheaper, reputation builds over time) or
   **EV** (instant SmartScreen trust, requires a hardware token / cloud HSM).
2. Complete the CA's identity vetting (individual or organization).
3. You'll receive either a **`.pfx`** file (OV, software-based) or a **hardware
   token / HSM credential** (EV).

## Signing

The exe is produced by [`build_exe.ps1`](../scripts/build_exe.ps1); sign it with
[`sign_exe.ps1`](../scripts/sign_exe.ps1). It finds `signtool` for you, applies a
SHA-256 signature **with an RFC-3161 timestamp** (so the signature stays valid
after the certificate expires), and verifies the result.

```powershell
# 1. build
.\scripts\build_exe.ps1

# 2a. sign with a .pfx (OV certificate)
.\scripts\sign_exe.ps1 -PfxPath C:\path\to\cert.pfx -PfxPassword ****

#     ...or keep secrets out of your history via environment variables:
$env:SIGN_PFX = "C:\path\to\cert.pfx"; $env:SIGN_PFX_PASSWORD = "****"
.\scripts\sign_exe.ps1

# 2b. sign with a certificate already in your Windows store (EV token, etc.)
.\scripts\sign_exe.ps1 -Thumbprint 1A2B3C...

# 2c. just test that the pipeline works (throwaway cert, NOT trusted elsewhere)
.\scripts\sign_exe.ps1 -SelfSigned
```

Prerequisite: the **Windows SDK Signing Tools** (provides `signtool.exe`). If
`signtool` isn't found, install it from the Windows 10/11 SDK.

## Verifying a signature

```powershell
# quick check from PowerShell
Get-AuthenticodeSignature .\OfflineTranscriber.exe | Format-List Status, SignerCertificate, TimeStamperCertificate

# or right-click the exe -> Properties -> Digital Signatures
```

`Status : Valid` with your name as the signer means it's done. On a self-signed
build the status is `UnknownError` (untrusted root) even though a signature and
timestamp were applied — that's expected.

## Notes

- **Timestamp always.** Without `/tr`, the signature dies when the cert expires.
  The script does this for you.
- **Keep the `.pfx` and its password out of git.** Prefer the `SIGN_PFX` /
  `SIGN_PFX_PASSWORD` environment variables, or a cert in the Windows store.
- The signature must be **re-applied after every build** — freezing produces a
  fresh, unsigned exe each time.
- Signing DLLs is optional; the script signs the app exe only by default (there
  are thousands of bundled DLLs and signing the launcher is what SmartScreen
  checks). See the commented line in the script to also sign DLLs.

---

<div align="center">

**[⬆ back to top](#-code-signing-the-windows-build)**  ·  [README](../README.md)  ·  [SECURITY](../SECURITY.md)

</div>
