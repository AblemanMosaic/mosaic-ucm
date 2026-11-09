#!/usr/bin/env python3
"""Run the fixed r036 positive correspondence set and emit one witness JSON."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from uclop.canonical import canonical_bytes, root
from ucm.pippi_cmba_composite import composite_profile

TESTS = (
    "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_observational_composite_keeps_roots_distinct",
    "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_effect_history_binds_ccp_and_complete_gates",
    "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_public_abi_exposes_profile",
    "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_public_cli_exposes_profile_without_writing",
)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-label", required=True,
                        choices=("WINDOWS_NATIVE", "WSL_NATIVE"))
    args = parser.parse_args()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in TESTS)
    # Product progress remains visible but cannot contaminate the canonical
    # one-line witness written to stdout.
    with redirect_stdout(sys.stderr):
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit("R036_POSITIVE_CORRESPONDENCE_FAILED")
    profile = composite_profile()
    body = {"schema": "mosaic.ucm.r036-positive-witness.v0.1",
        "platform": args.platform_label, "host_system": platform.system(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(), "test_ids": list(TESTS),
        "test_count": len(TESTS), "failures": 0, "errors": 0, "skips": 0,
        "profile_root": profile["profile_root"],
        "profile_canonical_sha256": hashlib.sha256(canonical_bytes(profile)).hexdigest(),
        "adversarial_cases_executed": 0, "status": "PASS", **BOUNDARY}
    print(canonical_bytes({**body, "witness_root": root(body)}).decode())


if __name__ == "__main__":
    main()
