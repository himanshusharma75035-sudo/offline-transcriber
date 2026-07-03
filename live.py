"""Live microphone transcription — fully offline.

Listens to the microphone, waits for you to pause, then transcribes the
utterance and prints it. Ctrl+C stops and saves the full session transcript.

Usage:
    live.bat                     # auto-detect language, small model
    live.bat --language hi       # lock to Hindi
    live.bat --model medium      # better accuracy, slower response
    live.bat --list-devices      # show microphones
    live.bat --input-device 2    # use a specific microphone
"""

import argparse
import queue
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

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


def rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block ** 2)))


def main():
    parser = argparse.ArgumentParser(
        description="Live offline microphone transcription.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                print(f"{i}: {d['name']}")
        return

    from faster_whisper import WhisperModel
    print(f"loading model '{args.model}' ...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    audio_q = queue.Queue()

    def callback(indata, frames, t, status):
        if status:
            print(status, file=sys.stderr)
        audio_q.put(indata[:, 0].copy())

    transcript = []

    def transcribe_chunk(audio: np.ndarray):
        segments, info = model.transcribe(
            audio, language=args.language,
            task="translate" if args.translate else "transcribe",
            beam_size=2, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        if text:
            stamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{stamp} {info.language}] {text}"
            print(line, flush=True)
            transcript.append(line)

    print("listening... speak, then pause. Ctrl+C to stop and save.\n")
    buffer = []          # list of audio blocks in the current utterance
    speech_seen = 0.0    # seconds of speech in the buffer
    silence_run = 0.0    # seconds of trailing silence

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", device=args.input_device,
                            blocksize=int(SAMPLE_RATE * BLOCK_SECONDS),
                            callback=callback):
            while True:
                block = audio_q.get()
                loud = rms(block) >= args.silence_threshold
                if loud:
                    buffer.append(block)
                    speech_seen += BLOCK_SECONDS
                    silence_run = 0.0
                elif buffer:
                    buffer.append(block)   # keep a little trailing silence
                    silence_run += BLOCK_SECONDS

                buffered = len(buffer) * BLOCK_SECONDS
                if buffer and (silence_run >= END_SILENCE
                               or buffered >= MAX_UTTERANCE):
                    if speech_seen >= MIN_SPEECH:
                        transcribe_chunk(np.concatenate(buffer))
                    buffer, speech_seen, silence_run = [], 0.0, 0.0
    except KeyboardInterrupt:
        pass

    if buffer and speech_seen >= MIN_SPEECH:
        transcribe_chunk(np.concatenate(buffer))

    if transcript:
        out = Path(__file__).parent / (
            "live_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt")
        out.write_text("\n".join(transcript) + "\n", encoding="utf-8")
        print(f"\nsaved session transcript: {out}")
    else:
        print("\nno speech captured.")


if __name__ == "__main__":
    main()
