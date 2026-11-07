#!/usr/bin/env python3
"""Build deterministic, separate UCM runtime, SDK, and audit artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import tempfile
import zipfile
import sys
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_policy_spec = importlib.util.spec_from_file_location(
    "pippi_archive_policy", ROOT / "src" / "ucm" / "pippi_archive_policy.py")
if _policy_spec is None or _policy_spec.loader is None:
    raise SystemExit("PIPPI_ARCHIVE_POLICY_IMPORT_FAILED")
_archive_policy = importlib.util.module_from_spec(_policy_spec)
_policy_spec.loader.exec_module(_archive_policy)
REVIEW_CUSTODY_PREFIXES = _archive_policy.CUSTODY_PREFIXES
_cert_spec = importlib.util.spec_from_file_location(
    "release_certification", ROOT / "src" / "ucm" / "release_certification.py")
if _cert_spec is None or _cert_spec.loader is None:
    raise SystemExit("RELEASE_CERTIFICATION_IMPORT_FAILED")
_release_certification = importlib.util.module_from_spec(_cert_spec)
_cert_spec.loader.exec_module(_release_certification)
_common_spec = importlib.util.spec_from_file_location(
    "release_common", ROOT / "tools" / "release_common.py")
if _common_spec is None or _common_spec.loader is None:
    raise SystemExit("RELEASE_COMMON_IMPORT_FAILED")
_release_common = importlib.util.module_from_spec(_common_spec)
_common_spec.loader.exec_module(_release_common)
verify_public_source = _release_common.verify_public_source
PUBLIC_VERSION = _release_common.PUBLIC_VERSION
ENGINEERING_REVISION = _release_common.ENGINEERING_REVISION


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def all_files() -> list[pathlib.Path]:
    excluded = {".git", ".build", ".test-tmp", ".targeted-temp", "dist", "build", "__pycache__", ".pytest_cache"}
    paths: list[pathlib.Path] = []
    for directory, directory_names, file_names in os.walk(ROOT, topdown=True, followlinks=False):
        directory_names[:] = sorted(name for name in directory_names if name not in excluded)
        base = pathlib.Path(directory)
        for name in sorted(file_names):
            path = base / name
            relative = path.relative_to(ROOT)
            if relative.as_posix() == "MANIFEST.json":
                continue  # deterministic qualification-source envelope metadata
            if path.is_symlink():
                raise SystemExit("RELEASE_SOURCE_ALIAS_REFUSED:" + relative.as_posix())
            paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


def runtime_files() -> list[pathlib.Path]:
    exact = {
        "README.md", "LICENSE", "NOTICE", "pyproject.toml",
        "PIPPI-START-HERE.md", "PIPPI-AGENT-ACCESS.md",
        "PIPPI.cmd", "PIPPI-DASHBOARD.cmd", "PIPPI-DASHBOARD.vbs",
        "PIPPI-SERVICE.cmd", "PIPPI-SERVICE.vbs",
        "PIPPI-INSTALLER.BAT", "PIPPI-INSTALLER.vbs",
        "PIPPI-HEADLESS.BAT", "PIPPI-HEADLESS.vbs",
    }
    prefixes = ("src/", "spec/", "completions/", "fixtures/", "examples/", "docs/",
                "conformance/", "evaluation/", "integration/", "policy-packs/",
                "program/", "install/", "skill/ucm-pippi-mediated-agent/",
                "vendor/optional-packs/", "vendor/ugk-adaptive-profile/")
    files = [
        p for p in all_files()
        if (p.relative_to(ROOT).as_posix() in exact
            or p.relative_to(ROOT).as_posix().startswith(prefixes))
        and not p.relative_to(ROOT).as_posix().startswith(REVIEW_CUSTODY_PREFIXES)
        and not p.relative_to(ROOT).as_posix().casefold().endswith(
            ("evidence.zip", ".tar.gz"))
    ]
    files.append(ROOT / "tools" / "ucm.py")
    files.append(ROOT / "tools" / "verify_runtime_tree.py")
    files.append(ROOT / "tools" / "run_pippi_windows_smoke.py")
    return sorted(set(files), key=lambda p: p.relative_to(ROOT).as_posix())


def sdk_files() -> list[pathlib.Path]:
    # The qualification receipt describes the already-built release. Keeping it
    # outside the SDK payload avoids making the release identity depend on its
    # own post-build receipt.
    excluded = {
        "release/UCM-v0.1-QUALIFICATION.json",
        "release/UCM-v0.1-PUBLIC-RELEASE.json",
    }
    return [
        p for p in all_files()
        if not p.relative_to(ROOT).as_posix().startswith("audit/frozen/")
        and not p.relative_to(ROOT).as_posix().startswith(REVIEW_CUSTODY_PREFIXES + ("audit/",))
        and p.relative_to(ROOT).as_posix() not in excluded
    ]


def review_files() -> list[pathlib.Path]:
    return [p for p in all_files()
            if p.relative_to(ROOT).as_posix().startswith(REVIEW_CUSTODY_PREFIXES)]


def manifest(rows: list[tuple[str, bytes]], artifact: str, completeness: str) -> dict:
    members = [{"path": path, "sha256": digest(data), "bytes": len(data)} for path, data in rows]
    body = {
        "schema": "mosaic.ucm.artifact-manifest.v0.1",
        "artifact": artifact,
        "version": PUBLIC_VERSION,
        "engineering_revision": ENGINEERING_REVISION,
        "completeness": completeness,
        "members": members,
        "member_count": len(members),
        "logical_bytes": sum(row["bytes"] for row in members),
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    return {**body, "root": digest(canonical(body))}


def write_zip(path: pathlib.Path, rows: list[tuple[str, bytes]], artifact: str,
              completeness: str, *, source_manifest_root: str,
              release_identity_root: str) -> dict:
    payload_rows = sorted(rows, key=lambda item: item[0])
    metadata = _release_certification.build_embedded_metadata(
        payload_rows=payload_rows, artifact=artifact, completeness=completeness,
        version=PUBLIC_VERSION, engineering_revision=ENGINEERING_REVISION,
        source_manifest_root=source_manifest_root,
        release_identity_root=release_identity_root)
    rows = sorted([*payload_rows, *metadata.items()], key=lambda item: item[0])
    mf = manifest(rows, artifact, completeness)
    complete = [("MANIFEST.json", canonical(mf) + b"\n"), *rows]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in complete:
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            zf.writestr(info, data)
    return {
        "path": path.name, "role": artifact, "completeness": completeness,
        "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
        "manifest_root": mf["root"],
        "state_root": json.loads(metadata["META/STATE-MANIFEST.json"])["state_root"],
        "thr_body_root": json.loads(metadata["META/THR-MANIFEST.json"])["h_body"],
        "dkn_binding_root": json.loads(metadata["META/DKN-BINDING.json"])["dkn_binding_root"],
        "self_certificate_root": json.loads(metadata["META/SELF-CERTIFICATE.json"])["certificate_root"],
        "self_certificate_status": json.loads(metadata["META/SELF-CERTIFICATE.json"])["certificate_status"],
    }


def rows_from(paths: list[pathlib.Path]) -> list[tuple[str, bytes]]:
    return [(p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in paths]


def audit_rows(source: pathlib.Path | None) -> tuple[list[tuple[str, bytes]], str, str, str]:
    rows = [("audit/README.md", (ROOT / "audit" / "README.md").read_bytes())]
    for p in sorted((ROOT / "audit").glob("*.json"),
                    key=lambda item: item.relative_to(ROOT).as_posix()):
        rows.append((f"audit/{p.name}", p.read_bytes()))
    if source is None:
        return rows, "UCM_LINEAGE_METADATA", "METADATA_ONLY", "UCM-v0.1-lineage.zip"
    lineage = json.loads((ROOT / "audit/C4-FROZEN-LINEAGE.json").read_text(encoding="utf-8"))
    wanted = {
        "dist/OPERATIONAL-C4-FREEZE-RECEIPT.json": None,
        "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-COLD-BOOT.zip": lineage["cold_boot_sha256"],
        "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-EVIDENCE.zip": lineage["evidence_sha256"],
        "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-INDEPENDENT-REVIEW-TRANSPORT.zip": lineage["review_transport_sha256"],
        "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-TIER1-REVIEW-EVIDENCE-47f788bf2b37e6e6.zip": lineage["tier1_evidence_sha256"],
        "dist/UCL-UCM-OPERATIONAL-CANONICAL-c4-WSL-FULL-QUALIFICATION-EVIDENCE-5d5c1212f910a5cf.zip": lineage["wsl_qualification_evidence_sha256"],
    }
    for rel, expected in wanted.items():
        p = source / rel
        if not p.is_file():
            raise SystemExit(f"AUDIT_INPUT_MISSING:{rel}")
        if expected is not None and digest(p.read_bytes()) != expected:
            raise SystemExit(f"AUDIT_INPUT_PIN_MISMATCH:{rel}")
        rows.append((f"frozen-c4/{p.name}", p.read_bytes()))
    receipt = json.loads((source / "dist/OPERATIONAL-C4-FREEZE-RECEIPT.json").read_text(encoding="utf-8"))
    receipt_body = {key: value for key, value in receipt.items() if key != "root"}
    if digest(canonical(receipt_body)) != receipt.get("root"):
        raise SystemExit("AUDIT_FREEZE_ROOT_MISMATCH")
    if receipt.get("source_root") != lineage["source_root"] or receipt.get("qualification_root") != lineage["qualification_root"]:
        raise SystemExit("AUDIT_FREEZE_IDENTITY_MISMATCH")
    if (
        receipt.get("cold_boot_sha256") != lineage["cold_boot_sha256"]
        or receipt.get("evidence_sha256") != lineage["evidence_sha256"]
        or receipt.get("transport_sha256") != lineage["review_transport_sha256"]
    ):
        raise SystemExit("AUDIT_FREEZE_ARCHIVE_BINDING_MISMATCH")
    qualification = json.loads((source / "evidence/operational-c4/OPERATIONAL-QUALIFICATION.json").read_text(encoding="utf-8"))
    qualification_body = {key: value for key, value in qualification.items() if key != "qualification_root"}
    if digest(canonical(qualification_body)) != qualification.get("qualification_root"):
        raise SystemExit("AUDIT_QUALIFICATION_ROOT_MISMATCH")
    if qualification.get("source_root") != lineage["source_root"] or qualification.get("status") != "PASS":
        raise SystemExit("AUDIT_QUALIFICATION_IDENTITY_MISMATCH")
    return rows, "UCM_AUDIT", "COMPLETE_FROZEN_CUSTODY", "UCM-v0.1-audit.zip"


def verify_archive(path: pathlib.Path, *, source_manifest_root: str,
                   release_identity_root: str) -> dict:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)) or names.count("MANIFEST.json") != 1:
            raise SystemExit(f"ARCHIVE_SET_INVALID:{path.name}")
        mf = json.loads(zf.read("MANIFEST.json"))
        if (mf.get("version") != PUBLIC_VERSION
                or mf.get("engineering_revision") != ENGINEERING_REVISION):
            raise SystemExit(f"ARCHIVE_IDENTITY_MISMATCH:{path.name}")
        expected = {row["path"]: row for row in mf["members"]}
        if set(names) != {"MANIFEST.json", *expected}:
            raise SystemExit(f"ARCHIVE_MANIFEST_SET_MISMATCH:{path.name}")
        for name, row in expected.items():
            data = zf.read(name)
            if digest(data) != row["sha256"] or len(data) != row["bytes"]:
                raise SystemExit(f"ARCHIVE_MEMBER_MISMATCH:{path.name}:{name}")
        body = {k: v for k, v in mf.items() if k != "root"}
        if digest(canonical(body)) != mf["root"]:
            raise SystemExit(f"ARCHIVE_MANIFEST_ROOT_MISMATCH:{path.name}")
        payload = [(name, zf.read(name)) for name in names
                   if name != "MANIFEST.json" and not name.startswith("META/")]
        metadata = {name: zf.read(name) for name in _release_certification.META_NAMES}
        _release_certification.verify_embedded_metadata(
            payload_rows=payload, metadata=metadata, artifact=mf["artifact"],
            completeness=mf["completeness"], version=mf["version"],
            engineering_revision=ENGINEERING_REVISION, source_manifest_root=source_manifest_root,
            release_identity_root=release_identity_root)
        return mf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-source", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "dist")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    custody = verify_public_source(ROOT)
    runtime = runtime_files(); sdk = sdk_files(); review = review_files(); source = all_files()
    partition = _archive_policy.validate_release_partition(
        runtime_paths=[p.relative_to(ROOT).as_posix() for p in runtime],
        sdk_paths=[p.relative_to(ROOT).as_posix() for p in sdk],
        review_paths=[p.relative_to(ROOT).as_posix() for p in review],
        source_paths=[p.relative_to(ROOT).as_posix() for p in source],
        review_mode="SELF_CONTAINED_CUSTODY")
    artifacts = []
    certification = {"source_manifest_root": custody["source_manifest"]["root"],
                     "release_identity_root": custody["release_identity"]["root"]}
    artifacts.append(write_zip(out / "UCM-v0.1-runtime.zip", rows_from(runtime), "UCM_RUNTIME", "COMPLETE_RUNTIME", **certification))
    artifacts.append(write_zip(out / "UCM-v0.1-sdk.zip", rows_from(sdk), "UCM_SDK", "COMPLETE_SDK", **certification))
    artifacts.append(write_zip(out / "UCM-v0.1-review.zip", rows_from(review), "UCM_REVIEW", "SELF_CONTAINED_CUSTODY", **certification))
    audit, role, completeness, filename = audit_rows(args.audit_source.resolve() if args.audit_source else None)
    artifacts.append(write_zip(out / filename, audit, role, completeness, **certification))
    for row in artifacts:
        verify_archive(out / row["path"], **certification)
    release = {
        "schema": "mosaic.ucm.release.v0.1",
        "product": "Universal Constitutional Machine",
        "version": PUBLIC_VERSION,
        "engineering_revision": ENGINEERING_REVISION,
        "publisher": "Ableman Mosaic",
        "copyright": "Copyright 2026 Ableman Mosaic",
        "license": "Apache-2.0",
        "source_manifest_root": custody["source_manifest"]["root"],
        "release_identity_root": custody["release_identity"]["root"],
        "release_kind": "COMPLETE_AUDIT" if role == "UCM_AUDIT" else "PUBLIC_LINEAGE",
        "archive_partition": partition,
        "artifacts": artifacts,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    release["root"] = digest(canonical(release))
    (out / "UCM-v0.1-release.json").write_bytes(canonical(release) + b"\n")
    print(json.dumps(release, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


