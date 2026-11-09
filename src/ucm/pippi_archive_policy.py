"""Pure transtemporal custody policy for P/PPI and UCM release profiles.

Runtime and SDK artifacts carry active machinery. Historical reviews and
returns live once in a content-addressed backend and are cited by rooted
references. A deliberately self-contained review envelope may carry those
bytes, but it must say so and contain the complete fixed denominator.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Iterable


ARCHIVE_POLICY_SCHEMA = "mosaic.ucm.pippi-transtemporal-archive-policy.v0.1"
ARCHIVE_REFERENCE_SCHEMA = "mosaic.ucm.pippi-transtemporal-reference.v0.1"
ARCHIVE_AVAILABILITY_SCHEMA = "mosaic.ucm.pippi-archive-availability.v0.1"
RELEASE_PARTITION_SCHEMA = "mosaic.ucm.release-archive-partition.v0.1"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}

# This is imported directly by the release builder so the split and the public
# policy cannot drift.
CUSTODY_PREFIXES = (
    "review/", "operator/", "operator-kits/",
    "integration/session-returns/", "integration/successor-returns/",
    "integration/audit-returns/", "integration/repair-returns/",
)
REVIEW_MODES = ("REFERENCE_ONLY", "SELF_CONTAINED_CUSTODY")
BACKENDS = ("LOCAL_CONTENT_STORE", "MEMORY_VAULT")


class ArchivePolicyRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code, self.detail = code, detail
        super().__init__(f"{code}:{detail}" if detail else code)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _root(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, code: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or
            any(ch not in "0123456789abcdef" for ch in value)):
        raise ArchivePolicyRefusal(code)
    return value


def _paths(values: Iterable[str]) -> tuple[str, ...]:
    rows = tuple(sorted(set(values)))
    if any(not isinstance(row, str) or not row or "\\" in row or
           row.startswith("/") or ".." in row.split("/") for row in rows):
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_PATH_INVALID")
    return rows


def is_custody_path(path: str) -> bool:
    return path.startswith(CUSTODY_PREFIXES)


def build_transtemporal_reference(*, project_root: str, artifact_role: str,
                                  artifact_sha256: str, artifact_bytes: int,
                                  semantic_root: str, metadata_root: str,
                                  governance_root: str, backend: str,
                                  backend_reference: str,
                                  availability: str = "AVAILABLE") -> dict[str, Any]:
    """Build a reference with separated semantic/state/metadata/governance roots."""
    _sha(project_root, "PIPPI_ARCHIVE_PROJECT_ROOT_INVALID")
    _sha(artifact_sha256, "PIPPI_ARCHIVE_HASH_INVALID")
    _sha(semantic_root, "PIPPI_ARCHIVE_SEMANTIC_ROOT_INVALID")
    _sha(metadata_root, "PIPPI_ARCHIVE_METADATA_ROOT_INVALID")
    _sha(governance_root, "PIPPI_ARCHIVE_GOVERNANCE_ROOT_INVALID")
    if not isinstance(artifact_role, str) or not artifact_role.strip():
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_ROLE_INVALID")
    if not isinstance(artifact_bytes, int) or isinstance(artifact_bytes, bool) or artifact_bytes < 0:
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_BYTES_INVALID")
    if backend not in BACKENDS:
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_BACKEND_INVALID")
    if not isinstance(backend_reference, str) or not backend_reference.strip():
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_REFERENCE_REQUIRED")
    if availability not in {"AVAILABLE", "UNAVAILABLE"}:
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_AVAILABILITY_INVALID")
    commitments = {
        "semantic_root": semantic_root,
        "state_root": artifact_sha256,
        "metadata_root": metadata_root,
        "governance_root": governance_root,
    }
    body = {
        "schema": ARCHIVE_REFERENCE_SCHEMA,
        "project_root": project_root,
        "artifact_role": artifact_role,
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": artifact_bytes,
        "content_address": f"sha256:{artifact_sha256}",
        "commitments": commitments,
        "backend": backend,
        "backend_reference": backend_reference,
        "availability": availability,
        "inline_bytes": False,
        **BOUNDARY,
    }
    return {**body, "archive_reference_root": _root(body)}


def validate_transtemporal_reference(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_REFERENCE_INVALID")
    commitments = value.get("commitments")
    if not isinstance(commitments, dict) or set(commitments) != {
            "semantic_root", "state_root", "metadata_root", "governance_root"}:
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_COMMITMENTS_INVALID")
    expected = build_transtemporal_reference(
        project_root=value.get("project_root"), artifact_role=value.get("artifact_role"),
        artifact_sha256=value.get("artifact_sha256"), artifact_bytes=value.get("artifact_bytes"),
        semantic_root=commitments.get("semantic_root"), metadata_root=commitments.get("metadata_root"),
        governance_root=commitments.get("governance_root"), backend=value.get("backend"),
        backend_reference=value.get("backend_reference"), availability=value.get("availability"))
    if value != expected:
        raise ArchivePolicyRefusal("PIPPI_ARCHIVE_REFERENCE_INVALID")
    return deepcopy(value)


def evaluate_archive_availability(*, references: list[dict[str, Any]],
                                  available_sha256: Iterable[str]) -> dict[str, Any]:
    available = set(available_sha256)
    for item in available:
        _sha(item, "PIPPI_ARCHIVE_AVAILABLE_HASH_INVALID")
    checked = [validate_transtemporal_reference(row) for row in references]
    missing = sorted({row["artifact_sha256"] for row in checked
                      if row["artifact_sha256"] not in available or
                      row["availability"] != "AVAILABLE"})
    unique = {row["artifact_sha256"]: row["artifact_bytes"] for row in checked}
    logical_bytes = sum(row["artifact_bytes"] for row in checked)
    physical_bytes = sum(unique.values())
    body = {
        "schema": ARCHIVE_AVAILABILITY_SCHEMA,
        "reference_roots": sorted(row["archive_reference_root"] for row in checked),
        "reference_count": len(checked), "unique_object_count": len(unique),
        "logical_bytes": logical_bytes, "physical_bytes": physical_bytes,
        "deduplicated_bytes": logical_bytes - physical_bytes,
        "missing_sha256": missing,
        "status": "PASS" if not missing else "HOLD_FOR_ARCHIVE_AVAILABILITY",
        **BOUNDARY,
    }
    return {**body, "availability_root": _root(body)}


def validate_release_partition(*, runtime_paths: Iterable[str], sdk_paths: Iterable[str],
                               review_paths: Iterable[str], source_paths: Iterable[str],
                               review_mode: str) -> dict[str, Any]:
    runtime, sdk, review, source = map(_paths,
        (runtime_paths, sdk_paths, review_paths, source_paths))
    if review_mode not in REVIEW_MODES:
        raise ArchivePolicyRefusal("PIPPI_REVIEW_CUSTODY_MODE_INVALID")
    for profile, rows in (("RUNTIME", runtime), ("SDK", sdk)):
        inline = [row for row in rows if is_custody_path(row)]
        if inline:
            raise ArchivePolicyRefusal("PIPPI_ACTIVE_PROFILE_INLINE_CUSTODY_REFUSED",
                                       f"{profile}:{inline[0]}")
    denominator = tuple(row for row in source if is_custody_path(row))
    if review_mode == "REFERENCE_ONLY" and review:
        raise ArchivePolicyRefusal("PIPPI_REFERENCE_ONLY_INLINE_CUSTODY_REFUSED")
    if review_mode == "SELF_CONTAINED_CUSTODY" and review != denominator:
        missing = sorted(set(denominator) - set(review))
        extra = sorted(set(review) - set(denominator))
        detail = ("MISSING:" + (missing[0] if missing else "NONE") +
                  ":EXTRA:" + (extra[0] if extra else "NONE"))
        raise ArchivePolicyRefusal("PIPPI_REVIEW_CUSTODY_DENOMINATOR_MISMATCH", detail)
    body = {
        "schema": RELEASE_PARTITION_SCHEMA, "policy_schema": ARCHIVE_POLICY_SCHEMA,
        "review_mode": review_mode, "runtime_member_count": len(runtime),
        "sdk_member_count": len(sdk), "review_member_count": len(review),
        "custody_denominator_count": len(denominator),
        "custody_prefixes": list(CUSTODY_PREFIXES), "status": "PASS", **BOUNDARY,
    }
    return {**body, "partition_root": _root(body)}
