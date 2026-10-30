#!/usr/bin/env python3
"""Build c2 review handoff after operator evidence has been verified."""
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
from ucm.qualification import validate_qualification  # noqa: E402


def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()


def member(raw: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive: return archive.read(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--qualification-source", type=Path, required=True)
    parser.add_argument("--qualification-evidence", type=Path, required=True)
    parser.add_argument("--review-archive", type=Path, required=True)
    parser.add_argument("--predecessor-handoff", type=Path, required=True)
    parser.add_argument("--operator-kit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    checkpoint_raw = args.checkpoint.read_bytes()
    source_raw = args.qualification_source.read_bytes()
    evidence_raw = args.qualification_evidence.read_bytes()
    qualification = strict_loads(member(evidence_raw, "QUALIFICATION.json"))
    tier1_raw = member(evidence_raw, "TIER1-EVIDENCE.zip")
    validate_qualification(qualification, qualification_source_raw=source_raw,
        checkpoint_raw=checkpoint_raw, operator_evidence_raw=tier1_raw)
    boundary_body = {"schema": "mosaic.ucm.amcas-stage-i4-c2-review-boundary.v0.1",
        "checkpoint_sha256": sha(checkpoint_raw),
        "qualification_source_sha256": sha(source_raw),
        "qualification_evidence_sha256": sha(evidence_raw),
        "qualification_root": qualification["qualification_root"],
        "operator_evidence_sha256": sha(tier1_raw),
        "review_archive_sha256": sha(args.review_archive.read_bytes()),
        "predecessor_handoff_sha256": sha(args.predecessor_handoff.read_bytes()),
        "operator_kit_sha256": sha(args.operator_kit.read_bytes()),
        "fixed_application_denominator": 7, "application_contact_authorized": False,
        "shadow_execution_authorized": False, "composition_authorized": False,
        **BOUNDARY}
    boundary = {**boundary_body, "boundary_root": root(boundary_body)}
    payloads = {"REVIEW-BOUNDARY.json": canonical_bytes(boundary),
        "subject/STAGE-I4-C2-CHECKPOINT.zip": checkpoint_raw,
        "qualification/QUALIFICATION-SOURCE.zip": source_raw,
        "qualification/OPERATOR-QUALIFICATION-EVIDENCE.zip": evidence_raw,
        "review/STAGE-I3-REVIEW-EVIDENCE.zip": args.review_archive.read_bytes(),
        "predecessor/STAGE-I3-C2-HANDOFF.zip": args.predecessor_handoff.read_bytes(),
        "operator/STAGE-I4-C2-OPERATOR-KIT.zip": args.operator_kit.read_bytes(),
        "review/WORK-ORDER.md": (ROOT / "review/STAGE-I4-C2-INTEGRATED-REPAIR-WORK-ORDER.md").read_bytes(),
        "spec/STAGE-I4-C2-CONTRACT.json": (ROOT / "spec/STAGE-I4-C2-CONTRACT.json").read_bytes(),
        "VERIFY.py": (ROOT / "review/stage4-c2/VERIFY.py").read_bytes()}
    raw_a = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas-stage-i4-c2-review-handoff.v0.1",
        artifact_role="INDEPENDENT_REVIEW_HANDOFF")
    raw_b = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas-stage-i4-c2-review-handoff.v0.1",
        artifact_role="INDEPENDENT_REVIEW_HANDOFF")
    if raw_a != raw_b: raise SystemExit("STAGE_I4_C2_HANDOFF_NONDETERMINISTIC")
    verify_deterministic_zip(raw_a,
        expected_schema="mosaic.ucm.amcas-stage-i4-c2-review-handoff.v0.1",
        expected_role="INDEPENDENT_REVIEW_HANDOFF")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists(): raise SystemExit("STAGE_I4_C2_HANDOFF_EXISTS")
    args.out.write_bytes(raw_a)
    receipt_body = {"schema": "mosaic.ucm.amcas-stage-i4-c2-handoff-receipt.v0.1",
        "handoff_sha256": sha(raw_a), "handoff_bytes": len(raw_a),
        "boundary_root": boundary["boundary_root"],
        "qualification_root": qualification["qualification_root"], **BOUNDARY}
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    args.out.with_name(args.out.stem + "-RECEIPT.json").write_bytes(canonical_bytes(receipt))
    print(canonical_bytes(receipt).decode()); return 0


if __name__ == "__main__": raise SystemExit(main())
