#!/usr/bin/env python3
"""Build or check the r036 Windows/WSL positive correspondence record."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance/cmba-composite-r036"
WITNESSES = ROOT / "review/cmba-composite-r036-positive"
IMPLEMENTATION = (
    "src/ucm/pippi_cmba_composite.py", "src/ucm/pippi_cmba.py",
    "src/ucm/pippi_turn_record.py", "src/ucm/process_governance.py",
    "src/ucm/ccp_admissibility.py", "src/ucm/operation_gateway.py",
    "src/ucm/operation_proofs.py", "src/ucm/thr_cas.py",
    "tests/test_pippi_cmba_composite_positive.py",
    "tools/run_cmba_composite_r036_positive.py",
)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build():
    rows = []
    for name in sorted(IMPLEMENTATION):
        raw = (ROOT / name).read_bytes()
        rows.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
    witnesses = []
    for label in ("WINDOWS", "WSL"):
        path = WITNESSES / f"{label}-WITNESS.json"
        witness = json.loads(path.read_bytes())
        body = {key: value for key, value in witness.items() if key != "witness_root"}
        if sha(canonical(body)) != witness.get("witness_root") or witness.get("status") != "PASS":
            raise SystemExit("R036_PORTABILITY_WITNESS_INVALID:" + label)
        witnesses.append({**witness, "witness_sha256": sha(path.read_bytes())})
    if {row["platform"] for row in witnesses} != {"WINDOWS_NATIVE", "WSL_NATIVE"}:
        raise SystemExit("R036_PORTABILITY_LEG_SET_INVALID")
    if len({row["profile_canonical_sha256"] for row in witnesses}) != 1 or len({row["profile_root"] for row in witnesses}) != 1:
        raise SystemExit("R036_PORTABILITY_OUTPUT_DIVERGED")
    body = {"schema": "mosaic.ucm.r036-cmba-composite-portability.v0.1",
        "scope": "R036_CMBA_COMPOSITE_POSITIVE_CORRESPONDENCE",
        "implementation_members": rows, "implementation_root": sha(canonical(rows)),
        "witnesses": witnesses, "status": "PASS", **BOUNDARY}
    return canonical({**body, "root": sha(canonical(body))}) + b"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = build()
    target = OUT / "PORTABILITY.json"
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    elif not target.is_file() or target.read_bytes() != raw:
        raise SystemExit("R036_PORTABILITY_RECORD_DRIFT")
    record = json.loads(raw)
    print(json.dumps({"status": "PASS", "root": record["root"],
        "implementation_root": record["implementation_root"],
        "adversarial_cases_executed": 0, **BOUNDARY}, sort_keys=True))


if __name__ == "__main__":
    main()
