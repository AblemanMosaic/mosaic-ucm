"""Rebind reviewed C1 Stage I3 plans to an exact successor pipeline release."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.stage3 import required_instruction_evidence, validate_instruction, validate_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_instruction", type=Path)
    parser.add_argument("new_instruction", type=Path)
    parser.add_argument("old_plan", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    old_instruction = validate_instruction(strict_loads(args.old_instruction.read_bytes()))
    new_instruction = validate_instruction(strict_loads(args.new_instruction.read_bytes()))
    old_plan = strict_loads(args.old_plan.read_bytes())
    legacy_checked = deepcopy(old_plan)
    legacy_checked["required_evidence_roots"] = sorted(
        set(legacy_checked["required_evidence_roots"])
        | required_instruction_evidence(old_instruction))
    legacy_checked["plan_root"] = root({key: value for key, value in legacy_checked.items()
                                         if key != "plan_root"})
    validate_plan(legacy_checked, expected_instruction=old_instruction)
    if old_instruction["application_id"] != new_instruction["application_id"]:
        raise SystemExit("STAGE_I3_REBIND_APPLICATION_INVALID")
    for key in ("thread_id", "predecessor_portfolio_sha256", "portfolio_status_root",
                "preflight_root", "court_root", "court_evidence_sha256",
                "stage_i1_artifact_sha256", "stage_i2_artifact_sha256",
                "stage_i1_status", "matched_relations", "cm1_requirements",
                "cm2_priorities", "requested_plan_fields", "mode"):
        if old_instruction[key] != new_instruction[key]:
            raise SystemExit("STAGE_I3_REBIND_NON_PIPELINE_CHANGE:" + key)
    plan = deepcopy(old_plan)
    plan["instruction_root"] = new_instruction["instruction_root"]
    old_required = required_instruction_evidence(old_instruction)
    preserved = set(plan["required_evidence_roots"]) - old_required
    plan["required_evidence_roots"] = sorted(
        preserved | required_instruction_evidence(new_instruction))
    plan["plan_root"] = root({key: value for key, value in plan.items()
                               if key != "plan_root"})
    validate_plan(plan, expected_instruction=new_instruction)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(canonical_bytes(plan)); stream.flush()
        __import__("os").fsync(stream.fileno())
    print(json.dumps({"status": "PASS", "application_id": plan["application_id"],
                      "plan_root": plan["plan_root"], "output": str(args.out),
                      "semantic_change": "NONE",
                      "binding_change": "PIPELINE_RELEASE_AND_INSTRUCTION_ONLY"},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
