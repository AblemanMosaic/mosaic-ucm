#!/usr/bin/env python3
"""Build a complete, replayable r021 review transport around qualified artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
REQUIRED_BASENAMES = (
    "PIPPI-v0.1-adaptive-cold-boot.zip",
    "UCM-DEPENDENCY-r021-OPERATOR-KIT.zip",
    "UCM-v0.1-QUALIFICATION.json",
    "UCM-v0.1-lineage.zip",
    "UCM-v0.1-release.json",
    "UCM-v0.1-review.zip",
    "UCM-v0.1-runtime.zip",
    "UCM-v0.1-sdk.zip",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def build(*, inputs: list[Path], output: Path) -> dict:
    by_name = {path.name: path.resolve() for path in inputs}
    if set(by_name) != set(REQUIRED_BASENAMES) or len(inputs) != len(by_name):
        raise ValueError("PIPPI_REVIEW_TRANSPORT_INPUT_SET_INVALID")
    payload = {name: by_name[name].read_bytes() for name in REQUIRED_BASENAMES}
    release = _json(payload["UCM-v0.1-release.json"])
    qualification = _json(payload["UCM-v0.1-QUALIFICATION.json"])
    if qualification.get("release_root") != release.get("root"):
        raise ValueError("PIPPI_REVIEW_TRANSPORT_RELEASE_BINDING_INVALID")
    release_rows = {row["path"]: row for row in release.get("artifacts", [])}
    for name in ("UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip",
                 "UCM-v0.1-review.zip", "UCM-v0.1-lineage.zip"):
        if name not in release_rows or release_rows[name]["sha256"] != sha(payload[name]):
            raise ValueError("PIPPI_REVIEW_TRANSPORT_RELEASE_ARTIFACT_INVALID:" + name)
    if qualification.get("pippi_cold_boot_sha256") != sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"]):
        raise ValueError("PIPPI_REVIEW_TRANSPORT_COLD_BOOT_INVALID")
    with zipfile.ZipFile(by_name["UCM-DEPENDENCY-r021-OPERATOR-KIT.zip"]) as archive:
        kit = _json(archive.read("KIT-MANIFEST.json"))
    if (kit.get("runtime_sha256") != sha(payload["UCM-v0.1-runtime.zip"])
            or kit.get("cold_boot_sha256") != sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"])):
        raise ValueError("PIPPI_REVIEW_TRANSPORT_OPERATOR_BINDING_INVALID")
    start = (
        "# P/PPI r021 Dependency and Evidence Graph complete review transport\n\n"
        "This transport contains every release artifact pinned by the qualification receipt, "
        "the adaptive cold boot, and the unexecuted builder-authored operator kit. Extract into "
        "a disposable directory. Replay qualification before running the operator kit. "
        "Nothing in this transport grants authority.\n"
    ).encode()
    payload["REVIEW-START-HERE.md"] = start
    rows = [{"path": name, "sha256": sha(data), "bytes": len(data)}
            for name, data in sorted(payload.items())]
    body = {
        "schema": "mosaic.ucm.pippi-complete-review-transport.v0.1",
        "version": "v0.1", "engineering_revision": "r021",
        "release_root": release["root"], "qualification_root": qualification["root"],
        "runtime_sha256": sha(payload["UCM-v0.1-runtime.zip"]),
        "review_sha256": sha(payload["UCM-v0.1-review.zip"]),
        "operator_kit_sha256": sha(payload["UCM-DEPENDENCY-r021-OPERATOR-KIT.zip"]),
        "members": rows, "member_count": len(rows),
        "replay_inputs_complete": True, "operator_kit_executed": False,
        **BOUNDARY,
    }
    manifest = {**body, "manifest_root": sha(canonical(body))}
    payload["TRANSPORT-MANIFEST.json"] = canonical(manifest) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, data)
    return {"status": "PASS", "path": str(output),
            "sha256": sha(output.read_bytes()),
            "manifest_root": manifest["manifest_root"],
            "member_count": len(payload), **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(inputs=args.input, output=args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
