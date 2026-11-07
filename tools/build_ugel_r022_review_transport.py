#!/usr/bin/env python3
"""Build the complete r022 UGEL review transport."""
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
REQUIRED = (
    "PIPPI-v0.1-adaptive-cold-boot.zip", "UCM-UGEL-r022-OPERATOR-KIT.zip",
    "UCM-v0.1-QUALIFICATION.json", "UCM-v0.1-lineage.zip",
    "UCM-v0.1-release.json", "UCM-v0.1-review.zip",
    "UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(inputs: list[Path], output: Path):
    by_name = {path.name: path.resolve() for path in inputs}
    if set(by_name) != set(REQUIRED) or len(inputs) != len(by_name):
        raise ValueError("UGEL_REVIEW_TRANSPORT_INPUT_SET_INVALID")
    payload = {name: by_name[name].read_bytes() for name in REQUIRED}
    release = json.loads(payload["UCM-v0.1-release.json"])
    qualification = json.loads(payload["UCM-v0.1-QUALIFICATION.json"])
    if qualification["release_root"] != release["root"]:
        raise ValueError("UGEL_REVIEW_TRANSPORT_RELEASE_BINDING_INVALID")
    release_rows = {row["path"]: row for row in release["artifacts"]}
    for name in ("UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip",
                 "UCM-v0.1-review.zip", "UCM-v0.1-lineage.zip"):
        if release_rows[name]["sha256"] != sha(payload[name]):
            raise ValueError("UGEL_REVIEW_TRANSPORT_ARTIFACT_INVALID:" + name)
    if qualification["pippi_cold_boot_sha256"] != sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"]):
        raise ValueError("UGEL_REVIEW_TRANSPORT_COLD_BOOT_INVALID")
    with zipfile.ZipFile(by_name["UCM-UGEL-r022-OPERATOR-KIT.zip"]) as archive:
        kit = json.loads(archive.read("KIT-MANIFEST.json"))
    if (kit["runtime_sha256"] != sha(payload["UCM-v0.1-runtime.zip"])
            or kit["qualification_sha256"] != sha(payload["UCM-v0.1-QUALIFICATION.json"])):
        raise ValueError("UGEL_REVIEW_TRANSPORT_OPERATOR_BINDING_INVALID")
    payload["REVIEW-WORK-ORDER.md"] = (ROOT / "docs/UGEL-r022-REVIEW-WORK-ORDER.md").read_bytes()
    payload["REVIEW-START-HERE.md"] = (
        b"# UCM / Pippi r022 UGEL complete review transport\n\n"
        b"Verify custody, replay qualification, then use the separate operator kit. "
        b"The operator court is builder-authored and has not been executed by the builder. "
        b"UGEL remains an optional external executor and this transport grants no authority.\n")
    rows = [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
            for name, raw in sorted(payload.items())]
    body = {"schema": "mosaic.ucm.ugel-complete-review-transport.v0.1",
            "version": "v0.1", "engineering_revision": "r022",
            "release_root": release["root"],
            "qualification_root": qualification["root"],
            "runtime_sha256": sha(payload["UCM-v0.1-runtime.zip"]),
            "operator_kit_sha256": sha(payload["UCM-UGEL-r022-OPERATOR-KIT.zip"]),
            "ugel_source_archive_sha256": "70e09459418a6672cc0e1924a7f6338fd1e0a929f8dc6f5630e61d0f866307cc",
            "ugel_source_root": "8bdcd1532f914f4c471d8311597e61e59d6cfdf15347e3f55d63f6556476d851",
            "members": rows, "member_count": len(rows),
            "replay_inputs_complete": True, "operator_kit_executed": False,
            **BOUNDARY}
    manifest = {**body, "manifest_root": sha(canonical(body))}
    payload["TRANSPORT-MANIFEST.json"] = canonical(manifest) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; info.create_system = 3
            archive.writestr(info, raw)
    return {"status": "PASS", "path": str(output),
            "sha256": sha(output.read_bytes()),
            "manifest_root": manifest["manifest_root"],
            "member_count": len(payload), **BOUNDARY}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
