# 📱 Native mobile app — architecture & roadmap

> **Status: plan, not shipped.** The desktop app is Python + PyTorch + a desktop GUI toolkit; **none of that runs on a phone**. A mobile app is a separate codebase and a multi-week effort. This document is the design we'll build against, honest about what's feasible on-device and what isn't.

<div align="center">

![Status](https://img.shields.io/badge/status-planning-orange?style=for-the-badge)
![Platform](https://img.shields.io/badge/target-Android%20%C2%B7%20iOS-2ea44f?style=for-the-badge)
![Privacy](https://img.shields.io/badge/on--device-offline%20first-8957e5?style=for-the-badge)

</div>

## 🧭 First, the reality

```
┌─────────────────────────────────────────────────────────────────────┐
│  WHAT CARRIES OVER TO A PHONE — AND WHAT DOESN'T                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    RUNS ON A PHONE                 DOES NOT RUN ON A PHONE          │
│    ·  Whisper (via whisper.cpp)    ·  PyTorch / faster-whisper      │
│    ·  on-device, offline STT       ·  SpeechBrain diarization       │
│    ·  mic capture + file import    ·  CustomTkinter desktop GUI     │
│    ·  txt / srt / json export      ·  the 0.7 GB PyInstaller build  │
│                                                                     │
│    => the ML idea carries over; the implementation is a rewrite.    │
└─────────────────────────────────────────────────────────────────────┘
```

The good news: **whisper.cpp** runs Whisper efficiently on phone CPUs/NPUs, and there are mature React Native / Flutter bindings for it. So on-device, offline transcription — the heart of this project — is genuinely achievable on mobile. Speaker diarization and local LLM notes are the hard parts, and we stage them later.

## 🧰 Recommended stack

| Concern | Choice | Why |
|---|---|---|
| Framework | **React Native** | Node tooling is already set up here; one codebase for Android + iOS. (Flutter is a fine alternative — the on-device story is similar.) |
| On-device STT | **`whisper.rn`** | A well-maintained RN binding of whisper.cpp with GGML models, Core ML / GPU acceleration, and streaming. |
| Models | **GGML quantized** (tiny/base/small) | Phone-sized. `large-v3` is too heavy for a handset; small is the practical ceiling. |
| Audio | `react-native-audio-*` | Mic capture + file import at 16 kHz mono. |
| Storage | on-device files + SQLite | Transcripts and settings stay local. |
| Diarization (later) | ONNX ECAPA + clustering | `onnxruntime-react-native`; no PyTorch/SpeechBrain on device. |

> **Flutter instead?** Equally valid — `whisper_ggml` / `whisper_flutter_plus` wrap the same whisper.cpp. The roadmap below is framework-agnostic; only the scaffold commands differ. Say the word and I'll target Flutter.

## 🏗️ Architecture — offline-first, on the device

The desktop's guiding rule carries straight over: **audio never leaves the device by default.** No server, no upload — the model runs on the phone.

```
┌─────────────────────────────────────────────────────────────────────────┐
│    UI  (React Native)      record · pick file · results · export        │
│          │                                                              │
│          ▼                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│    POLICY GATE             on-device by default; cloud is opt-in only   │
│          │                 (mirrors the desktop's policy.py)            │
│          ▼                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│    TRANSCRIPTION           whisper.rn  ->  whisper.cpp  ->  GGML model  │
│          │                 runs on the phone CPU/NPU, fully offline     │
│          ▼                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│    STORAGE                 transcripts + settings, local only (SQLite)  │
└─────────────────────────────────────────────────────────────────────────┘
```

## ⚖️ Feature parity — honestly

What the desktop does, and how it maps to a phone. **This is the part that sets expectations**: a v1 mobile app is transcription-first; diarization and notes come later because they're genuinely hard on-device.

| Desktop feature | On mobile | Notes |
|---|---|---|
| File transcription (Whisper) | ✅ **v1** | whisper.cpp, on-device |
| 90+ languages + auto-detect | ✅ **v1** | multilingual GGML models |
| Live mic capture | ✅ **v2** | stream mic → chunked inference |
| Model picker (tiny…small) | ✅ **v2** | download-on-demand manager |
| Export txt / srt / json | ✅ **v1** | native share sheet |
| Export docx | 🟡 later | via a JS docx library |
| Speaker diarization | 🔴 **v4** | ONNX embeddings + clustering; hard |
| Voice memory (named speakers) | 🔴 **v4** | depends on diarization |
| Meeting notes (LLM) | 🔴 **v5** | tiny on-device LLM, or opt-in cloud |
| Offline-by-default policy | ✅ **v1** | ported from `policy.py` |

## 🗺️ Phased roadmap

```
  P0 ─▶ P1 ─▶ P2 ─▶ P3 ─▶ P4 ─▶ P5 ─▶ P6

  P0  TOOLCHAIN     install RN + Android SDK (+ Xcode on a Mac for iOS),
                    scaffold the app, run hello-world on a real device
  P1  MVP           pick an audio file -> on-device transcribe -> show +
                    export txt/srt/json.  Offline-by-default gate.
  P2  LIVE          mic capture, streamed/chunked transcription
  P3  MODELS        model manager: download/pick tiny..small, languages
  P4  SPEAKERS      on-device diarization (ONNX ECAPA + clustering)
  P5  NOTES         summaries: tiny on-device LLM, or opt-in cloud
  P6  SHIP          offline model bundling, polish, store submission

  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  P1 is a usable app. P4-P5 are the research-heavy parts.
```

## 🧱 What it takes to start building

A native app needs a toolchain this project's Windows box doesn't have yet:

- **Node.js** ✅ already installed
- **React Native CLI + Android SDK + a JDK 17+** — for Android builds
- **A physical Android device or emulator** — to run and test
- **A Mac with Xcode** — *required* for iOS builds (can't be done on Windows)

> Heads-up: the Android SDK + emulator is a multi-GB install and the emulator is RAM-hungry — worth checking free memory first on this machine.

## 🚀 The scaffold

A starting project skeleton and the exact init commands live in [`mobile/README.md`](../mobile/README.md). It is **not built yet** — it's the P0 starting point, with the intended structure and the `whisper.rn` integration sketch, ready to initialize once the toolchain is in place.

---

<div align="center">

**[⬆ back to top](#-native-mobile-app--architecture--roadmap)**  ·  [README](../README.md)  ·  [SKILLS](../SKILLS.md)

</div>
