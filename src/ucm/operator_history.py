"""Immutable custody for predecessor operator courts and their exact kits."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from uclop.canonical import exact_keys, require, root

from .amcas import BOUNDARY
from .pippi_portability import portable_path_key


REGISTRY_SCHEMA = "mosaic.ucm.frozen-operator-registry.v0.1"
ROW_SCHEMA = "mosaic.ucm.frozen-operator-directory.v0.1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _members(directory: Path) -> list[dict[str, Any]]:
    require(directory.is_dir(), "FROZEN_OPERATOR_DIRECTORY_MISSING",
            detail=str(directory))
    return [
        {"path": path.relative_to(directory).as_posix(),
         "sha256": _sha(path.read_bytes()), "bytes": path.stat().st_size}
        for path in sorted(directory.rglob("*"),
                           key=lambda item: portable_path_key(item, directory))
        if (path.is_file() and "__pycache__" not in path.parts
            and path.suffix.casefold() not in {".pyc", ".pyo"})
    ]


def build_frozen_operator_row(*, source_root: Path, directory: str,
                              frozen_revision: str,
                              provenance: str) -> dict[str, Any]:
    require(type(directory) is str and directory
            and not directory.startswith(("/", "\\")) and ".." not in directory,
            "FROZEN_OPERATOR_PATH_INVALID")
    require(type(frozen_revision) is str and frozen_revision.startswith("r"),
            "FROZEN_OPERATOR_REVISION_INVALID")
    require(type(provenance) is str and provenance,
            "FROZEN_OPERATOR_PROVENANCE_INVALID")
    members = _members(source_root / directory)
    require(bool(members), "FROZEN_OPERATOR_EMPTY")
    body = {
        "schema": ROW_SCHEMA, "directory": directory,
        "frozen_revision": frozen_revision, "provenance": provenance,
        "members": members, "member_count": len(members), **BOUNDARY,
    }
    return {**body, "directory_root": root(body)}


def build_frozen_operator_registry(*, source_root: Path,
                                   rows: list[dict[str, str]],
                                   successor_revision: str) -> dict[str, Any]:
    require(type(rows) is list and bool(rows),
            "FROZEN_OPERATOR_ROWS_INVALID")
    rendered = [build_frozen_operator_row(
        source_root=source_root, directory=row["directory"],
        frozen_revision=row["frozen_revision"], provenance=row["provenance"])
        for row in rows]
    require([row["directory"] for row in rendered]
            == sorted(set(row["directory"] for row in rendered)),
            "FROZEN_OPERATOR_ORDER_INVALID")
    body = {
        "schema": REGISTRY_SCHEMA, "successor_revision": successor_revision,
        "directories": rendered, "directory_count": len(rendered),
        "mutation_policy": "REFUSE_IN_PLACE_REQUIRE_NEW_SUCCESSOR_DIRECTORY",
        **BOUNDARY,
    }
    return {**body, "registry_root": root(body)}


def verify_frozen_operator_registry(*, source_root: Path,
                                    registry: Any) -> dict[str, Any]:
    item = exact_keys(registry, {
        "schema", "successor_revision", "directories", "directory_count",
        "mutation_policy", "standing", "authority_effect", "real_a5", "g0",
        "registry_root",
    })
    require(item["schema"] == REGISTRY_SCHEMA,
            "FROZEN_OPERATOR_REGISTRY_SCHEMA_INVALID")
    require(item["mutation_policy"]
            == "REFUSE_IN_PLACE_REQUIRE_NEW_SUCCESSOR_DIRECTORY",
            "FROZEN_OPERATOR_MUTATION_POLICY_INVALID")
    require(type(item["directories"]) is list
            and item["directory_count"] == len(item["directories"])
            and bool(item["directories"]),
            "FROZEN_OPERATOR_DENOMINATOR_INVALID")
    actual_rows = []
    for expected in item["directories"]:
        expected_row = exact_keys(expected, {
            "schema", "directory", "frozen_revision", "provenance",
            "members", "member_count", "standing", "authority_effect",
            "real_a5", "g0", "directory_root",
        })
        actual = build_frozen_operator_row(
            source_root=source_root, directory=expected_row["directory"],
            frozen_revision=expected_row["frozen_revision"],
            provenance=expected_row["provenance"])
        require(actual == expected_row, "FROZEN_OPERATOR_CUSTODY_MISMATCH",
                expected_row["directory"])
        actual_rows.append(actual)
    rebuilt = {
        "schema": REGISTRY_SCHEMA,
        "successor_revision": item["successor_revision"],
        "directories": actual_rows, "directory_count": len(actual_rows),
        "mutation_policy": item["mutation_policy"], **BOUNDARY,
    }
    require(item == {**rebuilt, "registry_root": root(rebuilt)},
            "FROZEN_OPERATOR_REGISTRY_ROOT_MISMATCH")
    return deepcopy(item)
