#!/usr/bin/env python3
"""Build the deterministic Stage I3-repair plus I4 work 1–3 handoff."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--pipeline-handoff", type=Path, required=True)
    parser.add_argument("--predecessor-handoff", type=Path, required=True)
    parser.add_argument("--passive-review", type=Path, required=True)
    parser.add_argument("--passive-review-evidence", type=Path, required=True)
    parser.add_argument("--operator-oracle-evidence", type=Path, required=True)
    parser.add_argument("--candidate-court", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    qdir = args.qualification_dir
    paths = {
        "subject/STAGE-I4-WORK-1-3-CHECKPOINT.zip": args.checkpoint,
        "qualification/QUALIFICATION.json": qdir / "QUALIFICATION.json",
        "qualification/SOFTWARE-ANCHOR.json": qdir / "SOFTWARE-ANCHOR.json",
        "qualification/CANONICAL-SOFTWARE.zip": qdir / "CANONICAL-SOFTWARE.zip",
        "qualification/QUALIFICATION-SOURCE.zip": qdir / "QUALIFICATION-SOURCE.zip",
        "qualification/QUALIFICATION-SOURCE-ANCHOR.json": qdir / "QUALIFICATION-SOURCE-ANCHOR.json",
        "dependencies/PIPELINE-v0.1-HANDOFF.zip": args.pipeline_handoff,
        "predecessor/STAGE-I3-C2-REVIEW-HANDOFF.zip": args.predecessor_handoff,
        "predecessor/FOCUSED-PASSIVE-REVIEW.md": args.passive_review,
        "predecessor/PASSIVE-REVIEW-EVIDENCE.zip": args.passive_review_evidence,
        "predecessor/OPERATOR-ORACLE-EVIDENCE.zip": args.operator_oracle_evidence,
        "evidence/STAGE-I3-CANDIDATE-VALIDATOR-COURT.json": args.candidate_court,
        "review/WORK-ORDER.md": ROOT / "review/STAGE-I4-WORK-1-3-INDEPENDENT-REVIEW-WORK-ORDER.md",
        "spec/STAGE-I4-WORK-1-3-CONTRACT.json": ROOT / "spec/STAGE-I4-WORK-1-3-CONTRACT.json",
        "spec/QUALIFICATION-SOURCE-CONTRACT.json": ROOT / "spec/QUALIFICATION-SOURCE-CONTRACT.json",
        "VERIFY.py": ROOT / "VERIFY.py",
    }
    for path in paths.values():
        require(path.is_file(), "STAGE_I4_REVIEW_INPUT_MISSING")
    qualification = strict_loads(paths["qualification/QUALIFICATION.json"].read_bytes())
    anchor = strict_loads(paths["qualification/SOFTWARE-ANCHOR.json"].read_bytes())
    source_anchor = strict_loads(
        paths["qualification/QUALIFICATION-SOURCE-ANCHOR.json"].read_bytes())
    candidate = strict_loads(args.candidate_court.read_bytes())
    require(qualification["status"] == "PASS" and qualification["skips"] == 0
            and qualification["staged_qualification_source_status"] == "PASS",
            "STAGE_I4_QUALIFICATION_INVALID")
    require(anchor["archive_sha256"] == sha(
        paths["qualification/CANONICAL-SOFTWARE.zip"].read_bytes()),
        "STAGE_I4_SOFTWARE_ANCHOR_INVALID")
    require(source_anchor["archive_sha256"] == sha(
        paths["qualification/QUALIFICATION-SOURCE.zip"].read_bytes()),
        "STAGE_I4_QUALIFICATION_SOURCE_ANCHOR_INVALID")
    require(candidate["status"] == "PASS"
            and candidate["target"] == "PACKAGED_UCM_STAGE3_VALIDATE_PLAN",
            "STAGE_I4_CANDIDATE_COURT_INVALID")
    boundary_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-work-1-3-review-boundary.v0.1",
        "checkpoint_sha256": sha(args.checkpoint.read_bytes()),
        "qualification_root": qualification["qualification_root"],
        "qualification_sha256": sha(paths["qualification/QUALIFICATION.json"].read_bytes()),
        "qualification_source_sha256": source_anchor["archive_sha256"],
        "canonical_software_sha256": anchor["archive_sha256"],
        "pipeline_handoff_sha256": sha(args.pipeline_handoff.read_bytes()),
        "predecessor_handoff_sha256": sha(args.predecessor_handoff.read_bytes()),
        "passive_review_evidence_sha256": sha(args.passive_review_evidence.read_bytes()),
        "operator_oracle_evidence_sha256": sha(args.operator_oracle_evidence.read_bytes()),
        "candidate_validator_court_root": candidate["court_root"],
        "fixed_application_denominator": 7,
        "application_contact_authorized": False,
        "shadow_execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    boundary = {**boundary_body, "boundary_root": root(boundary_body)}
    payloads = {name: path.read_bytes() for name, path in paths.items()}
    payloads["REVIEW-BOUNDARY.json"] = canonical_bytes(boundary)
    raw_a = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas-stage-i4-work-1-3-review-handoff.v0.1",
        artifact_role="INDEPENDENT_REVIEW_HANDOFF")
    raw_b = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas-stage-i4-work-1-3-review-handoff.v0.1",
        artifact_role="INDEPENDENT_REVIEW_HANDOFF")
    require(raw_a == raw_b, "STAGE_I4_REVIEW_HANDOFF_NONDETERMINISTIC")
    manifest = verify_deterministic_zip(raw_a,
        expected_schema="mosaic.ucm.amcas-stage-i4-work-1-3-review-handoff.v0.1",
        expected_role="INDEPENDENT_REVIEW_HANDOFF")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    require(not args.out.exists(), "STAGE_I4_REVIEW_HANDOFF_OUTPUT_EXISTS")
    args.out.write_bytes(raw_a)
    receipt_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-work-1-3-review-handoff-receipt.v0.1",
        "handoff_sha256": sha(raw_a), "handoff_bytes": len(raw_a),
        "handoff_manifest_root": manifest["manifest_root"],
        "review_boundary_root": boundary["boundary_root"],
        "qualification_root": qualification["qualification_root"],
        "checkpoint_sha256": boundary["checkpoint_sha256"],
        "application_contact_authorized": False,
        "shadow_execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    receipt_path = args.out.with_name(args.out.stem + "-RECEIPT.json")
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(canonical_bytes(receipt).decode()); return 0


if __name__ == "__main__":
    raise SystemExit(main())
