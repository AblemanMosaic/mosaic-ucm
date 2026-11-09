#!/usr/bin/env python3
"""Dogfood r031 custody on exact r030/r031 runtime trees and seal the result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.transtemporal_archive import (  # noqa: E402
    build_semcrys_plan, diff_revisions, ingest_tree, materialize_revision,
    storage_report, verify_revision,
)
from ucm._blake3_portable import hexdigest as blake3_hex  # noqa: E402

FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def extract_closed(archive: Path, destination: Path) -> dict:
    raw = archive.read_bytes()
    with zipfile.ZipFile(archive) as package:
        infos = package.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise SystemExit("R031_HISTORY_DUPLICATE_MEMBER")
        for info in infos:
            path = PurePosixPath(info.filename)
            if info.is_dir() or path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise SystemExit("R031_HISTORY_MEMBER_PATH_INVALID")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(package.read(info))
    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))
    return {"sha256": sha(raw), "blake3_256": blake3_hex(raw),
            "manifest_root": manifest["root"], "members": len(names)}


def tree_rows(root_dir: Path) -> list[dict]:
    rows = []
    for path in sorted((item for item in root_dir.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(root_dir).as_posix()):
        raw = path.read_bytes()
        rows.append({"path": path.relative_to(root_dir).as_posix(),
                     "sha256": sha(raw), "bytes": len(raw)})
    return rows


def write_zip(output: Path, payload: dict[str, bytes]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as package:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            package.writestr(info, raw)


def build(r030_runtime: Path, r031_runtime: Path, output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ucm-r031-history-", dir=output.parent) as temporary:
        base = Path(temporary)
        old_tree, new_tree, repository = base / "r030", base / "r031", base / "repository"
        old_tree.mkdir(); new_tree.mkdir()
        old = extract_closed(r030_runtime, old_tree)
        new = extract_closed(r031_runtime, new_tree)
        for revision, source, identity, parent in (
                ("r030", old_tree, old, None), ("r031", new_tree, new, "r030")):
            semantic_root = root({"domain": "SEMANTICS", "runtime_manifest_root": identity["manifest_root"]})
            governance_root = root({"domain": "GOVERNANCE", "runtime_manifest_root": identity["manifest_root"]})
            jurisdiction_root = root({"domain": "JURISDICTION", "namespace": "mosaic.ucm.v0.1",
                                      "revision": revision})
            ingest_tree(source=source, repository=repository, revision=revision,
                        semantic_root=semantic_root, governance_root=governance_root,
                        jurisdiction_root=jurisdiction_root, parent_revision=parent)
            verify_revision(repository=repository, revision=revision)
            rebuilt = base / (revision + "-rebuilt")
            materialize_revision(repository=repository, revision=revision, destination=rebuilt)
            if tree_rows(rebuilt) != tree_rows(source):
                raise SystemExit("R031_HISTORY_RECONSTRUCTION_MISMATCH:" + revision)
        report = storage_report(repository=repository)
        delta = diff_revisions(repository=repository, before="r030", after="r031")
        semcrys = build_semcrys_plan(repository=repository, revision="r031",
                                     semcrys_manifest_root=None,
                                     memory_vault_binding_root=None)
        retention_body = {
            "schema": "mosaic.ucm.transtemporal-retention-dry-run.v0.1",
            "inputs": {"r030_runtime": old, "r031_runtime": new},
            "archive_verified_revisions": ["r030", "r031"],
            "proposed_deletions": [],
            "safe_deletion": False,
            "reason": "DRY_RUN_ONLY_RETAIN_INPUTS_UNTIL_EXTERNAL_ACCEPTANCE",
            **BOUNDARY,
        }
        retention = {**retention_body, "retention_root": root(retention_body)}
        reports = {
            "DOGFOOD/DIFF.json": canonical_bytes(delta) + b"\n",
            "DOGFOOD/STORAGE-REPORT.json": canonical_bytes(report) + b"\n",
            "DOGFOOD/SEMCRYS-PLAN.json": canonical_bytes(semcrys) + b"\n",
            "DOGFOOD/RETENTION-DRY-RUN.json": canonical_bytes(retention) + b"\n",
        }
        payload = {"REPOSITORY/" + path.relative_to(repository).as_posix(): path.read_bytes()
                   for path in repository.rglob("*") if path.is_file()}
        payload.update(reports)
        rows = [{"path": name, "sha256": sha(raw), "blake3_256": blake3_hex(raw),
                 "bytes": len(raw)} for name, raw in sorted(payload.items())]
        manifest_body = {
            "schema": "mosaic.ucm.r031-transtemporal-history-handoff.v0.1",
            "version": "v0.1", "engineering_revision": "r031",
            "namespace": "mosaic.ucm.v0.1", "revision_range": ["r030", "r031"],
            "storage_report_root": report["storage_report_root"],
            "retention_root": retention["retention_root"],
            "members": rows, "member_count": len(rows), **BOUNDARY,
        }
        manifest = {**manifest_body, "manifest_root": root(manifest_body)}
        payload["MANIFEST.json"] = canonical_bytes(manifest) + b"\n"
        write_zip(output, payload)
    raw = output.read_bytes()
    return {"status": "PASS", "path": str(output), "sha256": sha(raw),
            "blake3_256": blake3_hex(raw), "manifest_root": manifest["manifest_root"],
            "logical_bytes": report["logical_bytes"],
            "unique_object_bytes": report["unique_object_bytes"],
            "deduplicated_bytes": report["deduplicated_bytes"], **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r030-runtime", type=Path, required=True)
    parser.add_argument("--r031-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.r030_runtime.resolve(), args.r031_runtime.resolve(),
                           args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
