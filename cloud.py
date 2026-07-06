"""Free cloud transcription via Groq (optional speed boost).

Groq's free tier runs Whisper large-v3-turbo on their hardware at roughly
200x realtime — an hour of audio transcribes in about a minute, with better
accuracy than the local 'medium' model. Free limits (no credit card):
about 8 hours of audio per day, 20 requests per minute.

One-time setup:
  1. Create a free account at https://console.groq.com
  2. Create an API key at https://console.groq.com/keys
  3. Save it either:
       - in a file named  groq_api_key.txt  next to this script, or
       - in the GROQ_API_KEY environment variable.

Privacy note: cloud mode uploads the audio to Groq. Use the offline engine
for recordings that must not leave the machine.

Long recordings are split into 10-minute chunks at quiet points (the free
tier caps uploads at 25 MB) and the results are stitched back together.
"""

import http.client
import io
import json
import os
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

# Whisper's language table (name -> ISO code): the API echoes full names
# ("english") while the local engine uses codes ("en") — we normalize to
# codes so both engines report language identically.
LANGUAGE_CODES = {
    "english": "en", "chinese": "zh", "german": "de", "spanish": "es",
    "russian": "ru", "korean": "ko", "french": "fr", "japanese": "ja",
    "portuguese": "pt", "turkish": "tr", "polish": "pl", "catalan": "ca",
    "dutch": "nl", "arabic": "ar", "swedish": "sv", "italian": "it",
    "indonesian": "id", "hindi": "hi", "finnish": "fi", "vietnamese": "vi",
    "hebrew": "he", "ukrainian": "uk", "greek": "el", "malay": "ms",
    "czech": "cs", "romanian": "ro", "danish": "da", "hungarian": "hu",
    "tamil": "ta", "norwegian": "no", "thai": "th", "urdu": "ur",
    "croatian": "hr", "bulgarian": "bg", "lithuanian": "lt", "latin": "la",
    "maori": "mi", "malayalam": "ml", "welsh": "cy", "slovak": "sk",
    "telugu": "te", "persian": "fa", "latvian": "lv", "bengali": "bn",
    "serbian": "sr", "azerbaijani": "az", "slovenian": "sl", "kannada": "kn",
    "estonian": "et", "macedonian": "mk", "breton": "br", "basque": "eu",
    "icelandic": "is", "armenian": "hy", "nepali": "ne", "mongolian": "mn",
    "bosnian": "bs", "kazakh": "kk", "albanian": "sq", "swahili": "sw",
    "galician": "gl", "marathi": "mr", "punjabi": "pa", "sinhala": "si",
    "khmer": "km", "shona": "sn", "yoruba": "yo", "somali": "so",
    "afrikaans": "af", "occitan": "oc", "georgian": "ka", "belarusian": "be",
    "tajik": "tg", "sindhi": "sd", "gujarati": "gu", "amharic": "am",
    "yiddish": "yi", "lao": "lo", "uzbek": "uz", "faroese": "fo",
    "haitian creole": "ht", "pashto": "ps", "turkmen": "tk", "nynorsk": "nn",
    "maltese": "mt", "sanskrit": "sa", "luxembourgish": "lb", "myanmar": "my",
    "tibetan": "bo", "tagalog": "tl", "malagasy": "mg", "assamese": "as",
    "tatar": "tt", "hawaiian": "haw", "lingala": "ln", "hausa": "ha",
    "bashkir": "ba", "javanese": "jw", "sundanese": "su", "cantonese": "yue",
}

API_BASE = "https://api.groq.com/openai/v1/audio/"
TRANSCRIBE_MODEL = "whisper-large-v3-turbo"
TRANSLATE_MODEL = "whisper-large-v3"   # Groq's /translations needs large-v3
SAMPLE_RATE = 16000
CHUNK_SECONDS = 600                    # 10 min of 16 kHz s16 WAV ≈ 19 MB
SPLIT_SEARCH_SECONDS = 20              # hunt for silence this far around a cut
MAX_RETRIES = 3


class CloudUnavailable(Exception):
    """Cloud transcription can't be used right now (no key, offline, ...)."""


def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        key_file = Path(__file__).parent / "groq_api_key.txt"
        if key_file.is_file():
            key = key_file.read_text(encoding="utf-8").strip()
    return key or None


SETUP_HELP = """cloud mode needs a free Groq API key (one-time, ~2 minutes):
  1. create a free account at https://console.groq.com
  2. create a key at https://console.groq.com/keys
  3. paste it into a file named groq_api_key.txt next to the scripts,
     or set the GROQ_API_KEY environment variable"""


def _split_points(audio):
    """Chunk boundaries (sample offsets), cutting at the quietest moment
    near each 10-minute mark so words aren't sliced in half."""
    chunk = CHUNK_SECONDS * SAMPLE_RATE
    if len(audio) <= chunk:
        return [(0, len(audio))]
    search = SPLIT_SEARCH_SECONDS * SAMPLE_RATE
    frame = SAMPLE_RATE // 2                       # 0.5 s energy frames
    points, start = [], 0
    while len(audio) - start > chunk:
        target = start + chunk
        lo = max(start + chunk - search, start + frame)
        hi = min(target + search, len(audio) - frame)
        best, best_rms = target, float("inf")
        for pos in range(lo, hi, frame):
            rms = float(np.sqrt(np.mean(audio[pos:pos + frame] ** 2)))
            if rms < best_rms:
                best, best_rms = pos, rms
        points.append((start, best))
        start = best
    points.append((start, len(audio)))
    return points


