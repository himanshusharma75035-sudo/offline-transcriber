# 📓 Changelog

All notable changes to **Offline Transcriber** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<div align="center">

![Version](https://img.shields.io/badge/latest-v0.2.0-1f6feb?style=for-the-badge)
![Release](https://img.shields.io/badge/status-first%20public%20release-2ea44f?style=for-the-badge)
![Offline](https://img.shields.io/badge/100%25-OFFLINE-8957e5?style=for-the-badge)

</div>

```
┌──────────────────────────────────────────────────────────────────────────┐
│   OFFLINE TRANSCRIBER   ·   v0.1.0   ·   first public release            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│      AUDIO ──▶ TRANSCRIBE ──▶ DIARIZE ──▶ NOTES ──▶ EXPORT               │
│      file      Whisper        SpeechBrain  Ollama    txt·srt·docx·json   │
│                                                                          │
│      100% offline    ·    90+ languages    ·    audio never leaves       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🗺️ Release timeline

```
  v0.1.0                 ●  v0.2.0  (you are here)          the road ahead
  ───────────────────────┼──────────────────────────────────────────────▶
   first public          benchmarks · key mgr ·          a signed build ·
   release               code-sign tooling · mypy         v1.0
```

<a id="0-2-0"></a>

## [0.2.0] — 2026-07-20 · benchmarks, key manager & signing tooling

Post-release hardening — no breaking changes. The app itself (GUI/CLI
transcription) is unchanged; this release adds evaluation, security, and
build tooling around it.

### ✨ Added

- **`transcribe-key`** — a secure Groq API-key manager: store the key in the OS
  keyring, check where it resolves from, migrate a plaintext `groq_api_key.txt`
  into the keyring (and delete it), or clear it. The key value is never printed.
- **Accuracy benchmarking** — a dependency-free WER/DER metrics module
  (`transcriber/metrics.py`), a harness (`scripts/benchmark.py`) that scores
  Whisper + the diarizer against a labeled manifest, and
  [`docs/benchmarks.md`](docs/benchmarks.md) explaining the method.
- **Code-signing tooling** — `scripts/sign_exe.ps1` (signtool wrapper: SHA-256 +
  RFC-3161 timestamp, `.pfx` / store-cert / self-signed) and
  [`docs/code-signing.md`](docs/code-signing.md).

### 🔧 Changed

- **CI now enforces `mypy`** on the core-logic modules, alongside ruff and the
  test suite.

<a id="0-1-0"></a>

## [0.1.0] — 2026-07-15 · first public release

The first tagged, downloadable release. Everything runs **100% offline** by default; the optional cloud boost stays dormant unless you explicitly opt in.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│   WHAT'S IN v0.1.0                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ENGINES                    PRIVACY                   INTERFACES          │
│    ·  Whisper STT (90+ lang)  ·  offline by default     ·  desktop GUI      │
│    ·  SpeechBrain speakers    ·  nothing uploads         ·  command line    │
│    ·  voice memory (names)    ·  cloud is opt-in only    ·  live capture    │
│    ·  local LLM notes         ·  admin force-offline      ·  folder watch   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ✨ Added

- **Whisper speech-to-text** (via `faster-whisper`) for 90+ languages — every major Indian language, English, and code-mixed **Hinglish** — with automatic language detection.
- **Speaker diarization** using SpeechBrain ECAPA embeddings — labels *who said what*.
- **Voice memory** — remembers a speaker's voiceprint so the same person keeps the same name across recordings.
- **Local meeting notes** — summaries and action items generated on-device via Ollama (or the optional Groq boost when opted in).
- **Four ways to use it**: desktop GUI (drag-and-drop), command line, live call capture, and a folder-watch mode that transcribes new files automatically.
- **Export formats**: plain text, SRT subtitles, Word `.docx`, and JSON.
- **Standalone Windows `.exe`** — a one-folder build that runs on a PC with no Python installed. Attached to this release.
- **Full-text search** across past transcripts.

### 🔒 Privacy & security

- **Offline by default.** A single policy gate (`transcriber/policy.py`) governs all data egress. Cloud transcription and cloud notes are **opt-in only** — via `TRANSCRIBER_ALLOW_CLOUD=1` or an `allow_cloud` marker file.
- **Admin lock.** Organizations can force offline for everyone with `TRANSCRIBER_FORCE_OFFLINE=1` or a machine policy file — the GUI then hides the cloud switch entirely.
- **No secrets in the repo.** API keys live outside the package in a per-user data directory (or the OS keyring), never in git.
- Published [`SECURITY.md`](SECURITY.md) with the disclosure policy.

### 🏗️ Engineering

- Reorganized into a proper **`transcriber/` Python package** with a `scripts/` folder for launchers — the repo root went from ~32 loose files to a handful.
- **Test suite** (`pytest`, 46 tests) that runs without downloading any models, plus **GitHub Actions CI** (ruff + pytest across Python 3.10–3.13 on Linux and Windows).
- **Packaging**: `pyproject.toml` with console entry points (`transcribe`, `transcribe-gui`, …) and pinned `requirements.txt`.
- **Structured logging** (rotating file log) and a GUI crash handler.
- Diagram-rich README and this changelog.

### 📦 Download & run

```
  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
  │  1. download   │────▶│  2. unzip the  │────▶│  3. run the    │
  │  the release   │     │     folder     │     │     .exe       │
  │     .zip       │     │                │     │  (no Python!)  │
  └────────────────┘     └────────────────┘     └────────────────┘
      ~0.7 GB              anywhere you like       first run pulls
                                                   models once
```

> The `.exe` bundles the ML runtimes but not the speech models — those download once on first use. To go fully offline on an air-gapped machine, copy your `%USERPROFILE%\.cache\huggingface` folder across.

---

<div align="center">

**[⬆ back to top](#-changelog)**  ·  [Releases](https://github.com/himanshusharma75035-sudo/offline-transcriber/releases)  ·  [README](README.md)

</div>
