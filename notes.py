"""Turn a transcript into meeting notes (summary, key points, action items).

Two engines, tried in order:
  1. Groq free tier (same key as cloud transcription) — a 70B-class model,
     finishes in seconds.
  2. Local Ollama — fully offline, minutes on CPU.

Raises NotesUnavailable if neither is available.
"""

import json
import urllib.error
import urllib.request

from cloud import get_api_key

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
# preference order for the notes model; first substring match wins
GROQ_PREFERRED = ["llama-3.3-70b", "llama-4", "70b", "qwen", "instant"]
OLLAMA = "http://localhost:11434"
# a 1-hour meeting is ~15k tokens — fits one call for Groq's big models;
# chunk only truly huge inputs (and always chunk for small local models)
GROQ_CHUNK_CHARS = 100_000
OLLAMA_CHUNK_CHARS = 12_000


class NotesUnavailable(Exception):
    pass


PROMPT = """You are an assistant writing meeting notes from a transcript.
Write in {language}. Produce exactly these sections in markdown:

## Summary
A short paragraph on what the meeting was about and what was concluded.

## Key points
Bullet list of the important facts, numbers and decisions.

## Action items
Bullet list of tasks with owner if mentioned (e.g. "- Tania: send the
report by email tonight"). Use the speaker names from the transcript when
they are present. Write "None mentioned." if there are none.

Transcript:
{text}"""

MERGE_PROMPT = """These are notes from consecutive parts of one meeting.
Merge them into a single set of notes in {language} with the same three
sections (Summary, Key points, Action items), removing duplicates:

{text}"""


def _groq_json(url, payload=None, key=None, timeout=120):
    headers = {"Authorization": f"Bearer {key}",
               "User-Agent": "offline-transcriber/1.0"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    with urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=headers),
            timeout=timeout) as r:
        return json.loads(r.read())


def _pick_groq_model(key):
    models = [m["id"] for m in _groq_json(GROQ_MODELS_URL, key=key)["data"]]
    chat = [m for m in models
            if not any(x in m.lower() for x in
                       ("whisper", "tts", "guard", "embed", "vision"))]
    for pref in GROQ_PREFERRED:
        for m in chat:
            if pref in m.lower():
                return m
    return chat[0] if chat else None


def _groq_generate(prompt, key, model):
    data = _groq_json(GROQ_CHAT_URL, {
        "model": model, "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }, key=key, timeout=300)
    return data["choices"][0]["message"]["content"].strip()


def _ollama_generate(prompt, model):
    req = urllib.request.Request(
        OLLAMA + "/api/generate",
        data=json.dumps({"model": model, "prompt": prompt,
                         "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())["response"].strip()


def _ollama_model(preferred=None):
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
        models = sorted(json.loads(r.read()).get("models", []),
                        key=lambda m: m.get("size", 0))
    if preferred:
        return preferred
    return models[0]["name"] if models else None


def _chunked(text, generate, language, chunk_chars, log):
    chunks = [text[i:i + chunk_chars]
              for i in range(0, len(text), chunk_chars)]
    parts = []
    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            log(f"  notes: part {i}/{len(chunks)}...")
        parts.append(generate(PROMPT.format(language=language, text=chunk)))
    if len(parts) == 1:
        return parts[0]
    return generate(MERGE_PROMPT.format(language=language,
                                        text="\n\n---\n\n".join(parts)))


def generate_notes(text, language="English", llm=None, log=print):
    """Meeting notes from transcript text. Groq first, then Ollama."""
    text = text.strip()
    if not text:
        raise NotesUnavailable("the transcript is empty")

    key = get_api_key()
    if key:
        try:
            model = llm or _pick_groq_model(key)
            if model:
                log(f"  notes: using {model} via Groq (free cloud)...")
                return _chunked(text, lambda p: _groq_generate(p, key, model),
                                language, GROQ_CHUNK_CHARS, log)
        except (urllib.error.URLError, OSError, TimeoutError, KeyError,
                ValueError) as e:
            log(f"  notes: Groq unavailable ({e}), trying local Ollama...")

    try:
        model = _ollama_model(llm)
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        raise NotesUnavailable(
            "no Groq key and Ollama isn't running — add groq_api_key.txt "
            "(free, console.groq.com) or install Ollama (ollama.com)")
    if not model:
        raise NotesUnavailable(
            "Ollama is running but has no models; run: ollama pull llama3.2:3b")
    log(f"  notes: using {model} via Ollama (local, slower on CPU)...")
    try:
        return _chunked(text, lambda p: _ollama_generate(p, model),
                        language, OLLAMA_CHUNK_CHARS, log)
    except (urllib.error.URLError, OSError, TimeoutError, KeyError,
            ValueError) as e:
        raise NotesUnavailable(f"Ollama failed: {e}")
