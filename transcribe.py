"""Offline transcription tool for Indian languages + English.

Uses faster-whisper (Whisper large-v3 family via CTranslate2). Runs fully
offline after the model has been downloaded once. Auto-detects the spoken
language, or accepts an explicit --language code.

Supported Indian languages include: Hindi (hi), Bengali (bn), Tamil (ta),
Telugu (te), Marathi (mr), Gujarati (gu), Kannada (kn), Malayalam (ml),
Punjabi (pa), Urdu (ur), Odia (or), Assamese (as), Nepali (ne), Sanskrit (sa),
Sindhi (sd), Kashmiri (ks) — plus English (en) and ~90 other languages.
"""

import argparse
import json
import os
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

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".mp4", ".aac", ".flac", ".ogg", ".opus",
              ".wma", ".webm", ".mkv", ".avi", ".mov", ".amr", ".3gp"}


def get_vocabulary():
    """Domain terms from vocabulary.txt, hinted to the engines so company
    jargon and names get spelled correctly. Returns None if the file is
    missing or empty."""
    vocab_file = Path(__file__).parent / "vocabulary.txt"
    if not vocab_file.is_file():
        return None
    terms = [line.strip() for line in
             vocab_file.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.strip().startswith("#")]
    return ", ".join(terms)[:800] or None    # keep well under prompt limits


def fmt_ts(seconds: float, srt: bool = False) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if srt:
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def collect_inputs(paths):
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(f for f in sorted(path.iterdir())
                         if f.suffix.lower() in AUDIO_EXTS)
        elif path.is_file():
            files.append(path)
        else:
            print(f"warning: not found, skipping: {path}", file=sys.stderr)
    return files


def transcribe_file(get_model, audio_path: Path, args):
    print(f"\n=== {audio_path.name} ===")
    t0 = time.time()

    want_speakers = args.speakers or args.num_speakers
    segments = None
    if args.cloud:
        import cloud
        try:
            segments, info = cloud.transcribe(
                audio_path, language=args.language,
                translate=args.translate, want_words=bool(want_speakers),
                prompt=get_vocabulary())
        except cloud.CloudUnavailable as e:
            print(f"cloud unavailable — using the local engine.\n({e})\n")
    if segments is None:
        model = get_model()
        kwargs = dict(
            language=args.language,
            task="translate" if args.translate else "transcribe",
            beam_size=args.beam_size,
            word_timestamps=bool(want_speakers),
            hotwords=get_vocabulary(),
        )
        if args.no_batch or args.no_vad:
            segments, info = model.transcribe(
                str(audio_path), vad_filter=not args.no_vad,
                vad_parameters={"min_silence_duration_ms": 500}, **kwargs)
        else:
            # batched pipeline runs several VAD-cut chunks through the model
            # at once — much faster on multi-core CPU for long recordings
            from faster_whisper import BatchedInferencePipeline
            pipeline = BatchedInferencePipeline(model=model)
            segments, info = pipeline.transcribe(
                str(audio_path), batch_size=args.batch_size, **kwargs)

    print(f"detected language: {info.language} "
          f"(probability {info.language_probability:.0%}), "
          f"duration {fmt_ts(info.duration)}")

    seg_list = []
    for seg in segments:  # generator — transcription happens as we iterate
        seg_list.append(seg)
        print(f"[{fmt_ts(seg.start)} -> {fmt_ts(seg.end)}] {seg.text.strip()}")

    elapsed = time.time() - t0
    print(f"done in {elapsed:.1f}s "
          f"({info.duration / elapsed:.1f}x realtime)" if elapsed > 0 else "done")

    # lines to write: (start, end, text) — speaker turns when diarizing,
    # otherwise the raw Whisper segments
    lines = [(s.start, s.end, s.text.strip()) for s in seg_list]
    if want_speakers:
        from faster_whisper.audio import decode_audio

        from diarize import diarize_words
        from voices import display_name, match_speakers
        print("labelling speakers...")
        words = [(w.start, w.end, w.word)
                 for s in seg_list for w in (s.words or [])]
        audio = decode_audio(str(audio_path), sampling_rate=16000)
        turns, n, centroids = diarize_words(audio, words, args.num_speakers)
        if turns:
            print(f"speakers found: {n}")
            names = match_speakers(centroids)
            if names:
                print("recognized voices: " + ", ".join(
                    f"Speaker {num} = {name}" for num, name in
                    sorted(names.items())))
            lines = [(st, en, f"{display_name(spk, names)}: {tx}")
                     for spk, st, en, tx in turns]
            for _, _, tx in lines:
                print(tx)

    out_dir = Path(args.output_dir) if args.output_dir else audio_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / audio_path.stem

    txt_path = stem.with_suffix(".txt")
    txt_path.write_text("\n".join(tx for _, _, tx in lines) + "\n",
                        encoding="utf-8")
    written = [txt_path]

    if args.srt:
        blocks = []
        for i, (st, en, tx) in enumerate(lines, 1):
            blocks.append(f"{i}\n{fmt_ts(st, srt=True)} --> "
                          f"{fmt_ts(en, srt=True)}\n{tx}\n")
        srt_path = stem.with_suffix(".srt")
        srt_path.write_text("\n".join(blocks), encoding="utf-8")
        written.append(srt_path)

    if args.json:
        data = {
            "file": str(audio_path),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": [{"start": st, "end": en, "text": tx}
                         for st, en, tx in lines],
        }
        json_path = stem.with_suffix(".json")
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        written.append(json_path)

    print("saved: " + ", ".join(str(w) for w in written))


