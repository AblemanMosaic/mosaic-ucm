#!/usr/bin/env python3
"""Build or check r035 Windows/WSL positive correspondence records."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance/common-turn-r035"
IMPLEMENTATION = (
    "src/ucm/pippi_turn_workflow.py", "src/ucm/pippi_global.py",
    "src/ucm/pippi_turn_record.py", "src/ucm/pippi_cmba.py",
    "tools/run_common_turn_r035_demo.py", "examples/common-turn-r035/REQUEST.json",
)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build():
    request = (ROOT / "examples/common-turn-r035/REQUEST.json").read_bytes()
    rows = []
    for name in sorted(IMPLEMENTATION):
        raw = (ROOT / name).read_bytes()
        rows.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
    expected = None
    witnesses = []
    for platform, label, python_version in (("WINDOWS_NATIVE", "WINDOWS", "3.12"),
                                             ("WSL_NATIVE", "WSL", "3.12")):
        receipt_path = ROOT / f"review/common-turn-r035-positive/{label}-DEMO-RECEIPT.json"
        evidence_path = ROOT / f"review/common-turn-r035-positive/{label}-PILOT-EVIDENCE.zip"
        receipt = json.loads(receipt_path.read_bytes())
        with zipfile.ZipFile(evidence_path) as archive:
            canonical_bytes = archive.read("canonical.json")
        expected = canonical_bytes if expected is None else expected
        if canonical_bytes != expected:
            raise SystemExit("PORTABILITY_CANONICAL_BYTES_DIVERGED")
        witnesses.append({"platform": platform, "python": python_version, "status": "PASS",
            "provenance": "BUILDER_OBSERVED_NATIVE_POSITIVE_EXECUTION",
            "canonical_output_root": receipt["canonical_output_root"],
            "canonical_sha256": sha(canonical_bytes), "demo_receipt_root": receipt["receipt_root"],
            "demo_receipt_sha256": sha(receipt_path.read_bytes()),
            "evidence_zip_sha256": sha(evidence_path.read_bytes()),
            "adversarial_cases_executed": 0})
    body = {"schema": "mosaic.ucm.common-turn-portability.v0.1",
        "scope": "R035_COMMON_TURN_CLOSURE_POSITIVE_CORRESPONDENCE",
        "request_sha256": sha(request), "implementation_members": rows,
        "implementation_root": sha(canonical(rows)), "witnesses": witnesses,
        "status": "PASS", **BOUNDARY}
    return {"EXPECTED-CANONICAL.json": expected,
            "PORTABILITY.json": canonical({**body, "root": sha(canonical(body))}) + b"\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records = build()
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, raw in records.items():
            (OUT / name).write_bytes(raw)
    else:
        for name, raw in records.items():
            if not (OUT / name).is_file() or (OUT / name).read_bytes() != raw:
                raise SystemExit("R035_PORTABILITY_RECORD_DRIFT:" + name)
    print(json.dumps({"status": "PASS", "mode": "WRITE" if args.write else "CHECK",
                      "canonical_sha256": sha(records["EXPECTED-CANONICAL.json"]),
                      "adversarial_cases_executed": 0, **BOUNDARY}, sort_keys=True))


if __name__ == "__main__":
    main()
