#!/usr/bin/env python3
"""Compile and execute one positive UCM Native Core correspondence leg."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root  # noqa: E402
from ucm.native_core import (compile_native_core, detect_c17_compiler,
                             native_core_profile,
                             verify_native_correspondence)  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg-id", choices=("WINDOWS_NATIVE_C17", "WSL_NATIVE_C17"), required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    programs = [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((ROOT / "examples/native-core").glob("*.json"))]
    compiler = detect_c17_compiler()
    if not compiler["available"]:
        raise SystemExit("NATIVE_C17_COMPILER_UNAVAILABLE")
    scratch_parent = ROOT / ".build"
    scratch_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-leg-", dir=scratch_parent) as raw:
        work = pathlib.Path(raw)
        binary = work / ("ucm-native.exe" if args.leg_id == "WINDOWS_NATIVE_C17" else "ucm-native")
        build = compile_native_core(source=ROOT / "native/ucm_native_core.c",
                                    output=binary, compiler=compiler)
        correspondence = verify_native_correspondence(
            programs=programs, binary=binary, work_dir=work / "corpus")
    results = [{"program_id": row["program_id"],
                "program_root": row["program_root"],
                "projection_sha256": row["projection_sha256"],
                "result": row["result"]} for row in correspondence["programs"]]
    body = {
        "schema": "mosaic.ucm.native-core-platform-witness.v0.1",
        "leg_id": args.leg_id,
        "profile_root": native_core_profile()["profile_root"],
        "native_source_sha256": hashlib.sha256(
            (ROOT / "native/ucm_native_core.c").read_bytes()).hexdigest(),
        "compiler": {"name": compiler["name"], "version": compiler["version"]},
        "binary_sha256": build["binary_sha256"],
        "results": results,
        "result_set_root": root(results),
        "program_count": len(results),
        "status": "PASS_CORRESPONDENCE",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    witness = {**body, "witness_root": root(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(witness) + b"\n")
    print(json.dumps({"status": "PASS", "leg_id": args.leg_id,
                      "witness_root": witness["witness_root"],
                      "result_set_root": witness["result_set_root"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
