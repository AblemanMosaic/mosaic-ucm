#!/usr/bin/env python3
"""Build an exact Stage I3 semantic/binding reconciliation record."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_reconciliation import reconcile_stage_i3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("authoring_root", type=Path)
    parser.add_argument("pipeline_bound_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline", type=Path,
        default=ROOT / "integration" / "ECOSYSTEM-INTEGRATION-BASELINE.json")
    args = parser.parse_args()
    roster = strict_loads((ROOT / "examples" / "portfolio" / "MOSAIC-APPLICATIONS.json").read_bytes())
    baseline_raw = args.baseline.read_bytes()
    baseline = strict_loads(baseline_raw)
    application_ids = [row["id"] for row in roster["applications"]]
    result = reconcile_stage_i3(
        args.authoring_root.resolve(), args.pipeline_bound_root.resolve(), application_ids,
        baseline, hashlib.sha256(baseline_raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": "PASS",
        "applications": result["fixed_denominator"],
        "semantic_changes": result["semantic_changes"],
        "reconciliation_root": result["reconciliation_root"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
