#!/usr/bin/env python3
"""Derive a fixed-denominator next-work program from static outcomes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_work import build_next_work_program


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("outcomes", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_next_work_program(strict_loads(args.outcomes.read_bytes()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS_NEXT_WORK_DERIVED",
        "applications": len(result["applications"]),
        "work_program_root": result["work_program_root"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
