#!/usr/bin/env python3
"""Verify returned operator evidence and build a deterministic review addendum."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.maturity_operator_evidence import (  # noqa: E402
    build_maturity_operator_evidence_addendum,
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-kit", type=Path, required=True)
    parser.add_argument("--operator-evidence", type=Path, required=True)
    parser.add_argument("--review-handoff", type=Path, required=True)
    parser.add_argument("--freeze-receipt", type=Path, required=True)
    parser.add_argument("--expected-kit-sha256", required=True)
    parser.add_argument("--expected-review-handoff-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw, acceptance = build_maturity_operator_evidence_addendum(
        kit_raw=args.operator_kit.read_bytes(),
        evidence_raw=args.operator_evidence.read_bytes(),
        review_handoff_raw=args.review_handoff.read_bytes(),
        freeze_receipt_raw=args.freeze_receipt.read_bytes(),
        expected_kit_sha256=args.expected_kit_sha256,
        expected_review_handoff_sha256=args.expected_review_handoff_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({
        "status": "PASS_OPERATOR_EVIDENCE_BOUND",
        "output": str(args.output),
        "addendum_sha256": sha(raw),
        "acceptance_root": acceptance["acceptance_root"],
        "operator_case_count": acceptance["operator_case_count"],
        "independent_review_status": "PENDING",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
