"""Where the app reads and writes user data.

Keeps user-writable files (API key, voice profiles, settings, the cloud
opt-in marker, live transcripts) OUT of the package directory — which is
read-only when the app is pip-installed or frozen into an .exe — while
staying backward-compatible with the old flat layout where those files sat
next to the scripts.

Resolution order for a user file: an existing copy in the legacy location
(the repo root, i.e. the parent of this package) wins; otherwise a per-user
data directory is used:
    Windows :  %APPDATA%\\OfflineTranscriber\\
    macOS   :  ~/Library/Application Support/OfflineTranscriber/
    Linux   :  $XDG_DATA_HOME/offline-transcriber/  (or ~/.local/share)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent      # .../transcriber
_LEGACY_DIR = _PKG_DIR.parent                    # repo root in a source checkout
_APP = "OfflineTranscriber"


def data_dir() -> Path:
    """The per-user, writable data directory (created on demand)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData"
                                                 / "Roaming")
        d = Path(base) / _APP
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / _APP
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home()
                                                      / ".local" / "share")
        d = Path(base) / "offline-transcriber"
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_file(name: str) -> Path:
    """Resolve a user-writable file by name.

    An existing legacy copy next to the repo (old layout) is honoured so
    upgrades don't lose the user's key/profiles; otherwise the per-user data
    directory is used.
    """
    legacy = _LEGACY_DIR / name
    if legacy.exists():
        return legacy
    return data_dir() / name


def marker_exists(name: str) -> bool:
    """True if a marker file exists in either the legacy or per-user dir."""
    return (_LEGACY_DIR / name).exists() or (data_dir() / name).exists()


def vocabulary_file() -> Path:
    """The active vocabulary file: a user override if present (legacy repo
    dir, then per-user dir), otherwise the packaged default template."""
    for p in (_LEGACY_DIR / "vocabulary.txt", data_dir() / "vocabulary.txt"):
        if p.exists():
            return p
    return _PKG_DIR / "data" / "vocabulary.txt"
