"""Summarize a transcript into notes + action items.

Uses Groq's free tier when a key is present (seconds), otherwise a local
Ollama model (minutes on CPU, fully offline). See notes.py for the engine.

Usage:
    summarize.bat "meeting.txt"
    summarize.bat "meeting.txt" --language Hindi
    summarize.bat "meeting.txt" --llm llama3.2:3b     # force a model
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

from notes import NotesUnavailable, generate_notes  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Meeting notes + action items from a transcript.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("transcript", help="transcript .txt file")
    parser.add_argument("--llm", default=None,
                        help="force a specific model (Groq or Ollama name)")
    parser.add_argument("--language", default="English",
                        help="language to write the notes in")
    args = parser.parse_args()

    path = Path(args.transcript)
    if not path.is_file():
        print(f"error: not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        result = generate_notes(
            path.read_text(encoding="utf-8", errors="replace"),
            language=args.language, llm=args.llm)
    except NotesUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    out = path.with_name(path.stem + "_notes.md")
    out.write_text(result + "\n", encoding="utf-8")
    print("\n" + result)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
