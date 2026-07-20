"""Known-answer tests for the WER/DER metrics. Pure Python, no models."""
from transcriber.metrics import (
    diarization_error_rate,
    normalize,
    word_error_rate,
)

# --------------------------------------------------------------------------- #
#  WER
# --------------------------------------------------------------------------- #

def test_wer_perfect():
    r = word_error_rate("the quick brown fox", "the quick brown fox")
    assert r.wer == 0.0
    assert r.errors == 0
    assert r.reference_words == 4


def test_wer_one_substitution():
    r = word_error_rate("the quick brown fox", "the quick green fox")
    assert r.substitutions == 1
    assert r.deletions == 0
    assert r.insertions == 0
    assert r.wer == 1 / 4


def test_wer_deletion_and_insertion():
    # ref has 3 words; hyp drops "brown" (deletion) ...
    r = word_error_rate("the quick brown fox jumps", "the quick fox jumps")
    assert r.deletions == 1
    assert r.substitutions == 0
    assert r.insertions == 0
    assert r.wer == 1 / 5

    # ... and here an extra word is inserted
    r2 = word_error_rate("the quick fox", "the very quick fox")
    assert r2.insertions == 1
    assert r2.wer == 1 / 3


def test_wer_casefold_and_punctuation_ignored():
    r = word_error_rate("Hello, world!", "hello world")
    assert r.wer == 0.0


def test_wer_case_sensitive_when_asked():
    r = word_error_rate("Hello world", "hello world", casefold=False)
    assert r.substitutions == 1


def test_wer_empty_reference():
    assert word_error_rate("", "").wer == 0.0
    # words against an empty reference are all insertions -> capped at 1.0
    assert word_error_rate("", "spurious words").wer == 1.0


def test_wer_all_wrong():
    r = word_error_rate("alpha beta", "gamma delta")
    assert r.wer == 1.0
    assert r.substitutions == 2


def test_normalize_unicode_nfc():
    # composed vs decomposed "é" must compare equal after NFC
    composed = "café"
    decomposed = "café"
    assert normalize(composed) == normalize(decomposed)


# --------------------------------------------------------------------------- #
#  DER
# --------------------------------------------------------------------------- #

def test_der_perfect_match_relabeled():
    # Same timeline, speakers named differently -> DER 0 after optimal mapping.
    ref = [(0.0, 2.0, "A"), (2.0, 4.0, "B")]
    hyp = [(0.0, 2.0, 7), (2.0, 4.0, 9)]
    d = diarization_error_rate(ref, hyp, collar=0.0)
    assert d.der == 0.0


def test_der_swapped_labels_still_perfect():
    # Optimal assignment should undo a global label swap.
    ref = [(0.0, 2.0, "A"), (2.0, 4.0, "B")]
    hyp = [(0.0, 2.0, "B"), (2.0, 4.0, "A")]
    d = diarization_error_rate(ref, hyp, collar=0.0)
    assert d.der == 0.0


def test_der_missed_speech():
    # Hypothesis leaves the second half unlabeled -> ~50% missed.
    ref = [(0.0, 2.0, "A"), (2.0, 4.0, "B")]
    hyp = [(0.0, 2.0, "A")]
    d = diarization_error_rate(ref, hyp, collar=0.0)
    assert abs(d.der - 0.5) < 0.02
    assert d.missed > d.confusion


def test_der_false_alarm():
    # Hypothesis invents speech where the reference is silent.
    ref = [(0.0, 2.0, "A")]
    hyp = [(0.0, 2.0, "A"), (2.0, 4.0, "A")]
    d = diarization_error_rate(ref, hyp, collar=0.0)
    assert d.false_alarm > 0
    assert abs(d.der - 1.0) < 0.02  # 2s FA over 2s reference speech


def test_der_confusion():
    # Right timing, wrong speaker on the second half.
    ref = [(0.0, 2.0, "A"), (2.0, 4.0, "B")]
    hyp = [(0.0, 2.0, "A"), (2.0, 4.0, "A")]
    d = diarization_error_rate(ref, hyp, collar=0.0)
    assert d.confusion > 0
    assert abs(d.der - 0.5) < 0.02


def test_der_empty_reference_all_false_alarm():
    d = diarization_error_rate([], [(0.0, 1.0, "A")], collar=0.0)
    assert d.der == 1.0
    assert d.reference_speech == 0.0
