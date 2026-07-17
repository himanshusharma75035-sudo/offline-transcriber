<div align="center">

# 🎙️ Offline Transcriber

### Transcribe **every language spoken in India** — plus English & Hinglish — **100% offline and free**

<br>

![Offline](https://img.shields.io/badge/100%25-OFFLINE-2ea44f?style=for-the-badge&logo=ghost&logoColor=white)
![Free](https://img.shields.io/badge/100%25-FREE-1f6feb?style=for-the-badge)
![Languages](https://img.shields.io/badge/90%2B-LANGUAGES-orange?style=for-the-badge&logo=googletranslate&logoColor=white)
![Private](https://img.shields.io/badge/YOUR%20AUDIO-NEVER%20LEAVES-8957e5?style=for-the-badge&logo=protondrive&logoColor=white)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Whisper](https://img.shields.io/badge/engine-faster--whisper-00a3a3?style=flat-square)
![Speakers](https://img.shields.io/badge/diarization-SpeechBrain%20ECAPA-ff6b6b?style=flat-square)
![Cloud boost](https://img.shields.io/badge/optional%20boost-Groq%20~100%C3%97-f55036?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

</div>

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     O F F L I N E   T R A N S C R I B E R                      ║
║                                                                ║
║     Every language spoken in India  ·  English  ·  Hinglish    ║
║     100% offline  ·  100% free  ·  your audio never leaves     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

Speech-to-text (**Whisper**), speaker diarization (**SpeechBrain**) and
meeting notes (**Ollama / Groq LLM**) all run on your own machine. Hindi,
Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi,
Urdu, Odia, Assamese, Nepali, Sanskrit, English and ~90 more — including
code-mixed **Hinglish**. Internet is needed *only once*, to download the
models.

<br>

## ⏱️ The 30-second picture

```
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │   audio /   │──▶│  transcribe │──▶│   label     │──▶│   export    │
  │    video    │   │  + language │   │  speakers   │   │  txt · srt  │
  │    file     │   │   detect    │   │  + notes    │   │ docx · json │
  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
      drop it          Whisper          who said         share-ready
     in the GUI      (local/cloud)        what?            outputs
```

<br>

## 🧭 Table of contents

| | | |
|---|---|---|
| [✨ Highlights](#highlights) | [🏗️ How it works](#how-it-works) | [🔬 The pipeline](#pipeline) |
| [⚡ Offline vs cloud](#offline-vs-cloud) | [🗣️ Speakers & voice memory](#speakers) | [🎧 Live call capture](#live-call) |
| [🚀 Setup](#setup) | [📟 Usage](#usage) | [🎚️ Choosing a model](#model) |
| [📤 Output formats](#outputs) | [🧩 Project layout](#layout) | [📜 License & credits](#license) |
| [🧠 Skills & blueprint](SKILLS.md) | [📓 Changelog](CHANGELOG.md) | [🔒 Security](SECURITY.md) |

<br>

<a id="highlights"></a>

## ✨ Highlights

| | Feature | What it gives you |
|---|---|---|
| 🔒 | **Offline-only by default** | Nothing leaves your machine. Speech, speakers, and (via Ollama) notes all run locally — the compliant default for sensitive audio. |
| ⚡ | **Cloud boost** *(opt-in, off by default)* | *If you enable it,* one switch routes non-sensitive audio to Groq's free tier — **~100× faster** and *more* accurate (large-v3-turbo), with automatic offline fallback. Admin-lockable. |
| 🖥️ | **Modern GUI** | Drag & drop, dark/light theme, live progress, Cancel button, remembers your settings. |
| 🗣️ | **Speaker labels + voice memory** | Diarization splits *who said what*. Name a speaker once — future meetings label them automatically. Voice fingerprints stay on your machine. |
| 📝 | **Instant meeting notes** | Summary, key points and action items in seconds via Groq LLMs, or a local Ollama model fully offline. |
| 🎧 | **Live modes** | Dictate with the mic, or transcribe a **Teams/Zoom call live** by capturing system audio. "Mic + call" tags lines `[you]` / `[call]`. |
| 📖 | **Custom vocabulary** | Put your company terms and names in `vocabulary.txt` so they're spelled right. |
| 📂 | **Watch folder** | Auto-transcribe recordings the moment they land in a folder. |
| 🖱️ | **Explorer integration** | Right-click any audio/video → **Transcribe (offline)**. |
| 🔍 | **Search** | Grep across every transcript you've ever made. |
| 🌐 | **Translate** | Any supported language → English text. |
| 🇮🇳 | **IndicConformer engine** | Optional AI4Bharat model for the 22 official Indian languages. |
| 📦 | **Standalone .exe** | Package the whole app for teammates who don't have Python. |

<br>

<a id="how-it-works"></a>

## 🏗️ How it works

A four-layer architecture: many ways in, one core pipeline, pluggable
engines, share-ready outputs.

```
┌─────────────────────────────────────────────────────────────────┐
│  1 · INTERFACES                                                 │
│  GUI  ·  CLI  ·  Live mic/call  ·  Watch folder  ·  Right-click │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  2 · CORE PIPELINE          transcribe.py                       │
│  decode → chunk → transcribe → diarize → label → export → notes │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  3 · ENGINES                                                    │
│  faster-whisper  (local, CPU)   ·   Groq Whisper (cloud ~100×)  │
│  SpeechBrain ECAPA-TDNN (speakers)   ·   IndicConformer         │
│  Groq LLM  /  Ollama  (meeting notes)                           │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  4 · OUTPUTS                                                    │
│  .txt   ·   .srt   ·   .docx   ·   .json   ·   notes.md         │
└─────────────────────────────────────────────────────────────────┘
```

<br>

<a id="pipeline"></a>

## 🔬 The pipeline in detail

Every recording flows through the same stages. Speaker labelling and
notes are optional add-ons that switch on when you ask for them.

```
       audio / video file    (wav · mp3 · m4a · mp4 · mkv …  no ffmpeg)
             │
             ▼
     1 · DECODE       →  16 kHz mono PCM  ·  batched for ~10× speed
             │
             ▼
     2 · TRANSCRIBE   →  faster-whisper (local)  or  Groq (cloud)
             │            ·  auto-detects the spoken language
             ▼
     3 · DIARIZE      →  SpeechBrain ECAPA  →  cluster into speakers
             │            ·  match voiceprints to saved names   (optional)
             ▼
     4 · FORMAT       →  merge words + speaker labels + timestamps
             │
             ▼
       txt · srt · docx · json    +    notes.md
```

<br>

<a id="offline-vs-cloud"></a>

## ⚡ Offline vs cloud boost

**Offline is the default and nothing leaves your machine unless you turn
cloud on.** The offline engine is private but CPU-slow; when speed matters
and a recording *isn't* sensitive, you can opt in to the Groq cloud boost.
Cloud is **off by default** and must be explicitly enabled (see below) — and
even then, if the key is missing, you're offline, or an upload fails, it
silently falls back to local. **Nothing ever breaks; nothing is ever sent
without opt-in.** See [SECURITY.md](SECURITY.md) for the full data policy.

```
                       ┌────────────────────────────┐
                       │    Cloud boost enabled?     │
                       └──────────────┬─────────────┘
                    ┌── yes ──────────┴──────────── no ──┐
                    ▼                                    ▼
        ┌───────────────────────┐          ┌───────────────────────┐
        │   Groq Whisper API    │          │   faster-whisper      │
        │   cloud · ~100x fast  │          │   local CPU · private │
        │   more accurate       │          │   nothing leaves PC   │
        └───────────┬───────────┘          └───────────┬───────────┘
                    │                                  │
             no key / offline / error                  │
                    └─────────────▶ falls back ◀───────┘
                                        │
                                        ▼
                          ┌────────────────────────────┐
                          │   transcript + timestamps   │
                          └────────────────────────────┘
```

|  | 🛡️ Offline (default) | ⚡ Cloud boost (opt-in) |
|---|---|---|
| **Speed** | ~realtime on 4 cores | an hour of audio in ~1 minute |
| **Privacy** | audio never leaves the PC | audio uploaded to Groq |
| **Accuracy** | very good (`medium`/`large-v3`) | excellent (large-v3-turbo) |
| **Cost** | free forever | free (~8 hrs/day, no card) |
| **Internet** | only once, for models | required while it's on |

> **Enabling cloud (opt-in, for non-sensitive audio only):**
> 1. **Turn the policy on** — set `TRANSCRIBER_ALLOW_CLOUD=1` or create an
>    empty file named `allow_cloud` next to the app. Until you do, the ⚡
>    switch doesn't even appear and `--cloud` is ignored.
> 2. **Add a key** — free account at [console.groq.com](https://console.groq.com),
>    key at [console.groq.com/keys](https://console.groq.com/keys); store it
>    in the `GROQ_API_KEY` env var (or Windows Credential Manager via
>    `keyring`, or a `groq_api_key.txt` file — least secure).
>
> Long recordings are split at quiet moments and stitched back automatically.
>
> **Admin lock:** IT can force offline everywhere with
> `TRANSCRIBER_FORCE_OFFLINE=1` or a machine policy file — it overrides any
> user opt-in. Details in [SECURITY.md](SECURITY.md).

<br>

<a id="speakers"></a>

## 🗣️ Who said what — with real names

Turn on **Speaker labels**, transcribe a meeting, click **Name speakers**,
and type who *Speaker 1 / 2 / …* were. Their voice fingerprints are stored
locally — and **every future meeting labels them by name automatically**.

```
   ┌───────────────────────────────────────────────────────────┐
   │  1. FIRST MEETING  —  diarization finds anonymous voices  │
   │     Speaker 1  ▁▂▃▅▂▃    (ECAPA-TDNN voice embedding)     │
   │     Speaker 2  ▂▅▃▁▂▅                                     │
   └───────────────────────────────────────────────────────────┘
                                 │
                                 ▼
   ┌───────────────────────────────────────────────────────────┐
   │  2. YOU NAME THEM ONCE                                    │
   │     Speaker 1  →  Alex       Speaker 2  →  Sam            │
   │     voiceprints saved locally  →  speaker_profiles.json   │
   └───────────────────────────────────────────────────────────┘
                                 │
                                 ▼
   ┌───────────────────────────────────────────────────────────┐
   │  3. EVERY FUTURE MEETING  —  automatic                    │
   │     new voice  →  match saved (cosine ≥ 0.55)  →  name    │
   │     result:   "Alex: …"    "Sam: …"   ✓                   │
   └───────────────────────────────────────────────────────────┘
```

- **Diarization** — SpeechBrain **ECAPA-TDNN** embeds short windows, then
  agglomerative clustering (cosine) groups them into speakers.
- **Voice memory** — `voices.py` stores each named voice's fingerprint in
  `speaker_profiles.json` (atomic writes + backup, so it survives crashes)
  and greedily matches new speakers to known names.

<br>

<a id="live-call"></a>

## 🎧 Transcribing a live Teams/Zoom call

Two signal paths — your **microphone** and the **call audio** you hear —
are captured, chunked at silences, transcribed live, and tagged.

```
   ┌────────────────────────────────────────────────────────────────┐
   │  CAPTURE      mic (your voice)  +  call audio (Teams / Zoom)   │
   │               call = system audio via a loopback device        │
   └────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  CHUNK        VAD gates each utterance at silence              │
   └────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  TRANSCRIBE   faster-whisper (local) · one utterance at a time │
   └────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  TAG & SAVE   [12:04 you ]  hello everyone …                   │
   │               [12:04 call]  hi, can you hear me …              │
   │               tagged [you] / [call]  ·  saved on Ctrl+C        │
   └────────────────────────────────────────────────────────────────┘
```

In the GUI's **LIVE** section pick **Mic**, **Call audio (Teams/Zoom)**, or
**Mic + call**. Call capture uses a loopback device — Windows **Stereo Mix**
or the free [VB-Audio Cable](https://vb-audio.com/Cable/). Lines are tagged
`[you]` / `[call]` so you always know who's speaking.

<br>

<a id="setup"></a>

## 🚀 Setup (Windows)

Requires [Python 3.10+](https://www.python.org/downloads/) with **"Add to
PATH"** ticked. Then, in the project folder:

```
   ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
   │ scripts\setup.ps1 │──▶  │    venv + deps    │──▶  │  scripts\gui.bat  │──▶  │    drop a file    │
   └───────────────────┘     └───────────────────┘     └───────────────────┘     └───────────────────┘
         run once               auto-installed             opens the app             → transcribe
                                (outside sync)              the window                 hit Start
```

```powershell
.\scripts\setup.ps1
```

That's it. Speech models download automatically on first use
(`small` ≈ 460 MB, `medium` ≈ 1.5 GB) to `%USERPROFILE%\.cache`; after that
everything runs with **zero internet**. To hard-guarantee offline mode:
`$env:HF_HUB_OFFLINE = "1"`.

> 💡 If the project folder is inside **Dropbox/OneDrive**, `scripts\setup.ps1`
> automatically puts the environment *outside* the synced folder — sync
> tools lock files mid-install and break pip.

<br>

<a id="usage"></a>

## 📟 Usage

| Launcher | What it does |
|----------|--------------|
| `scripts\gui.bat` | The window app — files, live mic/call, speaker naming, everything |
| `scripts\transcribe.bat <files>` | Command-line transcription (`--speakers --cloud --docx …`) |
| `scripts\live.bat` | Live transcription: `--source mic` / `call` / `both` |
| `scripts\watch.bat <folder>` | Auto-transcribe new files appearing in a folder |
| `scripts\summarize.bat <txt>` | Meeting notes + action items from a transcript |
| `scripts\search.bat "text" [folder]` | Search across all transcripts |
| `scripts\indic.bat <files> --language hi` | AI4Bharat IndicConformer engine |
| `scripts\install_context_menu.ps1` | Add right-click → "Transcribe (offline)" |
| `scripts\build_exe.ps1` | Build a standalone `.exe` to share with teammates |

> Or, after `pip install -e .`, use the console commands directly:
> `transcribe`, `transcribe-gui`, `transcribe-live`, `transcribe-watch`, … .

**Examples:**

```powershell
.\scripts\transcribe.bat meeting.mp4 --speakers --srt      # who-said-what + subtitles
.\scripts\transcribe.bat "C:\recordings" --model large-v3  # whole folder, best accuracy
.\scripts\transcribe.bat tamil.m4a --translate             # Tamil speech → English text
.\scripts\live.bat --language hi                           # live Hindi dictation
.\scripts\watch.bat "C:\Users\me\Downloads" --speakers     # auto-transcribe new files
.\scripts\summarize.bat "meeting.txt" --language Hindi     # notes in Hindi
```

> Add `--help` to any command to see every flag.

<br>

<a id="model"></a>

## 🎚️ Choosing a model (CPU)

```
  accuracy  ▲
            │                                     ┌──────────────┐
     best   │                                     │   large-v3   │  noisy audio,
            │                        ┌──────────┐ │    3 GB      │  heavy code-mix,
            │                        │  medium  │ └──────────────┘  Dravidian langs
     good   │                        │  1.5 GB  │       ◀ slower than realtime
            │           ┌──────────┐ └──────────┘
            │           │  small   │  ◀ the default sweet spot
     draft  │           │  460 MB  │
            │           └──────────┘
            │      ◀ 3× realtime
            └──────────────────────────────────────────────────────▶  speed
                fast                                            slow
```

| Model | Size | Speed on a 4-core laptop | Best for |
|-------|------|--------------------------|----------|
| `small` | 460 MB | ~3× faster than realtime | clear speech, live mode, quick drafts |
| `medium` | 1.5 GB | ≈ realtime | **the default** — good accuracy everywhere |
| `large-v3` | 3 GB | slower than realtime | noisy audio, heavy code-mixing, Dravidian languages |

Long files use **batched inference** (~10× faster than naive Whisper on
CPU). A GPU is used automatically with `--device cuda` if you have one.

<br>

<a id="outputs"></a>

## 📤 Output formats

One transcription, many share-ready files — pick any combination.

```
                  ┌──────────────────┐
                  │  one transcript  │
                  └─────────┴────────┘
                            │
        ┌────────┬──────────┼─────────┬───────────┐
        ▼        ▼          ▼         ▼           ▼
    ┌──────┐ ┌───────┐ ┌────────┐ ┌───────┐ ┌──────────┐
    │ .txt │ │  .srt │ │ .docx  │ │ .json │ │ notes.md │
    │plain │ │subtit-│ │  bold  │ │  word │ │ summary  │
    │ text │ │  les  │ │speakers│ │ times │ │ actions  │
    └──────┘ └───────┘ └────────┘ └───────┘ └──────────┘
    read it  videos /  reports /   data /    share the
             captions   minutes   pipelines  decisions
```

<br>

## 🧠 The two engines

```
 ┌───────────────────────────────┐   ┌───────────────────────────────┐
 │  WHISPER  (default)           │   │  INDICCONFORMER  (indic.bat)  │
 │  gui / cli / live / watch     │   │  AI4Bharat · 22 Indian langs  │
 ├───────────────────────────────┤   ├───────────────────────────────┤
 │  ✓ auto language detect       │   │  ✓ stronger on regional langs │
 │  ✓ English + Hinglish         │   │  ✓ only option for Bodo,      │
 │  ✓ translation to English     │   │    Dogri, Konkani, Kashmiri,  │
 │  ✓ word timestamps + subs     │   │    Maithili, Manipuri, Santali│
 │  ✓ speaker diarization        │   │  ✗ no auto-detect / English   │
 │                               │   │  ✗ no timestamps              │
 └───────────────────────────────┘   └───────────────────────────────┘
```

The IndicConformer model is **gated** on Hugging Face: run `scripts\indic.bat`
once and follow the printed one-time unlock steps (free account + token).

<br>

## 📝 Meeting notes

With a Groq key present, notes (summary / key points / action items)
generate in seconds — turn on **📝 Meeting notes** in the GUI or run
`scripts\summarize.bat "meeting.txt"`. Without a key, it falls back to a local
[Ollama](https://ollama.com) model, **fully offline**.

```
   transcript.txt ──▶ [ Groq LLM  llama-3.3-70b ] ──▶ notes.md
                          │ no key / offline           summary
                          ▼                            key points
                     [ Ollama, local ] ───────────────▶ action items
```

<br>

<a id="layout"></a>

## 🧩 Project layout

```
offline-transcriber/
├─ transcriber/              The Python package
│  ├─ transcribe.py          CLI + shared core pipeline
│  ├─ gui.py                 Desktop app (CustomTkinter)
│  ├─ cloud.py               Groq Whisper cloud boost (opt-in, off by default)
│  ├─ policy.py              Offline-only data-egress gate
│  ├─ live.py                Live capture — mic / call / both
│  ├─ diarize.py             Speaker diarization (SpeechBrain ECAPA-TDNN)
│  ├─ voices.py              Named voice memory → speaker_profiles.json
│  ├─ notes.py, summarize.py Meeting notes (local Ollama, or Groq if enabled)
│  ├─ watch.py, search.py, docx_export.py, transcribe_indic.py
│  ├─ logging_setup.py       Rotating file log + GUI crash handler
│  ├─ paths.py               Resolves the per-user data directory
│  └─ data/vocabulary.txt    Default custom-terms template
├─ scripts/                  Launchers: *.bat, setup.ps1, build_exe.ps1, …
├─ tests/                    pytest suite (no model downloads)
├─ .github/workflows/        CI — ruff + pytest on Linux/Windows
├─ pyproject.toml            Packaging, dependencies, tool config
└─ README.md  LICENSE  SECURITY.md  requirements.txt
```

**A few good-to-knows**

- Transcripts are saved as **UTF-8** next to the input file.
- Accepts wav, mp3, m4a, mp4, aac, flac, ogg, opus, webm, mkv, mov, 3gp
  and more — **no ffmpeg install needed**.
- `scripts\build_exe.ps1` produces a ~2 GB folder; zip it to share. Speech models
  still download on first use on the target machine (or copy
  `%USERPROFILE%\.cache\huggingface` across for full offline).

<br>

<a id="license"></a>

## 📜 License & credits

[**MIT**](LICENSE). Built on the shoulders of:

| Project | Role | License |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | speech-to-text | MIT |
| [SpeechBrain](https://speechbrain.github.io/) | speaker diarization | Apache-2.0 |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | the GUI | MIT |
| [AI4Bharat IndicConformer](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) | Indian-language ASR | MIT |
| [Groq](https://groq.com) | optional cloud boost + LLM notes | free tier |
| [Ollama](https://ollama.com) | offline LLM notes | MIT |

<div align="center">

<br>

**Contributions welcome** — open an issue or a PR.

*Made for everyone who works across India's many languages.* 🇮🇳

</div>
