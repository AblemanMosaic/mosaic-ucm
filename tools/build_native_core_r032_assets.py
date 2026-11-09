#!/usr/bin/env python3
"""Generate the frozen r032 UCM Native Core profile and correspondence corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.native_core import (build_native_program, lower_native_program,
                             native_core_profile)  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def programs() -> list[dict]:
    return [
        build_native_program(
            program_id="ucm.gate.three_receipts", registers=[1, 1, 1],
            max_steps=32, expected_result_i64=1,
            instructions=[
                {"op": "LOAD", "arg": 0}, {"op": "LOAD", "arg": 1},
                {"op": "AND"}, {"op": "LOAD", "arg": 2}, {"op": "AND"},
                {"op": "HALT"},
            ]),
        build_native_program(
            program_id="ucm.gate.held_missing_witness", registers=[1, 0, 1],
            max_steps=32, expected_result_i64=0,
            instructions=[
                {"op": "LOAD", "arg": 0}, {"op": "LOAD", "arg": 1},
                {"op": "AND"}, {"op": "LOAD", "arg": 2}, {"op": "AND"},
                {"op": "HALT"},
            ]),
        build_native_program(
            program_id="ucm.budget.within_limit", registers=[30, 20, 100],
            max_steps=32, expected_result_i64=1,
            instructions=[
                {"op": "LOAD", "arg": 0}, {"op": "LOAD", "arg": 1},
                {"op": "ADD"}, {"op": "LOAD", "arg": 2}, {"op": "LT"},
                {"op": "HALT"},
            ]),
        build_native_program(
            program_id="ucm.branch.typed_disposition", registers=[0],
            max_steps=32, expected_result_i64=3,
            instructions=[
                {"op": "LOAD", "arg": 0}, {"op": "JZ", "arg": 4},
                {"op": "PUSH", "arg": 0}, {"op": "HALT"},
                {"op": "PUSH", "arg": 3}, {"op": "HALT"},
            ]),
        build_native_program(
            program_id="ucm.arithmetic.truncating_division", registers=[-7, 3],
            max_steps=32, expected_result_i64=-2,
            instructions=[
                {"op": "LOAD", "arg": 0}, {"op": "LOAD", "arg": 1},
                {"op": "DIV"}, {"op": "HALT"},
            ]),
    ]


def payload() -> dict[str, bytes]:
    result = {"spec/UCM-NATIVE-CORE-PROFILE.json":
              canonical(native_core_profile()) + b"\n"}
    corpus = []
    for program in programs():
        stem = program["program_id"].replace(".", "-")
        result[f"examples/native-core/{stem}.json"] = canonical(program) + b"\n"
        projection = lower_native_program(program)
        result[f"examples/native-core/{stem}.ucln"] = projection
        corpus.append({"program_id": program["program_id"],
                       "program_root": program["program_root"],
                       "projection_path": f"examples/native-core/{stem}.ucln"})
    corpus_record = {
        "schema": "mosaic.ucm.native-core-corpus.v0.1",
        "profile_root": native_core_profile()["profile_root"],
        "programs": corpus, "program_count": len(corpus),
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    result["spec/UCM-NATIVE-CORE-CORPUS.json"] = canonical(corpus_record) + b"\n"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = payload()
    if args.check:
        for name, raw in files.items():
            if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != raw:
                raise SystemExit("R032_NATIVE_ASSET_DRIFT:" + name)
    else:
        for name, raw in files.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print(json.dumps({"status": "PASS", "files": len(files),
                      "programs": len(programs())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
