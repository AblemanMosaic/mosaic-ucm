#!/usr/bin/env python3
"""Repository-local wrapper for the installed UCM CLI."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from ucm.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

