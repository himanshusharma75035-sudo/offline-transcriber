"""Summarize a transcript into notes + action items — fully offline.

Uses a local LLM served by Ollama (https://ollama.com — free, open source,
runs models on your own machine with no internet). If Ollama isn't
installed, this prints setup instructions and exits.

Usage:
    summarize.bat "meeting.txt"
    summarize.bat "meeting.txt" --llm qwen2.5:3b --language Hindi
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows consoles often default to a legacy codepage that can't print
# Indian scripts; force UTF-8 so Devanagari/Tamil/etc. don't crash output.
# (Under pythonw there is no console, so the streams are None.)
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA = "http://localhost:11434"
CHUNK_CHARS = 12000        # ~3k tokens per chunk keeps small models accurate

PROMPT = """You are an assistant writing meeting notes from a transcript.
Write in {language}. Produce exactly these sections in markdown:

## Summary
A short paragraph on what the meeting was about and what was concluded.

## Key points
Bullet list of the important facts, numbers and decisions.

## Action items
Bullet list of tasks with owner if mentioned (e.g. "- Speaker 2: send the
report by email tonight"). Write "None mentioned." if there are none.

Transcript:
{text}"""

MERGE_PROMPT = """These are notes from consecutive parts of one meeting.
Merge them into a single set of notes in {language} with the same three
sections (Summary, Key points, Action items), removing duplicates:

{text}"""


def ollama(path, payload=None, timeout=600):
    url = OLLAMA + path
    if payload is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def generate(model, prompt):
    return ollama("/api/generate", {
        "model": model, "prompt": prompt, "stream": False,
    })["response"].strip()


def main():
    parser = argparse.ArgumentParser(
        description="Offline transcript summarizer (needs Ollama).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("transcript", help="transcript .txt file")
    parser.add_argument("--llm", default=None,
                        help="Ollama model name (default: first installed)")
    parser.add_argument("--language", default="English",
                        help="language to write the notes in")
    args = parser.parse_args()

    path = Path(args.transcript)
    if not path.is_file():
        print(f"error: not found: {path}", file=sys.stderr)
        sys.exit(1)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        print("error: transcript is empty", file=sys.stderr)
        sys.exit(1)

    try:
        tags = ollama("/api/tags", timeout=5)
    except (urllib.error.URLError, OSError):
        print("""
Ollama is not running. One-time setup (free, open source, offline):

  1. Download Ollama from https://ollama.com/download and install it.
  2. In a terminal, run:  ollama pull llama3.2:3b
     (a good small model for this CPU; ~2 GB one-time download)
  3. Re-run this command.

After the download everything runs locally with no internet.
""", file=sys.stderr)
        sys.exit(1)

    # smallest model first: most likely to fit in RAM and fastest on CPU
    models = sorted(tags.get("models", []), key=lambda m: m.get("size", 0))
    model = args.llm or (models[0]["name"] if models else None)
    if not model:
        print("Ollama is running but has no models. Run:  "
              "ollama pull llama3.2:3b", file=sys.stderr)
        sys.exit(1)
    print(f"summarizing with {model} (local) — this can take a few minutes "
          "on CPU...")

    chunks = [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]
    notes = []
    try:
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"  part {i}/{len(chunks)}...")
            notes.append(generate(model, PROMPT.format(language=args.language,
                                                       text=chunk)))
        result = notes[0] if len(notes) == 1 else generate(
            model, MERGE_PROMPT.format(language=args.language,
                                       text="\n\n---\n\n".join(notes)))
    except urllib.error.HTTPError as e:
        print(f"""
Ollama could not run '{model}' (HTTP {e.code}). Usually this means the
model is too big for the free RAM right now. Try:
  - closing some applications, or
  - a smaller model:  ollama pull llama3.2:3b
    then:  summarize.bat "{path}" --llm llama3.2:3b
""", file=sys.stderr)
        sys.exit(1)

    out = path.with_name(path.stem + "_notes.md")
    out.write_text(result + "\n", encoding="utf-8")
    print("\n" + result)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
