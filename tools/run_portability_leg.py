#!/usr/bin/env python3
"""Run one non-adversarial r033 portability witness leg."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from release_common import canonical, public_source_body, sha  # noqa: E402
from ucm.pippi_portability import (build_portability_witness,
                                   observe_execution_context,
                                   portability_policy)  # noqa: E402
from ucm.pippi_portability_evidence import recompute_canonical_outputs  # noqa: E402

TEST_IDS = (
    "tests.test_pippi_portability",
    "tests.test_pippi_adaptive",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leg-id", required=True,
                        choices=("WINDOWS_NATIVE", "WSL_NATIVE"))
    parser.add_argument("--shell-family", required=True,
                        choices=("POWERSHELL", "BASH"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = observe_execution_context(shell_family=args.shell_family)
    reason_codes = []
    if context["filesystem_class"] != args.leg_id:
        reason_codes.append("EXECUTION_CONTEXT_LEG_MISMATCH")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    # Bind test scratch space to this explicit leg rather than inheriting an
    # opaque host temp policy.  The directory is disposable and cannot become
    # evidence because only canonical result roots enter the witness.
    with tempfile.TemporaryDirectory(
            prefix=f"r033-{args.leg_id.casefold()}-", dir=args.output.parent) as scratch:
        environment["TEMP"] = scratch
        environment["TMP"] = scratch
        result = subprocess.run(
            [sys.executable, "-m", "unittest", *TEST_IDS, "-q"],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        reason_codes.append("PORTABILITY_TEST_SET_FAILED")
    source_body = public_source_body(ROOT)
    source_root = sha(canonical(source_body))
    test_set_root = hashlib.sha256(canonical({
        "schema": "mosaic.ucm.r033-portability-test-set.v0.1",
        "test_module_ids": list(TEST_IDS),
    })).hexdigest()
    outputs = recompute_canonical_outputs(ROOT)
    witness = build_portability_witness(
        leg_id=args.leg_id, execution_context=context,
        source_root=source_root, test_set_root=test_set_root,
        canonical_outputs=sorted(outputs, key=lambda row: row["artifact_id"]),
        status="PASS" if not reason_codes else "FAIL",
        reason_codes=sorted(reason_codes))
    args.output.write_bytes(canonical(witness) + b"\n")
    print(json.dumps({"status": witness["status"],
                      "leg_id": args.leg_id,
                      "witness_root": witness["witness_root"],
                      "output": str(args.output),
                      "tests_returncode": result.returncode,
                      "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "real_a5": False, "g0": "CLOSED"}, sort_keys=True))
    return 0 if witness["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
