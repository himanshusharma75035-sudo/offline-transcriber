"""Voice memory: crash-safe persistence and speaker matching. Regression
cover for the atomic-save / backup-recovery / corrupt-file bugs."""

import numpy as np
import pytest

import voices


@pytest.fixture
def store(monkeypatch, tmp_path):
    """Redirect the profile files into a temp dir so tests never touch the
    real speaker_profiles.json."""
    monkeypatch.setattr(voices, "PROFILES_FILE", tmp_path / "profiles.json")
    monkeypatch.setattr(voices, "BACKUP_FILE", tmp_path / "profiles.bak.json")
    return tmp_path


def _vec(*vals, dim=192):
    v = np.zeros(dim, dtype=np.float32)
    v[: len(vals)] = vals
    return v


def test_enroll_then_load_roundtrip(store):
    voices.enroll("Alice", _vec(1, 0, 0))
    voices.enroll("Bob", _vec(0, 1, 0))
    loaded = voices.load_profiles()
    assert set(loaded) == {"Alice", "Bob"}


def test_second_save_leaves_a_backup(store):
    voices.enroll("Alice", _vec(1))
    voices.enroll("Bob", _vec(1))        # second save snapshots the first
    assert voices.BACKUP_FILE.is_file()


def test_corrupt_main_file_recovers_from_backup(store):
    voices.enroll("Alice", _vec(1))
    voices.enroll("Bob", _vec(1))        # backup now holds {Alice}
    voices.PROFILES_FILE.write_text('{"Alice": [[1.0, 2.0', encoding="utf-8")
    recovered = voices.load_profiles()
    assert set(recovered) == {"Alice"}
    # the corrupt file is preserved for inspection, not silently destroyed
    assert voices.PROFILES_FILE.with_suffix(".corrupt.json").is_file()


def test_non_dict_json_degrades_to_empty(store):
    voices.PROFILES_FILE.write_text("[]", encoding="utf-8")
    assert voices.load_profiles() == {}
    # and matching against it must not raise
    assert voices.match_speakers({1: _vec(1)}) == {}


def test_missing_file_is_empty(store):
    assert voices.load_profiles() == {}


def test_match_assigns_each_name_at_most_once(store):
    voices.enroll("Alice", _vec(1, 0, 0))
    voices.enroll("Bob", _vec(0, 1, 0))
    # two clusters, both closest to Alice; only the best may take her name
    result = voices.match_speakers({1: _vec(1.0, 0.0, 0.0),
                                    2: _vec(0.9, 0.1, 0.0)})
    assert result[1] == "Alice"
    assert result.get(2) != "Alice"


def test_match_ignores_dissimilar_voices(store):
    voices.enroll("Alice", _vec(1, 0, 0))
    # orthogonal voice — similarity 0, below MATCH_THRESHOLD
    assert voices.match_speakers({1: _vec(0, 1, 0)}) == {}


def test_similarity_bounds():
    assert voices._similarity(_vec(1, 0), _vec(1, 0)) == pytest.approx(1.0)
    assert voices._similarity(_vec(1, 0), _vec(0, 1)) == pytest.approx(0.0)
    assert voices._similarity(_vec(0, 0), _vec(0, 0)) == 0.0   # no NaN


def test_enroll_caps_samples_per_person(store):
    for i in range(voices.MAX_SAMPLES_PER_PERSON + 3):
        voices.enroll("Alice", _vec(float(i)))
    assert len(voices.load_profiles()["Alice"]) == voices.MAX_SAMPLES_PER_PERSON


def test_display_name_falls_back_to_number():
    assert voices.display_name(2, {1: "Alice"}) == "Speaker 2"
    assert voices.display_name(1, {1: "Alice"}) == "Alice"
