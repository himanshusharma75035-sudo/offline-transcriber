"""Transcribe with AI4Bharat IndicConformer (600M multilingual).

Alternative engine to Whisper, tuned specifically for the 22 official Indian
languages — often more accurate for regional languages, and it covers several
that Whisper handles poorly (Bodo, Dogri, Konkani, Maithili, Manipuri,
Santali, Kashmiri...). It does NOT support English and cannot auto-detect
the language: you must say which language is spoken with --language.

Runs fully offline after the one-time model download (~2.5 GB).

Usage:
    indic.bat recording.mp3 --language hi
    indic.bat somefolder --language ta --output-dir transcripts
"""

import argparse
import sys
from pathlib import Path

# Windows consoles often default to a legacy codepage that can't print
# Indian scripts; force UTF-8 so Devanagari/Tamil/etc. don't crash output.
# (Under pythonw there is no console, so the streams are None.)
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .transcribe import collect_inputs  # noqa: E402

MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"
LANGS = {
    "as": "Assamese", "bn": "Bengali", "brx": "Bodo", "doi": "Dogri",
    "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada", "ks": "Kashmiri",
    "kok": "Konkani", "mai": "Maithili", "ml": "Malayalam", "mni": "Manipuri",
    "mr": "Marathi", "ne": "Nepali", "or": "Odia", "pa": "Punjabi",
    "sa": "Sanskrit", "sat": "Santali", "sd": "Sindhi", "ta": "Tamil",
    "te": "Telugu", "ur": "Urdu",
}


def main():
    parser = argparse.ArgumentParser(
        description="Offline transcription with AI4Bharat IndicConformer "
                    "(Indian languages only, no auto-detect).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("inputs", nargs="+",
                        help="audio/video file(s) or folder(s)")
    parser.add_argument("--language", required=True, metavar="CODE",
                        help="language spoken: " + ", ".join(
                            f"{c}={n}" for c, n in LANGS.items()))
    parser.add_argument("--decoding", default="rnnt", choices=["ctc", "rnnt"],
                        help="rnnt is usually more accurate, ctc is faster")
    parser.add_argument("--output-dir", default=None,
                        help="where to write .txt files (default: next to input)")
    args = parser.parse_args()

    if args.language not in LANGS:
        print(f"error: unsupported language '{args.language}'. Choose from: "
              + ", ".join(f"{c} ({n})" for c, n in LANGS.items()),
              file=sys.stderr)
        sys.exit(1)

    files = collect_inputs(args.inputs)
    if not files:
        print("error: no audio files found", file=sys.stderr)
        sys.exit(1)

    import torch
    from faster_whisper.audio import decode_audio  # any format -> 16k mono
    from transformers import AutoModel

    print(f"loading IndicConformer ({MODEL_ID}) ...")
    print("(first use downloads ~2.5 GB once; after that it's fully offline)")
    try:
        model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True)
    except OSError as e:
        if "gated" not in str(e).lower():
            raise
        print(f"""
This model is gated on Hugging Face — one-time (free) setup needed:

  1. Create a free account at https://huggingface.co/join
  2. Open https://huggingface.co/{MODEL_ID}
     and click "Agree and access repository"
  3. Create a Read token at https://huggingface.co/settings/tokens
  4. In PowerShell, run:
       [Environment]::SetEnvironmentVariable("HF_TOKEN", "hf_yourtoken", "User")
     then open a NEW terminal and re-run this command.

The model downloads once (~2.5 GB); after that it works fully offline.
(Meanwhile, transcribe.bat / gui.bat already work for all these languages.)
""", file=sys.stderr)
        sys.exit(1)

    for f in files:
        try:
            print(f"\n=== {f.name} ({LANGS[args.language]}) ===")
            audio = decode_audio(str(f), sampling_rate=16000)
            wav = torch.from_numpy(audio).unsqueeze(0)
            text = model(wav, args.language, args.decoding)
            if isinstance(text, list):
                text = " ".join(str(t) for t in text)
            text = str(text).strip()
            print(text)

            out_dir = Path(args.output_dir) if args.output_dir else f.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            out = (out_dir / f.stem).with_suffix(".txt")
            out.write_text(text + "\n", encoding="utf-8")
            print(f"saved: {out}")
        except Exception as e:
            print(f"error transcribing {f}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
