#!/usr/bin/env python3
"""Verify the frozen r016 interface program through its r019 normalization."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from normalize_pippi_work_selection_history import canonical, expected, write  # noqa: E402


OUTPUT = ROOT / "program" / "pippi-interface-r016"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    programs, receipt = expected()
    records = programs["pippi-interface-r016"]
    mismatches = []
    for name, value in records.items():
        path = OUTPUT / name
        raw = canonical(value) + b"\n"
        if args.write:
            write(path, value)
        elif not path.is_file() or path.read_bytes() != raw:
            mismatches.append(name)
    result = {
        "status": "PASS" if not mismatches else "REFUSED",
        "mode": "WRITE" if args.write else "CHECK",
        "records": len(records),
        "program_inventory_root": records["PROGRAM-INVENTORY.json"]["program_inventory_root"],
        "normalization_root": receipt["normalization_root"],
        "mismatches": mismatches,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())
