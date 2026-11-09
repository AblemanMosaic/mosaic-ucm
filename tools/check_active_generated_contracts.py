#!/usr/bin/env python3
"""Read-only parity check for current generated interface contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tools"))

from uclop.canonical import canonical_bytes
from ucm.governance import abi_stability_table
from ucm.profiles import profile_registry, validate_profile_selection
import build_pippi_adaptive_contracts
import build_pippi_pack_contracts


def expected_records() -> dict[Path, bytes]:
    records: dict[Path, bytes] = {
        ROOT / "spec" / "ABI-STABILITY.json": canonical_bytes(abi_stability_table()) + b"\n",
    }
    profiles = profile_registry()
    records[ROOT / "spec" / "product-profiles" / "PROFILE-REGISTRY.json"] = canonical_bytes(profiles) + b"\n"
    for profile in profiles["profiles"]:
        selection = validate_profile_selection({
            "schema": "mosaic.ucm.product-profile-selection.v0.1",
            "profile_id": profile["profile_id"],
            "capability_registry_root": profiles["capability_registry_root"],
        })
        records[ROOT / "spec" / "product-profiles" / f"{profile['profile_id']}-PROFILE.json"] = canonical_bytes(selection) + b"\n"
    for path, value in build_pippi_adaptive_contracts.records().items():
        records[path] = ((value.rstrip("\n").encode("utf-8") if isinstance(value, str)
                          else canonical_bytes(value)) + b"\n")
    records.update(build_pippi_pack_contracts.records())
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="Write the active generated records before checking them.")
    args = parser.parse_args()
    mismatches = []
    for path, expected in sorted(expected_records().items(), key=lambda item: item[0].as_posix()):
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        if not path.is_file() or path.read_bytes() != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
    result = {
        "schema": "mosaic.ucm.active-generated-contract-parity.v0.1",
        "status": "PASS" if not mismatches else "REFUSED",
        "checked_records": len(expected_records()),
        "mismatches": mismatches,
        "mode": "WRITE_THEN_CHECK" if args.write else "CHECK_READ_ONLY",
        "frozen_history_excluded": True,
        "frozen_exclusion_roots": ["historical", "review", "program"],
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())
