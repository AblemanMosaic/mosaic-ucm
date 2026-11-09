#!/usr/bin/env python3
"""Build the complete deterministic r025 review transport."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
RELEASE_FILES = (
    "UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip", "UCM-v0.1-review.zip",
    "UCM-v0.1-lineage.zip", "UCM-v0.1-release.json",
    "UCM-v0.1-QUALIFICATION.json", "PIPPI-v0.1-adaptive-cold-boot.zip",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def write_zip(path, payload):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; info.create_system = 3
            archive.writestr(info, raw)


def build(qualified: Path, operator: Path, output: Path) -> dict:
    payload = {name: (qualified / name).read_bytes() for name in RELEASE_FILES}
    kit = operator / "UCM-r025-CONTRACT-PARITY-OPERATOR-KIT.zip"
    payload[kit.name] = kit.read_bytes()
    # Preserve the launchers under the names they reference internally. This
    # is an executable boundary check, not a cosmetic rename.
    payload["RUN.cmd"] = (operator / "RUN.cmd").read_bytes()
    payload["RUN.ps1"] = (operator / "RUN.ps1").read_bytes()
    payload["REVIEW-WORK-ORDER.md"] = (ROOT / "docs/R25-REVIEW-WORK-ORDER.md").read_bytes()
    for name in ("PORTABILITY-GATE.json", "WINDOWS-NATIVE-WITNESS.json",
                 "WSL-NATIVE-WITNESS.json"):
        payload[name] = (ROOT / "evidence/r025-portability" / name).read_bytes()
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payload.items())]
    release = json.loads(payload["UCM-v0.1-release.json"])
    qualification = json.loads(payload["UCM-v0.1-QUALIFICATION.json"])
    body = {"schema": "mosaic.ucm.r025-review-transport.v0.1",
            "version": "v0.1", "engineering_revision": "r025",
            "subject_source_root": qualification["source_manifest_root"],
            "subject_qualification_root": qualification["root"],
            "subject_release_root": release["root"],
            "subject_runtime_sha256": qualification["runtime_sha256"],
            "operator_kit_sha256": sha(payload[kit.name]),
            "members": rows, "member_count": len(rows),
            "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED", **BOUNDARY}
    manifest = {**body, "transport_root": sha(canonical(body))}
    payload["TRANSPORT-MANIFEST.json"] = canonical(manifest) + b"\n"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "UCM-v0.1-r025-CONTRACT-PARITY-REVIEW-TRANSPORT.zip"
    write_zip(path, payload)
    return {"status": "PASS", "path": str(path),
            "sha256": sha(path.read_bytes()),
            "transport_root": manifest["transport_root"],
            "members": len(payload), **BOUNDARY}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualified", type=Path, required=True)
    parser.add_argument("--operator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.qualified.resolve(), args.operator.resolve(),
                           args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
