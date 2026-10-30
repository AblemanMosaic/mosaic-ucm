#!/usr/bin/env python3
"""Build the sealed, human-run Stage I4 c2 Tier 1 and qualification kit."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402


def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    subject_raw = args.subject.read_bytes()
    tier1 = (ROOT / "review/stage4-c2/RUN-STAGE-I4-C2-TIER1.py").read_bytes()
    qualification = (ROOT / "review/stage4-c2/RUN-STAGE-I4-C2-QUALIFICATION.py").read_bytes()
    work_order = (ROOT / "review/STAGE-I4-C2-INTEGRATED-REPAIR-WORK-ORDER.md").read_bytes()
    contract_body = {"schema": "mosaic.ucm.amcas-stage-i4-c2-operator-kit-contract.v0.1",
        "subject_sha256": sha(subject_raw), "tier1_runner_sha256": sha(tier1),
        "qualification_runner_sha256": sha(qualification),
        "work_order_sha256": sha(work_order),
        "operator_evidence_class": "OPERATOR_REPRODUCED",
        "independent_review": False, "network_required": False,
        "install_required": False, "persistent_host_change": False, **BOUNDARY}
    contract = {**contract_body, "contract_root": root(contract_body)}
    start = b"""# Stage I4 c2 operator review\n\nDouble-click `RUN-STAGE-I4-C2-REVIEW.cmd`. It verifies this sealed kit, runs the builder-authored Tier 1 court in a disposable workspace, then runs the cache-free qualification under each locally available CPython 3.12 and 3.13 interpreter. It writes sealed evidence beside the launcher, removes temporary files, and pauses. No network, install, application contact, or authority grant is performed. The result is operator-reproduced engineering evidence, not independent review.\n"""
    raw = deterministic_zip({"OPERATOR-SUBJECT.zip": subject_raw,
        "KIT-CONTRACT.json": canonical_bytes(contract),
        "RUN-STAGE-I4-C2-TIER1.py": tier1,
        "RUN-STAGE-I4-C2-QUALIFICATION.py": qualification,
        "WORK-ORDER.md": work_order, "START-HERE.md": start},
        schema="mosaic.ucm.amcas-stage-i4-c2-operator-kit.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C2_OPERATOR_KIT")
    manifest = verify_deterministic_zip(raw,
        expected_schema="mosaic.ucm.amcas-stage-i4-c2-operator-kit.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C2_OPERATOR_KIT")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists(): raise SystemExit("STAGE_I4_C2_OPERATOR_KIT_EXISTS")
    args.out.write_bytes(raw)
    print(canonical_bytes({"status": "PASS", "kit_sha256": sha(raw),
        "kit_bytes": len(raw), "manifest_root": manifest["manifest_root"],
        "subject_sha256": sha(subject_raw), **BOUNDARY}).decode())
    return 0


if __name__ == "__main__": raise SystemExit(main())
