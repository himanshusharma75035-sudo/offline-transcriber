"""Live transcription — microphone, call audio (Teams/Zoom), or both.

Fully offline. Sources:
  --source mic    your microphone (default)
  --source call   what you HEAR — captures system audio via a loopback
                  device (Stereo Mix or VB-Audio Cable), so an online
                  meeting's other participants are transcribed live
  --source both   mic + call together; lines are tagged [you] / [call]

Ctrl+C stops and saves the full session transcript.

Usage:
    live.bat                          # dictate with your mic
    live.bat --source call            # transcribe a Teams/Zoom call live
    live.bat --source both --language hi
    live.bat --list-devices           # show capture devices
"""

import argparse
import queue
import sys
from datetime import datetime

import numpy as np
import sounddevice as sd

from . import paths

# Windows consoles often default to a legacy codepage that can't print
# Indian scripts; force UTF-8 so Devanagari/Tamil/etc. don't crash output.
# (Under pythonw there is no console, so the streams are None.)
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.25          # granularity of the capture loop
SILENCE_RMS = 0.01            # below this = silence
END_SILENCE = 0.8             # seconds of silence that ends an utterance
MAX_UTTERANCE = 12.0          # force a flush after this many seconds
MIN_SPEECH = 0.4              # ignore blips shorter than this
LOOPBACK_KEYWORDS = ("stereo mix", "cable output", "loopback", "what u hear")


def rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block ** 2)))


def find_loopback_device():
    """Find a device that captures system audio (what the speakers play).

    Windows enumerates the same physical device once per host API (MME,
    DirectSound, WASAPI, WDM-KS); only some accept a 16 kHz mono stream
    (PortAudio does not resample). Prefer a candidate that actually opens.
    """
    candidates = [i for i, d in enumerate(sd.query_devices())
                  if d["max_input_channels"] > 0
                  and any(k in d["name"].lower() for k in LOOPBACK_KEYWORDS)]
    for i in candidates:
        try:
            sd.check_input_settings(device=i, samplerate=SAMPLE_RATE,
                                    channels=1, dtype="float32")
            return i
        except Exception:
            continue
    return candidates[0] if candidates else None


def resolve_sources(source, mic_device):
    """[(tag, device_index_or_None)] for the requested capture mode."""
    if source == "mic":
        return [("you", mic_device)]
    loop = find_loopback_device()
    if loop is None:
        print("error: no system-audio capture device found.\n"
              "Enable 'Stereo Mix' (Sound settings > Recording devices) or\n"
              "install VB-Audio Cable (vb-audio.com/Cable, free) and set it\n"
              "as the meeting app's speaker.", file=sys.stderr)
        sys.exit(1)
    if source == "call":
        return [("call", loop)]
    return [("you", mic_device), ("call", loop)]


def main():
    parser = argparse.ArgumentParser(
        description="Live offline transcription of mic and/or call audio.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--source", default="mic",
                        choices=["mic", "call", "both"],
                        help="what to listen to (call = system audio, e.g. "
                             "an online meeting)")
    parser.add_argument("--model", default="small",
                        help="tiny/base/small are responsive; medium/large-v3 "
                             "are more accurate but lag on CPU")
    parser.add_argument("--language", default=None, metavar="CODE",
                        help="force language (hi, ta, bn, en ...); "
                             "default: auto-detect per utterance")
    parser.add_argument("--translate", action="store_true",
                        help="output English translation of whatever is spoken")
    parser.add_argument("--input-device", type=int, default=None,
                        help="microphone index from --list-devices")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--silence-threshold", type=float, default=SILENCE_RMS,
                        help="raise if background noise keeps triggering it")
    args = parser.parse_args()

    if args.list_devices:
        loop = find_loopback_device()
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                mark = "  <- call capture" if i == loop else ""
                print(f"{i}: {d['name']}{mark}")
        return

    sources = resolve_sources(args.source, args.input_device)
    tagged = len(sources) > 1

    from faster_whisper import WhisperModel

    from .transcribe import get_vocabulary
    print(f"loading model '{args.model}' ...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    audio_q = queue.Queue()
    transcript = []

    def make_callback(tag):
        def callback(indata, frames, t, status):
            audio_q.put((tag, indata[:, 0].copy()))
        return callback

    def transcribe_chunk(tag, audio):
        segments, info = model.transcribe(
            audio, language=args.language,
            task="translate" if args.translate else "transcribe",
            beam_size=2, vad_filter=True, hotwords=get_vocabulary())
        text = " ".join(s.text.strip() for s in segments).strip()
        if text:
            stamp = datetime.now().strftime("%H:%M:%S")
            label = f" {tag}" if tagged else ""
            line = f"[{stamp} {info.language}{label}] {text}"
            print(line, flush=True)
            transcript.append(line)

    what = " + ".join(tag for tag, _ in sources)
    print(f"listening ({what})... Ctrl+C to stop and save.\n")
    bufs = {tag: [] for tag, _ in sources}
    speech = {tag: 0.0 for tag, _ in sources}
    silence = {tag: 0.0 for tag, _ in sources}

    def feed(tag, block, drain_all=False):
        loud = rms(block) >= args.silence_threshold
        if loud:
            bufs[tag].append(block)
            speech[tag] += BLOCK_SECONDS
            silence[tag] = 0.0
        elif bufs[tag]:
            bufs[tag].append(block)   # keep a little trailing silence
            silence[tag] += BLOCK_SECONDS
        buffered = len(bufs[tag]) * BLOCK_SECONDS
        if bufs[tag] and (silence[tag] >= END_SILENCE
                          or buffered >= MAX_UTTERANCE or drain_all):
            if speech[tag] >= MIN_SPEECH:
                transcribe_chunk(tag, np.concatenate(bufs[tag]))
            bufs[tag], speech[tag], silence[tag] = [], 0.0, 0.0

    def save_transcript():
        if not transcript:
            print("\nno speech captured.")
            return
        out = paths.data_dir() / (
            "live_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt")
        out.write_text("\n".join(transcript) + "\n", encoding="utf-8")
        print(f"\nsaved session transcript: {out}")

    streams = [sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                              dtype="float32", device=dev,
                              blocksize=int(SAMPLE_RATE * BLOCK_SECONDS),
                              callback=make_callback(tag))
               for tag, dev in sources]
    try:
        for s in streams:
            s.start()
        # timeout so Ctrl+C is honoured promptly and, if every stream dies
        # silently (device unplugged, endpoint change), we don't hang forever
        while any(s.active for s in streams):
            try:
                tag, block = audio_q.get(timeout=0.3)
            except queue.Empty:
                continue
            feed(tag, block)
        else:
            print("\naudio device stopped; saving what was captured.",
                  file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        # Everything below must run even on a second Ctrl+C or a transcribe
        # error, or an entire meeting's transcript is lost.
        try:
            for s in streams:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
            # drain whatever is still queued, then flush the open buffers
            while True:
                try:
                    tag, block = audio_q.get_nowait()
                except queue.Empty:
                    break
                feed(tag, block)
            for tag, _ in sources:
                feed(tag, np.zeros(int(SAMPLE_RATE * BLOCK_SECONDS),
                                   dtype=np.float32), drain_all=True)
        except BaseException as e:      # never lose the transcript to cleanup
            print(f"\n(finishing early: {e})", file=sys.stderr)
        save_transcript()


if __name__ == "__main__":
    main()
