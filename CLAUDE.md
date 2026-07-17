# Working in this repo

Offline-first transcription desktop app: Whisper STT, SpeechBrain diarization with
voice memory, local LLM notes. GUI + CLI + live capture + folder watch.

## Layout

- `transcriber/` — the package. All modules live here; **intra-package imports are relative**
  (`from . import policy`, `from .diarize import ...`).
- `scripts/` — launchers (`.bat`), setup/build PowerShell, and the PyInstaller entry script.
  Launchers run `python -m transcriber.<module>` with `PYTHONPATH` set to the repo root —
  **they must never `cd`**, or relative file arguments the user typed stop resolving.
- `tests/` — pytest. Must run with **numpy only**: no torch import, no model download, no network.
- `transcriber/data/` — packaged defaults (e.g. the vocabulary template), read-only once installed.

## Non-negotiables

- **Offline by default.** `transcriber/policy.py` is the single data-egress gate. Any code path
  that sends data off the machine **must** call it first. Never add a second, parallel check —
  the whole point is that one file is auditable.
- **User data goes through `transcriber/paths.py`**, never beside the code. An installed package
  is read-only; writing settings next to modules breaks on install and upgrade.
- **Heavy imports stay lazy.** `torch`/`faster_whisper`/`speechbrain` are imported *inside*
  functions so `--help` and the tests stay fast.
- **Never commit secrets.** API keys resolve env → OS keyring → gitignored file.

## Keep SKILLS.md current

`SKILLS.md` is the public blueprint — it teaches someone to build an app like this. A blueprint
that drifts teaches the wrong thing confidently, so **update it in the same commit as the change
it describes** when you:

- change the architecture (a layer, a module boundary, a new interface),
- swap or add a stack choice — record *why* in the stack table,
- make a decision worth defending — add a row to *Decisions that mattered*,
- lose more than an hour to something surprising — **add a gotcha** (highest-value section),
- climb a rung on the prototype→production ladder.

Also update `CHANGELOG.md` for user-visible changes (Keep a Changelog + SemVer).

## Public repo — keep it clean

Everything here ships to GitHub. **No real names, employer names, local filesystem paths,
emails other than the project contact, API keys, or internal URLs** — in code, comments, docs,
test fixtures, or sample data. Use placeholder speaker names (Alex, Sam, Speaker 1) in examples.
Write lessons so they're useful to a stranger; that's also what makes them safe to publish.

## Diagrams

Docs use **ASCII/box-drawing diagrams, never mermaid**. Inside a code fence, use only
single-width characters — emoji and CJK are double-width and will shift every border. Emoji are
fine in headings and prose. After editing a diagram, verify every box is a true rectangle
(equal row lengths) rather than eyeballing it.

## Verification

Before committing: `ruff check .` and `pytest` must both be clean.
