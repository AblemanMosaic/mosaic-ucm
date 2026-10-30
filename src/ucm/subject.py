"""Exact application-subject binding for archives and working trees."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any
import zipfile

from uclop.canonical import exact_keys, require, root

from .amcas import BOUNDARY


POLICY_SCHEMA = "mosaic.ucm.subject-binding-policy.v0.1"
BINDING_SCHEMA = "mosaic.ucm.subject-binding.v0.1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_path(value: str) -> str:
    require(type(value) is str and value and "\\" not in value, "SUBJECT_PATH_INVALID")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and "." not in path.parts,
            "SUBJECT_PATH_INVALID")
    return path.as_posix()


def _matches(path: str, patterns: list[str]) -> bool:
    item = PurePosixPath(path)
    return any(item.match(pattern) or (pattern.startswith("**/") and item.match(pattern[3:]))
               for pattern in patterns)


def validate_policy(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_id", "mode", "include", "exclude",
                              "allow_symlinks", "git_observation"})
    require(item["schema"] == POLICY_SCHEMA, "SUBJECT_POLICY_SCHEMA_INVALID")
    require(type(item["subject_id"]) is str and bool(item["subject_id"].strip()),
            "SUBJECT_ID_INVALID")
    require(item["mode"] in {"IMMUTABLE_ARCHIVE", "WORKING_BASELINE", "IMMUTABLE_SNAPSHOT"},
            "SUBJECT_MODE_INVALID")
    for field in ("include", "exclude"):
        require(type(item[field]) is list and all(type(row) is str and row for row in item[field]),
                "SUBJECT_PATTERN_SET_INVALID")
    require(bool(item["include"]), "SUBJECT_INCLUDE_EMPTY")
    require(type(item["allow_symlinks"]) is bool, "SUBJECT_SYMLINK_POLICY_INVALID")
    require(item["git_observation"] in {"REQUIRED", "OPTIONAL", "NONE"},
            "SUBJECT_GIT_POLICY_INVALID")
    return item


def _git_observation(directory: Path, policy: str) -> dict[str, Any]:
    empty = {"status": "NOT_OBSERVED", "head": None, "dirty": None,
             "status_sha256": None}
    if policy == "NONE":
        return empty
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory,
                              check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=directory,
                                check=True, capture_output=True).stdout.encode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        require(policy != "REQUIRED", "SUBJECT_GIT_OBSERVATION_REQUIRED")
        return empty
    require(len(head) == 40 and all(ch in "0123456789abcdef" for ch in head),
            "SUBJECT_GIT_HEAD_INVALID")
    return {"status": "OBSERVED", "head": head, "dirty": bool(status),
            "status_sha256": _sha(status)}


def _directory_rows(directory: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink():
            require(policy["allow_symlinks"], "SUBJECT_SYMLINK_REFUSED")
            continue
        if not path.is_file() or not _matches(relative, policy["include"]):
            continue
        if _matches(relative, policy["exclude"]):
            continue
        raw = path.read_bytes()
        rows.append({"path": _safe_path(relative), "sha256": _sha(raw), "bytes": len(raw)})
    require(bool(rows), "SUBJECT_FILE_SET_EMPTY")
    return rows


def _archive_rows(archive: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    require(zipfile.is_zipfile(archive), "SUBJECT_ARCHIVE_INVALID")
    rows = []
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as source:
        for info in sorted(source.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            path = _safe_path(info.filename)
            require(path not in seen, "SUBJECT_ARCHIVE_DUPLICATE_PATH")
            seen.add(path)
            if not _matches(path, policy["include"]) or _matches(path, policy["exclude"]):
                continue
            raw = source.read(info)
            rows.append({"path": path, "sha256": _sha(raw), "bytes": len(raw)})
    require(bool(rows), "SUBJECT_FILE_SET_EMPTY")
    return rows


def bind_subject(subject: Path, policy_value: Any) -> dict[str, Any]:
    policy = validate_policy(policy_value)
    subject = Path(subject)
    require(subject.exists(), "SUBJECT_INPUT_MISSING")
    if subject.is_file():
        require(policy["mode"] == "IMMUTABLE_ARCHIVE", "SUBJECT_ARCHIVE_MODE_REQUIRED")
        rows = _archive_rows(subject, policy)
        kind = "ZIP_ARCHIVE"
        source_archive_sha256 = _sha(subject.read_bytes())
        git = {"status": "NOT_APPLICABLE", "head": None, "dirty": None,
               "status_sha256": None}
        binding_status = "BOUND_IMMUTABLE"
    else:
        require(policy["mode"] != "IMMUTABLE_ARCHIVE", "SUBJECT_DIRECTORY_MODE_REQUIRED")
        rows = _directory_rows(subject, policy)
        kind = "DIRECTORY"
        source_archive_sha256 = None
        git = _git_observation(subject, policy["git_observation"])
        binding_status = ("BOUND_WORKING_BASELINE" if policy["mode"] == "WORKING_BASELINE"
                          else "BOUND_IMMUTABLE_SNAPSHOT")
    manifest_body = {"schema": "mosaic.ucm.subject-manifest.v0.1",
                     "subject_id": policy["subject_id"], "files": rows}
    manifest = {**manifest_body, "manifest_root": root(manifest_body)}
    body = {
        "schema": BINDING_SCHEMA,
        "subject_id": policy["subject_id"],
        "binding_status": binding_status,
        "subject_kind": kind,
        "source_root": root({"schema": "mosaic.ucm.subject-tree.v0.1", "files": rows}),
        "manifest_root": manifest["manifest_root"],
        "source_archive_sha256": source_archive_sha256,
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "policy": policy,
        "git": git,
        "manifest": manifest,
        **BOUNDARY,
    }
    return {**body, "binding_root": root(body)}


def verify_subject_binding(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_id", "binding_status", "subject_kind", "source_root",
        "manifest_root", "source_archive_sha256", "file_count", "total_bytes",
        "policy", "git", "manifest", "standing", "authority_effect", "real_a5",
        "g0", "binding_root",
    })
    require(item["schema"] == BINDING_SCHEMA, "SUBJECT_BINDING_SCHEMA_INVALID")
    policy = validate_policy(item["policy"])
    require(item["subject_id"] == policy["subject_id"], "SUBJECT_BINDING_ID_MISMATCH")
    manifest = exact_keys(item["manifest"], {
        "schema", "subject_id", "files", "manifest_root",
    })
    require(manifest["schema"] == "mosaic.ucm.subject-manifest.v0.1"
            and manifest["subject_id"] == item["subject_id"]
            and type(manifest["files"]) is list and bool(manifest["files"]),
            "SUBJECT_MANIFEST_INVALID")
    paths = set()
    rows = []
    for raw in manifest["files"]:
        row = exact_keys(raw, {"path", "sha256", "bytes"})
        path = _safe_path(row["path"])
        require(path not in paths and type(row["bytes"]) is int and row["bytes"] >= 0,
                "SUBJECT_MANIFEST_ROW_INVALID")
        require(type(row["sha256"]) is str and len(row["sha256"]) == 64
                and all(ch in "0123456789abcdef" for ch in row["sha256"]),
                "SUBJECT_MANIFEST_ROW_INVALID")
        paths.add(path); rows.append(row)
    manifest_body = {"schema": manifest["schema"], "subject_id": manifest["subject_id"],
                     "files": rows}
    require(manifest["manifest_root"] == root(manifest_body)
            and item["manifest_root"] == manifest["manifest_root"],
            "SUBJECT_MANIFEST_ROOT_INVALID")
    require(item["source_root"] == root({"schema": "mosaic.ucm.subject-tree.v0.1",
                                         "files": rows})
            and item["file_count"] == len(rows)
            and item["total_bytes"] == sum(row["bytes"] for row in rows),
            "SUBJECT_TREE_ROOT_INVALID")
    require((item["subject_kind"] == "ZIP_ARCHIVE"
             and item["binding_status"] == "BOUND_IMMUTABLE"
             and policy["mode"] == "IMMUTABLE_ARCHIVE"
             and type(item["source_archive_sha256"]) is str
             and len(item["source_archive_sha256"]) == 64
             and all(ch in "0123456789abcdef" for ch in item["source_archive_sha256"]))
            or (item["subject_kind"] == "DIRECTORY"
                and item["source_archive_sha256"] is None
                and ((policy["mode"] == "WORKING_BASELINE"
                      and item["binding_status"] == "BOUND_WORKING_BASELINE")
                     or (policy["mode"] == "IMMUTABLE_SNAPSHOT"
                         and item["binding_status"] == "BOUND_IMMUTABLE_SNAPSHOT"))),
            "SUBJECT_BINDING_MODE_INVALID")
    git = exact_keys(item["git"], {"status", "head", "dirty", "status_sha256"})
    require(git["status"] in {"NOT_OBSERVED", "NOT_APPLICABLE", "OBSERVED"},
            "SUBJECT_GIT_OBSERVATION_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "SUBJECT_AUTHORITY_CEILING_INVALID")
    body = {key: raw for key, raw in item.items() if key != "binding_root"}
    require(item["binding_root"] == root(body), "SUBJECT_BINDING_ROOT_INVALID")
    return item
