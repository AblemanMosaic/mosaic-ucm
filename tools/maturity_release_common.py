"""Deterministic source, runtime, and profile artifacts for the UCM successor."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402
from ucm.profiles import profile_registry, validate_profile_selection  # noqa: E402


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
TOP_LEVEL = {"README.md", "AGENT-ACCESS.md", "LICENSE", "NOTICE", "SECURITY.md",
             "CONTRIBUTING.md", "pyproject.toml", "VERIFY.py", "STAGE.py",
             "PIPPI-START-HERE.md", "PIPPI-AGENT-ACCESS.md",
             "PIPPI.cmd", "PIPPI-DASHBOARD.cmd", "PIPPI-SERVICE.cmd"}
ACTIVE_ROOTS = {"src", "spec", "docs", "examples", "fixtures", "conformance",
                "evaluation", "integration", "policy-packs", "program", "skill",
                "sidecar", "integration-kits", "campaign", "vendor", "completions",
                "install"}
# Generated release receipts are derived after qualification and deliberately
# remain outside the qualified source, just as they remain outside the public
# source manifest.  This prevents a successor from qualifying executable bytes
# while recursively carrying a stale predecessor release identity.
REVIEW_ROOTS = ACTIVE_ROOTS | {"tests", "tools", "audit", "review", "fuzz", "operator"}
EXCLUDED_PARTS = {".git", ".build", ".venv", "dist", "build", "evidence",
                  "__pycache__", ".pytest_cache"}
RUNTIME_EXCLUDED_PREFIXES = (
    "vendor/amcas-standard/evidence/", "vendor/amcas-standard/tests/",
    "vendor/amcas-standard/tools/", "integration/session-returns/",
    "integration/successor-returns/",
    "integration/audit-returns/",
    "integration/repair-returns/",
)
RUNTIME_EXCLUDED_FILES = {
    "vendor/amcas-standard/FINAL-REPORT.md",
    "vendor/amcas-standard/SOURCE-MANIFEST.json",
    "vendor/amcas-standard/SOURCE-PINS.json",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _allowed(relative: str, roots: set[str]) -> bool:
    parts = PurePosixPath(relative).parts
    return (relative in TOP_LEVEL or bool(parts and parts[0] in roots))


def collect_payloads(*, review: bool) -> dict[str, bytes]:
    roots = REVIEW_ROOTS if review else ACTIVE_ROOTS
    payloads: dict[str, bytes] = {}
    for directory, directories, files in os.walk(ROOT, topdown=True, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED_PARTS)
        base = Path(directory)
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(ROOT).as_posix()
            parts = PurePosixPath(relative).parts
            if any(part in EXCLUDED_PARTS for part in parts) or path.suffix.casefold() in {".pyc", ".pyo"}:
                continue
            if (not review and (relative in RUNTIME_EXCLUDED_FILES
                                or relative.startswith(RUNTIME_EXCLUDED_PREFIXES))):
                continue
            if not _allowed(relative, roots):
                continue
            if path.is_symlink():
                raise ValueError("MATURITY_SOURCE_ALIAS_REFUSED:" + relative)
            payloads[relative] = path.read_bytes()
    if not review:
        for relative in ("tools/ucm.py", "tools/build_architecture_study_kits.py",
                         "tools/reconcile_ecosystem_stage3.py",
                         "tools/wrap_ecosystem_session_return.py",
                         "tools/build_ecosystem_return_index.py",
                         "tools/build_ecosystem_outcome_register.py",
                         "tools/build_ecosystem_next_work.py",
                         "tools/build_ecosystem_next_dispatch.py",
                         "tools/wrap_ecosystem_successor_return.py",
                         "tools/build_ecosystem_successor_return_index.py",
                         "tools/build_ecosystem_successor_outcome_register.py",
                         "tools/build_ecosystem_audit_return_register.py",
                         "tools/wrap_ecosystem_repair_return.py",
                         "tools/build_ecosystem_repair_return_register.py",
                         "tools/build_ecosystem_current_state.py",
                         "tools/build_ecosystem_repair_program.py",
                         "tools/build_maturity_operator_evidence_addendum.py",
                         "tools/verify_runtime_tree.py"):
            payloads[relative] = (ROOT / relative).read_bytes()
    return dict(sorted(payloads.items()))


def source_record(payloads: dict[str, bytes], *, role: str) -> dict:
    body = {"schema": "mosaic.ucm.maturity-source.v0.1", "role": role,
            "files": [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                      for name, raw in sorted(payloads.items())],
            "file_count": len(payloads), "logical_bytes": sum(map(len, payloads.values())),
            **BOUNDARY}
    return {**body, "source_root": root(body)}


def _archive(payloads: dict[str, bytes], *, schema: str, role: str) -> tuple[bytes, dict]:
    raw = deterministic_zip(payloads, schema=schema, artifact_role=role)
    manifest = verify_deterministic_zip(raw, expected_schema=schema, expected_role=role)
    anchor_body = {"schema": "mosaic.ucm.maturity-artifact-anchor.v0.1",
                   "artifact_schema": schema, "artifact_role": role,
                   "archive_sha256": sha(raw), "archive_bytes": len(raw),
                   "manifest_root": manifest["manifest_root"],
                   "file_count": len(manifest["files"]), **BOUNDARY}
    return raw, {**anchor_body, "anchor_root": root(anchor_body)}


def build_runtime_archive() -> tuple[bytes, dict]:
    payloads = collect_payloads(review=False)
    raw, anchor = _archive(payloads,
        schema="mosaic.ucm.maturity-canonical-software.v0.1",
        role="UCM_MATURITY_CANONICAL_SOFTWARE")
    return raw, {**anchor, "source": source_record(payloads, role="CANONICAL_SOFTWARE"),
                 "profile_registry_root": profile_registry()["profile_registry_root"]}


def build_review_source_archive() -> tuple[bytes, dict]:
    payloads = collect_payloads(review=True)
    raw, anchor = _archive(payloads,
        schema="mosaic.ucm.maturity-qualification-source.v0.1",
        role="UCM_MATURITY_QUALIFICATION_SOURCE")
    return raw, {**anchor, "source": source_record(payloads, role="QUALIFICATION_SOURCE")}


def build_profile_overlay(profile_id: str) -> tuple[bytes, dict]:
    registry = profile_registry()
    profiles = {row["profile_id"]: row for row in registry["profiles"]}
    if profile_id not in profiles:
        raise ValueError("MATURITY_PROFILE_UNKNOWN")
    selection = json.loads((ROOT / "spec" / "product-profiles" /
                            f"{profile_id}-PROFILE.json").read_text(encoding="utf-8"))
    if validate_profile_selection({
            "schema": selection["schema"], "profile_id": selection["profile_id"],
            "capability_registry_root": selection["capability_registry_root"]}) != selection:
        raise ValueError("MATURITY_PROFILE_SELECTION_DRIFT")
    payloads = {
        "PROFILE-REGISTRY.json": canonical_bytes(registry),
        "PROFILE-SELECTION.json": canonical_bytes(selection),
        "README.txt": (f"UCM {profile_id} profile overlay\n"
                       "Apply only to the exact capability registry root in PROFILE-SELECTION.json.\n"
                       "A profile attenuates surfaces and grants no authority.\n").encode("ascii"),
    }
    return _archive(payloads, schema="mosaic.ucm.product-profile-overlay.v0.1",
                    role=f"UCM_{profile_id}_PROFILE_OVERLAY")


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
