# 🧠 Skills & Blueprint

**How to build an app like this — and what you need to know to do it.**

This is the knowledge-transfer document for **Offline Transcriber**. The [README](README.md) tells you *what the app does*; this file tells you *how it was built, why it was built that way, and what we learned the hard way* — so you could rebuild something like it from scratch without repeating our mistakes.

<div align="center">

![Blueprint](https://img.shields.io/badge/doc-blueprint-1f6feb?style=for-the-badge)
![Level](https://img.shields.io/badge/level-intermediate-orange?style=for-the-badge)
![Stack](https://img.shields.io/badge/stack-Python%20%C2%B7%20ML%20%C2%B7%20Desktop-2ea44f?style=for-the-badge)

</div>

## 🧭 Contents

| | | |
|---|---|---|
| [🎯 Who this is for](#who) | [🧰 Skills you need](#skills) | [🏗️ The architecture](#arch) |
| [🗺️ Build it in 7 stages](#stages) | [⚖️ Decisions that mattered](#decisions) | [🕳️ Gotchas](#gotchas) |
| [📈 Prototype → production](#ladder) | [🔁 Keeping this doc alive](#maintain) | |

<a id="who"></a>

## 🎯 Who this is for

You want to build a **local-first AI desktop app** — something that runs ML models on the user's own machine, has a real GUI, and handles private data without shipping it to a server. The domain here is speech, but the blueprint transfers to OCR, vision, local LLM tools, or anything with the same shape:

> *heavy model + desktop UI + privacy constraint + non-technical end users*

You should be comfortable with Python. You do **not** need to be an ML engineer — this app trains nothing. It wires together pre-trained models.

<a id="skills"></a>

## 🧰 Skills you need

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│   SKILLS MAP   ·   what you actually use to build this                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    FOUNDATION                      ML / AUDIO                                   │
│    ·  Python 3.10+                 ·  what STT / ASR is (not how to train it)   │
│    ·  virtualenvs & pip            ·  speaker diarization & embeddings          │
│    ·  packages vs scripts          ·  sample rates, mono/stereo, chunking       │
│    ·  relative imports             ·  model size vs speed vs accuracy           │
│                                                                                 │
│    DESKTOP                         ENGINEERING                                  │
│    ·  a GUI toolkit (Tk/Qt)        ·  pytest without heavyweight fixtures       │
│    ·  threads vs the UI loop       ·  CI (GitHub Actions)                       │
│    ·  drag-and-drop, file dialogs  ·  packaging & entry points                  │
│    ·  freezing to an .exe          ·  structured logging & crash handling       │
│                                                                                 │
│    PRIVACY                         NICE TO HAVE                                 │
│    ·  where user data belongs      ·  PowerShell / shell scripting              │
│    ·  secret storage (keyring)     ·  Windows app distribution                  │
│    ·  designing an opt-in gate     ·  local LLM serving (Ollama etc.)           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### The stack we chose

| Layer | Choice | Why this one |
|---|---|---|
| Speech-to-text | `faster-whisper` | 4× faster than reference Whisper on CPU, same weights |
| Speaker ID | SpeechBrain ECAPA | strong pretrained voice embeddings, runs on CPU |
| Clustering | scikit-learn | agglomerative clustering is enough; no need for a DL model |
| GUI | CustomTkinter | Tk ships with Python → nothing extra to freeze; looks modern |
| Drag & drop | tkinterdnd2 | Tk has no native DnD |
| Audio capture | sounddevice | simple PortAudio binding, works with loopback devices |
| Local LLM | Ollama (HTTP) | keeps the LLM out of your process and your dependency tree |
| Freezing | PyInstaller | the only mature option for a Tk + torch app |

> **Lesson:** every dependency you add gets *frozen into the shipped binary*. Choosing Tk over Qt and an out-of-process LLM over an in-process one is why the build is ~0.7 GB and not several GB more.

<a id="arch"></a>

## 🏗️ The architecture

Four layers. The rule that keeps it honest: **interfaces never talk to the network directly — everything goes through the policy gate.**

```
┌────────────────────────────────────────────────────────────────────────────┐
│     INTERFACES        GUI  ·  CLI  ·  live capture  ·  folder watch        │
│           │           (thin — they only collect options and show output)   │
│           ▼                                                                │
├────────────────────────────────────────────────────────────────────────────┤
│     POLICY GATE       is data allowed to leave this machine?               │
│           │           one module · one question · no bypass                │
│           ▼                                                                │
├────────────────────────────────────────────────────────────────────────────┤
│     CORE              transcribe  ·  diarize  ·  voice memory  ·  notes    │
│           │           (pure-ish logic, testable, no UI imports)            │
│           ▼                                                                │
├────────────────────────────────────────────────────────────────────────────┤
│     RUNTIME           Whisper  ·  SpeechBrain  ·  local LLM  ·  ffmpeg     │
│                       (heavy, lazily imported, downloaded once)            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why a policy gate is a *module*, not an `if` statement

Privacy promises rot when they're enforced in ten places. Put the question in **one function** that every egress path must call, then the promise is auditable — a reviewer reads one file, not the whole codebase.

```
      some code wants to send data off the machine
                        │
                        ▼
             ┌────────────────────┐      no
             │  did the user      ├──────────────▶  stay local
             │  explicitly opt in?│                 (default!)
             └─────────┬──────────┘
                       │ yes
                       ▼
             ┌────────────────────┐      yes
             │  has an admin set  ├──────────────▶  stay local
             │  a force-offline   │                 (lock wins)
             │  lock?             │
             └─────────┬──────────┘
                       │ no
                       ▼
                  cloud allowed
```

Two independent switches, and **local always wins ties**. Opt-in is the user's choice; the lock is the organization's. Neither can silently enable egress.

<a id="stages"></a>

## 🗺️ Build it in 7 stages

Each stage is independently useful — you always have something that runs.

```
  1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 6 ──▶ 7

  1  SKELETON      venv, one script, transcribe one file, print text
  2  CORE          language detect, model choice, export txt/srt/json
  3  SPEAKERS      diarization, then voice memory so names persist
  4  INTERFACE     the GUI: drag-drop, a queue, progress, cancel
  5  REACH         live capture, folder watch, search, notes
  6  HARDEN        policy gate, tests, CI, logging, packaging, docs
  7  SHIP          freeze the exe, tag a release, attach the binary

     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     stages 1-5 are the fun part and about 40% of the work.
     stages 6-7 are what separate a script from a product.
```

### Stage 1 is smaller than you think

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.m4a")
for s in segments:
    print(f"[{s.start:.1f}s] {s.text}")
```

That's a working transcriber. **Everything after this is product work, not ML work** — which is exactly why the engineering stages deserve most of your respect.

<a id="decisions"></a>

## ⚖️ Decisions that mattered

| Decision | What we did | Why |
|---|---|---|
| **Offline by default** | Cloud paths exist but are dormant until opt-in | A privacy claim you can't audit isn't a claim. Default matters more than capability. |
| **Keep the cloud code** | Gated, not deleted | Deleting it would force a fork for users who *want* the speed boost. Gate, don't amputate. |
| **Package, not scripts** | `pkg/` + `scripts/` | Loose scripts at root stop scaling around 15 files. Relative imports + one entry point per interface. |
| **User data ≠ package data** | Per-user dir, with legacy fallback | An installed package is read-only. Writing settings next to your code breaks on install and on upgrade. |
| **Lazy heavy imports** | `import torch` inside functions | Lets the test suite and `--help` run in milliseconds without a 2 GB import. |
| **Tests that need no models** | Pure logic, numpy only | If tests download a model, they're not tests — they're an integration suite that will flake in CI. |
| **Out-of-process LLM** | HTTP to Ollama | Keeps a multi-GB dependency out of your binary, and lets users swap models. |

<a id="gotchas"></a>

## 🕳️ Gotchas that cost us real time

The stuff no tutorial mentions. Each of these cost hours or days.

```
┌────────────────────────────────────────────────────────────────────────────┐
│   HARD-WON LESSONS                                                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│    1  Cloud-synced folders break virtualenvs.                              │
│       A sync client (Dropbox/OneDrive/Drive) will fight pip over open      │
│       files and half-sync your site-packages. Put the venv OUTSIDE the     │
│       synced tree. Symptom: bizarre, unreproducible install failures.      │
│                                                                            │
│    2  An allocation error is usually not your code.                        │
│       'failed to allocate memory' from a math library means the OS said    │
│       no. On Windows check the COMMIT CHARGE, not free RAM - a leaked      │
│       process can hold commit while its working set looks tiny.            │
│                                                                            │
│    3  Windowed builds have no stdout.                                      │
│       In a --windowed freeze, sys.stdout/stderr are None. Any bare         │
│       print() or stream call crashes at startup with no visible error.     │
│       Guard them, and install a crash handler that shows a dialog.         │
│                                                                            │
│    4  Freezing needs to be told about your own package.                    │
│       Dynamic imports are invisible to the analyzer. You must pass the     │
│       search path and explicitly collect your submodules and data files.   │
│                                                                            │
│    5  Don't exclude a dependency's dependency.                             │
│       Trimming a 'unused' audio lib silently broke speaker labels: the     │
│       diarization library imported it at load time. Test the frozen        │
│       build, not just the source.                                          │
│                                                                            │
│    6  Launchers must not cd.                                               │
│       If your .bat changes directory, relative file arguments the user     │
│       typed stop resolving. Set the module search path instead.            │
│                                                                            │
│    7  Some models are gated.                                               │
│       A few pretrained weights need an account + token before download.    │
│       Fail with an instruction, not a stack trace.                         │
│                                                                            │
│    8  Wide glyphs wreck ASCII diagrams.                                    │
│       Emoji and CJK are double-width. Inside a code block they shift       │
│       every border. Keep diagrams to single-width characters.              │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

<a id="ladder"></a>

## 📈 Prototype → production

Most hobby projects stall at rung 2. The climb is unglamorous and it is the whole game.

```
  rung 5   SIGNED & TRUSTED    code-signed · benchmarked · versioned
     ▲
  rung 4   DISTRIBUTABLE       one-click binary · tagged releases
     ▲
  rung 3   TRUSTWORTHY         tests · CI · logging · security policy
     ▲
  rung 2   USABLE              a GUI · error messages a human can read
     ▲
  rung 1   IT WORKS            runs on your machine, in your terminal
```

### The checklist that gets you up the ladder

- [ ] **Package layout** — importable package, launchers separate, entry points declared
- [ ] **User data in a user directory** — never beside the code
- [ ] **Secrets outside the repo** — env var → OS keyring → file, and gitignore the file
- [ ] **A privacy default you can point at** — one gate, documented, testable
- [ ] **Tests that run in seconds** — no model downloads, no network
- [ ] **CI on every push** — lint + tests, on every Python you claim to support
- [ ] **Logs and a crash handler** — you cannot debug a GUI over chat without them
- [ ] **A README that shows, not tells** — diagrams beat paragraphs
- [ ] **SECURITY.md** — say how to report a problem
- [ ] **A tagged release with a real binary** — the difference between a repo and a product
- [ ] **Code signing** — without it, your installer looks like malware to Windows

<a id="maintain"></a>

## 🔁 Keeping this doc alive

A blueprint that drifts is worse than none — it teaches the wrong thing confidently.
**Update this file in the same commit as the change it describes**, whenever you:

- change the **architecture** (a new layer, a module moves, a boundary shifts),
- swap or add a **stack choice** (and record *why* in the table),
- make a **decision worth defending** (add a row to *Decisions that mattered*),
- lose more than an hour to something surprising (add a **gotcha** — that's the highest-value section in this file),
- climb a **rung** on the ladder.

> **Keep it public-safe.** This file ships on GitHub. No names, no employers, no local paths, no keys, no internal URLs. Write every lesson so it's useful to a stranger — that's also what makes it safe to publish.

---

<div align="center">

**[⬆ back to top](#-skills--blueprint)**  ·  [README](README.md)  ·  [CHANGELOG](CHANGELOG.md)  ·  [SECURITY](SECURITY.md)

</div>
