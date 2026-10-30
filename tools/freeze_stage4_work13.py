#!/usr/bin/env python3
"""Freeze the exact, deterministically rebuilt Stage I4 work 1-3 handoff."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402


def sha(path: Path) -> str:
    require(path.is_file(), "STAGE_I4_FREEZE_INPUT_MISSING")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired(name: str, first: Path, second: Path) -> dict:
    first_sha, second_sha = sha(first), sha(second)
    require(first_sha == second_sha, f"STAGE_I4_{name}_NONDETERMINISTIC")
    return {"sha256": first_sha, "bytes": first.stat().st_size,
            "deterministic_rebuild_equal": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-a", type=Path, required=True)
    parser.add_argument("--checkpoint-b", type=Path, required=True)
    parser.add_argument("--pipeline-a", type=Path, required=True)
    parser.add_argument("--pipeline-b", type=Path, required=True)
    parser.add_argument("--handoff-a", type=Path, required=True)
    parser.add_argument("--handoff-b", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    qualification_path = args.qualification_dir / "QUALIFICATION.json"
    anchor_path = args.qualification_dir / "SOFTWARE-ANCHOR.json"
    software_path = args.qualification_dir / "CANONICAL-SOFTWARE.zip"
    source_path = args.qualification_dir / "QUALIFICATION-SOURCE.zip"
    source_anchor_path = args.qualification_dir / "QUALIFICATION-SOURCE-ANCHOR.json"
    qualification = strict_loads(qualification_path.read_bytes())
    anchor = strict_loads(anchor_path.read_bytes())
    source_anchor = strict_loads(source_anchor_path.read_bytes())
    require(qualification["status"] == "PASS" and qualification["skips"] == 0
            and qualification["staged_qualification_source_status"] == "PASS",
            "STAGE_I4_FREEZE_QUALIFICATION_INVALID")
    require(anchor["archive_sha256"] == sha(software_path),
            "STAGE_I4_FREEZE_SOFTWARE_ANCHOR_INVALID")
    require(source_anchor["archive_sha256"] == sha(source_path),
            "STAGE_I4_FREEZE_QUALIFICATION_SOURCE_ANCHOR_INVALID")

    artifacts = {
        "checkpoint": paired("CHECKPOINT", args.checkpoint_a, args.checkpoint_b),
        "pipeline_handoff": paired("PIPELINE", args.pipeline_a, args.pipeline_b),
        "review_handoff": paired("REVIEW_HANDOFF", args.handoff_a, args.handoff_b),
        "qualification": {"sha256": sha(qualification_path),
                          "bytes": qualification_path.stat().st_size},
        "canonical_software": {"sha256": sha(software_path),
                               "bytes": software_path.stat().st_size},
        "qualification_source": {"sha256": sha(source_path),
                                 "bytes": source_path.stat().st_size},
    }
    receipt_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-work-1-3-freeze-receipt.v0.1",
        "subject": "UCM-AMCAS Stage I4 work 1-3 c1",
        "qualification_root": qualification["qualification_root"],
        "source_root": qualification["source_graph_root"],
        "candidate_validator_court_root": qualification["candidate_validator_court_root"],
        "artifacts": artifacts,
        "fixed_application_denominator": 7,
        "application_contact_authorized": False,
        "shadow_execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    boundary_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-work-1-3-exact-artifact-boundary.v0.1",
        "review_handoff_sha256": artifacts["review_handoff"]["sha256"],
        "freeze_receipt_root": receipt["receipt_root"],
        "runner_required_files": [
            "UCL-UCM-AMCAS-STAGE-I4-WORK-1-3-C1-INDEPENDENT-REVIEW-HANDOFF.zip",
            "STAGE-I4-WORK-1-3-FREEZE-RECEIPT.json",
        ],
        "directory_layout": "SIBLING_FILES",
        "retry_identity": artifacts["review_handoff"]["sha256"],
        **BOUNDARY,
    }
    boundary = {**boundary_body, "boundary_root": root(boundary_body)}

    args.out_dir.mkdir(parents=True, exist_ok=False)
    final_handoff = args.out_dir / boundary["runner_required_files"][0]
    shutil.copyfile(args.handoff_a, final_handoff)
    (args.out_dir / "STAGE-I4-WORK-1-3-FREEZE-RECEIPT.json").write_bytes(
        canonical_bytes(receipt))
    (args.out_dir / "EXACT-ARTIFACT-BOUNDARY.json").write_bytes(
        canonical_bytes(boundary))
    print(canonical_bytes({"status": "PASS", "handoff_sha256": sha(final_handoff),
                           "qualification_root": qualification["qualification_root"],
                           "receipt_root": receipt["receipt_root"],
                           "boundary_root": boundary["boundary_root"], **BOUNDARY}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
