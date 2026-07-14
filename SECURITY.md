# Security & Data Handling

Offline Transcriber is built for sensitive audio (e.g. internal financial
meetings). Its defining guarantee: **it is offline-only by default — no
audio, transcript, or derived text ever leaves the machine** unless an
operator explicitly enables the optional cloud features.

## What runs where

| Capability | Where it runs | Data leaves the machine? |
|---|---|---|
| Speech-to-text (faster-whisper / Whisper) | Local CPU/GPU | **No** |
| Speaker diarization (SpeechBrain ECAPA) | Local | **No** |
| Voice memory (`speaker_profiles.json`) | Local disk | **No** |
| Meeting notes — local (Ollama) | Local | **No** |
| Model downloads (first run only) | Hugging Face | Downloads only; no audio sent |
| **Cloud transcription boost (Groq)** | Groq API | **Yes — only if enabled** |
| **Cloud notes (Groq LLM)** | Groq API | **Yes — only if enabled** |

The last two are the *only* paths that transmit your content, and they are
**disabled by default**. Everything else is fully local.

## The offline-only default and how cloud is gated

All data egress is governed by a single module, [`policy.py`](policy.py).
Cloud is permitted **only** when it is opted in **and** not force-disabled.

**Opt in** (per user, for non-sensitive audio only) with either:

- environment variable `TRANSCRIBER_ALLOW_CLOUD=1`, or
- a marker file named `allow_cloud` next to the application.

**Force-offline** (administrator lock — always wins over any opt-in) with
either:

- environment variable `TRANSCRIBER_FORCE_OFFLINE=1`, or
- a machine-wide policy file that only an administrator can create:
  - Windows: `%PROGRAMDATA%\OfflineTranscriber\force_offline`
  - Linux/macOS: `/etc/offline-transcriber/force_offline`

```
        opted in?  ──no──▶  OFFLINE (default)
            │yes
            ▼
     force-offline?  ──yes─▶  OFFLINE (admin lock)
            │no
            ▼
          CLOUD allowed
```

On a managed fleet, IT can drop the force-offline policy file (or set the
env var via Group Policy / MDM) to guarantee the tool can never use cloud,
regardless of what any user configures.

## Where your data is stored

- **Transcripts** (`.txt`, `.srt`, `.docx`, `.json`, `_notes.md`) are written
  next to the input file (or the chosen output folder), as UTF-8, unencrypted.
  Treat them with the same care as the recording itself; store them on an
  encrypted volume (e.g. BitLocker/FileVault) for sensitive content.
- **Voice fingerprints** live in `speaker_profiles.json` beside the app. They
  are numeric embeddings, not audio, but still identify individuals — keep
  them local and out of version control (they are `.gitignore`d).
- **Live-session transcripts** are saved as `live_*.txt` beside the app.
- Nothing is sent to any telemetry or analytics service. There is none.

## Handling the Groq API key (only relevant if cloud is enabled)

The key is read in order of decreasing security:

1. `GROQ_API_KEY` environment variable,
2. the OS secret store via [`keyring`](https://pypi.org/project/keyring/)
   (Windows Credential Manager / macOS Keychain / Secret Service) — recommended,
3. a plaintext `groq_api_key.txt` next to the app — **discouraged**; convenience
   only.

The key is **never written to logs or error messages**. `groq_api_key.txt` is
`.gitignore`d. Prefer the environment variable or `keyring`.

## Supply chain & builds

- Dependencies are declared in [`pyproject.toml`](pyproject.toml) and pinned in
  [`requirements.txt`](requirements.txt) for reproducible installs.
- Releases are built in CI; verify the checksum published with each release.
- The standalone `.exe` is currently **unsigned** — Windows SmartScreen will
  warn "unknown publisher". Code-signing is on the roadmap; until then, verify
  the download against the release checksum.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Email
**himanshusharma75035@gmail.com** with:

- a description and impact,
- steps to reproduce (a proof-of-concept if possible),
- affected version / commit.

You'll get an acknowledgement within **5 business days**, and we'll agree a
disclosure timeline with you. Thank you for helping keep users safe.
