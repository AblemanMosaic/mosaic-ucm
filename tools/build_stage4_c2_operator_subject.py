#!/usr/bin/env python3
"""Build the exact subject consumed by the human-run c2 review apparatus."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uclop.canonical import canonical_bytes  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--review-archive", type=Path, required=True)
    parser.add_argument("--stage3-handoff", type=Path, required=True)
    parser.add_argument("--work-order", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = {"QUALIFICATION-SOURCE.zip": args.qualification_source,
        "STAGE-I4-C2-CHECKPOINT.zip": args.checkpoint,
        "STAGE-I3-REVIEW-EVIDENCE.zip": args.review_archive,
        "STAGE-I3-C2-HANDOFF.zip": args.stage3_handoff,
        "WORK-ORDER.md": args.work_order,
        "STAGE-I4-C2-CONTRACT.json": ROOT / "spec/STAGE-I4-C2-CONTRACT.json"}
    for path in paths.values():
        if not path.is_file(): raise SystemExit("STAGE_I4_C2_OPERATOR_SUBJECT_INPUT_MISSING")
    raw = deterministic_zip({name: path.read_bytes() for name, path in paths.items()},
        schema="mosaic.ucm.amcas-stage-i4-c2-operator-subject.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C2_OPERATOR_SUBJECT")
    manifest = verify_deterministic_zip(raw,
        expected_schema="mosaic.ucm.amcas-stage-i4-c2-operator-subject.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C2_OPERATOR_SUBJECT")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists(): raise SystemExit("STAGE_I4_C2_OPERATOR_SUBJECT_EXISTS")
    args.out.write_bytes(raw)
    print(canonical_bytes({"status": "PASS", "subject_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_root": manifest["manifest_root"], "bytes": len(raw), **BOUNDARY}).decode())
    return 0


if __name__ == "__main__": raise SystemExit(main())
