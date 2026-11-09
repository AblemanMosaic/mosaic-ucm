#!/usr/bin/env python3
"""Generate P/PPI r030 constitutional atlas and pipeline contracts."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes  # noqa: E402
from ucm.pippi_constitution import (  # noqa: E402
    build_constitutional_standards_atlas,
    build_pipeline_model,
)


OUTPUTS = {
    ROOT / "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json": build_constitutional_standards_atlas,
    ROOT / "spec/PIPPI-PIPELINE-MODEL.json": build_pipeline_model,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, builder in OUTPUTS.items():
        expected = canonical_bytes(builder()) + b"\n"
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.is_file() or path.read_bytes() != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
    print({"status": "PASS" if not mismatches else "REFUSED",
           "outputs": len(OUTPUTS), "mismatches": mismatches,
           "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
           "real_a5": False, "g0": "CLOSED"})
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())
