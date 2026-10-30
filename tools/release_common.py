"""Standard-library custody checks shared by v0.1 release tooling."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import zipfile
from typing import Any

PUBLIC_EXCLUDED = {".git", ".build", ".venv", "dist", "build", "evidence",
                   "__pycache__", ".pytest_cache", "release"}
PUBLIC_EXCLUDED_FILES = {
    "MANIFEST.json",  # deterministic archive envelope metadata
    # Exact frozen predecessor dependency.  It is bound and carried beside the
    # qualification subject, not recursively embedded in source archives.
    "predecessors/stage-i4-c2-r5-freeze/UCL-UCM-AMCAS-STAGE-I4-C2-INDEPENDENT-REVIEW-HANDOFF.zip",
}
C4_EXCLUDED_ROOTS = {"evidence", "dist", "runtime", "assessment", ".git", ".pytest_cache"}
C4_MUTABLE = {
    "planning/WORKBENCH-C1-STATE-CAPSULE.json",
    "planning/WORKBENCH-C1-PROGRESS.json",
    "planning/WORKBENCH-C3-STATE-CAPSULE.json",
    "planning/WORKBENCH-C4-STATE-CAPSULE.json",
}
C4_HISTORICAL_GENERATED = (
    "historical/pcb-c3/evidence/hbip-c1/",
    "historical/pcb-c3/evidence/hbip-c2/",
    "historical/pcb-c3/evidence/pcb-c1/",
    "historical/pcb-c3/evidence/pcb-c2/",
    "historical/pcb-c3/evidence/pcb-c3/",
    "historical/pcb-c3/evidence/pcb-c3-lanes/",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def public_source_body(root: pathlib.Path) -> dict:
    rows = []
    for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        directory_names[:] = sorted(name for name in directory_names if name not in PUBLIC_EXCLUDED)
        base = pathlib.Path(directory)
        for name in sorted(file_names):
            path = base / name
            relative = path.relative_to(root)
            if relative.as_posix() in PUBLIC_EXCLUDED_FILES:
                continue
            if path.is_symlink():
                raise SystemExit("PUBLIC_SOURCE_ALIAS_REFUSED:" + relative.as_posix())
            data = path.read_bytes()
            rows.append({"path": relative.as_posix(), "sha256": sha(data), "bytes": len(data)})
    rows.sort(key=lambda row: row["path"])
    return {
        "schema": "mosaic.ucm.source-manifest.v0.1",
        "version": "v0.1",
        "scope": "PUBLIC_SOURCE_EXCLUDING_RELEASE_METADATA_AND_GENERATED_ARTIFACTS",
        "members": rows,
        "member_count": len(rows),
        "logical_bytes": sum(row["bytes"] for row in rows),
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }


def verify_public_source(root: pathlib.Path) -> dict:
    stored = _load(root / "release/SOURCE-MANIFEST.json")
    body = {key: value for key, value in stored.items() if key != "root"}
    if sha(canonical(body)) != stored.get("root"):
        raise SystemExit("SOURCE_MANIFEST_ROOT_MISMATCH")
    current = public_source_body(root)
    if current != body:
        raise SystemExit("SOURCE_MANIFEST_BYTES_OR_SET_MISMATCH")
    identity = _load(root / "release/RELEASE-IDENTITY.json")
    identity_body = {key: value for key, value in identity.items() if key != "root"}
    if sha(canonical(identity_body)) != identity.get("root"):
        raise SystemExit("RELEASE_IDENTITY_ROOT_MISMATCH")
    if identity.get("source_manifest_root") != stored["root"]:
        raise SystemExit("RELEASE_SOURCE_IDENTITY_MISMATCH")
    return {"source_manifest": stored, "release_identity": identity}


def c4_source_record(workspace: pathlib.Path) -> dict:
    rows = []
    for path in workspace.rglob("*"):
        relative = path.relative_to(workspace).as_posix()
        parts = pathlib.PurePosixPath(relative).parts
        if (
            not parts
            or parts[0] in C4_EXCLUDED_ROOTS
            or relative in C4_MUTABLE
            or relative.startswith(C4_HISTORICAL_GENERATED)
            or relative == "historical/pcb-c3/evidence/PCB-C3-COURT.json"
            or any(part in {"__pycache__", ".git", ".pytest_cache"} for part in parts)
            or path.suffix.casefold() in {".pyc", ".pyo"}
        ):
            continue
        if path.is_symlink():
            raise SystemExit("PREDECESSOR_SOURCE_ALIAS_REFUSED:" + relative)
        if path.is_file():
            data = path.read_bytes()
            rows.append({"path": relative, "sha256": sha(data), "bytes": len(data)})
    rows.sort(key=lambda row: row["path"])
    body = {"schema": "ucl.ucm.workbench_c1_source_manifest.v1", "files": rows, "file_count": len(rows)}
    return {**body, "source_root": sha(canonical(body))}


def _stage_c4_archive(archive: pathlib.Path, destination: pathlib.Path, *, expected_archive_sha256: str, expected_source_root: str) -> dict:
    if sha(archive.read_bytes()) != expected_archive_sha256:
        raise SystemExit("PREDECESSOR_COLD_BOOT_PIN_MISMATCH")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise SystemExit("PREDECESSOR_COLD_BOOT_DUPLICATE_MEMBER")
        manifest = json.loads(package.read("BOOTSTRAP-MANIFEST.json"))
        manifest_body = {key: value for key, value in manifest.items() if key != "manifest_root"}
        if sha(canonical(manifest_body)) != manifest.get("manifest_root") or manifest.get("source_root") != expected_source_root:
            raise SystemExit("PREDECESSOR_COLD_BOOT_MANIFEST_MISMATCH")
        profile_ref = manifest.get("profiles", {}).get("FULL_DEVELOPMENT", {})
        profile = json.loads(package.read(profile_ref.get("member", "")))
        profile_body = {key: value for key, value in profile.items() if key != "profile_root"}
        if sha(canonical(profile_body)) != profile.get("profile_root") or profile.get("profile_root") != profile_ref.get("profile_root"):
            raise SystemExit("PREDECESSOR_PROFILE_ROOT_MISMATCH")
        files = profile.get("files")
        if type(files) is not list or len(files) != profile.get("file_count") or len(files) != manifest.get("source_file_count"):
            raise SystemExit("PREDECESSOR_PROFILE_SET_MISMATCH")
        seen: set[str] = set()
        for row in files:
            relative = pathlib.PurePosixPath(row["path"])
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise SystemExit("PREDECESSOR_PROFILE_PATH_REFUSED")
            folded = relative.as_posix().casefold()
            if folded in seen:
                raise SystemExit("PREDECESSOR_PROFILE_PATH_ALIAS")
            seen.add(folded)
            member = f"objects/sha256/{row['sha256'][:2]}/{row['sha256']}"
            data = package.read(member)
            if sha(data) != row["sha256"] or len(data) != row["bytes"]:
                raise SystemExit("PREDECESSOR_PROFILE_OBJECT_MISMATCH:" + row["path"])
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return {"manifest": manifest, "profile": profile}


def verify_c4_predecessor(
    workspace: pathlib.Path,
    *,
    expected_source_root: str,
    expected_qualification_root: str,
    stage_destination: pathlib.Path,
) -> dict:
    freeze = _load(workspace / "dist/OPERATIONAL-C4-FREEZE-RECEIPT.json")
    qualification = _load(workspace / "evidence/operational-c4/OPERATIONAL-QUALIFICATION.json")
    if sha(canonical({key: value for key, value in freeze.items() if key != "root"})) != freeze.get("root"):
        raise SystemExit("PREDECESSOR_FREEZE_ROOT_MISMATCH")
    if sha(canonical({key: value for key, value in qualification.items() if key != "qualification_root"})) != qualification.get("qualification_root"):
        raise SystemExit("PREDECESSOR_QUALIFICATION_ROOT_MISMATCH")
    if freeze.get("source_root") != expected_source_root or freeze.get("qualification_root") != expected_qualification_root:
        raise SystemExit("PREDECESSOR_FREEZE_PIN_MISMATCH")
    if qualification.get("source_root") != expected_source_root or qualification.get("qualification_root") != expected_qualification_root or qualification.get("status") != "PASS":
        raise SystemExit("PREDECESSOR_QUALIFICATION_PIN_MISMATCH")
    lineage = _load(pathlib.Path(__file__).resolve().parents[1] / "audit/C4-FROZEN-LINEAGE.json")
    if (
        freeze.get("cold_boot_sha256") != lineage.get("cold_boot_sha256")
        or freeze.get("evidence_sha256") != lineage.get("evidence_sha256")
        or freeze.get("transport_sha256") != lineage.get("review_transport_sha256")
    ):
        raise SystemExit("PREDECESSOR_FREEZE_ARCHIVE_BINDING_MISMATCH")
    staged = _stage_c4_archive(
        workspace / "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-COLD-BOOT.zip",
        stage_destination,
        expected_archive_sha256=lineage["cold_boot_sha256"],
        expected_source_root=expected_source_root,
    )
    recomputed = c4_source_record(stage_destination)
    if recomputed.get("source_root") != expected_source_root:
        raise SystemExit("PREDECESSOR_STAGED_SOURCE_ROOT_MISMATCH")
    return {"source": {"source_root": staged["manifest"]["source_root"], "file_count": staged["manifest"]["source_file_count"]},
            "qualification": qualification, "freeze": freeze, "profile_root": staged["profile"]["profile_root"]}
