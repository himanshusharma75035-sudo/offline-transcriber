"""Diarization logic that needs no model download: the quiet-speaker
regression guard and the word -> speaker-turn grouping.

(The clustering/embedding path in build_timeline needs torch + speechbrain
and is covered by monkeypatching it here; a full end-to-end run is exercised
separately with real audio.)"""

import numpy as np

from transcriber import diarize


def test_min_cluster_windows_is_absolute_two():
    # Regression: a share-based threshold (e.g. 10%) deleted genuine but quiet
    # speakers. It must stay a tiny ABSOLUTE count so quiet voices survive.
    assert diarize.MIN_CLUSTER_WINDOWS == 2


def test_diarize_words_groups_consecutive_speakers(monkeypatch):
    times = [0.5, 1.5, 2.5]
    labels = [1, 1, 2]
    monkeypatch.setattr(diarize, "build_timeline",
                        lambda audio, n=None: (times, labels, {1: None, 2: None}))
    words = [(0.0, 1.0, "hello "), (1.0, 2.0, "world "), (2.0, 3.0, "bye ")]

    turns, count, _ = diarize.diarize_words(np.zeros(4), words)

    assert count == 2
    assert turns == [(1, 0.0, 2.0, "hello world"), (2, 2.0, 3.0, "bye")]


def test_diarize_words_handles_silence(monkeypatch):
    monkeypatch.setattr(diarize, "build_timeline",
                        lambda audio, n=None: ([], [], {}))
    assert diarize.diarize_words(np.zeros(4), [(0, 1, "x")]) == ([], 0, {})
