#!/usr/bin/env python3
"""Build the no-execution Stage I4 work 1–3 preparation checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402
from ucm.stage4 import derive_eligibility, verify_review_archive  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_stage3(handoff_raw: bytes) -> tuple[dict[str, dict], dict[str, dict]]:
    with zipfile.ZipFile(io.BytesIO(handoff_raw)) as handoff:
        subject_raw = handoff.read("subject/STAGE-I3-SNAPSHOT.zip")
    instructions = {}; plans = {}
    with zipfile.ZipFile(io.BytesIO(subject_raw)) as subject:
        for name in subject.namelist():
            if name.startswith("stage-i3/instructions/") and name.endswith(".json"):
                value = strict_loads(subject.read(name)); instructions[value["application_id"]] = value
            if name.startswith("stage-i3/responses/") and name.endswith("-PLAN.json"):
                value = strict_loads(subject.read(name)); plans[value["application_id"]] = value
    if set(instructions) != set(plans) or len(plans) != 7:
        raise SystemExit("STAGE_I4_FIXED_DENOMINATOR_INVALID")
    return instructions, plans


def build(*, handoff: Path, review_archive: Path, review_evidence: Path, review_report: Path,
          manual_evidence: Path, candidate_court: Path, output: Path) -> dict:
    handoff_raw = handoff.read_bytes(); review_raw = review_evidence.read_bytes()
    review_archive_raw = review_archive.read_bytes()
    verified_review = verify_review_archive(review_archive_raw)
    review_disposition = verified_review["disposition"]
    instructions, plans = load_stage3(handoff_raw)
    eligibility = {}
    for application_id in sorted(plans):
        eligibility[application_id] = derive_eligibility(
            instruction=instructions[application_id], plan=plans[application_id],
            review_archive=review_archive_raw)
    preparation_ready = sum(row["eligible_for_shadow_preparation"] for row in eligibility.values())
    execution_ready = sum(row["eligible_for_shadow_execution"] for row in eligibility.values())
    status_body = {
        "schema": "mosaic.ucm.stage-i4-c2-status.v0.1",
        "fixed_application_denominator": 7,
        "stage_i3_preparation_ready": preparation_ready,
        "stage_i3_held": 7 - preparation_ready,
        "shadow_execution_eligible": execution_ready,
        "run_contracts_issued": 0, "application_contacts": 0,
        "shadow_executions": 0, "composition_events": 0,
        "stage_i3_review_verdict": review_disposition["verdict"],
        "stage_i3_review_archive_sha256": sha(review_archive_raw),
        "stage_i3_review_disposition_root": review_disposition["disposition_root"],
        "predecessor_handoff_sha256": sha(handoff_raw),
        "candidate_validator_court_root": strict_loads(candidate_court.read_bytes())["court_root"],
        "next_action": "INDEPENDENT_REVIEW_REPAIR_AND_I4_CONTRACTS_BEFORE_ANY_RUN",
        "application_contact_authorized": False,
        "execution_authorized": False, "composition_authorized": False,
        **BOUNDARY,
    }
    status = {**status_body, "status_root": root(status_body)}
    closure_body = {
        "schema": "mosaic.ucm.stage-i3-c2-focused-repair-closure.v0.1",
        "predecessor_handoff_sha256": sha(handoff_raw),
        "passive_review_evidence_sha256": sha(review_raw),
        "passive_review_report_sha256": sha(review_report.read_bytes()),
        "operator_oracle_evidence_sha256": sha(manual_evidence.read_bytes()),
        "operator_oracle_claim": "REFERENCE_ORACLE_EVIDENCE",
        "candidate_validator_court_sha256": sha(candidate_court.read_bytes()),
        "candidate_validator_court_root": strict_loads(candidate_court.read_bytes())["court_root"],
        "qualification_dependency_closure": "PACKAGED",
        "production_case_coverage": "EXACT_AND_CAPABILITY_OWNED",
        "relation_disposition_multiplicity": "UNIQUE",
        "terminal_independent_verdict_inferred": False,
        **BOUNDARY,
    }
    closure = {**closure_body, "closure_root": root(closure_body)}
    payloads = {
        "README.md": (ROOT / "docs/STAGE-I4-WORK-1-3.md").read_bytes(),
        "STAGE-I4-C2-STATUS.json": canonical_bytes(status),
        "STAGE-I3-C2-REPAIR-CLOSURE.json": canonical_bytes(closure),
        "spec/STAGE-I4-WORK-1-3-CONTRACT.json":
            (ROOT / "spec/STAGE-I4-WORK-1-3-CONTRACT.json").read_bytes(),
        "spec/STAGE-I4-C2-CONTRACT.json":
            (ROOT / "spec/STAGE-I4-C2-CONTRACT.json").read_bytes(),
        "spec/QUALIFICATION-SOURCE-CONTRACT.json":
            (ROOT / "spec/QUALIFICATION-SOURCE-CONTRACT.json").read_bytes(),
        "review/STAGE-I3-REVIEW-EVIDENCE.zip": review_archive_raw,
        "evidence/STAGE-I3-CANDIDATE-VALIDATOR-COURT.json": candidate_court.read_bytes(),
    }
    for application_id, row in sorted(eligibility.items()):
        payloads[f"stage-i4/eligibility/{application_id}.json"] = canonical_bytes(row)
    archive = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas-stage-i4-c2-checkpoint.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C2_PREPARATION")
    manifest = verify_deterministic_zip(archive,
        expected_schema="mosaic.ucm.amcas-stage-i4-c2-checkpoint.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C2_PREPARATION")
    output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(archive)
    result = {"status": "PASS", "archive_sha256": sha(archive),
              "archive_bytes": len(archive), "manifest_root": manifest["manifest_root"],
              "status_root": status["status_root"], "applications": 7,
              "preparation_ready": preparation_ready, "execution_eligible": execution_ready,
              **BOUNDARY}
    print(json.dumps(result, sort_keys=True)); return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--review-archive", type=Path, required=True)
    parser.add_argument("--review-evidence", type=Path, required=True)
    parser.add_argument("--review-report", type=Path, required=True)
    parser.add_argument("--manual-evidence", type=Path, required=True)
    parser.add_argument("--candidate-court", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); build(**vars(args)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
