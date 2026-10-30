#!/usr/bin/env python3
"""Freeze Stage I4 c2 only after exact operator evidence passes."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.qualification import validate_qualification  # noqa: E402


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def pair(name: str, a: Path, b: Path) -> dict:
    if sha(a) != sha(b): raise SystemExit("STAGE_I4_C2_" + name + "_NONDETERMINISTIC")
    return {"sha256": sha(a), "bytes": a.stat().st_size,
            "deterministic_rebuild_equal": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-evidence", type=Path, required=True)
    parser.add_argument("--qualification-source", type=Path, required=True)
    parser.add_argument("--checkpoint-a", type=Path, required=True)
    parser.add_argument("--checkpoint-b", type=Path, required=True)
    parser.add_argument("--handoff-a", type=Path, required=True)
    parser.add_argument("--handoff-b", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence_raw = args.qualification_evidence.read_bytes()
    with zipfile.ZipFile(io.BytesIO(evidence_raw)) as archive:
        qualification = strict_loads(archive.read("QUALIFICATION.json"))
        tier1_raw = archive.read("TIER1-EVIDENCE.zip")
    validate_qualification(qualification,
        qualification_source_raw=args.qualification_source.read_bytes(),
        checkpoint_raw=args.checkpoint_a.read_bytes(), operator_evidence_raw=tier1_raw)
    artifacts = {"checkpoint": pair("CHECKPOINT", args.checkpoint_a, args.checkpoint_b),
        "review_handoff": pair("HANDOFF", args.handoff_a, args.handoff_b),
        "qualification_evidence": {"sha256": sha(args.qualification_evidence),
            "bytes": args.qualification_evidence.stat().st_size},
        "qualification_source": {"sha256": sha(args.qualification_source),
            "bytes": args.qualification_source.stat().st_size}}
    receipt_body = {"schema": "mosaic.ucm.amcas-stage-i4-c2-freeze-receipt.v0.1",
        "subject": "UCM-AMCAS Stage I4 c2 integrated repair",
        "qualification_root": qualification["qualification_root"],
        "source_root": qualification["source_graph_root"], "artifacts": artifacts,
        "fixed_application_denominator": 7, "preparation_ready": 4,
        "execution_eligible": 0, "application_contact_authorized": False,
        "shadow_execution_authorized": False, "composition_authorized": False, **BOUNDARY}
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    args.out_dir.mkdir(parents=True, exist_ok=False)
    handoff_name = "UCL-UCM-AMCAS-STAGE-I4-C2-INDEPENDENT-REVIEW-HANDOFF.zip"
    shutil.copyfile(args.handoff_a, args.out_dir / handoff_name)
    (args.out_dir / "STAGE-I4-C2-FREEZE-RECEIPT.json").write_bytes(canonical_bytes(receipt))
    boundary_body = {"schema": "mosaic.ucm.amcas-stage-i4-c2-exact-boundary.v0.1",
        "review_handoff_sha256": artifacts["review_handoff"]["sha256"],
        "freeze_receipt_root": receipt["receipt_root"],
        "runner_required_files": [handoff_name, "STAGE-I4-C2-FREEZE-RECEIPT.json"],
        "directory_layout": "SIBLING_FILES", "retry_identity": artifacts["review_handoff"]["sha256"],
        **BOUNDARY}
    boundary = {**boundary_body, "boundary_root": root(boundary_body)}
    (args.out_dir / "EXACT-ARTIFACT-BOUNDARY.json").write_bytes(canonical_bytes(boundary))
    print(canonical_bytes({"status": "PASS", "qualification_root": qualification["qualification_root"],
        "receipt_root": receipt["receipt_root"], "boundary_root": boundary["boundary_root"], **BOUNDARY}).decode())
    return 0


if __name__ == "__main__": raise SystemExit(main())
