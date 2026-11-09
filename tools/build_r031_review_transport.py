#!/usr/bin/env python3
"""Build the self-contained r031 replay, history and operator transport."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FILES = ("UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip", "UCM-v0.1-review.zip",
         "UCM-v0.1-lineage.zip", "UCM-v0.1-release.json",
         "UCM-v0.1-QUALIFICATION.json", "PIPPI-v0.1-adaptive-cold-boot.zip")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(qualified: Path, operator: Path, history: Path, output: Path) -> dict:
    payload = {name: (qualified / name).read_bytes() for name in FILES}
    kit = operator / "UCM-r031-TRANSTEMPORAL-NATIVE-OPERATOR-KIT.zip"
    payload[kit.name] = kit.read_bytes()
    payload["RUN.cmd"] = (operator / "RUN.cmd").read_bytes()
    payload["RUN.ps1"] = (operator / "RUN.ps1").read_bytes()
    payload["REVIEW-WORK-ORDER.md"] = (ROOT / "docs/R31-REVIEW-WORK-ORDER.md").read_bytes()
    payload[history.name] = history.read_bytes()
    for name in ("PORTABILITY-GATE.json", "WINDOWS-NATIVE-WITNESS.json",
                 "WSL-NATIVE-WITNESS.json"):
        payload[name] = (ROOT / "evidence/r031-portability" / name).read_bytes()
    release = json.loads(payload["UCM-v0.1-release.json"])
    qualification = json.loads(payload["UCM-v0.1-QUALIFICATION.json"])
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payload.items())]
    body = {
        "schema": "mosaic.ucm.r031-review-transport.v0.1", "version": "v0.1",
        "engineering_revision": "r031",
        "review_scope": "COMPLETE_SOURCE_REPLAY_HISTORY_AND_OPERATOR_TIER1",
        "qualification_replay_complete": True,
        "subject_source_root": qualification["source_manifest_root"],
        "subject_qualification_root": qualification["root"],
        "subject_release_root": release["root"],
        "subject_runtime_sha256": qualification["runtime_sha256"],
        "operator_kit_sha256": sha(payload[kit.name]),
        "transtemporal_history_sha256": sha(payload[history.name]),
        "members": rows, "member_count": len(rows),
        "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED", **BOUNDARY,
    }
    manifest = {**body, "transport_root": sha(canonical(body))}
    payload["TRANSPORT-MANIFEST.json"] = canonical(manifest) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as package:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            package.writestr(info, raw)
    return {"status": "PASS", "path": str(output), "sha256": sha(output.read_bytes()),
            "transport_root": manifest["transport_root"], "members": len(payload),
            **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualified", type=Path, required=True)
    parser.add_argument("--operator", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.qualified.resolve(), args.operator.resolve(),
                           args.history.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
