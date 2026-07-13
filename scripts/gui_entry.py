"""PyInstaller entry point for the standalone GUI build.

A frozen entry script runs as a top-level module, so it uses an ABSOLUTE
import; the transcriber package (made importable via PyInstaller --paths)
supplies everything else.
"""

from transcriber.gui import main

if __name__ == "__main__":
    main()
