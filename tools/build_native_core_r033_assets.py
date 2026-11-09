#!/usr/bin/env python3
"""Generate the r033 boundary corpus for the frozen Native Core profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.native_core import (I64_MAX, I64_MIN, build_native_program,
                             lower_native_program, native_core_profile)  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def programs() -> list[dict]:
    max_instructions = []
    for _ in range(2047):
        max_instructions.extend(({"op": "PUSH", "arg": 0}, {"op": "DROP"}))
    max_instructions.extend(({"op": "PUSH", "arg": 1}, {"op": "HALT"}))
    max_stack = ([{"op": "PUSH", "arg": 1}] * 1024
                 + [{"op": "DROP"}] * 1023 + [{"op": "HALT"}])
    exact_step_limit = ([{"op": "PUSH", "arg": 0}, {"op": "DROP"}] * 3 + [
        {"op": "LOAD", "arg": 0}, {"op": "PUSH", "arg": 1},
        {"op": "SUB"}, {"op": "DUP"}, {"op": "STORE", "arg": 0},
        {"op": "PUSH", "arg": 0}, {"op": "EQ"}, {"op": "JZ", "arg": 6},
        {"op": "PUSH", "arg": 1}, {"op": "HALT"},
    ])
    return [
        build_native_program(
            program_id="ucm.boundary.max_registers",
            registers=[I64_MIN if index % 2 == 0 else I64_MAX for index in range(256)],
            max_steps=2, expected_result_i64=I64_MAX,
            instructions=[{"op": "LOAD", "arg": 255}, {"op": "HALT"}]),
        build_native_program(
            program_id="ucm.boundary.max_instructions", registers=[],
            max_steps=4096, expected_result_i64=1,
            instructions=max_instructions),
        build_native_program(
            program_id="ucm.boundary.max_stack", registers=[],
            max_steps=2048, expected_result_i64=1,
            instructions=max_stack),
        build_native_program(
            program_id="ucm.boundary.max_steps", registers=[124999],
            max_steps=1_000_000, expected_result_i64=1,
            instructions=exact_step_limit),
    ]


def payload() -> dict[str, bytes]:
    result: dict[str, bytes] = {}
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
        "schema": "mosaic.ucm.native-core-boundary-corpus.v0.1",
        "profile_root": native_core_profile()["profile_root"],
        "programs": corpus, "program_count": len(corpus),
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    result["spec/UCM-NATIVE-CORE-BOUNDARY-CORPUS.json"] = canonical(corpus_record) + b"\n"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = payload()
    if args.check:
        for name, raw in files.items():
            if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != raw:
                raise SystemExit("R033_NATIVE_ASSET_DRIFT:" + name)
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
