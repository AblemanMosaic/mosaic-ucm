#!/usr/bin/env python3
"""Build the non-authorizing static successor-outcome register."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes
from ucm.ecosystem_successor_outcomes import build_successor_outcome_register


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("returns_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    packages = {path.name: path.read_bytes()
                for path in sorted(args.returns_dir.glob("*.zip"))}
    result = build_successor_outcome_register(packages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS_STATIC_RECONCILIATION",
        "received": result["received_count"],
        "pending": result["pending_count"],
        "outcome_register_root": result["outcome_register_root"],
        "output": str(args.output),
        "standing": result["standing"],
        "authority_effect": result["authority_effect"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
