"""Build the deterministic, self-contained Stage I3 review handoff."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip


SCHEMA = "mosaic.ucm.amcas-stage-i3-review-handoff.v0.1"
ROLE = "INDEPENDENT_REVIEW_HANDOFF"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--pipeline-handoff", type=Path, required=True)
    parser.add_argument("--predecessor-snapshot", type=Path, required=True)
    parser.add_argument("--court-evidence", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--software-anchor", type=Path, required=True)
    parser.add_argument("--c1-review-evidence", type=Path, required=True)
    parser.add_argument("--c1-review-disposition", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    paths = {
        "subject/STAGE-I3-SNAPSHOT.zip": args.snapshot.resolve(),
        "subject/STAGE-I3-SNAPSHOT-RECEIPT.json": args.receipt.resolve(),
        "dependencies/PIPELINE-v0.1-HANDOFF.zip": args.pipeline_handoff.resolve(),
        "dependencies/PREDECESSOR-C4-SNAPSHOT.zip": args.predecessor_snapshot.resolve(),
        "dependencies/CORRESPONDENCE-COURT-EVIDENCE.zip": args.court_evidence.resolve(),
        "qualification/QUALIFICATION.json": args.qualification.resolve(),
        "qualification/SOFTWARE-ANCHOR.json": args.software_anchor.resolve(),
        "review/c1/REVIEWER-EVIDENCE.zip": args.c1_review_evidence.resolve(),
        "review/c1/DISPOSITION.json": args.c1_review_disposition.resolve(),
        "review/WORK-ORDER.md": ROOT / "review" / "STAGE-I3-INDEPENDENT-REVIEW-WORK-ORDER.md",
        "VERIFY.py": ROOT / "VERIFY.py",
    }
    for path in paths.values():
        require(path.is_file(), "STAGE_I3_REVIEW_INPUT_MISSING")

    receipt = strict_loads(paths["subject/STAGE-I3-SNAPSHOT-RECEIPT.json"].read_bytes())
    qualification = strict_loads(paths["qualification/QUALIFICATION.json"].read_bytes())
    c1_disposition = strict_loads(paths["review/c1/DISPOSITION.json"].read_bytes())
    require(c1_disposition.get("finding") == "AMCAS1-01"
            and c1_disposition.get("disposition") == "ACCEPTED_FOR_C2_REPAIR",
            "STAGE_I3_C1_DISPOSITION_INVALID")
    boundary_body = {
        "schema": "mosaic.ucm.amcas-stage-i3-review-boundary.v0.1",
        "subject_schema": "mosaic.ucm.amcas-integration-portfolio-snapshot.v0.5",
        "subject_role": "PORTABLE_CANONICAL_INTEGRATION_PORTFOLIO",
        "subject_sha256": sha(paths["subject/STAGE-I3-SNAPSHOT.zip"].read_bytes()),
        "subject_receipt_sha256": sha(paths["subject/STAGE-I3-SNAPSHOT-RECEIPT.json"].read_bytes()),
        "subject_status_root": receipt["portfolio_status_root"],
        "stage_i3_inventory_root": receipt["stage_i3_inventory_root"],
        "pipeline_release_handoff_sha256": sha(paths["dependencies/PIPELINE-v0.1-HANDOFF.zip"].read_bytes()),
        "predecessor_snapshot_sha256": sha(paths["dependencies/PREDECESSOR-C4-SNAPSHOT.zip"].read_bytes()),
        "correspondence_court_evidence_sha256": sha(paths["dependencies/CORRESPONDENCE-COURT-EVIDENCE.zip"].read_bytes()),
        "qualification_sha256": sha(paths["qualification/QUALIFICATION.json"].read_bytes()),
        "qualification_root": qualification["qualification_root"],
        "c1_review_evidence_sha256": sha(paths["review/c1/REVIEWER-EVIDENCE.zip"].read_bytes()),
        "c1_review_disposition_sha256": sha(paths["review/c1/DISPOSITION.json"].read_bytes()),
        "accepted_c1_finding": "AMCAS1-01",
        "fixed_application_denominator": 7,
        "review_scope": "STAGE_I3_SHADOW_PLANNING",
        "shadow_execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    boundary = {**boundary_body, "boundary_root": root(boundary_body)}
    payloads = {name: path.read_bytes() for name, path in paths.items()}
    payloads["REVIEW-BOUNDARY.json"] = canonical_bytes(boundary)
    raw_a = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    raw_b = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    require(raw_a == raw_b, "STAGE_I3_REVIEW_HANDOFF_NONDETERMINISTIC")
    manifest = verify_deterministic_zip(raw_a, expected_schema=SCHEMA,
                                        expected_role=ROLE)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    require(not args.out.exists(), "STAGE_I3_REVIEW_HANDOFF_OUTPUT_EXISTS")
    args.out.write_bytes(raw_a)
    handoff_body = {
        "schema": "mosaic.ucm.amcas-stage-i3-review-handoff-receipt.v0.1",
        "handoff_filename": args.out.name,
        "handoff_sha256": sha(raw_a),
        "handoff_bytes": len(raw_a),
        "handoff_manifest_root": manifest["manifest_root"],
        "review_boundary_root": boundary["boundary_root"],
        "subject_sha256": boundary["subject_sha256"],
        "qualification_root": boundary["qualification_root"],
        "shadow_execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    handoff = {**handoff_body, "receipt_root": root(handoff_body)}
    receipt_path = args.out.with_name(args.out.stem + "-RECEIPT.json")
    require(not receipt_path.exists(), "STAGE_I3_REVIEW_HANDOFF_RECEIPT_EXISTS")
    receipt_path.write_bytes(canonical_bytes(handoff))
    print(canonical_bytes(handoff).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
