# Offline Transcriber — Indian languages + English

Transcribe audio and video **100% offline and free**. Auto-detects the spoken
language. Works with Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati,
Kannada, Malayalam, Punjabi, Urdu, Odia, Assamese, Nepali, Sanskrit, English
and ~90 other languages — including code-mixed speech like Hinglish.

Nothing ever leaves your machine: speech-to-text (Whisper), speaker
diarization (SpeechBrain) and summarization (Ollama) all run locally.
Internet is needed only once, to download the models.

## Features

- ⚡ **Free cloud boost (optional)** — one switch sends the audio to Groq's
  free tier instead: ~100× faster than CPU and *more* accurate
  (Whisper large-v3-turbo). Needs internet + a free API key; falls back
  to the offline engine automatically
- 🖥 **Modern GUI** — drag & drop files, dark/light theme, live progress,
  Cancel button, remembers your settings
- 🗣 **Speaker labels with voice memory** — diarization splits "who said
  what"; name a speaker once and future meetings label them by name
  automatically (voice fingerprints stay on your machine)
- 📝 **Meeting notes** — summary, key points and action items in seconds
  via Groq's free LLMs (or a local Ollama model, fully offline)
- 🎤 **Live modes** — dictate with the mic, or transcribe a **Teams/Zoom
  call live** by capturing system audio; "Mic + call" tags lines
  [you]/[call]
- 📖 **Custom vocabulary** — put your company terms and names in
  `vocabulary.txt` so they're spelled right
- 📂 **Watch folder** — auto-transcribe recordings as they land in a folder
- 🖱 **Explorer integration** — right-click any audio/video → Transcribe
- 🔍 **Search** — grep across all your transcripts (`search.bat`)
- 🌐 **Translate** — any supported language → English text
- 💬 Outputs: `.txt`, subtitles (`.srt`), Word (`.docx`) with bold speaker
  names, timestamps (`.json`), notes (`.md`)
- 🇮🇳 Optional **AI4Bharat IndicConformer** engine for the 22 official Indian
  languages
- 📦 `build_exe.ps1` packages a standalone .exe for PCs without Python

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
| `gui.bat` | The window app — files, live mic/call, speaker naming, everything |
| `transcribe.bat <files>` | Command-line transcription (`--speakers --cloud --docx ...`) |
| `live.bat` | Live transcription: `--source mic` / `call` / `both` |
| `watch.bat <folder>` | Auto-transcribe new files appearing in a folder |
| `summarize.bat <txt>` | Meeting notes + action items from a transcript |
| `search.bat "text" [folder]` | Search across all transcripts |
| `indic.bat <files> --language hi` | AI4Bharat IndicConformer engine |
| `install_context_menu.ps1` | Add right-click → "Transcribe (offline)" |
| `build_exe.ps1` | Build a standalone .exe to share with teammates |

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

## Fast mode: the free cloud boost

The offline engine is private but CPU-slow. When speed matters and the
recording is not sensitive, flip on **⚡ Cloud boost** in the GUI (or add
`--cloud` to `transcribe.bat` / `watch.bat`):

- ~100× faster: an hour of audio in about a minute
- better accuracy than the local `medium` model
- completely free (Groq free tier: roughly 8 hours of audio per day,
  no credit card)

One-time setup: create a free account at
[console.groq.com](https://console.groq.com), make a key at
[console.groq.com/keys](https://console.groq.com/keys), and paste it into a
file named `groq_api_key.txt` next to the scripts. Long recordings are
split at quiet moments and stitched back automatically. If the key is
missing or there's no internet, the tool quietly uses the offline engine
instead — nothing breaks.

**Privacy:** cloud mode uploads that recording to Groq. Keep the switch
off for anything confidential.

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

## Meeting notes

With a Groq key present, notes (summary / key points / action items)
generate in seconds — turn on **📝 Meeting notes** in the GUI or run
`summarize.bat "meeting.txt"`. Without a key, it falls back to a local
[Ollama](https://ollama.com) model, fully offline.

## Who said what — with real names

Turn on **Speaker labels**, transcribe a meeting, then click
**Name speakers** and type who Speaker 1/2/… were. Their voice
fingerprints are stored locally (`speaker_profiles.json`) and future
meetings label them by name automatically.

## Transcribing a live Teams/Zoom call

In the GUI's LIVE section pick **Call audio (Teams/Zoom)** (captures what
you hear through a loopback device — Stereo Mix or the free
[VB-Audio Cable](https://vb-audio.com/Cable/)) or **Mic + call** to also
capture your own voice, tagged `[you]` / `[call]`. Then Start.

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
