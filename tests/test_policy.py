"""The offline-only data-egress gate — the compliance-critical behaviour."""

import pytest


@pytest.fixture
def policy(monkeypatch, tmp_path):
    """The policy module with a clean env and an app dir that has no markers."""
    import policy as _policy
    monkeypatch.delenv("TRANSCRIBER_ALLOW_CLOUD", raising=False)
    monkeypatch.delenv("TRANSCRIBER_FORCE_OFFLINE", raising=False)
    # point the "app dir" and machine-policy lookup at empty temp locations
    monkeypatch.setattr(_policy, "_APP_DIR", tmp_path)
    monkeypatch.setattr(_policy, "_machine_policy_files", lambda: iter(()))
    return _policy


def test_offline_by_default(policy):
    assert policy.cloud_allowed() is False
    assert "offline-only" in policy.reason()


def test_env_opt_in_enables_cloud(policy, monkeypatch):
    monkeypatch.setenv("TRANSCRIBER_ALLOW_CLOUD", "1")
    assert policy.cloud_allowed() is True
    assert "cloud enabled" in policy.reason()


@pytest.mark.parametrize("value", ["1", "true", "YES", "on", "y"])
def test_opt_in_accepts_truthy_spellings(policy, monkeypatch, value):
    monkeypatch.setenv("TRANSCRIBER_ALLOW_CLOUD", value)
    assert policy.cloud_allowed() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "", "off", "maybe"])
def test_opt_in_rejects_non_truthy(policy, monkeypatch, value):
    monkeypatch.setenv("TRANSCRIBER_ALLOW_CLOUD", value)
    assert policy.cloud_allowed() is False


def test_marker_file_opts_in(policy):
    (policy._APP_DIR / "allow_cloud").write_text("", encoding="utf-8")
    assert policy.cloud_allowed() is True


def test_force_offline_env_overrides_opt_in(policy, monkeypatch):
    monkeypatch.setenv("TRANSCRIBER_ALLOW_CLOUD", "1")
    monkeypatch.setenv("TRANSCRIBER_FORCE_OFFLINE", "1")
    assert policy.cloud_allowed() is False
    assert "force-disabled" in policy.reason()


def test_force_offline_machine_file_overrides_opt_in(policy, monkeypatch,
                                                     tmp_path):
    lock = tmp_path / "force_offline"
    lock.write_text("", encoding="utf-8")
    monkeypatch.setattr(policy, "_machine_policy_files", lambda: iter([lock]))
    monkeypatch.setenv("TRANSCRIBER_ALLOW_CLOUD", "1")
    assert policy.force_offline() is True
    assert policy.cloud_allowed() is False


def test_require_cloud_raises_when_offline(policy):
    with pytest.raises(policy.CloudDisabled):
        policy.require_cloud()
