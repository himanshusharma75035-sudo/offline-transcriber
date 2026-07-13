"""Meeting notes: chunking/merge logic and the offline-only routing (Groq is
skipped unless cloud is explicitly enabled; local Ollama otherwise)."""

import urllib.error

import pytest

from transcriber import notes


def test_empty_transcript_raises():
    with pytest.raises(notes.NotesUnavailable):
        notes.generate_notes("   ")


def test_chunked_single_pass_returns_generated_text():
    calls = []

    def gen(prompt):
        calls.append(prompt)
        return "NOTES"

    out = notes._chunked("short text", gen, "English",
                         chunk_chars=1000, log=lambda *_: None)
    assert out == "NOTES"
    assert len(calls) == 1                       # no merge pass for one chunk


def test_chunked_multi_chunk_merges():
    calls = []

    def gen(prompt):
        calls.append(prompt)
        return f"part{len(calls)}"

    out = notes._chunked("abcdefgh", gen, "English",
                         chunk_chars=3, log=lambda *_: None)
    # 8 chars / 3 -> 3 chunks, then 1 merge pass = 4 generate calls
    assert len(calls) == 4
    assert "Merge them" in calls[-1]             # final call is the merge prompt
    assert out == "part4"


def test_offline_skips_groq_and_uses_ollama(monkeypatch):
    from transcriber import policy
    monkeypatch.setattr(policy, "cloud_allowed", lambda: False)

    def boom(*_a, **_k):
        raise AssertionError("Groq must not be contacted when offline")

    monkeypatch.setattr(notes, "_pick_groq_model", boom)
    monkeypatch.setattr(notes, "_groq_generate", boom)
    monkeypatch.setattr(notes, "_ollama_model", lambda *_a, **_k: "llama3.2:3b")
    monkeypatch.setattr(notes, "_ollama_generate", lambda *_a, **_k: "LOCAL")

    assert notes.generate_notes("hello meeting") == "LOCAL"


def test_offline_without_ollama_reports_ollama_not_groq(monkeypatch):
    from transcriber import policy
    monkeypatch.setattr(policy, "cloud_allowed", lambda: False)

    def no_ollama(*_a, **_k):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(notes, "_ollama_model", no_ollama)
    with pytest.raises(notes.NotesUnavailable) as exc:
        notes.generate_notes("hello")
    msg = str(exc.value).lower()
    assert "ollama" in msg and "groq" not in msg   # offline advice, no key nag


def test_cloud_enabled_uses_groq(monkeypatch):
    from transcriber import policy
    monkeypatch.setattr(policy, "cloud_allowed", lambda: True)
    monkeypatch.setattr(notes, "get_api_key", lambda: "gsk_test")
    monkeypatch.setattr(notes, "_pick_groq_model", lambda key: "llama-3.3-70b")
    monkeypatch.setattr(notes, "_groq_generate", lambda p, k, m: "CLOUD")

    def boom(*_a, **_k):
        raise AssertionError("Ollama must not run when Groq succeeds")

    monkeypatch.setattr(notes, "_ollama_generate", boom)
    assert notes.generate_notes("hello meeting") == "CLOUD"
