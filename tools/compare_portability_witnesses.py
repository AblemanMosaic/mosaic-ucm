#!/usr/bin/env python3
"""Evaluate exact Windows/WSL witness correspondence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from release_common import canonical  # noqa: E402
from ucm.pippi_portability import evaluate_portability_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witness", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gate = evaluate_portability_gate(witnesses=[
        json.loads(path.read_text(encoding="utf-8")) for path in args.witness])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(gate) + b"\n")
    print(json.dumps({"status": gate["status"],
                      "portable_claim_allowed": gate["portable_claim_allowed"],
                      "portability_gate_root": gate["portability_gate_root"],
                      "output": str(args.output)}, sort_keys=True))
    return 0 if gate["status"] == "PASS_PORTABLE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
