"""Accuracy metrics for transcription and diarization — pure Python, no deps.

WER (word error rate) scores the transcript; DER (diarization error rate)
scores who-spoke-when. Both are implemented from scratch so the test suite and
CI need nothing beyond the standard library.

These are the two numbers people ask for when they evaluate a speech system:

    WER = (substitutions + deletions + insertions) / reference_words
    DER = (missed + false_alarm + speaker_confusion) / reference_speech_time

Lower is better for both; 0.0 is perfect.
"""
from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
#  Word Error Rate
# --------------------------------------------------------------------------- #

_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)
_SPACE = re.compile(r"\s+", flags=re.UNICODE)


def normalize(text: str, *, casefold: bool = True, strip_punct: bool = True) -> str:
    """Canonicalize text before scoring so trivial differences don't count.

    Unicode-NFC first (so composed/decomposed forms match), then optional
    case-folding and punctuation removal, then whitespace collapse. This is the
    usual WER pre-processing; keep reference and hypothesis on the same footing.
    """
    text = unicodedata.normalize("NFC", text)
    if casefold:
        text = text.casefold()
    if strip_punct:
        text = _PUNCT.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class WordErrorRate:
    substitutions: int
    deletions: int
    insertions: int
    reference_words: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def wer(self) -> float:
        if self.reference_words == 0:
            # No reference words: any hypothesis word is an insertion error,
            # a perfectly empty hypothesis is perfect.
            return 0.0 if self.insertions == 0 else 1.0
        return self.errors / self.reference_words

    @property
    def accuracy(self) -> float:
        return max(0.0, 1.0 - self.wer)


def word_error_rate(
    reference: str,
    hypothesis: str,
    *,
    casefold: bool = True,
    strip_punct: bool = True,
) -> WordErrorRate:
    """Levenshtein distance over word tokens, itemized into S/D/I.

    Uses a Wagner-Fischer DP with backtracking so we can report the individual
    edit counts (not just the total), which is what makes a WER report useful.
    """
    ref = normalize(reference, casefold=casefold, strip_punct=strip_punct).split()
    hyp = normalize(hypothesis, casefold=casefold, strip_punct=strip_punct).split()
    n, m = len(ref), len(hyp)

    # dp[i][j] = edit distance between ref[:i] and hyp[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j - 1],  # substitution
                    dp[i - 1][j],      # deletion (ref word dropped)
                    dp[i][j - 1],      # insertion (extra hyp word)
                )

    # Backtrack to itemize the edits.
    subs = dels = ins = 0
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            subs += 1
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dels += 1
            i -= 1
        else:
            ins += 1
            j -= 1

    return WordErrorRate(subs, dels, ins, n)


# --------------------------------------------------------------------------- #
#  Diarization Error Rate
# --------------------------------------------------------------------------- #

# A segment is (start_seconds, end_seconds, speaker_label).
Segment = tuple[float, float, object]


@dataclass(frozen=True)
class DiarizationErrorRate:
    missed: float          # reference speech the system left unlabeled (s)
    false_alarm: float     # system speech where reference is silent (s)
    confusion: float       # both speak but the mapped speaker is wrong (s)
    reference_speech: float  # total reference speech time (s)

    @property
    def der(self) -> float:
        if self.reference_speech == 0:
            return 0.0 if (self.false_alarm == 0) else 1.0
        return (self.missed + self.false_alarm + self.confusion) / self.reference_speech


def _speaker_at(segments: list[Segment], t: float) -> object | None:
    """The speaker talking at instant t, or None for silence.

    On overlapped reference speech the earliest-listed segment wins; our
    diarizer emits one speaker per instant anyway, so this only bites on
    hand-labeled references with overlap (documented in benchmarks.md).
    """
    for start, end, spk in segments:
        if start <= t < end:
            return spk
    return None