def _wav_bytes(audio):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16)
                      .tobytes())
    return buf.getvalue()


def _multipart(fields, file_bytes):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields:
        body.write(f"--{boundary}\r\nContent-Disposition: form-data; "
                   f"name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    body.write(f"--{boundary}\r\nContent-Disposition: form-data; "
               f"name=\"file\"; filename=\"audio.wav\"\r\n"
               f"Content-Type: audio/wav\r\n\r\n".encode())
    body.write(file_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def _request(endpoint, fields, wav, key, log=print):
    body, content_type = _multipart(fields, wav)
    last_error = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(
            API_BASE + endpoint, data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": content_type,
                     # Groq's edge (Cloudflare) 403s urllib's default UA
                     "User-Agent": "offline-transcriber/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read()).get("error", {}).get("message", "")
            except Exception:
                pass
            if e.code == 401:
                raise CloudUnavailable(
                    "the API key was rejected (401). " + SETUP_HELP)
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                try:
                    wait = min(float(e.headers.get("retry-after") or 15), 60)
                except ValueError:      # Retry-After can be an HTTP date
                    wait = 15
                log(f"  rate limited by Groq, waiting {wait:.0f}s...")
                time.sleep(wait)
                last_error = f"rate limited (429): {detail}"
                continue
            raise CloudUnavailable(f"Groq error {e.code}: {detail}")
        except (urllib.error.URLError, OSError, TimeoutError,
                http.client.HTTPException, ValueError) as e:
            # URLError/OSError: no connection; HTTPException: connection
            # dropped mid-response; ValueError: non-JSON body (captive
            # portal / proxy). All mean "can't use the cloud right now".
            raise CloudUnavailable(f"no usable connection to Groq ({e})")
    raise CloudUnavailable(last_error or "retries exhausted")


def transcribe(audio_path, language=None, translate=False, want_words=False,
               prompt=None, log=print):
    """Transcribe (or translate) a file with Groq.

    Returns (segments, info) shaped like faster-whisper's output: segments
    have .start/.end/.text/.words; info has .language,
    .language_probability, .duration. Raises CloudUnavailable if the cloud
    can't be used (caller should fall back to the local engine).
    """
    key = get_api_key()
    if not key:
        raise CloudUnavailable(SETUP_HELP)

    from faster_whisper.audio import decode_audio
    audio = decode_audio(str(audio_path), sampling_rate=SAMPLE_RATE)
    duration = len(audio) / SAMPLE_RATE
    if duration < 0.1:      # header-only / broken file: nothing to upload
        return [], SimpleNamespace(language=language or "unknown",
                                   language_probability=1.0,
                                   duration=duration)

    if translate:
        endpoint, model = "translations", TRANSLATE_MODEL
    else:
        endpoint, model = "transcriptions", TRANSCRIBE_MODEL

    parts = _split_points(audio)
    segments, language_seen = [], None
    for i, (start, end) in enumerate(parts, 1):
        if len(parts) > 1:
            log(f"  cloud: uploading part {i}/{len(parts)}...")
        fields = [("model", model), ("response_format", "verbose_json"),
                  ("temperature", "0")]
        if language and not translate:
            fields.append(("language", language))
        if prompt:
            fields.append(("prompt", prompt))
        if want_words:
            fields.append(("timestamp_granularities[]", "word"))
            fields.append(("timestamp_granularities[]", "segment"))
        data = _request(endpoint, fields, _wav_bytes(audio[start:end]), key,
                        log=log)

        offset = start / SAMPLE_RATE
        language_seen = language_seen or data.get("language")
        words = [SimpleNamespace(start=w["start"] + offset,
                                 end=w["end"] + offset,
                                 word=w["word"] if w["word"].startswith(" ")
                                 else " " + w["word"])
                 for w in data.get("words") or []]
        chunk_segs = [SimpleNamespace(start=seg["start"] + offset,
                                      end=seg["end"] + offset,
                                      text=seg["text"], words=[])
                      for seg in data.get("segments") or []]
        if not chunk_segs and data.get("text"):
            chunk_segs = [SimpleNamespace(start=offset,
                                          end=end / SAMPLE_RATE,
                                          text=data["text"], words=[])]
        # assign every word to exactly one segment: the one containing its
        # midpoint, else the nearest (word timestamps routinely stray into
        # the silence gaps between segments — those words must not be lost)
        for w in words:
            mid = (w.start + w.end) / 2
            best = min(chunk_segs, default=None,
                       key=lambda s: max(s.start - mid, mid - s.end, 0.0))
            if best is not None:
                best.words.append(w)
        for s in chunk_segs:
            s.words = s.words or None
        segments.extend(chunk_segs)

    # normalize: the API echoes full names ("english"), the local engine
    # uses ISO codes ("en") — an explicitly requested language wins
    detected = LANGUAGE_CODES.get((language_seen or "").strip().lower(),
                                  language_seen)
    info = SimpleNamespace(language=language or detected or "unknown",
                           language_probability=1.0, duration=duration)
    return segments, info
