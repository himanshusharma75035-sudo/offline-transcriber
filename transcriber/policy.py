"""Runtime data-egress policy — the single source of truth for whether any
audio or text may leave this machine.

Offline Transcriber is **offline-only by default**: nothing is ever uploaded
anywhere unless the optional cloud features are explicitly enabled. This is
the compliant default for sensitive recordings such as financial meetings.

The optional cloud features governed here are:
  * Groq Whisper transcription boost   (cloud.py)
  * Groq LLM meeting notes             (notes.py; the local Ollama path is
                                        always offline and is unaffected)

Enabling cloud  (opt-in — for non-sensitive audio only)
-------------------------------------------------------
Cloud is permitted only when it is opted in AND not force-disabled.
Opt in with either:
    * environment variable   TRANSCRIBER_ALLOW_CLOUD=1   (1/true/yes/on), or
    * a marker file named     allow_cloud                next to the app.

Force-disabling cloud  (administrator / enterprise)
---------------------------------------------------
Cloud can be centrally prohibited regardless of any opt-in with either:
    * environment variable   TRANSCRIBER_FORCE_OFFLINE=1, or
    * a machine-wide policy file:
          Windows :  %PROGRAMDATA%\\OfflineTranscriber\\force_offline
          POSIX   :  /etc/offline-transcriber/force_offline
A force-offline signal always wins, so a managed machine stays offline even
if a user sets the opt-in. This lets IT lock the tool to offline-only.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import paths

_TRUE = {"1", "true", "yes", "on", "y"}


class CloudDisabled(Exception):
    """Raised when a cloud feature is requested but policy forbids it."""


def _env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


def _machine_policy_files():
    """Machine-wide force-offline lock files (admin-owned locations)."""
    if os.name == "nt":
        base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        yield Path(base) / "OfflineTranscriber" / "force_offline"
    else:
        yield Path("/etc/offline-transcriber/force_offline")


def force_offline() -> bool:
    """True when cloud is hard-disabled by admin/env. Wins over any opt-in."""
    if _env_true("TRANSCRIBER_FORCE_OFFLINE"):
        return True
    return any(p.is_file() for p in _machine_policy_files())


def _opted_in() -> bool:
    if _env_true("TRANSCRIBER_ALLOW_CLOUD"):
        return True
    return paths.marker_exists("allow_cloud")


def cloud_allowed() -> bool:
    """Whether cloud features may run. Default False (offline-only)."""
    return _opted_in() and not force_offline()


def reason() -> str:
    """Human-readable explanation of the current cloud state, for logs/UI."""
    if force_offline():
        return ("cloud is force-disabled on this machine (offline-only); an "
                "administrator or TRANSCRIBER_FORCE_OFFLINE has locked it")
    if not _opted_in():
        return ("offline-only (default): no audio leaves this machine. To use "
                "cloud for non-sensitive audio, set TRANSCRIBER_ALLOW_CLOUD=1 "
                "or create an 'allow_cloud' file next to the app")
    return "cloud enabled (opted in): audio for cloud jobs is uploaded to Groq"


def require_cloud() -> None:
    """Raise CloudDisabled with an explanatory message if cloud isn't allowed."""
    if not cloud_allowed():
        raise CloudDisabled(reason())
