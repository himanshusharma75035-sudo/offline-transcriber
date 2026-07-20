"""Search across all your transcripts.

Usage:
    search.bat "mismatch"                          # search current folder
    search.bat "invoice" "C:\\Users\\me\\Downloads"  # search a specific folder
    search.bat "refund" --context 1                # show surrounding lines
"""

import argparse
import sys
from pathlib import Path

# Windows consoles often default to a legacy codepage that can't print
# Indian scripts; force UTF-8 so Devanagari/Tamil/etc. don't crash output.
# (Under pythonw there is no console, so the streams are None.)
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure:
        _reconfigure(encoding="utf-8", errors="replace")

SEARCH_SUFFIXES = {".txt", ".md", ".srt"}


def main():
    parser = argparse.ArgumentParser(
        description="Search across transcript files (.txt/.md/.srt).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("query", help="text to look for (case-insensitive)")
    parser.add_argument("folders", nargs="*", default=["."],
                        help="folder(s) to search, recursively")
    parser.add_argument("--context", type=int, default=0,
                        help="lines of context to show around each match")
    args = parser.parse_args()

    query = args.query.lower()
    hits = files_hit = 0
    for folder in args.folders:
        root = Path(folder)
        if not root.is_dir():
            print(f"warning: not a folder: {root}", file=sys.stderr)
            continue
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() not in SEARCH_SUFFIXES or not f.is_file():
                continue
            try:
                text_lines = f.read_text(encoding="utf-8",
                                         errors="replace").splitlines()
            except OSError:
                continue
            matches = [i for i, line in enumerate(text_lines)
                       if query in line.lower()]
            if not matches:
                continue
            files_hit += 1
            hits += len(matches)
            print(f"\n=== {f} ===")
            shown = set()
            for i in matches:
                lo = max(0, i - args.context)
                hi = min(len(text_lines), i + args.context + 1)
                for j in range(lo, hi):
                    if j not in shown:
                        shown.add(j)
                        marker = ">" if j == i else " "
                        print(f" {marker} {j + 1:5d}: {text_lines[j]}")

    print(f"\n{hits} match(es) in {files_hit} file(s)."
          if hits else "no matches.")


if __name__ == "__main__":
    main()
