"""Store the Groq API key securely, and migrate it off the plaintext file.

The plaintext `groq_api_key.txt` is the least-secure option — and if your
project folder is synced (Dropbox/OneDrive/Drive), the key rides along to the
cloud. This tool moves the key into your OS secret store (Windows Credential
Manager / macOS Keychain / Linux Secret Service) via `keyring`, where other
apps and sync clients can't read it.

    transcribe-key --status     show where the key currently resolves from
    transcribe-key --set        prompt for a key and store it in the keyring
    transcribe-key --migrate    move an existing groq_api_key.txt into the
                                keyring, then delete the plaintext file
    transcribe-key --clear      remove the key from the keyring

The key value is never printed or logged.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from . import paths

SERVICE = "offline-transcriber"
USERNAME = "GROQ_API_KEY"


def _keyring():
    try:
        import keyring
        return keyring
    except Exception:
        return None


def _mask(key: str) -> str:
    """Show only enough to recognize a key, never the secret itself."""
    if not key:
        return "(empty)"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-2:]} ({len(key)} chars)"


def cmd_status() -> int:
    import os
    print("Groq API key resolution (first hit wins):")

    env = os.environ.get("GROQ_API_KEY", "").strip()
    print(f"  1. GROQ_API_KEY env var .......... {'set ' + _mask(env) if env else 'not set'}")

    kr = _keyring()
    if kr is None:
        print("  2. OS keyring .................... keyring not installed")
    else:
        try:
            v = (kr.get_password(SERVICE, USERNAME) or "").strip()
            print(f"  2. OS keyring ({kr.get_keyring().__class__.__name__}) "
                  f".. {'stored ' + _mask(v) if v else 'empty'}")
        except Exception as e:
            print(f"  2. OS keyring .................... error: {e}")

    f = paths.user_file("groq_api_key.txt")
    if f.is_file():
        low = str(f).lower()
        synced = any(s in low for s in ("dropbox", "onedrive", "google drive", "\\box\\"))
        warn = "  <-- SYNCED FOLDER! rotate + move it (transcribe-key --migrate)" if synced else ""
        print(f"  3. plaintext file ............... EXISTS at {f}{warn}")
    else:
        print("  3. plaintext file ............... none")
    return 0


def _store(kr, key: str) -> bool:
    try:
        kr.set_password(SERVICE, USERNAME, key)
        back = (kr.get_password(SERVICE, USERNAME) or "").strip()
        return back == key
    except Exception as e:
        print(f"failed to store in keyring: {e}", file=sys.stderr)
        return False


def cmd_set() -> int:
    kr = _keyring()
    if kr is None:
        print("keyring is not installed. Install it with:  pip install keyring",
              file=sys.stderr)
        return 2
    key = getpass.getpass("Paste your Groq API key (hidden): ").strip()
    if not key:
        print("no key entered.", file=sys.stderr)
        return 2
    if _store(kr, key):
        print(f"stored {_mask(key)} in the OS keyring.")
        return 0
    return 1


def cmd_migrate() -> int:
    kr = _keyring()
    if kr is None:
        print("keyring is not installed. Install it with:  pip install keyring",
              file=sys.stderr)
        return 2
    f = paths.user_file("groq_api_key.txt")
    if not f.is_file():
        print("no groq_api_key.txt found — nothing to migrate. "
              "Use --set to enter a key.")
        return 0
    key = f.read_text(encoding="utf-8").strip()
    if not key:
        print("groq_api_key.txt is empty — nothing to migrate.", file=sys.stderr)
        return 2
    if not _store(kr, key):
        return 1
    print(f"stored {_mask(key)} in the OS keyring.")
    try:
        f.unlink()
        print(f"deleted the plaintext file: {f}")
    except Exception as e:
        print(f"stored in keyring, but could not delete {f}: {e}", file=sys.stderr)
        return 1
    print("done — the key now lives only in the OS secret store.")
    return 0


def cmd_clear() -> int:
    kr = _keyring()
    if kr is None:
        print("keyring is not installed.", file=sys.stderr)
        return 2
    try:
        kr.delete_password(SERVICE, USERNAME)
        print("removed the key from the OS keyring.")
    except Exception:
        print("no key was stored in the keyring.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true",
                   help="show where the key resolves from (default)")
    g.add_argument("--set", action="store_true",
                   help="prompt for a key and store it in the keyring")
    g.add_argument("--migrate", action="store_true",
                   help="move groq_api_key.txt into the keyring, then delete it")
    g.add_argument("--clear", action="store_true",
                   help="remove the key from the keyring")
    args = ap.parse_args()

    if args.set:
        return cmd_set()
    if args.migrate:
        return cmd_migrate()
    if args.clear:
        return cmd_clear()
    return cmd_status()


if __name__ == "__main__":
    raise SystemExit(main())
