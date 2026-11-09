#!/usr/bin/env python3
"""Build non-authorizing batch repair instructions from exact audit returns."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_repair_program import build_ecosystem_repair_program


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("successor_register", type=Path)
    parser.add_argument("audit_register", type=Path)
    parser.add_argument("repair_register", type=Path)
    parser.add_argument("current_state", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_ecosystem_repair_program(
        strict_loads(args.successor_register.read_bytes()),
        strict_loads(args.audit_register.read_bytes()),
        strict_loads(args.repair_register.read_bytes()),
        strict_loads(args.current_state.read_bytes()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS_NONAUTHORIZING_REPAIR_PROGRAM",
        "repair_batches": result["repair_batch_count"],
        "repair_program_root": result["repair_program_root"],
        "output": str(args.output),
        "standing": result["standing"],
        "authority_effect": result["authority_effect"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