def diarization_error_rate(
    reference: list[Segment],
    hypothesis: list[Segment],
    *,
    resolution: float = 0.010,
    collar: float = 0.25,
) -> DiarizationErrorRate:
    """Frame-based DER with optimal reference→hypothesis speaker mapping.

    - `resolution`: frame step in seconds (10 ms is the NIST convention).
    - `collar`: seconds ignored on each side of every reference boundary, to
      forgive imprecise cut points (NIST uses 0.25 s). Set 0 to score strictly.

    The hypothesis speaker labels are matched to reference labels by the
    assignment that maximizes total overlap, so it doesn't matter whether the
    system called someone "1" or "Alex" — only whether it kept them distinct.
    """
    if not reference:
        # Nothing to be right about; any hypothesis speech is false alarm.
        end = max((e for _, e, _ in hypothesis), default=0.0)
        fa = 0.0
        t = 0.0
        while t < end:
            if _speaker_at(hypothesis, t) is not None:
                fa += resolution
            t += resolution
        return DiarizationErrorRate(0.0, fa, 0.0, 0.0)

    end = max(e for _, e, _ in reference)
    if hypothesis:
        end = max(end, max(e for _, e, _ in hypothesis))

    # Collar mask: drop frames near any reference boundary.
    boundaries = sorted({b for s, e, _ in reference for b in (s, e)})

    def in_collar(t: float) -> bool:
        return any(abs(t - b) < collar for b in boundaries)

    ref_speakers = sorted({s for _, _, s in reference}, key=repr)
    hyp_speakers = sorted({s for _, _, s in hypothesis}, key=repr)

    # Overlap[r][h] = scored frames where ref speaker r and hyp speaker h coincide.
    overlap: dict[tuple[object, object], float] = {}
    ref_speech = 0.0
    frames = []  # (ref_spk_or_None, hyp_spk_or_None) for scored frames
    t = 0.0
    while t < end:
        if not in_collar(t):
            r = _speaker_at(reference, t)
            h = _speaker_at(hypothesis, t)
            frames.append((r, h))
            if r is not None:
                ref_speech += resolution
            if r is not None and h is not None:
                overlap[(r, h)] = overlap.get((r, h), 0.0) + resolution
        t += resolution

    mapping = _best_mapping(ref_speakers, hyp_speakers, overlap)

    missed = false_alarm = confusion = 0.0
    for r, h in frames:
        if r is None and h is None:
            continue
        if r is None:                       # hyp speaks, ref silent
            false_alarm += resolution
        elif h is None:                     # ref speaks, hyp silent
            missed += resolution
        elif mapping.get(h) != r:           # both speak, wrong speaker
            confusion += resolution

    return DiarizationErrorRate(missed, false_alarm, confusion, ref_speech)


def _best_mapping(
    ref_speakers: list,
    hyp_speakers: list,
    overlap: dict[tuple[object, object], float],
) -> dict[object, object]:
    """Assign each hypothesis speaker to a reference speaker to maximize overlap.

    Speaker counts in real recordings are small, so we brute-force the optimal
    1:1 assignment when feasible and fall back to a greedy match otherwise —
    no scipy dependency for a handful of speakers.
    """
    if not hyp_speakers or not ref_speakers:
        return {}

    def score(pairs) -> float:
        return sum(overlap.get((r, h), 0.0) for h, r in pairs)

    # Brute force is fine up to ~7 speakers on the smaller side (5040 perms).
    if min(len(ref_speakers), len(hyp_speakers)) <= 7:
        best: dict[object, object] = {}
        best_score = -1.0
        if len(hyp_speakers) <= len(ref_speakers):
            for perm in itertools.permutations(ref_speakers, len(hyp_speakers)):
                pairs = list(zip(hyp_speakers, perm, strict=True))
                s = score(pairs)
                if s > best_score:
                    best_score, best = s, dict(pairs)
        else:
            for perm in itertools.permutations(hyp_speakers, len(ref_speakers)):
                pairs = list(zip(perm, ref_speakers, strict=True))
                s = score(pairs)
                if s > best_score:
                    best_score, best = s, dict(pairs)
        return best

    # Greedy fallback for many speakers: take the best pairs first.
    pairs_by_overlap = sorted(overlap.items(), key=lambda kv: kv[1], reverse=True)
    mapping: dict[object, object] = {}
    used_ref: set = set()
    for (r, h), _ in pairs_by_overlap:
        if h not in mapping and r not in used_ref:
            mapping[h] = r
            used_ref.add(r)
    return mapping
