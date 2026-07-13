"""Voice memory: recognize known speakers by name across meetings.

After a diarized transcription you can name the speakers once (GUI:
"Name speakers" button). Each name is stored with that speaker's voice
fingerprint (ECAPA embedding) in speaker_profiles.json — from then on,
future transcriptions label them by name automatically.

Everything stays local; the profiles file never leaves this folder.
"""

import json
import os
from pathlib import Path

import numpy as np

PROFILES_FILE = Path(__file__).parent / "speaker_profiles.json"
BACKUP_FILE = Path(__file__).parent / "speaker_profiles.bak.json"
# cosine similarity needed to call a voice "the same person"; ECAPA
# same-speaker similarity across sessions is typically 0.6-0.85,
# different speakers 0.0-0.4
MATCH_THRESHOLD = 0.55
MAX_SAMPLES_PER_PERSON = 5


def _read(path):
    """Parse a profiles file into {name: [embedding, ...]}, or None if it
    is missing / unreadable / not the expected shape."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return {name: [np.asarray(e, dtype=np.float32) for e in embs]
                for name, embs in data.items()
                if isinstance(embs, list)}
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def load_profiles():
    """Load enrolled voices, falling back to the backup if the main file
    is corrupt. Never raises — returns {} if nothing is readable."""
    profiles = _read(PROFILES_FILE)
    if profiles is not None:
        return profiles
    # main file is missing or corrupt; try the backup before giving up
    backup = _read(BACKUP_FILE)
    if backup is not None:
        # preserve the corrupt file for inspection instead of overwriting it
        if PROFILES_FILE.is_file():
            try:
                PROFILES_FILE.replace(PROFILES_FILE.with_suffix(".corrupt.json"))
            except OSError:
                pass
        return backup
    return {}


def save_profiles(profiles):
    """Write profiles atomically (temp file + os.replace) and keep the
    previous good version as a backup, so a partial/interrupted write can
    never destroy the enrolled voices."""
    data = {name: [np.asarray(e, dtype=np.float32).round(5).tolist()
                   for e in embs]
            for name, embs in profiles.items()}
    if PROFILES_FILE.is_file():               # snapshot the current good file
        try:
            PROFILES_FILE.replace(BACKUP_FILE)
        except OSError:
            pass
    tmp = PROFILES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, PROFILES_FILE)            # atomic on Windows and POSIX


def _similarity(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def enroll(name, embedding, profiles=None):
    """Add (or reinforce) a person's voice fingerprint."""
    profiles = load_profiles() if profiles is None else profiles
    samples = profiles.setdefault(name, [])
    samples.append(np.asarray(embedding, dtype=np.float32))
    del samples[:-MAX_SAMPLES_PER_PERSON]
    save_profiles(profiles)
    return profiles


def match_speakers(centroids):
    """Match diarization clusters against enrolled voices.

    centroids: {speaker_number: embedding}. Returns {speaker_number: name}
    for the clusters that confidently match an enrolled person; each name
    is used at most once (best-scoring cluster wins).
    """
    profiles = load_profiles()
    if not profiles or not centroids:
        return {}
    scores = []      # (similarity, speaker_number, name)
    for num, emb in centroids.items():
        for name, samples in profiles.items():
            best = max((_similarity(emb, s) for s in samples), default=0.0)
            if best >= MATCH_THRESHOLD:
                scores.append((best, num, name))
    assigned, used_nums, used_names = {}, set(), set()
    for _score, num, name in sorted(scores, reverse=True):
        if num not in used_nums and name not in used_names:
            assigned[num] = name
            used_nums.add(num)
            used_names.add(name)
    return assigned


def display_name(num, names):
    return names.get(num, f"Speaker {num}")
