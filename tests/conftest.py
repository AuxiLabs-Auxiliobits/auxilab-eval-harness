"""Shared pytest configuration: make src/ importable in CI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DEMO = ROOT / "demo"

for path in (SRC, DEMO):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
