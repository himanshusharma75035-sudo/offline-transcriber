"""Offline speaker diarization: split a transcript into speaker turns.

Approach:
  1. Slide short windows (1.5 s) over the recording and embed each with a
     speaker-recognition model (SpeechBrain ECAPA-TDNN, MIT license,
     ~80 MB one-time download).
  2. Cluster the embeddings — each cluster is one speaker — giving a
     "who is speaking when" timeline.
  3. Assign every transcribed word to the speaker active at its midpoint
     and group consecutive same-speaker words into turns.

Word-level assignment matters: a single Whisper segment can contain a
speaker change mid-sentence (common in back-to-back conversation).
"""

import os
import sys
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
WINDOW_SECONDS = 1.5
HOP_SECONDS = 0.75
SILENCE_RMS = 0.003          # windows quieter than this are skipped
EMBED_BATCH = 32
# cosine-distance threshold for "same speaker" when the count is unknown;
# raise it if one voice gets split into two, lower it if voices merge
CLUSTER_THRESHOLD = 0.8
# A cluster this small is treated as a boundary artifact (a stray window
# straddling two voices) and merged into the nearest real cluster. Kept as
# a tiny ABSOLUTE count on purpose: a share-based threshold (e.g. 10%) would
# delete a genuine but quiet participant — someone who speaks only a few
# minutes of a long meeting — and their words would be misattributed.
MIN_CLUSTER_WINDOWS = 2

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from speechbrain.inference.speaker import EncoderClassifier
        cache = Path(os.environ.get("SPEECHBRAIN_CACHE",
                                    Path.home() / ".cache" / "speechbrain"))
        print("loading speaker-recognition model (one-time ~80 MB download)...",
              file=sys.stderr)
        _classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(cache / "spkrec-ecapa-voxceleb"))
    return _classifier


def build_timeline(audio: np.ndarray, num_speakers=None):
    """Cluster sliding windows into speakers.

    Returns (times, labels, centroids): center time of each speech window,
    its 1-based speaker number (first voice heard = Speaker 1), and
    {speaker_number: mean embedding} for voice-memory matching.
    """
    import torch
    from sklearn.cluster import AgglomerativeClustering

    size = int(WINDOW_SECONDS * SAMPLE_RATE)
    hop = int(HOP_SECONDS * SAMPLE_RATE)
    chunks, times = [], []
    for start in range(0, max(len(audio) - size, 1), hop):
        chunk = audio[start:start + size]
        if len(chunk) < size:
            chunk = np.pad(chunk, (0, size - len(chunk)))
        if float(np.sqrt(np.mean(chunk ** 2))) >= SILENCE_RMS:
            chunks.append(chunk)
            times.append(start / SAMPLE_RATE + WINDOW_SECONDS / 2)
    if not chunks:
        return [], [], {}
    if len(chunks) == 1:
        with torch.no_grad():
            emb = (_get_classifier()
                   .encode_batch(torch.from_numpy(np.stack(chunks)).float())
                   .squeeze(1).cpu().numpy()[0])
        return times, [1], {1: emb / (np.linalg.norm(emb) or 1.0)}

    classifier = _get_classifier()
    embs = []
    with torch.no_grad():
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = torch.from_numpy(np.stack(chunks[i:i + EMBED_BATCH])).float()
            embs.append(classifier.encode_batch(batch)
                        .squeeze(1).cpu().numpy())
    X = np.concatenate(embs)
    X /= np.linalg.norm(X, axis=1, keepdims=True)

    if num_speakers:
        clusterer = AgglomerativeClustering(
            n_clusters=min(num_speakers, len(chunks)),
            metric="cosine", linkage="average")
    else:
        clusterer = AgglomerativeClustering(
            n_clusters=None, distance_threshold=CLUSTER_THRESHOLD,
            metric="cosine", linkage="average")
    raw = clusterer.fit_predict(X)

    # absorb genuinely tiny (artifact-sized) clusters into the nearest real
    # cluster; a real quiet speaker keeps their own cluster
    if num_speakers is None:
        counts = {lab: int((raw == lab).sum()) for lab in set(raw)}
        big = [lab for lab, c in counts.items() if c > MIN_CLUSTER_WINDOWS]
        if big and len(big) < len(counts):
            cluster_centroids = {lab: X[raw == lab].mean(axis=0)
                                 for lab in big}
            for i, lab in enumerate(raw):
                if lab not in big:
                    raw[i] = min(big, key=lambda b: 1 - float(
                        np.dot(X[i], cluster_centroids[b])
                        / np.linalg.norm(cluster_centroids[b])))

    # temporal smoothing: a lone window between two same-speaker windows is
    # almost always a mis-assignment at a turn boundary
    for i in range(1, len(raw) - 1):
        if raw[i - 1] == raw[i + 1] != raw[i]:
            raw[i] = raw[i - 1]

    order = {}
    for lab in raw:
        if lab not in order:
            order[lab] = len(order) + 1
    labels = [order[lab] for lab in raw]
    centroids = {num: X[np.asarray(labels) == num].mean(axis=0)
                 for num in set(labels)}
    return times, labels, centroids


def diarize_words(audio: np.ndarray, words, num_speakers=None):
    """Group transcribed words into speaker turns.

    words: [(start_s, end_s, text)] from Whisper word timestamps.
    Returns ([(speaker, turn_start_s, turn_end_s, text)], speaker_count,
    {speaker: voice embedding}) — the embeddings feed voice memory
    (voices.py) so known people can be named automatically.
    """
    times, labels, centroids = build_timeline(audio, num_speakers)
    if not times:
        return [], 0, {}
    times_arr = np.asarray(times)

    def speaker_at(t):
        return labels[int(np.abs(times_arr - t).argmin())]

    turns = []
    for start, end, text in words:
        spk = speaker_at((start + end) / 2)
        if turns and turns[-1][0] == spk:
            prev = turns[-1]
            turns[-1] = (spk, prev[1], end, prev[3] + text)
        else:
            turns.append((spk, start, end, text))
    return ([(s, st, en, tx.strip()) for s, st, en, tx in turns],
            max(labels), centroids)
