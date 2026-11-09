"""Exact, dual-digest transtemporal custody for P/PPI projects.

The archive stores each distinct byte string once, gives logical paths stable
integer identifiers, and records immutable revision manifests.  BLAKE3 is the
primary content address; SHA-256 is retained as an interoperability and native
verification projection.  Compression is an optional external realization and
never changes the logical state manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any, Iterable

from uclop.canonical import (Refusal, canonical_bytes, require, require_root,
                             root, strict_loads)
try:
    from blake3 import blake3 as _accelerated_blake3
except ImportError:  # the runtime remains sovereign and dependency-free
    _accelerated_blake3 = None
from ._blake3_portable import hexdigest as _portable_blake3


BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}
SCHEMA = "mosaic.ucm.transtemporal-archive.v0.1"
PATH_POLICY = "PORTABLE_POSIX_RELATIVE_CASE_DISTINCT_V1"


def _b3(data: bytes) -> str:
    return (_accelerated_blake3(data).hexdigest() if _accelerated_blake3 is not None
            else _portable_blake3(data))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sealed(body: dict[str, Any], field: str = "root") -> dict[str, Any]:
    return {**body, field: root(body)}


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        require(path.read_bytes() == data, "ARCHIVE_IMMUTABLE_MEMBER_MISMATCH", str(path))


def _replace(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".pending", dir=path.parent)
    pending = Path(raw)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def _portable(relative: str) -> str:
    require(type(relative) is str and bool(relative), "ARCHIVE_PATH_INVALID")
    require("\\" not in relative and "\x00" not in relative, "ARCHIVE_PATH_INVALID", detail=relative)
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and "." not in path.parts,
            "ARCHIVE_PATH_INVALID", detail=relative)
    require(path.as_posix() == relative and all(part not in {"", ".", ".."} for part in path.parts),
            "ARCHIVE_PATH_NONCANONICAL", detail=relative)
    require(not any(part.endswith((" ", ".")) for part in path.parts),
            "ARCHIVE_PATH_PORTABILITY_REFUSED", detail=relative)
    return relative


def digest_record(data: bytes) -> dict[str, Any]:
    require(type(data) is bytes, "ARCHIVE_BYTES_REQUIRED")
    body = {
        "schema": "mosaic.ucm.dual-digest.v0.1",
        "primary_algorithm": "BLAKE3-256",
        "blake3_256": _b3(data),
        "sha256": _sha(data),
        "bytes": len(data),
    }
    return _sealed(body, "digest_root")


def _object_path(repository: Path, digest: dict[str, Any]) -> Path:
    value = digest["blake3_256"]
    return repository / "objects" / "blake3-256" / value[:2] / value


def _load(path: Path) -> dict[str, Any]:
    require(path.is_file(), "ARCHIVE_RECORD_MISSING", str(path))
    value = strict_loads(path.read_bytes())
    require(type(value) is dict, "ARCHIVE_RECORD_INVALID", str(path))
    return value


def _verify_seal(value: dict[str, Any], field: str = "root") -> None:
    require_root(value.get(field), f"$.{field}")
    require(root({key: item for key, item in value.items() if key != field}) == value[field],
            "ARCHIVE_RECORD_ROOT_MISMATCH", f"$.{field}")


def _previous_ids(parent: dict[str, Any] | None) -> tuple[dict[str, str], int]:
    if parent is None:
        return {}, 0
    rows = parent.get("files")
    require(type(rows) is list, "ARCHIVE_PARENT_INVALID")
    by_path: dict[str, str] = {}
    maximum = 0
    for row in rows:
        identifier = row.get("file_id", "")
        require(type(identifier) is str and len(identifier) == 10 and identifier.startswith("F")
                and identifier[1:].isdigit(), "ARCHIVE_FILE_ID_INVALID")
        maximum = max(maximum, int(identifier[1:]))
        by_path[row["path"]] = identifier
    return by_path, maximum


def _inventory(source: Path, excludes: Iterable[str]) -> list[tuple[str, bytes]]:
    excluded = set(excludes)
    rows: list[tuple[str, bytes]] = []
    folded: dict[str, str] = {}
    for base, directories, files in os.walk(source, topdown=True, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in excluded)
        folder = Path(base)
        for name in sorted(files):
            path = folder / name
            relative = _portable(path.relative_to(source).as_posix())
            require(not path.is_symlink(), "ARCHIVE_SOURCE_ALIAS_REFUSED", relative)
            key = relative.casefold()
            require(key not in folded or folded[key] == relative,
                    "ARCHIVE_CASE_ALIAS_REFUSED", detail=f"{folded.get(key)}|{relative}")
            folded[key] = relative
            rows.append((relative, path.read_bytes()))
    return sorted(rows, key=lambda item: item[0])


def build_thr_manifest(*, state_root: str, semantic_root: str,
                       governance_root: str, jurisdiction_root: str,
                       receipt_root: str) -> dict[str, Any]:
    commitments = {
        "H_s_state": require_root(state_root),
        "H_m_semantics": require_root(semantic_root),
        "H_c_governance": require_root(governance_root),
        "H_j_jurisdiction": require_root(jurisdiction_root),
        "H_r_receipt": require_root(receipt_root),
    }
    body = {
        "schema": "mosaic.thr.manifest.v0.1",
        "commitments": commitments,
        "h_body": root(commitments),
        "separation": "STATE_SEMANTICS_GOVERNANCE_JURISDICTION_RECEIPT",
        **BOUNDARY,
    }
    return _sealed(body, "thr_manifest_root")


def build_dkn_binding(*, namespace: str = "mosaic.ucm.v0.1",
                      epoch: str = "r033") -> dict[str, Any]:
    body = {
        "schema": "mosaic.dkn.binding.v0.1",
        "namespace": namespace,
        "epoch": epoch,
        "status": "DECLARED_UNBOUND",
        "public_key": None,
        "signature": None,
        "claim": "NO_SELF_CERTIFICATION_WITHOUT_KEY_CEREMONY",
        **BOUNDARY,
    }
    return _sealed(body, "dkn_binding_root")


def ingest_tree(*, source: Path, repository: Path, revision: str,
                semantic_root: str, governance_root: str,
                jurisdiction_root: str, parent_revision: str | None = None,
                excludes: Iterable[str] = (".git", "__pycache__", ".pytest_cache")) -> dict[str, Any]:
    source, repository = source.resolve(), repository.resolve()
    require(source.is_dir(), "ARCHIVE_SOURCE_DIRECTORY_REQUIRED")
    require(type(revision) is str and revision.startswith("r") and revision[1:].isdigit(),
            "ARCHIVE_REVISION_INVALID")
    require(not repository.is_relative_to(source), "ARCHIVE_REPOSITORY_INSIDE_SOURCE_REFUSED")
    target = repository / "revisions" / revision
    require(not target.exists(), "ARCHIVE_REVISION_EXISTS")
    parent = None
    if parent_revision is not None:
        parent = _load(repository / "revisions" / parent_revision / "MANIFEST.json")
        _verify_seal(parent, "manifest_root")
    previous, next_id = _previous_ids(parent)
    file_rows = []
    for relative, data in _inventory(source, excludes):
        identifier = previous.get(relative)
        if identifier is None:
            next_id += 1
            identifier = f"F{next_id:09d}"
        digest = digest_record(data)
        _write_new(_object_path(repository, digest), data)
        file_rows.append({"file_id": identifier, "path": relative, "digest": digest})
    body = {
        "schema": SCHEMA,
        "revision": revision,
        "parent_revision": parent_revision,
        "parent_manifest_root": parent.get("manifest_root") if parent else None,
        "path_policy": PATH_POLICY,
        "primary_content_address": "BLAKE3-256",
        "interoperability_digest": "SHA-256",
        "files": file_rows,
        "file_count": len(file_rows),
        "logical_bytes": sum(row["digest"]["bytes"] for row in file_rows),
        **BOUNDARY,
    }
    manifest = _sealed(body, "manifest_root")
    receipt = _sealed({
        "schema": "mosaic.ucm.transtemporal-ingest-receipt.v0.1",
        "revision": revision,
        "manifest_root": manifest["manifest_root"],
        "parent_manifest_root": manifest["parent_manifest_root"],
        "object_count": len({row["digest"]["blake3_256"] for row in file_rows}),
        "file_count": len(file_rows),
        "logical_bytes": manifest["logical_bytes"],
        **BOUNDARY,
    }, "receipt_root")
    thr = build_thr_manifest(state_root=manifest["manifest_root"],
        semantic_root=semantic_root, governance_root=governance_root,
        jurisdiction_root=jurisdiction_root, receipt_root=receipt["receipt_root"])
    dkn = build_dkn_binding(epoch=revision)
    records = {"MANIFEST.json": manifest, "RECEIPT.json": receipt,
               "THR-MANIFEST.json": thr, "DKN-BINDING.json": dkn}
    for name, value in records.items():
        _write_new(target / name, canonical_bytes(value) + b"\n")
    _replace(repository / "HEAD", (revision + "\n").encode("ascii"))
    return {"status": "PASS", **records, **BOUNDARY}


def verify_revision(*, repository: Path, revision: str) -> dict[str, Any]:
    base = repository.resolve() / "revisions" / revision
    manifest = _load(base / "MANIFEST.json"); _verify_seal(manifest, "manifest_root")
    receipt = _load(base / "RECEIPT.json"); _verify_seal(receipt, "receipt_root")
    thr = _load(base / "THR-MANIFEST.json"); _verify_seal(thr, "thr_manifest_root")
    dkn = _load(base / "DKN-BINDING.json"); _verify_seal(dkn, "dkn_binding_root")
    require(receipt.get("manifest_root") == manifest["manifest_root"], "ARCHIVE_RECEIPT_STATE_MISMATCH")
    require(thr.get("commitments", {}).get("H_s_state") == manifest["manifest_root"],
            "ARCHIVE_THR_STATE_MISMATCH")
    require(thr.get("commitments", {}).get("H_r_receipt") == receipt["receipt_root"],
            "ARCHIVE_THR_RECEIPT_MISMATCH")
    require(dkn.get("status") == "DECLARED_UNBOUND" and dkn.get("public_key") is None,
            "ARCHIVE_DKN_OVERCLAIM")
    parent_revision = manifest.get("parent_revision")
    if parent_revision is None:
        require(manifest.get("parent_manifest_root") is None, "ARCHIVE_PARENT_ROOT_UNEXPECTED")
    else:
        parent = _load(repository.resolve() / "revisions" / parent_revision / "MANIFEST.json")
        _verify_seal(parent, "manifest_root")
        require(manifest.get("parent_manifest_root") == parent["manifest_root"],
                "ARCHIVE_PARENT_ROOT_MISMATCH")
    seen_ids: set[str] = set(); seen_paths: set[str] = set()
    for row in manifest.get("files", []):
        require(row["file_id"] not in seen_ids, "ARCHIVE_FILE_ID_DUPLICATE")
        require(row["path"] not in seen_paths, "ARCHIVE_PATH_DUPLICATE")
        seen_ids.add(row["file_id"]); seen_paths.add(_portable(row["path"]))
        data = _object_path(repository, row["digest"]).read_bytes()
        require(digest_record(data) == row["digest"], "ARCHIVE_OBJECT_DIGEST_MISMATCH", row["path"])
    require(len(seen_paths) == manifest.get("file_count"), "ARCHIVE_FILE_COUNT_MISMATCH")
    return _sealed({
        "schema": "mosaic.ucm.transtemporal-verification.v0.1",
        "status": "PASS",
        "revision": revision,
        "manifest_root": manifest["manifest_root"],
        "thr_manifest_root": thr["thr_manifest_root"],
        "dkn_binding_root": dkn["dkn_binding_root"],
        "file_count": len(seen_paths),
        **BOUNDARY,
    }, "verification_root")


def materialize_revision(*, repository: Path, revision: str, destination: Path) -> dict[str, Any]:
    verification = verify_revision(repository=repository, revision=revision)
    destination = destination.resolve()
    require(not destination.exists() or not any(destination.iterdir()), "ARCHIVE_DESTINATION_NOT_EMPTY")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = _load(repository.resolve() / "revisions" / revision / "MANIFEST.json")
    for row in manifest["files"]:
        target = destination.joinpath(*PurePosixPath(row["path"]).parts)
        require(target.resolve().is_relative_to(destination), "ARCHIVE_DESTINATION_ESCAPE")
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_new(target, _object_path(repository, row["digest"]).read_bytes())
    return _sealed({
        "schema": "mosaic.ucm.transtemporal-materialization.v0.1",
        "status": "PASS",
        "revision": revision,
        "manifest_root": verification["manifest_root"],
        "file_count": verification["file_count"],
        **BOUNDARY,
    }, "materialization_root")


def diff_revisions(*, repository: Path, before: str, after: str) -> dict[str, Any]:
    verify_revision(repository=repository, revision=before)
    verify_revision(repository=repository, revision=after)
    left = _load(repository / "revisions" / before / "MANIFEST.json")
    right = _load(repository / "revisions" / after / "MANIFEST.json")
    a = {row["path"]: row for row in left["files"]}; b = {row["path"]: row for row in right["files"]}
    body = {
        "schema": "mosaic.ucm.transtemporal-diff.v0.1",
        "before_manifest_root": left["manifest_root"],
        "after_manifest_root": right["manifest_root"],
        "added": sorted(set(b) - set(a)),
        "removed": sorted(set(a) - set(b)),
        "changed": sorted(path for path in set(a) & set(b)
                          if a[path]["digest"]["blake3_256"] != b[path]["digest"]["blake3_256"]),
        "unchanged_count": sum(a[path]["digest"]["blake3_256"] == b[path]["digest"]["blake3_256"]
                               for path in set(a) & set(b)),
        **BOUNDARY,
    }
    return _sealed(body, "diff_root")


def storage_report(*, repository: Path) -> dict[str, Any]:
    repository = repository.resolve()
    manifests = []
    revisions_root = repository / "revisions"
    for path in sorted(revisions_root.glob("*/MANIFEST.json"),
                       key=lambda item: item.relative_to(revisions_root).as_posix()):
        value = _load(path); _verify_seal(value, "manifest_root"); manifests.append(value)
    logical = sum(value["logical_bytes"] for value in manifests)
    objects = [path for path in (repository / "objects" / "blake3-256").glob("*/*") if path.is_file()]
    physical = sum(path.stat().st_size for path in objects)
    body = {
        "schema": "mosaic.ucm.transtemporal-storage-report.v0.1",
        "revision_count": len(manifests),
        "object_count": len(objects),
        "logical_bytes": logical,
        "unique_object_bytes": physical,
        "deduplicated_bytes": logical - physical,
        "compression": "NOT_APPLIED",
        "safe_deletion": "NONE_PERFORMED",
        **BOUNDARY,
    }
    return _sealed(body, "storage_report_root")


def build_semcrys_plan(*, repository: Path, revision: str,
                       semcrys_manifest_root: str | None,
                       memory_vault_binding_root: str | None) -> dict[str, Any]:
    verification = verify_revision(repository=repository, revision=revision)
    ready = semcrys_manifest_root is not None and memory_vault_binding_root is not None
    if semcrys_manifest_root is not None: require_root(semcrys_manifest_root)
    if memory_vault_binding_root is not None: require_root(memory_vault_binding_root)
    body = {
        "schema": "mosaic.ucm.semcrys-transtemporal-plan.v0.1",
        "status": "READY_FOR_EXTERNAL_COMPRESSION" if ready else "HELD_OPTIONAL_PACK_UNBOUND",
        "revision": revision,
        "manifest_root": verification["manifest_root"],
        "semcrys_manifest_root": semcrys_manifest_root,
        "memory_vault_binding_root": memory_vault_binding_root,
        "plan_performs_effects": False,
        "required_postcondition": "RESTORED_BYTES_MATCH_DUAL_DIGEST_MANIFEST",
        **BOUNDARY,
    }
    return _sealed(body, "plan_root")


def build_native_manifest(*, repository: Path, revision: str) -> bytes:
    """Return the stable line protocol consumed by the small C verifier."""
    verify_revision(repository=repository, revision=revision)
    manifest = _load(repository / "revisions" / revision / "MANIFEST.json")
    rows = []
    for row in manifest["files"]:
        require("\t" not in row["path"] and "\n" not in row["path"], "ARCHIVE_NATIVE_PATH_INVALID")
        rows.append(f"{row['digest']['sha256']}\t{row['digest']['bytes']}\t{row['path']}")
    require(bool(rows), "ARCHIVE_NATIVE_EMPTY_DENOMINATOR")
    row_bytes = ("\n".join(rows) + "\n").encode("utf-8")
    header = (f"UCM-NATIVE-MANIFEST\t2\tSHA-256\t{manifest['manifest_root']}\t{len(rows)}\n").encode("ascii")
    trailer = f"END\t{len(rows)}\t{hashlib.sha256(row_bytes).hexdigest()}\n".encode("ascii")
    return header + row_bytes + trailer


def build_native_manifest_binding(*, repository: Path, revision: str) -> dict[str, Any]:
    """Return the external denominator and row-stream pins for the C verifier."""
    raw = build_native_manifest(repository=repository, revision=revision)
    manifest = _load(repository / "revisions" / revision / "MANIFEST.json")
    rows = [
        f"{row['digest']['sha256']}\t{row['digest']['bytes']}\t{row['path']}"
        for row in manifest["files"]
    ]
    row_bytes = ("\n".join(rows) + "\n").encode("utf-8")
    body = {
        "schema": "mosaic.ucm.native-manifest-binding.v0.1",
        "revision": revision,
        "manifest_root": manifest["manifest_root"],
        "rows_root": _sha(row_bytes),
        "member_count": len(rows),
        "native_manifest_sha256": _sha(raw),
        **BOUNDARY,
    }
    return _sealed(body, "binding_root")

