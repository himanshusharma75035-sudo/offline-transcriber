# Bundled assets

These files are **not committed** (they're large binaries) — they're downloaded
into this folder during the CI build, and `App.tsx` `require()`s them so Metro
bundles them into the APK for fully-offline use.

| File | What | Source |
|---|---|---|
| `ggml-tiny.bin` | Whisper tiny model (~75 MB, multilingual) | huggingface.co/ggerganov/whisper.cpp |
| `jfk.wav` | ~11s English sample clip | whisper.cpp samples |

To build locally, download them here first:

```bash
cd mobile/app/assets
curl -L -o ggml-tiny.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin
curl -L -o jfk.wav https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav
```
