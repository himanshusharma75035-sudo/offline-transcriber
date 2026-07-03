# Offline Transcriber — Indian languages + English

Transcribe audio and video **100% offline and free**. Auto-detects the spoken
language. Works with Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati,
Kannada, Malayalam, Punjabi, Urdu, Odia, Assamese, Nepali, Sanskrit, English
and ~90 other languages — including code-mixed speech like Hinglish.

Nothing ever leaves your machine: speech-to-text (Whisper), speaker
diarization (SpeechBrain) and summarization (Ollama) all run locally.
Internet is needed only once, to download the models.

## Features

- 🖥 **Modern GUI** — drag & drop files, dark/light theme, live progress
- 🗣 **Speaker labels** — "Speaker 1 / Speaker 2" diarization, fully offline
- 🎤 **Live microphone mode** — speak, pause, watch the text appear
- 📂 **Watch folder** — auto-transcribe recordings as they land in a folder
- 🖱 **Explorer integration** — right-click any audio/video → Transcribe
- 📝 **Meeting notes** — offline summary + action items via a local LLM
- 🌐 **Translate** — any supported language → English text
- 💬 Subtitles (`.srt`), timestamps (`.json`), plain text (`.txt`)
- 🇮🇳 Optional **AI4Bharat IndicConformer** engine for the 22 official Indian
  languages

## Setup (Windows)

Requires [Python 3.10+](https://www.python.org/downloads/) with
"Add to PATH" ticked. Then, in the project folder:

```powershell
.\setup.ps1
```

That's it. Speech models download automatically on first use
(`small` ≈ 460 MB, `medium` ≈ 1.5 GB) to `%USERPROFILE%\.cache`; after that
everything runs with zero internet. To force-guarantee offline mode:
`$env:HF_HUB_OFFLINE = "1"`.

## Usage

| Launcher | What it does |
|----------|--------------|
| `gui.bat` | The window app — drag files in, pick options, Transcribe |
| `transcribe.bat <files>` | Command-line transcription |
| `live.bat` | Live microphone transcription |
| `watch.bat <folder>` | Auto-transcribe new files appearing in a folder |
| `summarize.bat <txt>` | Meeting notes + action items from a transcript |
| `indic.bat <files> --language hi` | AI4Bharat IndicConformer engine |
| `install_context_menu.ps1` | Add right-click → "Transcribe (offline)" |

Examples:

```powershell
.\transcribe.bat meeting.mp4 --speakers --srt     # who-said-what + subtitles
.\transcribe.bat "C:\recordings" --model large-v3 # folder, best accuracy
.\transcribe.bat tamil.m4a --translate            # Tamil speech → English text
.\live.bat --language hi                          # live Hindi dictation
.\watch.bat "C:\Users\me\Downloads" --speakers    # auto-transcribe new files
.\summarize.bat "meeting.txt" --language Hindi    # notes written in Hindi
```

All flags: add `--help` to any command.

## Choosing a model (CPU)

| Model | Size | Speed on a 4-core laptop | Best for |
|-------|------|--------------------------|----------|
| `small` | 460 MB | ~3× faster than realtime | clear speech, live mode, quick drafts |
| `medium` | 1.5 GB | ≈ realtime | the default — good accuracy everywhere |
| `large-v3` | 3 GB | slower than realtime | noisy audio, heavy code-mixing, Dravidian languages |

Long files are processed with batched inference (~10× faster than naive
Whisper on CPU). A GPU is used automatically with `--device cuda` if you
have one.

## The two engines

- **Whisper** (default, used by the GUI/CLI/live/watch): auto language
  detection, English + Hinglish, translation, timestamps, subtitles.
- **IndicConformer** (`indic.bat`): AI4Bharat's model for the 22 official
  Indian languages — often stronger on regional languages, and the only
  option for Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Santali.
  No auto-detect/English/timestamps. The model is gated on Hugging Face:
  run `indic.bat` once and follow the printed one-time unlock steps
  (free account + token).

## Meeting notes (summarize.bat)

Install [Ollama](https://ollama.com) (free, open source), pull a small
model once (`ollama pull llama3.2:3b`), and `summarize.bat` turns any
transcript into a summary, key points and action items — locally.

## Notes

- If the project folder is inside Dropbox/OneDrive, `setup.ps1`
  automatically puts the environment outside the synced folder (sync tools
  lock files mid-install and break pip).
- Transcripts are saved as UTF-8 next to the input file.
- Accepts wav, mp3, m4a, mp4, aac, flac, ogg, opus, webm, mkv, mov, 3gp
  and more — no ffmpeg install needed.

## License

[MIT](LICENSE). Built on
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT),
[SpeechBrain](https://speechbrain.github.io/) (Apache-2.0),
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (MIT) and
[AI4Bharat IndicConformer](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) (MIT).
Contributions welcome — open an issue or PR.
