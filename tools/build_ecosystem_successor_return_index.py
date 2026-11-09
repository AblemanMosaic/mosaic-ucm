#!/usr/bin/env python3
"""Build the fixed-denominator index of exact successor-work returns."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_successor_returns import build_successor_return_index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("returns_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dispatch", type=Path, default=ROOT / "integration" /
                        "ECOSYSTEM-NEXT-WORK-DISPATCH.json")
    args = parser.parse_args()
    packages = {path.name: path.read_bytes()
                for path in sorted(args.returns_dir.glob("*.zip"))}
    result = build_successor_return_index(
        strict_loads(args.dispatch.read_bytes()), packages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS",
        "received": result["received_count"],
        "pending": result["pending_count"],
        "return_index_root": result["return_index_root"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
