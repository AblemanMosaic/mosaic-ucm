#!/usr/bin/env python3
"""Normalize exact Stage I3 review material into a typed review archive."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402
from ucm.stage4 import (REVIEW_ARCHIVE_ROLE, REVIEW_ARCHIVE_SCHEMA, REVIEW_POLICY_ID,
                        REVIEW_SCHEMA, validate_review_disposition)  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage3-handoff", type=Path, required=True)
    parser.add_argument("--review-report", type=Path, required=True)
    parser.add_argument("--review-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    handoff_raw = args.stage3_handoff.read_bytes()
    report_raw = args.review_report.read_bytes()
    evidence_raw = args.review_evidence.read_bytes()
    with zipfile.ZipFile(io.BytesIO(handoff_raw)) as handoff:
        snapshot_raw = handoff.read("subject/STAGE-I3-SNAPSHOT.zip")
        qualification = strict_loads(handoff.read("qualification/QUALIFICATION.json"))
    applications = []
    with zipfile.ZipFile(io.BytesIO(snapshot_raw)) as snapshot:
        instructions = {}
        plans = {}
        for name in snapshot.namelist():
            if name.startswith("stage-i3/instructions/") and name.endswith(".json"):
                item = strict_loads(snapshot.read(name)); instructions[item["application_id"]] = item
            if name.startswith("stage-i3/responses/") and name.endswith("-PLAN.json"):
                item = strict_loads(snapshot.read(name)); plans[item["application_id"]] = item
    if set(instructions) != set(plans) or len(plans) != 7:
        raise SystemExit("STAGE_I3_REVIEW_APPLICATION_SET_INVALID")
    for app in sorted(plans):
        applications.append({"application_id": app,
            "instruction_root": instructions[app]["instruction_root"],
            "plan_root": plans[app]["plan_root"]})
    identity_root = root({"policy_id": REVIEW_POLICY_ID,
        "report_sha256": sha(report_raw), "evidence_sha256": sha(evidence_raw)})
    body = {"schema": REVIEW_SCHEMA, "review_class": "INDEPENDENT_REVIEW",
        "reviewer_policy_id": REVIEW_POLICY_ID,
        "reviewer_identity_root": identity_root,
        "reviewed_subject_root": sha(snapshot_raw),
        "reviewed_qualification_root": qualification["qualification_root"],
        "reviewed_source_root": qualification["source_graph_root"],
        "applications": applications, "verdict": "HOLD_FOR_REPAIR",
        "findings": [
            {"id": "I3C2-R1", "severity": "MED", "status": "OPEN",
             "summary": "Qualification reproduction package is incomplete."},
            {"id": "I3C2-R2", "severity": "MED", "status": "OPEN",
             "summary": "Operator court did not exercise the packaged implementation."},
            {"id": "I3C2-R3", "severity": "MED", "status": "OPEN",
             "summary": "Production coverage checks were weaker than the reference checker."}],
        "limitations": ["TIER1_NOT_INDEPENDENTLY_EXECUTED",
                        "TERMINAL_QUALIFICATION_WITHHELD"], **BOUNDARY}
    disposition = validate_review_disposition(
        {**body, "disposition_root": root(body)})
    payloads = {"REVIEW-DISPOSITION.json": canonical_bytes(disposition),
        "REPORT.md": report_raw, "REVIEWER-EVIDENCE.zip": evidence_raw,
        "STAGE-I3-HANDOFF.sha256": (sha(handoff_raw) + "\n").encode("ascii")}
    raw = deterministic_zip(payloads, schema=REVIEW_ARCHIVE_SCHEMA,
                            artifact_role=REVIEW_ARCHIVE_ROLE)
    verify_deterministic_zip(raw, expected_schema=REVIEW_ARCHIVE_SCHEMA,
                             expected_role=REVIEW_ARCHIVE_ROLE)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists(): raise SystemExit("STAGE_I3_REVIEW_OUTPUT_EXISTS")
    args.out.write_bytes(raw)
    print(canonical_bytes({"status": "PASS", "archive_sha256": sha(raw),
        "disposition_root": disposition["disposition_root"], **BOUNDARY}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
