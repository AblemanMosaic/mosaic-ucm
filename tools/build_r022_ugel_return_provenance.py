#!/usr/bin/env python3
"""Build exact provenance over the received r022 UGEL review and operator returns."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review/ugel-r022-operator-return/PROVENANCE.json"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def evidence(path: Path, run_class: str) -> dict[str, object]:
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        result = json.loads(archive.read("TIER1-RESULT.json"))
    return {
        "path": path.relative_to(ROOT).as_posix(), "sha256": sha(raw),
        "bytes": len(raw), "status": result["status"],
        "case_count": len(result["cases"]), "failed": result["failed"],
        "court_root": result["court_root"], "run_class": run_class,
        "builder_authored": True, "operator_executed": True,
        "independent_review": False,
    }


def record() -> dict[str, object]:
    rows = [
        evidence(ROOT / "review/ugel-r022-operator-return/UCM-UGEL-r022-TIER1-HOLD-EVIDENCE.zip",
                 "INITIAL_OPERATOR_RUN_DISCOVERED_COURT_DEFECTS"),
        evidence(ROOT / "review/ugel-r022-operator-return/UCM-UGEL-r022-TIER1-PASS-EVIDENCE.zip",
                 "REPAIRED_COURT_OPERATOR_RUN"),
    ]
    review_rows = []
    for path in sorted((ROOT / "review/ugel-r022-review-return").iterdir()):
        if path.is_file():
            data = path.read_bytes()
            review_rows.append({"path": path.relative_to(ROOT).as_posix(),
                                "bytes": len(data), "sha256": sha(data)})
    body = {
        "schema": "mosaic.ucm.ugel-r022-return-provenance.v0.1",
        "subject_revision": "r022",
        "subject_runtime_sha256": "dce704f49607f98bed14c9fcae149cea0c39259efe1f70203bcaa518c5fd79f62",
        "operator_runs": rows, "review_files": review_rows,
        "pass_run_supersedes_hold_for_court_predicates_only": True,
        "pass_run_does_not_create_independent_review": True,
        **BOUNDARY,
    }
    return {**body, "provenance_root": sha(canonical(body))}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = canonical(record()) + b"\n"
    if args.write:
        OUT.write_bytes(raw)
    ok = OUT.is_file() and OUT.read_bytes() == raw
    print(json.dumps({"status": "PASS" if ok else "REFUSED",
                      "provenance_root": record()["provenance_root"], **BOUNDARY},
                     sort_keys=True))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
