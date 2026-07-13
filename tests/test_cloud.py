"""Cloud helpers: chunking, WAV encoding, language normalisation, and the
policy gate that must block uploads before any network/file access."""

import io
import wave

import numpy as np
import pytest

import cloud


def test_short_audio_is_a_single_chunk():
    audio = np.zeros(cloud.SAMPLE_RATE * 5, dtype=np.float32)   # 5 s
    assert cloud._split_points(audio) == [(0, len(audio))]


def test_long_audio_splits_at_silence_and_stitches(monkeypatch):
    # shrink the chunking constants so the test stays small and deterministic
    monkeypatch.setattr(cloud, "CHUNK_SECONDS", 1)          # chunk = 16000
    monkeypatch.setattr(cloud, "SPLIT_SEARCH_SECONDS", 1)   # frame = 8000
    audio = np.full(cloud.SAMPLE_RATE * 3, 0.5, dtype=np.float32)  # loud 3 s
    audio[16000:24000] = 0.0     # a silent frame exactly on the 1 s boundary
    audio[32000:40000] = 0.0     # and on the 2 s boundary

    parts = cloud._split_points(audio)

    # cuts land on the silent frames, and chunks tile the audio with no gaps
    assert parts == [(0, 16000), (16000, 32000), (32000, 48000)]
    assert parts[0][0] == 0 and parts[-1][1] == len(audio)
    for (_, end), (start, _) in zip(parts, parts[1:], strict=False):
        assert end == start


def test_wav_bytes_roundtrips_as_16k_mono_pcm():
    audio = (np.sin(np.linspace(0, 20, 8000)) * 0.5).astype(np.float32)
    with wave.open(io.BytesIO(cloud._wav_bytes(audio)), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == cloud.SAMPLE_RATE
        assert w.getnframes() == len(audio)


def test_wav_bytes_clips_out_of_range_samples():
    audio = np.array([2.0, -2.0, 0.0], dtype=np.float32)   # beyond [-1, 1]
    with wave.open(io.BytesIO(cloud._wav_bytes(audio)), "rb") as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    assert pcm[0] == 32767 and pcm[1] == -32767      # clipped, not wrapped


@pytest.mark.parametrize("name,code", [
    ("english", "en"), ("hindi", "hi"), ("tamil", "ta"),
    ("bengali", "bn"), ("marathi", "mr"),
])
def test_language_names_normalise_to_iso_codes(name, code):
    assert cloud.LANGUAGE_CODES[name] == code


def test_transcribe_refuses_before_touching_audio_when_offline(monkeypatch):
    # even pointed at a missing file, it must raise on policy, not IO/network
    monkeypatch.delenv("TRANSCRIBER_ALLOW_CLOUD", raising=False)
    import policy
    monkeypatch.setattr(policy, "cloud_allowed", lambda: False)
    with pytest.raises(cloud.CloudUnavailable):
        cloud.transcribe("does-not-exist.wav")
