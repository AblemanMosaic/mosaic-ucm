"""Standalone standard-library verifier for UCM deterministic archives."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile


FIXED_TIME = (1980, 1, 1, 0, 0, 0)
MAX_MEMBER = 64 * 1024 * 1024
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def root(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def decode(raw):
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("SOURCE_BOM_FORBIDDEN")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_float=lambda _: (_ for _ in ()).throw(ValueError("FLOAT_FORBIDDEN")),
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NUMBER_FORBIDDEN")))
    if canonical(value) != raw:
        raise ValueError("JSON_NOT_CANONICAL")
    return value


def _safe(name):
    path = PurePosixPath(name)
    if (not name or name != path.as_posix() or name.startswith("/") or ".." in path.parts
            or "\\" in name or ":" in name):
        raise ValueError("ARCHIVE_PATH_UNSAFE")
    return name


def _rebuild(payloads, schema, role):
    rows = [{"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(payloads.items())]
    body = {"schema": schema, "artifact_role": role, "files": rows, **BOUNDARY}
    all_payloads = {**payloads, "MANIFEST.json": canonical({**body, "manifest_root": root(body)})}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_payloads.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def verify(path: Path, expected_schema: str | None = None,
           expected_role: str | None = None):
    raw = Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("ARCHIVE_DUPLICATE_MEMBER")
        payloads = {}
        for info in infos:
            _safe(info.filename)
            if info.file_size > MAX_MEMBER or info.compress_type != zipfile.ZIP_STORED:
                raise ValueError("ARCHIVE_MEMBER_INVALID")
            payloads[info.filename] = archive.read(info)
    if "MANIFEST.json" not in payloads:
        raise ValueError("ARCHIVE_MANIFEST_MISSING")
    manifest = decode(payloads.pop("MANIFEST.json"))
    expected_keys = {"schema", "artifact_role", "files", "standing", "authority_effect",
                     "real_a5", "g0", "manifest_root"}
    if set(manifest) != expected_keys or {key: manifest[key] for key in BOUNDARY} != BOUNDARY:
        raise ValueError("ARCHIVE_MANIFEST_INVALID")
    if expected_schema is not None and manifest["schema"] != expected_schema:
        raise ValueError("ARCHIVE_SCHEMA_MISMATCH")
    if expected_role is not None and manifest["artifact_role"] != expected_role:
        raise ValueError("ARCHIVE_ROLE_MISMATCH")
    body = {key: value for key, value in manifest.items() if key != "manifest_root"}
    if manifest["manifest_root"] != root(body):
        raise ValueError("ARCHIVE_MANIFEST_ROOT_MISMATCH")
    if _rebuild(payloads, manifest["schema"], manifest["artifact_role"]) != raw:
        raise ValueError("ARCHIVE_NOT_CANONICAL")
    return {"status": "PASS", "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "members": len(payloads), **manifest}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--schema")
    parser.add_argument("--role")
    args = parser.parse_args()
    try:
        print(canonical(verify(args.archive, args.schema, args.role)).decode())
        return 0
    except Exception as error:
        print(canonical({"status": "REFUSED", "diagnostic": str(error), **BOUNDARY}).decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
