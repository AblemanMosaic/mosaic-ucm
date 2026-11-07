#!/usr/bin/env python3
"""Build deterministic golden vectors for the maturity successor surfaces."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.architecture import check_architecture_change
from ucm.diagnostics import smoke
from ucm.evolution import negotiate_feature_level
from ucm.evaluation import build_run_roster
from ucm.profiles import profile_registry


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    base = ROOT / "examples" / "architecture" / "reference-data-client"
    contract = load(base / "ARCHITECTURE-CONTRACT.json")
    compatible = {"schema": "mosaic.ucm.feature-descriptor.v0.1",
                  "minimum_feature_level": 1, "maximum_feature_level": 1,
                  "required_features": ["CANONICAL_JSON_V1"], "extensions": {}}
    study = load(ROOT / "evaluation" / "ARCHITECTURE-COMPLIANCE-STUDY.json")
    vectors = [
        {"id": "FEATURE-LEVEL-1", "input_root": root(compatible),
         "output": negotiate_feature_level(compatible)},
        {"id": "ARCHITECTURE-CONFORMING", "input_root": root({
            "contract": contract, "candidate": load(base / "CONFORMING-CHANGE.json")}),
         "output": check_architecture_change(
             contract, load(base / "CONFORMING-CHANGE.json"))},
        {"id": "ARCHITECTURE-DRIFT", "input_root": root({
            "contract": contract, "candidate": load(base / "DRIFTING-CHANGE.json")}),
         "output": check_architecture_change(
             contract, load(base / "DRIFTING-CHANGE.json"))},
        {"id": "PRODUCT-PROFILES", "input_root": root({}),
         "output": profile_registry()},
        {"id": "FIELD-SMOKE", "input_root": root({}), "output": smoke()},
        {"id": "ARCHITECTURE-STUDY-ROSTER", "input_root": root(study),
         "output": build_run_roster(study)},
    ]
    for vector in vectors:
        vector["output_root"] = root(vector["output"])
    body = {"schema": "mosaic.ucm.maturity-conformance-vectors.v0.1",
            "vectors": vectors,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
    value = {**body, "conformance_root": root(body)}
    path = ROOT / "conformance" / "MATURITY-CONFORMANCE-v0.1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
