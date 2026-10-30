#!/usr/bin/env python3
"""Attack the packaged Stage I3 production validator over the exact C2 plans."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.stage3 import validate_plan  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reroot(plan: dict) -> None:
    plan["plan_root"] = root({key: value for key, value in plan.items()
                              if key != "plan_root"})


def load_subject(raw: bytes) -> tuple[dict[str, dict], dict[str, dict]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as handoff:
        subject_raw = handoff.read("subject/STAGE-I3-SNAPSHOT.zip")
    instructions: dict[str, dict] = {}
    plans: dict[str, dict] = {}
    with zipfile.ZipFile(io.BytesIO(subject_raw)) as subject:
        for name in subject.namelist():
            if name.startswith("stage-i3/instructions/") and name.endswith(".json"):
                value = strict_loads(subject.read(name)); instructions[value["application_id"]] = value
            if (name.startswith("stage-i3/responses/") and name.endswith("-PLAN.json")):
                value = strict_loads(subject.read(name)); plans[value["application_id"]] = value
    if set(instructions) != set(plans) or len(plans) != 7:
        raise SystemExit("STAGE_I3_FIXED_DENOMINATOR_INVALID")
    return instructions, plans


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--expected-handoff-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    handoff_raw = args.handoff.read_bytes()
    if sha(handoff_raw) != args.expected_handoff_sha256:
        raise SystemExit("STAGE_I3_HANDOFF_HASH_MISMATCH")
    instructions, plans = load_subject(handoff_raw)
    rows = []

    def baseline(application_id: str) -> tuple[dict, dict]:
        instruction = instructions[application_id]
        plan = plans[application_id]
        validate_plan(plan, expected_instruction=instruction)
        return instruction, plan

    def attack(application_id: str, case_id: str, mutate, expected: str) -> None:
        instruction, original = baseline(application_id)
        plan = deepcopy(original)
        mutate(plan)
        if "plan_root" in plan:
            reroot(plan)
        observed = "ACCEPTED"
        try:
            validate_plan(plan, expected_instruction=instruction)
        except Exception as exc:  # typed candidate refusal is checked below
            observed = str(exc)
        status = "PASS" if expected in observed else "FAIL"
        rows.append({"id": f"{application_id}:{case_id}", "expected": expected,
                     "observed": observed, "status": status})

    for application_id in sorted(plans):
        plan = plans[application_id]
        attack(application_id, "AUTHORITY_EFFECT", lambda p: p.update(authority_effect="EXECUTE"),
               "STAGE_I3_AUTHORITY_CEILING_INVALID")
        attack(application_id, "REAL_A5", lambda p: p.update(real_a5=True),
               "STAGE_I3_AUTHORITY_CEILING_INVALID")
        attack(application_id, "G0", lambda p: p.update(g0="OPEN"),
               "STAGE_I3_AUTHORITY_CEILING_INVALID")
        attack(application_id, "SHADOW_REQUEST", lambda p: p.update(shadow_execution_requested=True),
               "STAGE_I3_PLAN_AUTHORITY_INVALID")
        attack(application_id, "COMPOSITION_REQUEST", lambda p: p.update(composition_requested=True),
               "STAGE_I3_PLAN_AUTHORITY_INVALID")
        attack(application_id, "PLAN_STATUS_CASE", lambda p: p.update(plan_status="ready_for_shadow_review"),
               "STAGE_I3_PLAN_STATUS_INVALID")
        attack(application_id, "PLAN_STATUS_NULL", lambda p: p.update(plan_status=None),
               "STAGE_I3_PLAN_STATUS_INVALID")
        attack(application_id, "PLAN_STATUS_DELETE", lambda p: p.pop("plan_status"),
               "REQUIRED_FIELD_MISSING")
        attack(application_id, "RESULT_DIVERGENCE",
               lambda p: p["correspondence_cases"][0].update(expected_ucm_result_root="0" * 64),
               "STAGE_I3_EXPECTED_RESULT_DIVERGENCE")
        required_root = instructions[application_id]["pipeline_release_sha256"]
        attack(application_id, "REQUIRED_EVIDENCE_DELETE",
               lambda p, required_root=required_root: p["required_evidence_roots"].remove(
                   required_root),
               "STAGE_I3_REQUIRED_EVIDENCE_MISSING")
        def add_uncovered(p):
            extra = deepcopy(p["correspondence_cases"][0])
            extra["id"] = extra["id"] + ".UNPROJECTED"
            extra["input_root"] = "0" * 64
            p["correspondence_cases"].append(extra)
        attack(application_id, "UNPROJECTED_CASE", add_uncovered,
               "STAGE_I3_CAPABILITY_CASE_COVERAGE_INVALID")
        if plan["relation_dispositions"]:
            attack(application_id, "DUPLICATE_RELATION",
                   lambda p: p["relation_dispositions"].append(
                       deepcopy(p["relation_dispositions"][0])),
                   "STAGE_I3_RELATION_DISPOSITION_DUPLICATE")
        if len(plan["capability_projections"]) > 1:
            def move_case(p):
                source = p["capability_projections"][0]
                target = p["capability_projections"][1]
                case_id = source["case_ids"].pop()
                target["case_ids"].append(case_id)
            attack(application_id, "WRONG_CAPABILITY_OWNER", move_case,
                   "STAGE_I3_CAPABILITY_CASE_OWNERSHIP_INVALID")
        if instructions[application_id]["stage_i1_status"] == "HOLD_FOR_REPAIR":
            attack(application_id, "INHERITED_HOLD_CLEAR", lambda p: p.update(holds=[]),
                   "STAGE_I3_INHERITED_HOLD_LOST")

    application_ids = sorted(plans)
    for left, right in zip(application_ids, application_ids[1:]):
        observed = "ACCEPTED"
        try:
            validate_plan(plans[right], expected_instruction=instructions[left])
        except Exception as exc:
            observed = str(exc)
        rows.append({"id": f"SWAP:{left}:{right}", "expected": "STAGE_I3_PLAN_BINDING_INVALID",
                     "observed": observed,
                     "status": "PASS" if "STAGE_I3_PLAN_BINDING_INVALID" in observed else "FAIL"})

    body = {
        "schema": "mosaic.ucm.stage-i3-candidate-attack-court.v0.1",
        "target": "PACKAGED_UCM_STAGE3_VALIDATE_PLAN",
        "handoff_sha256": sha(handoff_raw),
        "application_count": len(plans), "case_count": len(rows), "rows": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    result = {**body, "court_root": root(body)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_bytes(result))
    print(json.dumps({"status": result["status"], "cases": len(rows),
                      "court_root": result["court_root"], "out": str(args.out)},
                     sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
