"""Measure transcription (WER) and diarization (DER) accuracy on your own data.

The metric math lives in `transcriber.metrics` and is unit-tested; this script
is the harness that runs the models over a manifest of labeled samples and
prints a report. Nothing here is bundled into the app — it's an evaluation tool.

USAGE
-----
    python scripts/benchmark.py manifest.json --model small [--diarize]

MANIFEST (JSON) — a list of samples:

    [
      {
        "name":          "board-call-2024-03",
        "audio":         "samples/board.m4a",
        "reference_txt": "samples/board.txt",
        "reference_rttm": "samples/board.rttm"   // optional, enables DER
      },
      ...
    ]

Paths are resolved relative to the manifest file. `reference_txt` is the
ground-truth transcript (plain text). `reference_rttm` is standard NIST RTTM
(who spoke when); include it and pass --diarize to score speaker labels too.

The script downloads the Whisper model on first use like the app does; run it
once online, then it works offline.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# Import the package whether or not it's pip-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcriber.metrics import (  # noqa: E402
    DiarizationErrorRate,
    WordErrorRate,
    diarization_error_rate,
    word_error_rate,
)


def parse_rttm(path: Path) -> list[tuple[float, float, str]]:
    """Read NIST RTTM into (start, end, speaker) segments."""
    segments = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts or parts[0] != "SPEAKER":
            continue
        start, dur, speaker = float(parts[3]), float(parts[4]), parts[7]
        segments.append((start, start + dur, speaker))
    return segments


def load_model(name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel  # heavy import, deferred
    return WhisperModel(name, device=device, compute_type=compute_type)


def transcribe_plain(model, audio: Path, *, want_words: bool):
    """Return (full_text, word_list) for one file. word_list is [] unless asked."""
    segments, _info = model.transcribe(str(audio), word_timestamps=want_words)
    texts, words = [], []
    for seg in segments:
        texts.append(seg.text.strip())
        if want_words:
            words.extend((w.start, w.end, w.word) for w in (seg.words or []))
    return " ".join(texts), words


def hyp_diarization(audio: Path, words, num_speakers):
    """Run the app's diarizer, return (start, end, speaker) segments."""
    from faster_whisper.audio import decode_audio

    from transcriber.diarize import diarize_words
    pcm = decode_audio(str(audio), sampling_rate=16000)
    turns, _n, _centroids = diarize_words(pcm, words, num_speakers)
    return [(st, en, spk) for spk, st, en, _tx in turns]


def fmt_pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path, help="JSON manifest of labeled samples")
    ap.add_argument("--model", default="small", help="Whisper model (default: small)")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--diarize", action="store_true",
                    help="also score speaker labels (needs reference_rttm)")
    ap.add_argument("--num-speakers", type=int, default=None,
                    help="fix the speaker count (default: auto-detect)")
    ap.add_argument("--collar", type=float, default=0.25,
                    help="DER boundary collar in seconds (default: 0.25)")
    ap.add_argument("--out", type=Path, default=None,
                    help="write a JSON results file here")
    ap.add_argument("--markdown", type=Path, default=None,
                    help="write a Markdown results table here")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base = args.manifest.resolve().parent

    print(f"Loading Whisper '{args.model}' on {args.device}/{args.compute_type} ...")
    model = load_model(args.model, args.device, args.compute_type)

    results = []
    for item in manifest:
        name = item.get("name") or Path(item["audio"]).stem
        audio = (base / item["audio"]).resolve()
        ref_txt = (base / item["reference_txt"]).read_text(encoding="utf-8")
        want_rttm = args.diarize and item.get("reference_rttm")

        print(f"\n=== {name} ===")
        hyp_text, words = transcribe_plain(model, audio, want_words=bool(want_rttm))
        wer: WordErrorRate = word_error_rate(ref_txt, hyp_text)
        print(f"WER {fmt_pct(wer.wer)}  "
              f"(S={wer.substitutions} D={wer.deletions} I={wer.insertions} "
              f"/ {wer.reference_words} words)")

        der: DiarizationErrorRate | None = None
        if want_rttm:
            ref_seg = parse_rttm((base / item["reference_rttm"]).resolve())
            hyp_seg = hyp_diarization(audio, words, args.num_speakers)
            der = diarization_error_rate(ref_seg, hyp_seg, collar=args.collar)
            print(f"DER {fmt_pct(der.der)}  "
                  f"(miss={der.missed:.1f}s FA={der.false_alarm:.1f}s "
                  f"conf={der.confusion:.1f}s / {der.reference_speech:.1f}s)")

        results.append({"name": name, "wer": wer, "der": der})

    # ---- summary ----
    wers = [r["wer"].wer for r in results]
    ders = [r["der"].der for r in results if r["der"] is not None]
    print("\n" + "=" * 48)
    print(f"samples: {len(results)}")
    if wers:
        print(f"mean WER: {fmt_pct(statistics.mean(wers))}  "
              f"median: {fmt_pct(statistics.median(wers))}")
    if ders:
        print(f"mean DER: {fmt_pct(statistics.mean(ders))}  "
              f"median: {fmt_pct(statistics.median(ders))}")

    if args.markdown:
        rows = ["| Sample | WER | DER |", "|---|---|---|"]
        for r in results:
            d = fmt_pct(r["der"].der).strip() if r["der"] else "—"
            rows.append(f"| {r['name']} | {fmt_pct(r['wer'].wer).strip()} | {d} |")
        overall_der = fmt_pct(statistics.mean(ders)).strip() if ders else "—"
        rows.append(f"| **mean** | **{fmt_pct(statistics.mean(wers)).strip()}** "
                    f"| **{overall_der}** |")
        args.markdown.write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"\nwrote {args.markdown}")

    if args.out:
        payload = [{
            "name": r["name"],
            "wer": r["wer"].wer,
            "wer_detail": vars(r["wer"]),
            "der": (r["der"].der if r["der"] else None),
            "der_detail": (vars(r["der"]) if r["der"] else None),
        } for r in results]
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
