#!/usr/bin/env python3
"""Build or check r027 custody over immutable predecessor operator courts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes  # noqa: E402
from ucm.operator_history import (build_frozen_operator_registry,
                                  verify_frozen_operator_registry)  # noqa: E402


OUT = ROOT / "spec" / "FROZEN-OPERATOR-REGISTRY.json"
ROWS = (
    ("operator/dependency-graph-r021", "r021", "EXACT_ORIGINAL_R021_OPERATOR_DIRECTORY"),
    ("operator/dependency-graph-r023-compat", "r023", "R023_COMPATIBILITY_SUCCESSOR_DIRECTORY"),
    ("operator/incremental-hotfix-c1", "r011", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/pippi-adaptive-r017", "r017", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/pippi-adaptive-r018", "r018", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/pippi-adaptive-r019", "r019", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/pippi-adaptive-r020", "r020", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/portability-determinism-r024", "r024", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/contract-parity-r025", "r025", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/runtime-parity-r026", "r026", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/systemic-repair-r023", "r023", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("operator/ugel-executor-r022", "r022", "EXACT_PREDECESSOR_OPERATOR_DIRECTORY"),
    ("historical/operator-preimages/r021/original", "r021", "RECOVERED_ORIGINAL_OPERATOR_PREIMAGE"),
    ("historical/operator-preimages/r021/repaired", "r021", "RECOVERED_REPAIRED_OPERATOR_PREIMAGE"),
)


def rows() -> list[dict[str, str]]:
    return [{"directory": path, "frozen_revision": revision,
             "provenance": provenance}
            for path, revision, provenance in sorted(ROWS)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_frozen_operator_registry(
        source_root=ROOT, rows=rows(), successor_revision="r027")
    raw = canonical_bytes(expected) + b"\n"
    if args.write:
        OUT.write_bytes(raw)
    mismatches = [] if OUT.is_file() and OUT.read_bytes() == raw else [
        OUT.relative_to(ROOT).as_posix()]
    if not mismatches:
        verify_frozen_operator_registry(source_root=ROOT, registry=expected)
    print(json.dumps({
        "status": "PASS" if not mismatches else "REFUSED",
        "mode": "WRITE" if args.write else "CHECK",
        "registry_root": expected["registry_root"],
        "directories": expected["directory_count"],
        "mismatches": mismatches,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())
