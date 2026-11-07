#!/usr/bin/env python3
"""Import an exact, non-authorizing summary of a frozen ecosystem portfolio."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, require_root, root, strict_loads


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("portfolio_status", type=Path)
    parser.add_argument("record_inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    status_raw = args.portfolio_status.read_bytes()
    inventory_raw = args.record_inventory.read_bytes()
    status, inventory = strict_loads(status_raw), strict_loads(inventory_raw)
    require(status["schema"] == "mosaic.ucm.integration-portfolio-status.v0.4",
            "UCM_ECOSYSTEM_STATUS_SCHEMA_INVALID")
    require(inventory["schema"] == "mosaic.ucm.portfolio-record-inventory.v0.1",
            "UCM_ECOSYSTEM_INVENTORY_SCHEMA_INVALID")
    expected = strict_loads((ROOT / "examples" / "portfolio" / "MOSAIC-APPLICATIONS.json").read_bytes())
    expected_ids = [row["id"] for row in expected["applications"]]
    rows = []
    for item in status["applications"]:
        rows.append({key: item[key] for key in (
            "application_id", "artifact_sha256", "stage_i1_status",
            "stage_i2_artifact_sha256", "stage_i2_revision",
            "stage_i3_instruction_sha256", "stage_i3_plan_sha256",
            "stage_i3_plan_status")})
        for key, value in rows[-1].items():
            if key.endswith("sha256"):
                require_root(value)
    require([row["application_id"] for row in rows] == expected_ids,
            "UCM_ECOSYSTEM_DENOMINATOR_MISMATCH")
    require([row["application_id"] for row in inventory["records"]] == expected_ids,
            "UCM_ECOSYSTEM_INVENTORY_DENOMINATOR_MISMATCH")
    counts = {name: sum(row["stage_i3_plan_status"] == name for row in rows)
              for name in ("READY_FOR_SHADOW_REVIEW", "HOLD_FOR_REPAIR")}
    body = {
        "schema": "mosaic.ucm.ecosystem-integration-baseline.v0.1",
        "portfolio_id": status["portfolio_id"],
        "portfolio_status_sha256": hashlib.sha256(status_raw).hexdigest(),
        "portfolio_status_root": status["status_root"],
        "record_inventory_sha256": hashlib.sha256(inventory_raw).hexdigest(),
        "fixed_denominator": len(rows), "stage_i3_plan_counts": counts,
        "applications": rows,
        "stage_i3_shadow_authorized": False,
        "composition_authorized": False,
        "non_claims": ["NO_APPLICATION_EXECUTION", "NO_APPLICATION_CONTACT",
                       "NO_HOLD_CLEARANCE", "NO_AUTHORITY_GRANT"],
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    value = {**body, "baseline_root": root(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(value))
    print(json.dumps({"status": "PASS", "baseline_root": value["baseline_root"],
                      "applications": len(rows), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
