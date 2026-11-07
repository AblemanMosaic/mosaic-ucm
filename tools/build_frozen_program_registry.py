#!/usr/bin/env python3
"""Build or check r027 custody over immutable predecessor program records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes  # noqa: E402
from ucm.program_history import (build_frozen_program_registry,
                                 verify_frozen_program_registry)  # noqa: E402


OUT = ROOT / "spec" / "FROZEN-PROGRAM-REGISTRY.json"
ACTIVE = [
    "program/ccp-admissibility-r014",
    "program/ccp-courthouse-r015",
    "program/dependency-graph-r021",
    "program/maturity-evolution",
    "program/pippi-adaptive-r017",
    "program/pippi-adaptive-r018",
    "program/pippi-adaptive-r019",
    "program/pippi-adaptive-r020",
    "program/pippi-interface-r016",
    "program/pippi-r010",
    "program/pippi-r011",
    "program/pippi-work-selection-normalization-r019",
    "program/portability-determinism-r024",
    "program/contract-parity-r025",
    "program/runtime-parity-r026",
    "program/public-vocabulary-r012",
    "program/public-vocabulary-r013",
    "program/public-vocabulary-r020-normalization",
    "program/systemic-repair-r023",
    "program/ugel-executor-r022",
]
PREIMAGES = [
    "historical/program-preimages/r020/ccp-admissibility-r014",
    "historical/program-preimages/r020/public-vocabulary-r013",
    "historical/program-preimages/r021/ccp-admissibility-r014",
    "historical/program-preimages/r021/public-vocabulary-r013",
]


def rows() -> list[dict[str, str]]:
    return sorted(
        [{"directory": path,
          "frozen_revision": ("r026" if path.endswith("runtime-parity-r026")
                              else "r025" if path.endswith("contract-parity-r025")
                              else "r024" if path.endswith("portability-determinism-r024")
                              else "r023" if path.endswith("systemic-repair-r023")
                              else "r022"),
          "provenance": "EXACT_R023_PREDECESSOR_PROGRAM_DIRECTORY"}
         for path in ACTIVE]
        + [{"directory": path,
            "frozen_revision": path.split("/")[2],
            "provenance": "RECOVERED_EXACT_PREDECESSOR_PREIMAGE"}
           for path in PREIMAGES],
        key=lambda row: row["directory"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_frozen_program_registry(
        source_root=ROOT, rows=rows(), successor_revision="r027")
    raw = canonical_bytes(expected) + b"\n"
    if args.write:
        OUT.write_bytes(raw)
    mismatches = [] if OUT.is_file() and OUT.read_bytes() == raw else [
        OUT.relative_to(ROOT).as_posix()]
    if not mismatches:
        verify_frozen_program_registry(source_root=ROOT, registry=expected)
    print(json.dumps({
        "status": "PASS" if not mismatches else "REFUSED",
        "mode": "WRITE" if args.write else "CHECK",
        "registry_root": expected["registry_root"],
        "directories": expected["directory_count"],
        "mismatches": mismatches, "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED",
    }, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())
