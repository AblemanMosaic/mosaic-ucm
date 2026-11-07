#!/usr/bin/env python3
"""Build the append-only current ecosystem integration state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_current_state import build_ecosystem_current_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("successor_register", type=Path)
    parser.add_argument("audit_register", type=Path)
    parser.add_argument("repair_register", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_ecosystem_current_state(
        strict_loads(args.successor_register.read_bytes()),
        strict_loads(args.audit_register.read_bytes()),
        strict_loads(args.repair_register.read_bytes()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS_NONAUTHORIZING_CURRENT_STATE",
        "applications": result["application_count"],
        "audit_overlays": result["audit_overlay_count"],
        "repair_overlays": result["repair_overlay_count"],
        "applications_on_hold": len(result["applications_on_hold"]),
        "current_state_root": result["current_state_root"],
        "output": str(args.output),
        "standing": result["standing"],
        "authority_effect": result["authority_effect"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