def main():
    parser = argparse.ArgumentParser(
        description="Offline transcription for Indian languages + English.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("inputs", nargs="+",
                        help="audio/video file(s) or folder(s) to transcribe")
    parser.add_argument("--model", default="medium",
                        help="Whisper model: tiny, base, small, medium, "
                             "large-v3 (best accuracy, slowest on CPU)")
    parser.add_argument("--language", default=None, metavar="CODE",
                        help="force language (hi, ta, te, bn, mr, gu, kn, ml, "
                             "pa, ur, or, as, ne, en ...); default: auto-detect")
    parser.add_argument("--translate", action="store_true",
                        help="translate the speech to English instead of "
                             "transcribing in the original language")
    parser.add_argument("--cloud", action="store_true",
                        help="use the free Groq cloud: ~100x faster and more "
                             "accurate, needs internet + a free API key "
                             "(instructions are printed if it's missing); "
                             "falls back to the local engine automatically")
    parser.add_argument("--srt", action="store_true",
                        help="also write an .srt subtitle file")
    parser.add_argument("--json", action="store_true",
                        help="also write a .json file with timestamps")
    parser.add_argument("--speakers", action="store_true",
                        help="label each line with Speaker 1/2/... "
                             "(offline diarization; speaker count inferred)")
    parser.add_argument("--num-speakers", type=int, default=None, metavar="N",
                        help="like --speakers but with a known speaker count")
    parser.add_argument("--output-dir", default=None,
                        help="where to write outputs (default: next to input)")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8,
                        help="chunks transcribed at once (higher = faster, "
                             "more RAM)")
    parser.add_argument("--no-batch", action="store_true",
                        help="disable batched inference (slower, but exact "
                             "same behaviour as before)")
    parser.add_argument("--no-vad", action="store_true",
                        help="disable voice-activity-detection filtering "
                             "(also disables batching)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = parser.parse_args()

    files = collect_inputs(args.inputs)
    if not files:
        print("error: no audio files found", file=sys.stderr)
        sys.exit(1)

    cache = {}

    def get_model():
        if "model" not in cache:
            from faster_whisper import WhisperModel  # deferred: slow import
            compute = "int8" if args.device == "cpu" else "float16"
            print(f"loading model '{args.model}' on {args.device} "
                  f"({compute}) ...")
            print("(first use of a model downloads it once; after that it's "
                  "fully offline)")
            cache["model"] = WhisperModel(args.model, device=args.device,
                                          compute_type=compute,
                                          cpu_threads=os.cpu_count() or 4)
        return cache["model"]

    if not args.cloud:
        get_model()      # load upfront so the wait happens before file 1

    for f in files:
        try:
            transcribe_file(get_model, f, args)
        except Exception as e:
            print(f"error transcribing {f}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
