"""Put the repo root on sys.path so `import transcriber` works when running
the test suite from a source checkout without installing the package."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
