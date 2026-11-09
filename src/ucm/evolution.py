"""Feature negotiation and semantic migration receipts for UCM contracts."""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


CURRENT_FEATURE_LEVEL = 1
MINIMUM_FEATURE_LEVEL = 1
EXTENSION_ID = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")


def validate_feature_descriptor(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "minimum_feature_level", "maximum_feature_level",
        "required_features", "extensions",
    })
    require(item["schema"] == "mosaic.ucm.feature-descriptor.v0.1",
            "UCM_FEATURE_SCHEMA_INVALID")
    minimum, maximum = item["minimum_feature_level"], item["maximum_feature_level"]
    require(type(minimum) is int and type(maximum) is int
            and 1 <= minimum <= maximum, "UCM_FEATURE_RANGE_INVALID")
    require(type(item["required_features"]) is list
            and all(type(name) is str and name for name in item["required_features"])
            and len(item["required_features"]) == len(set(item["required_features"])),
            "UCM_FEATURE_SET_INVALID")
    require(type(item["extensions"]) is dict
            and all(type(name) is str and EXTENSION_ID.fullmatch(name)
                    and type(body) is dict for name, body in item["extensions"].items()),
            "UCM_EXTENSION_NAMESPACE_INVALID")
    return deepcopy(item)


def negotiate_feature_level(value: Any, *, tool_feature_level: int = CURRENT_FEATURE_LEVEL) -> dict[str, Any]:
    descriptor = validate_feature_descriptor(value)
    require(type(tool_feature_level) is int and tool_feature_level >= MINIMUM_FEATURE_LEVEL,
            "UCM_TOOL_FEATURE_LEVEL_INVALID")
    accepted = descriptor["minimum_feature_level"] <= tool_feature_level <= descriptor["maximum_feature_level"]
    body = {
        "schema": "mosaic.ucm.feature-negotiation.v0.1",
        "descriptor_root": root(descriptor),
        "tool_feature_level": tool_feature_level,
        "status": "PASS_COMPATIBLE" if accepted else "REFUSED_FEATURE_LEVEL",
        "required_features": deepcopy(descriptor["required_features"]),
        "extension_ids": sorted(descriptor["extensions"]),
        **BOUNDARY,
    }
    return {**body, "negotiation_root": root(body)}


def build_migration_receipt(*, predecessor_root: str, successor_root: str,
                            migration_id: str, semantic_changes: list[str],
                            preserved_invariants: list[str]) -> dict[str, Any]:
    require_root(predecessor_root); require_root(successor_root)
    require(predecessor_root != successor_root, "UCM_MIGRATION_ROOTS_IDENTICAL")
    require(type(migration_id) is str and migration_id, "UCM_MIGRATION_ID_INVALID")
    for values, code in ((semantic_changes, "UCM_MIGRATION_CHANGES_INVALID"),
                         (preserved_invariants, "UCM_MIGRATION_INVARIANTS_INVALID")):
        require(type(values) is list and all(type(item) is str and item for item in values)
                and len(values) == len(set(values)), code)
    body = {
        "schema": "mosaic.ucm.semantic-migration-receipt.v0.1",
        "migration_id": migration_id,
        "predecessor_root": predecessor_root,
        "successor_root": successor_root,
        "semantic_changes": sorted(semantic_changes),
        "preserved_invariants": sorted(preserved_invariants),
        "status": "RECORDED_NOT_RATIFIED",
        "non_claims": ["NOT_AN_AUTHORITY_TRANSITION", "NOT_ADOPTION", "NOT_EXECUTION"],
        **BOUNDARY,
    }
    return {**body, "migration_receipt_root": root(body)}
