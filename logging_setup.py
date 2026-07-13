"""Central logging: a rotating file log plus uncaught-exception capture.

User-facing progress still goes to stdout/the GUI as before — this adds a
diagnostic trail so failures (especially silent GUI ones) can be traced.

The log lives in a per-user directory, NOT next to the app, so it works from
a read-only install and never lands in the synced project folder:
    Windows :  %LOCALAPPDATA%\\OfflineTranscriber\\logs\\transcriber.log
    macOS   :  ~/Library/Logs/OfflineTranscriber/transcriber.log
    Linux   :  $XDG_STATE_HOME/offline-transcriber/logs/ (or ~/.local/state)

Set TRANSCRIBER_LOG_LEVEL (DEBUG/INFO/WARNING/ERROR) to change console
verbosity; the file always records DEBUG.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def log_dir() -> Path:
    """Per-user log directory, created if needed."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData"
                                                      / "Local")
        d = Path(base) / "OfflineTranscriber" / "logs"
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Logs" / "OfflineTranscriber"
    else:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home()
                                                        / ".local" / "state")
        d = Path(base) / "offline-transcriber" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def setup(level: str | None = None, console: bool = True) -> logging.Logger:
    """Configure logging once and return the app logger. Safe to call repeatedly."""
    global _CONFIGURED
    logger = logging.getLogger("transcriber")
    if _CONFIGURED:
        return logger

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(_FORMAT)

    try:
        fh = RotatingFileHandler(log_dir() / "transcriber.log",
                                 maxBytes=1_000_000, backupCount=5,
                                 encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass          # never let logging setup stop the app from running

    if console and sys.stderr is not None:   # pythonw GUI has no stderr
        ch = logging.StreamHandler(sys.stderr)
        lvl = (level or os.environ.get("TRANSCRIBER_LOG_LEVEL", "WARNING")
               ).upper()
        ch.setLevel(getattr(logging, lvl, logging.WARNING))
        ch.setFormatter(fmt)
        root.addHandler(ch)

    _install_excepthooks(logger)
    _CONFIGURED = True
    logger.debug("logging initialised; log dir=%s", log_dir())
    return logger


def _install_excepthooks(logger: logging.Logger) -> None:
    """Log uncaught exceptions in the main thread and worker threads."""
    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("uncaught exception", exc_info=(exc_type, exc, tb))
    sys.excepthook = hook

    def thread_hook(args):
        logger.critical("uncaught exception in thread %s",
                        args.thread.name if args.thread else "?",
                        exc_info=(args.exc_type, args.exc_value,
                                  args.exc_traceback))
    threading.excepthook = thread_hook


def install_gui_crash_handler(root) -> None:
    """Route Tk callback exceptions to the log and a friendly dialog, so a
    GUI failure leaves a trace instead of vanishing silently."""
    logger = logging.getLogger("transcriber")

    def report(exc_type, exc, tb):
        logger.critical("unhandled GUI exception",
                        exc_info=(exc_type, exc, tb))
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Offline Transcriber — unexpected error",
                f"{exc_type.__name__}: {exc}\n\n"
                f"A full report was saved to:\n{log_dir() / 'transcriber.log'}")
        except Exception:
            pass

    root.report_callback_exception = report
