#!/usr/bin/env python3
"""Verify the exact UGEL Batch E source archive without loading subject code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "qualification/inputs/ugel/UGEL-BATCH-E-r001.zip"
ARCHIVE_SHA256 = "70e09459418a6672cc0e1924a7f6338fd1e0a929f8dc6f5630e61d0f866307cc"
SOURCE_ROOT = "8bdcd1532f914f4c471d8311597e61e59d6cfdf15347e3f55d63f6556476d851"
DOMAIN = b"MOSAIC-UGEL-E1\0"
PINNED_MEMBERS = {
    "spec/ugel-effects.wit": "cd0babc8e6221f5df82ac766615ef1c185dc9cbdbbea6ab1b417af548211abf9",
    "src/ugel_component/boundary.py": "fae15cdd1a2ae19d2842ed657faf5531f51cfa8aa8ae617306e45407f8cb11fd",
    "src/ugel_component/host.py": "f738561cc20cc1cc25415ff8af2f592528fa1f7128e3a861dcddc490856f78a3",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and "\\" not in name and not path.is_absolute() \
        and not any(part in {"", ".", ".."} for part in path.parts)


def verify_archive(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if sha(raw) != ARCHIVE_SHA256:
        raise ValueError("UGEL_SOURCE_ARCHIVE_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or not all(_safe_name(name) for name in names):
            raise ValueError("UGEL_SOURCE_ARCHIVE_PATH_SET_INVALID")
        blobs = {name: archive.read(name) for name in names}

    manifest = json.loads(blobs["PACKAGE-MANIFEST.json"])
    rows = [{"path": name, "bytes": len(data), "sha256": sha(data)}
            for name, data in sorted(blobs.items()) if name != "PACKAGE-MANIFEST.json"]
    if manifest.get("files") != rows or manifest.get("member_count") != len(blobs):
        raise ValueError("UGEL_PACKAGE_MANIFEST_INVALID")
    if manifest.get("schema") != "mosaic.ugel.batch-e.package-manifest.v1":
        raise ValueError("UGEL_PACKAGE_MANIFEST_SCHEMA_INVALID")

    source_rows = [row for row in rows
                   if not row["path"].startswith(("evidence/", "release/"))
                   and row["path"] != "PACKAGE-MANIFEST.json"
                   and not row["path"].endswith((".pyc", ".pyo"))
                   and "/__pycache__/" not in row["path"]]
    source = json.loads(blobs["evidence/SOURCE-MANIFEST.json"])
    body = {"schema": "mosaic.ugel.batch-e.source.v1",
            "files": source_rows, "file_count": len(source_rows)}
    source_root = sha(DOMAIN + canonical(body))
    if source != {**body, "root": source_root} or source_root != SOURCE_ROOT:
        raise ValueError("UGEL_SOURCE_MANIFEST_INVALID")
    for name, expected in PINNED_MEMBERS.items():
        if name not in blobs or sha(blobs[name]) != expected:
            raise ValueError("UGEL_PINNED_MEMBER_MISMATCH")
    return {
        "schema": "mosaic.ucm.ugel-source-custody-verification.v0.1",
        "status": "PASS", "archive_sha256": sha(raw),
        "source_root": source_root, "package_members": len(blobs),
        "source_members": len(source_rows), "subject_code_loaded": False,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.archive.resolve()), sort_keys=True,
                     separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
