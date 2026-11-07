#!/usr/bin/env python3
"""Seal the complete Stage I4 c3 operator folder as one portable archive."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402


SCHEMA = "mosaic.ucm.amcas-stage-i4-c3-operator-delivery.v0.1"
ROLE = "UCM_AMCAS_STAGE_I4_C3_OPERATOR_DELIVERY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.directory.is_dir() or args.out.exists():
        raise SystemExit("STAGE_I4_C3_OPERATOR_DELIVERY_BOUNDARY_INVALID")
    payloads = {
        path.relative_to(args.directory).as_posix(): path.read_bytes()
        for path in sorted(args.directory.rglob("*"),
                           key=lambda row: row.relative_to(args.directory).as_posix())
        if path.is_file()
    }
    required = {
        "BOOTSTRAP-STAGE-I4-C3.py", "EXACT-ARTIFACT-BOUNDARY.json",
        "RUN-STAGE-I4-C3-OPERATOR-REVIEW.cmd", "START-HERE.md",
        "UCL-UCM-AMCAS-STAGE-I4-C3-OPERATOR-KIT.zip",
    }
    if set(payloads) != required:
        raise SystemExit("STAGE_I4_C3_OPERATOR_DELIVERY_FILE_SET_INVALID")
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    manifest = verify_deterministic_zip(raw, expected_schema=SCHEMA,
                                        expected_role=ROLE)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        __import__("os").fsync(stream.fileno())
    print(json.dumps({"status": "PASS", "path": str(args.out),
        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "members": len(manifest["files"]), "manifest_root": manifest["manifest_root"],
        **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
