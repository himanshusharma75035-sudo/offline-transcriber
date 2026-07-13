"""Watch a folder and transcribe every new recording automatically.

Point it at the folder where your recordings land (e.g. where Teams saves
meeting recordings). Any new audio/video file gets transcribed to a .txt
next to it. Files that already have a .txt are skipped, so it is safe to
restart at any time.

Usage:
    watch.bat "C:\\Users\\me\\Downloads"
    watch.bat "D:\\recordings" --model medium --speakers --srt
"""

import argparse
import sys
import time
from pathlib import Path

# Windows consoles often default to a legacy codepage that can't print
# Indian scripts; force UTF-8 so Devanagari/Tamil/etc. don't crash output.
# (Under pythonw there is no console, so the streams are None.)
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .transcribe import AUDIO_EXTS, transcribe_file  # noqa: E402

POLL_SECONDS = 5


def is_stable(path: Path, sizes: dict) -> bool:
    """True once the file stops growing (i.e. finished copying/recording)."""
    size = path.stat().st_size
    stable = sizes.get(path) == size and size > 0
    sizes[path] = size
    return stable


def main():
    parser = argparse.ArgumentParser(
        description="Auto-transcribe new recordings appearing in a folder.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("folder", help="folder to watch")
    parser.add_argument("--model", default="small",
                        help="Whisper model (small/medium/large-v3)")
    parser.add_argument("--language", default=None, metavar="CODE",
                        help="force language; default: auto-detect")
    parser.add_argument("--speakers", action="store_true",
                        help="label speakers in the transcripts")
    parser.add_argument("--srt", action="store_true",
                        help="also write .srt subtitles")
    parser.add_argument("--cloud", action="store_true",
                        help="use the free Groq cloud (faster; needs internet "
                             "+ free API key; falls back to local)")
    parser.add_argument("--existing", action="store_true",
                        help="also transcribe files already in the folder "
                             "(default: only new arrivals)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"error: not a folder: {folder}", file=sys.stderr)
        sys.exit(1)

    # settings expected by transcribe_file
    args.translate = False
    args.json = False
    args.output_dir = None
    args.beam_size = 5
    args.batch_size = 8
    args.no_batch = False
    args.no_vad = False
    args.num_speakers = None

    cache = {}

    def get_model():
        if "model" not in cache:
            import os

            from faster_whisper import WhisperModel
            print(f"loading model '{args.model}' ...")
            cache["model"] = WhisperModel(args.model, device="cpu",
                                          compute_type="int8",
                                          cpu_threads=os.cpu_count() or 4)
        return cache["model"]

    if not args.cloud:
        get_model()

    def needs_transcribing(f: Path) -> bool:
        return (f.suffix.lower() in AUDIO_EXTS
                and not f.with_suffix(".txt").exists())

    seen = set() if args.existing else {
        f for f in folder.iterdir() if f.is_file()}
    sizes = {}
    print(f"watching {folder} — drop recordings in, Ctrl+C to stop.")

    try:
        while True:
            for f in sorted(folder.iterdir()):
                if not f.is_file() or f in seen or not needs_transcribing(f):
                    continue
                if not is_stable(f, sizes):
                    continue        # still being written; check next poll
                seen.add(f)
                try:
                    transcribe_file(get_model, f, args)
                except Exception as e:
                    print(f"error transcribing {f.name}: {e}",
                          file=sys.stderr)
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
