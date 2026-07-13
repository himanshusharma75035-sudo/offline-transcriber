"""Make the top-level modules importable when running the test suite from
the repo root (the project ships as loose modules, not an installed package)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
