#!/usr/bin/env python3
"""Verify v0.1 release archives without importing UCM subject code."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile
from pathlib import PurePosixPath


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def verify(path: pathlib.Path, expected: str, expected_role: str, expected_completeness: str) -> dict:
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise SystemExit(f"ARCHIVE_PIN_MISMATCH:{path.name}")
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)) or names.count("MANIFEST.json") != 1:
            raise SystemExit(f"ARCHIVE_SET_INVALID:{path.name}")
        for name in names:
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or "\\" in name:
                raise SystemExit(f"ARCHIVE_PATH_REFUSED:{path.name}:{name}")
        mf = json.loads(zf.read("MANIFEST.json"))
        if (
            mf.get("schema") != "mosaic.ucm.artifact-manifest.v0.1"
            or mf.get("version") != "v0.1"
            or mf.get("standing") != "INFORMATION_ONLY"
            or mf.get("authority_effect") != "NONE"
            or mf.get("real_a5") is not False
            or mf.get("g0") != "CLOSED"
        ):
            raise SystemExit(f"ARCHIVE_BOUNDARY_REFUSED:{path.name}")
        if mf.get("artifact") != expected_role or mf.get("completeness") != expected_completeness:
            raise SystemExit(f"ARCHIVE_ROLE_REFUSED:{path.name}")
        rows = {row["path"]: row for row in mf["members"]}
        if set(names) != {"MANIFEST.json", *rows}:
            raise SystemExit(f"ARCHIVE_CLOSED_SET_REFUSED:{path.name}")
        for name, row in rows.items():
            data = zf.read(name)
            if sha(data) != row["sha256"] or len(data) != row["bytes"]:
                raise SystemExit(f"ARCHIVE_MEMBER_REFUSED:{path.name}:{name}")
        body = {k: v for k, v in mf.items() if k != "root"}
        if sha(canonical(body)) != mf["root"]:
            raise SystemExit(f"MANIFEST_ROOT_REFUSED:{path.name}")
        return mf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", type=pathlib.Path)
    parser.add_argument("--expected-release-root", required=True)
    args = parser.parse_args()
    release = json.loads(args.release.read_text(encoding="utf-8"))
    body = {k: v for k, v in release.items() if k != "root"}
    if sha(canonical(body)) != release["root"]:
        raise SystemExit("RELEASE_ROOT_REFUSED")
    if release["root"] != args.expected_release_root:
        raise SystemExit("RELEASE_EXTERNAL_PIN_MISMATCH")
    if (
        release.get("schema") != "mosaic.ucm.release.v0.1"
        or release.get("product") != "Universal Constitutional Machine"
        or release.get("version") != "v0.1"
        or release.get("publisher") != "Ableman Mosaic"
        or release.get("copyright") != "Copyright 2026 Ableman Mosaic"
        or release.get("license") != "Apache-2.0"
        or release.get("standing") != "INFORMATION_ONLY"
        or release.get("authority_effect") != "NONE"
        or release.get("real_a5") is not False
        or release.get("g0") != "CLOSED"
    ):
        raise SystemExit("RELEASE_BOUNDARY_REFUSED")
    if not all(type(release.get(field)) is str and len(release[field]) == 64 for field in ("source_manifest_root", "release_identity_root")):
        raise SystemExit("RELEASE_SOURCE_IDENTITY_REFUSED")
    roles = [row.get("role") for row in release["artifacts"]]
    if len(roles) != len(set(roles)) or set(roles[:2]) != {"UCM_RUNTIME", "UCM_SDK"} or len(roles) != 3:
        raise SystemExit("RELEASE_ARTIFACT_ROLE_SET_REFUSED")
    if roles[2] not in {"UCM_LINEAGE_METADATA", "UCM_AUDIT"}:
        raise SystemExit("RELEASE_ARTIFACT_ROLE_SET_REFUSED")
    expected_kind = "PUBLIC_LINEAGE" if roles[2] == "UCM_LINEAGE_METADATA" else "COMPLETE_AUDIT"
    if release.get("release_kind") != expected_kind:
        raise SystemExit("RELEASE_KIND_REFUSED")
    expected_completeness = {
        "UCM_RUNTIME": "COMPLETE_RUNTIME",
        "UCM_SDK": "COMPLETE_SDK",
        "UCM_LINEAGE_METADATA": "METADATA_ONLY",
        "UCM_AUDIT": "COMPLETE_FROZEN_CUSTODY",
    }
    verified = []
    for row in release["artifacts"]:
        artifact_path = PurePosixPath(row.get("path", ""))
        if artifact_path.is_absolute() or len(artifact_path.parts) != 1 or "\\" in row.get("path", ""):
            raise SystemExit("RELEASE_ARTIFACT_PATH_REFUSED")
        if row.get("completeness") != expected_completeness[row["role"]]:
            raise SystemExit("RELEASE_ARTIFACT_COMPLETENESS_REFUSED")
        manifest = verify(args.release.parent / row["path"], row["sha256"], row["role"], row["completeness"])
        if row.get("manifest_root") != manifest["root"] or row.get("bytes") != (args.release.parent / row["path"]).stat().st_size:
            raise SystemExit("RELEASE_ARTIFACT_DESCRIPTOR_REFUSED")
        verified.append({"role": row["role"], "completeness": row["completeness"], "manifest_root": manifest["root"]})
    print(json.dumps({"status": "PASS", "release_root": release["root"], "artifact_count": len(release["artifacts"]), "artifacts": verified, "authority_effect": "NONE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

