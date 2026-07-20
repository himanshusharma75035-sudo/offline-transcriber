# 📈 Accuracy benchmarks

How accurate is it? This page explains **how we measure** transcription and
speaker accuracy, how to reproduce the numbers on your own recordings, and
where the results go.

> **Why "measure it yourself" is a feature, not a cop-out.** Speech accuracy
> depends enormously on *your* audio — accent, language, microphone, crosstalk,
> background noise. A single headline number from someone else's clean studio
> data would mislead you. The harness below lets you get **honest numbers for
> the audio you actually care about**, fully offline.

## The two numbers

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WER — Word Error Rate            "did it hear the words right?"        │
│  ─────────────────────────────────────────────────────────────────      │
│      substitutions + deletions + insertions                             │
│      ───────────────────────────────────────   ×  100%                  │
│                 words in reference                                      │
│                                                                         │
│  DER — Diarization Error Rate     "did it get who-spoke-when right?"    │
│  ─────────────────────────────────────────────────────────────────      │
│      missed speech + false alarm + speaker confusion                    │
│      ───────────────────────────────────────────────   ×  100%          │
│                 total reference speech time                             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Lower is better. 0% is perfect.** As a rough industry yardstick: WER under
10% is very good for real-world audio, and DER under 15% is a solid diarizer.

## How to run it

You need, per sample: the **audio file**, a **reference transcript** (what was
*actually* said), and — for DER — a **reference RTTM** (who spoke when).

```
  ┌───────────────┐   ┌────────────────┐   ┌───────────────┐   ┌──────────┐
  │  1. label a   │──▶│  2. write a    │──▶│  3. run the   │──▶│  4. read │
  │     few clips │   │     manifest   │   │     harness   │   │  the WER │
  │  (txt + rttm) │   │    (JSON)      │   │               │   │  + DER   │
  └───────────────┘   └────────────────┘   └───────────────┘   └──────────┘
```

**1 · The manifest** (`manifest.json`) — a list of labeled samples. Paths are
relative to the manifest file:

```json
[
  {
    "name": "board-call",
    "audio": "samples/board.m4a",
    "reference_txt": "samples/board.txt",
    "reference_rttm": "samples/board.rttm"
  }
]
```

**2 · Run it:**

```bash
# transcription only
python scripts/benchmark.py manifest.json --model small

# transcription + speaker labels, write a Markdown table
python scripts/benchmark.py manifest.json --model large-v3 --diarize \
    --markdown results.md --out results.json
```

The model downloads once on first run (like the app), then works offline.

## Reference formats

- **`reference_txt`** — plain text of what was said. Scoring normalizes both
  sides first (Unicode NFC, case-folding, punctuation removal), so you don't
  have to match capitalization or commas.
- **`reference_rttm`** — standard [NIST RTTM](https://github.com/nryant/dscore#rttm).
  One line per speaker turn:

  ```
  SPEAKER board 1 0.00 12.34 <NA> <NA> alice <NA> <NA>
  SPEAKER board 1 12.34 5.20 <NA> <NA> bob   <NA> <NA>
  ```

  The fields that matter are **start** (col 4), **duration** (col 5) and
  **speaker** (col 8). Speaker *names* are arbitrary — the harness maps your
  labels to the system's by best overlap, so you're scored on whether it kept
  people **distinct and consistent**, not on what it named them.

## How the scoring works (and its limits)

- **WER** is a Levenshtein (edit) distance over word tokens, itemized into
  substitutions / deletions / insertions. Character-level languages without
  spaces (e.g. some Indic scripts in certain fonts) are scored per
  whitespace-token; treat those numbers as directional.
- **DER** is frame-based at **10 ms** resolution with the NIST-standard
  **0.25 s collar** (boundary frames are ignored, forgiving imprecise cut
  points — tune with `--collar`). Speaker labels are matched by the assignment
  that maximizes overlap. **Overlapped speech** (two people at once) is scored
  against the earliest-listed reference speaker; the app assigns one speaker per
  instant, so heavy crosstalk will inflate DER — a known, documented limit.

The metric math is small, dependency-free, and **unit-tested** with
known-answer cases in [`tests/test_metrics.py`](../tests/test_metrics.py); the
functions live in [`transcriber/metrics.py`](../transcriber/metrics.py) if you
want to score things programmatically.

## Results

<!-- Fill this in by running the harness on a labeled set and pasting the
     Markdown table it writes with --markdown. Record the model, the machine,
     and a one-line description of the audio so the numbers are interpretable. -->

_No official numbers are published yet._ Run the harness on a labeled set and
paste its `--markdown` table here, noting the **model**, the **audio** (language,
setting, mic), and the **machine**. For example:

> **Model:** large-v3 · **Audio:** 6 Hindi/English meeting clips, headset mic ·
> **Machine:** CPU-only laptop
>
> | Sample | WER | DER |
> |---|---|---|
> | _your data_ | _—_ | _—_ |
> | **mean** | **—** | **—** |

---

<div align="center">

**[⬆ back to top](#-accuracy-benchmarks)**  ·  [README](../README.md)  ·  [SKILLS](../SKILLS.md)

</div>
