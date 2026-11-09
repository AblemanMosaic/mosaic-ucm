"""Standard component catalog: the closed set of Mosaic UI kinds and their realization tiers.

A kind is realized_by a realizer only where r012 evidence is cited. Tiers are
evidence-backed, not capability-maximal. The catalog grants no authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from mosaic_ui.canonical import commitment, read_json
from mosaic_ui.model import (
    ALL_COMPONENT_KINDS, COMPONENT_KINDS, FORBIDDEN_KEYS,
    STATES, SUCCESSOR_COMPONENT_KINDS, UIRefusal, walk,
)

CATALOG_SCHEMA = "mosaic.ui.std.catalog.v0.1"
PROFILE_CATALOG_SCHEMA = "mosaic.ui.std.catalog-profile.v0.1"
RUNTIME_CATALOG_SCHEMA = "mosaic.ui.std.catalog.v0.2"
RUNTIME_PROFILE_CATALOG_SCHEMA = "mosaic.ui.std.catalog-profile.v0.2"
RICH_DOCUMENT_CATALOG_SCHEMA = "mosaic.ui.std.catalog.v0.3-rich-document"
RICH_DOCUMENT_PROFILE_CATALOG_SCHEMA = "mosaic.ui.std.catalog-profile.v0.3-rich-document"
CATALOG_KEYS = {"schema", "catalog_id", "states", "realizers", "components", "tier_basis", "standing", "authority_effect"}
PROFILE_KEYS = {"mode", "source_catalog_root", "subject_root", "retained_kinds", "removed_kinds"}
COMPONENT_KEYS = {"component_id", "kind", "realized_by", "evidence"}
REALIZERS = ("HEADLESS", "WIN32")
RUNTIME_REALIZERS = ("HEADLESS", "BROWSER", "WIN32")
TIER_TAGS = {
    "HEADLESS": "REALIZED_HEADLESS", "BROWSER": "REALIZED_BROWSER", "WIN32": "REALIZED_WIN32",
}
DECLARED_ONLY = "DECLARED_ONLY"
DEFAULT_CATALOG = Path(__file__).resolve().parent / "catalog.json"
SUFFICIENCY_CATALOG = Path(__file__).resolve().parent / "sufficiency-catalog.json"
RICH_DOCUMENT_EXTENSION = Path(__file__).resolve().parent / "rich-document-extension.json"


def _keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def validate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(catalog, dict):
        raise UIRefusal("CATALOG_REFUSED", "CATALOG_NOT_OBJECT")
    schema = catalog.get("schema")
    profile_schema = schema in {
        PROFILE_CATALOG_SCHEMA, RUNTIME_PROFILE_CATALOG_SCHEMA,
        RICH_DOCUMENT_PROFILE_CATALOG_SCHEMA,
    }
    expected_keys = CATALOG_KEYS | ({"profile"} if profile_schema else set())
    if set(catalog) != expected_keys:
        failures.append("CATALOG_KEYS_MISMATCH:" + ",".join(sorted(set(catalog) ^ expected_keys)))
    if schema not in {
        CATALOG_SCHEMA, PROFILE_CATALOG_SCHEMA, RUNTIME_CATALOG_SCHEMA,
        RUNTIME_PROFILE_CATALOG_SCHEMA, RICH_DOCUMENT_CATALOG_SCHEMA,
        RICH_DOCUMENT_PROFILE_CATALOG_SCHEMA,
    }:
        failures.append("SCHEMA_MISMATCH")
    if tuple(catalog.get("states", ())) != STATES:
        failures.append("STATE_MODEL_MISMATCH")
    expected_realizers = RUNTIME_REALIZERS if schema in {
        RUNTIME_CATALOG_SCHEMA, RUNTIME_PROFILE_CATALOG_SCHEMA,
        RICH_DOCUMENT_CATALOG_SCHEMA, RICH_DOCUMENT_PROFILE_CATALOG_SCHEMA,
    } else REALIZERS
    if tuple(catalog.get("realizers", ())) != expected_realizers:
        failures.append("REALIZER_SET_MISMATCH")
    if catalog.get("authority_effect") != "NONE":
        failures.append("AUTHORITY_EFFECT_NOT_NONE")
    components = catalog.get("components")
    if not isinstance(components, list):
        failures.append("COMPONENTS_NOT_LIST")
        components = []
    ids: set[str] = set()
    kinds: list[str] = []
    for index, component in enumerate(components):
        if not isinstance(component, dict) or set(component) != COMPONENT_KEYS:
            failures.append(f"COMPONENT_SHAPE_INVALID:{index}")
            continue
        component_id, kind, realized_by = component["component_id"], component["kind"], component["realized_by"]
        if not isinstance(component_id, str) or not component_id or component_id in ids:
            failures.append(f"COMPONENT_ID_INVALID:{component_id}")
        ids.add(str(component_id))
        kinds.append(str(kind))
        if not isinstance(realized_by, list) or realized_by != [r for r in expected_realizers if r in realized_by] \
                or not set(realized_by) <= set(expected_realizers):
            failures.append(f"REALIZED_BY_INVALID:{kind}")
        evidence = component["evidence"]
        if not isinstance(evidence, list) or not evidence or not all(isinstance(e, str) and e for e in evidence):
            failures.append(f"EVIDENCE_REQUIRED:{kind}")
    if schema in {RICH_DOCUMENT_CATALOG_SCHEMA, RICH_DOCUMENT_PROFILE_CATALOG_SCHEMA}:
        all_kinds = set(SUCCESSOR_COMPONENT_KINDS)
    elif schema in {RUNTIME_CATALOG_SCHEMA, RUNTIME_PROFILE_CATALOG_SCHEMA}:
        all_kinds = set(ALL_COMPONENT_KINDS)
    else:
        all_kinds = set(COMPONENT_KINDS)
    expected_kinds = set(all_kinds)
    if profile_schema:
        profile = catalog.get("profile")
        if not isinstance(profile, dict) or set(profile) != PROFILE_KEYS:
            failures.append("PROFILE_SHAPE_INVALID")
        else:
            retained = profile.get("retained_kinds")
            removed = profile.get("removed_kinds")
            if profile.get("mode") != "APPLICATION_BOUND":
                failures.append("PROFILE_MODE_INVALID")
            for field in ("source_catalog_root", "subject_root"):
                value = profile.get(field)
                if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                    failures.append(f"PROFILE_COMMITMENT_INVALID:{field}")
            for field, value in (("retained_kinds", retained), ("removed_kinds", removed)):
                if not isinstance(value, list):
                    failures.append(f"PROFILE_KIND_SET_INVALID:{field}")
                elif value != sorted(set(value)):
                    failures.append(f"PROFILE_KIND_SET_INVALID:{field}")
            if isinstance(retained, list) and isinstance(removed, list):
                retained_set, removed_set = set(retained), set(removed)
                if retained_set & removed_set or retained_set | removed_set != all_kinds:
                    failures.append("PROFILE_PARTITION_INVALID")
                expected_kinds = retained_set
    # Closed catalog: exactly the kinds declared by the full or application-bound scope.
    if sorted(kinds) != sorted(expected_kinds):
        extra = sorted(set(kinds) - expected_kinds)
        missing = sorted(expected_kinds - set(kinds))
        duplicated = sorted({k for k in kinds if kinds.count(k) > 1})
        failures.append(f"KIND_SET_MISMATCH:extra={extra},missing={missing},duplicated={duplicated}")
    forbidden = sorted(set(_keys(catalog)) & FORBIDDEN_KEYS)
    if forbidden:
        failures.append("FORBIDDEN_KEYS:" + ",".join(forbidden))
    if failures:
        raise UIRefusal("CATALOG_REFUSED", ";".join(sorted(failures)))
    return {
        "schema": "mosaic.ui.std.catalog-validation.v0.1",
        "catalog_root": commitment("MOSAIC.UI.STD.CATALOG.v0.1", catalog),
        "component_count": len(components),
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    catalog = read_json(path)
    validate_catalog(catalog)
    return catalog


def load_runtime_catalog(
    base_path: Path = DEFAULT_CATALOG, extension_path: Path = SUFFICIENCY_CATALOG,
) -> dict[str, Any]:
    """Load the additive pre-1.0 catalog without changing the frozen v0.1 catalog."""
    base = load_catalog(base_path)
    if base.get("schema") in {PROFILE_CATALOG_SCHEMA, RUNTIME_PROFILE_CATALOG_SCHEMA}:
        return base
    extension = read_json(extension_path)
    if extension.get("schema") != "mosaic.ui.std.catalog-extension.v0.1" \
            or extension.get("authority_effect") != "NONE":
        raise UIRefusal("CATALOG_EXTENSION_REFUSED", "SCHEMA_OR_AUTHORITY")
    components = extension.get("components")
    if not isinstance(components, list):
        raise UIRefusal("CATALOG_EXTENSION_REFUSED", "COMPONENTS_NOT_LIST")
    expected = set(ALL_COMPONENT_KINDS) - set(COMPONENT_KINDS)
    observed = {str(item.get("kind")) for item in components if isinstance(item, dict)}
    if observed != expected:
        raise UIRefusal("CATALOG_EXTENSION_REFUSED", f"KIND_SET_MISMATCH:{sorted(observed ^ expected)}")
    upgraded = []
    for component in base["components"]:
        item = dict(component)
        item["realized_by"] = ["HEADLESS", "BROWSER", "WIN32"]
        item["evidence"] = [*item["evidence"], "browser_realizer.py: semantic DOM projection"]
        upgraded.append(item)
    catalog = {
        **base,
        "schema": RUNTIME_CATALOG_SCHEMA,
        "catalog_id": str(extension.get("catalog_id")),
        "realizers": list(RUNTIME_REALIZERS),
        "components": [*upgraded, *components],
        "tier_basis": str(extension.get("tier_basis")),
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    validate_catalog(catalog)
    return catalog


def load_rich_document_catalog(
    extension_path: Path = RICH_DOCUMENT_EXTENSION,
) -> dict[str, Any]:
    """Load the additive native-document successor without rewriting the frozen 25-kind contract."""
    base = load_runtime_catalog()
    extension = read_json(extension_path)
    if extension.get("schema") != "mosaic.ui.std.catalog-extension.rich-document.v0.1" \
            or extension.get("authority_effect") != "NONE":
        raise UIRefusal("RICH_DOCUMENT_CATALOG_EXTENSION_REFUSED", "SCHEMA_OR_AUTHORITY")
    components = extension.get("components")
    if not isinstance(components, list) or len(components) != 1 \
            or components[0].get("kind") != "RICH_DOCUMENT":
        raise UIRefusal("RICH_DOCUMENT_CATALOG_EXTENSION_REFUSED", "COMPONENT_SET")
    catalog = {
        **base,
        "schema": RICH_DOCUMENT_CATALOG_SCHEMA,
        "catalog_id": str(extension.get("catalog_id")),
        "components": [*base["components"], *components],
        "tier_basis": str(extension.get("tier_basis")),
        "standing": "LOCAL_SUCCESSOR_CANDIDATE",
        "authority_effect": "NONE",
    }
    validate_catalog(catalog)
    return catalog


def _by_kind(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {component["kind"]: component for component in catalog["components"]}


def tiers(catalog: dict[str, Any], kind: str) -> tuple[str, ...]:
    """Tier tags for a kind: REALIZED_* per realizer, or (DECLARED_ONLY,)."""
    component = _by_kind(catalog).get(kind)
    if component is None:
        raise UIRefusal("UNKNOWN_COMPONENT_KIND", kind)
    tags = tuple(TIER_TAGS[r] for r in component["realized_by"])
    return tags or (DECLARED_ONLY,)


def require_realized(catalog: dict[str, Any], kinds: Iterable[str], realizer: str) -> None:
    """Refuse unless every kind is realized by the realizer. Order-independent, deterministic detail."""
    if realizer not in tuple(catalog.get("realizers", ())):
        raise UIRefusal("UNKNOWN_REALIZER", str(realizer))
    table = _by_kind(catalog)
    kinds = sorted(set(kinds))
    unknown = [k for k in kinds if k not in table]
    if unknown:
        raise UIRefusal("UNKNOWN_COMPONENT_KIND", ";".join(unknown))
    missing = [k for k in kinds if realizer not in table[k]["realized_by"]]
    if missing:
        raise UIRefusal("KIND_NOT_REALIZED", ";".join(missing))


def check_realizable(catalog: dict[str, Any], tree: dict[str, Any], realizer: str) -> dict[str, Any]:
    """Refuse a tree if any node that requests realization has a kind the realizer does not realize.

    A node requests realization iff props.realization_key is present (the rule headless.py:25
    already uses). Unkeyed nodes are structural and are not checked for realization; their kind
    must still be a catalog kind.
    """
    if realizer not in tuple(catalog.get("realizers", ())):
        raise UIRefusal("UNKNOWN_REALIZER", str(realizer))
    table = _by_kind(catalog)
    unknown: set[str] = set()
    malformed: set[str] = set()
    missing: set[str] = set()
    keyed = structural = 0
    for item in walk(tree):
        node_id = str(item.get("node_id"))
        kind = item.get("kind")
        props = item.get("props", {})
        if not isinstance(props, dict):
            malformed.add(node_id)
            continue
        if kind not in table:
            unknown.add(f"{kind}:{node_id}")
            continue
        if props.get("realization_key"):
            keyed += 1
            if realizer not in table[kind]["realized_by"]:
                missing.add(f"{kind}:{node_id}")
        else:
            structural += 1
    if malformed:
        raise UIRefusal("PROPS_NOT_OBJECT", ";".join(sorted(malformed)))
    if unknown:
        raise UIRefusal("UNKNOWN_COMPONENT_KIND", ";".join(sorted(unknown)))
    if missing:
        raise UIRefusal("KIND_NOT_REALIZED", ";".join(sorted(missing)))
    return {
        "schema": "mosaic.ui.std.realizability.v0.1",
        "realizer": realizer,
        "keyed_nodes": keyed,
        "structural_nodes": structural,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
