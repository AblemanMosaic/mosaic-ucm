#!/usr/bin/env python3
"""Bind the next ecosystem work program to the established session roster."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_work import build_next_dispatch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program", type=Path)
    parser.add_argument("prior_dispatch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_next_dispatch(
        strict_loads(args.program.read_bytes()),
        strict_loads(args.prior_dispatch.read_bytes()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS_NEXT_DISPATCH_BOUND",
        "applications": len(result["applications"]),
        "dispatch_root": result["dispatch_root"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
