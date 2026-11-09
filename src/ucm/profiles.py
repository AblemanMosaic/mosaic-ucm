"""Explicit UCM product profiles.

Profiles attenuate the public surface for a particular use.  They never add a
capability and they are not authority.  A verifier can therefore be shipped
without the authoring and operational machinery, while every profile remains
bound to the same public capability registry.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, root

from .system import BOUNDARY, capability_registry, legacy_capability_registry


PROFILE_DEFINITIONS = {
    "AUTHORING": {
        "purpose": "Construct, lint, compare, and compile governed contracts.",
        "effect_ceiling": "PURE_COMPUTATION",
        "surface_classes": ["AUTHORING", "ORIENTATION", "VERIFICATION"],
    },
    "OPERATIONAL": {
        "purpose": "Prepare and receipt externally authorized operations.",
        "effect_ceiling": "EXTERNAL_RECEIPTS_ONLY",
        "surface_classes": ["ORIENTATION", "VERIFICATION", "OPERATIONAL"],
    },
    "VERIFY_ONLY": {
        "purpose": "Verify exact artifacts, contracts, journals, and evidence read-only.",
        "effect_ceiling": "READ_ONLY",
        "surface_classes": ["ORIENTATION", "VERIFICATION"],
    },
    "COMPATIBILITY": {
        "purpose": "Run an explicitly selected predecessor surface for exact migration or replay.",
        "effect_ceiling": "PURE_COMPUTATION",
        "surface_classes": ["ORIENTATION", "LEGACY_COMPATIBILITY"],
    },
}

VERIFY_PREFIXES = ("VALIDATE_", "VERIFY_", "CHECK_", "INSPECT_", "SUMMARIZE_", "DIFF_")
VERIFY_EXACT = {
    "ORIENT", "DISCOVER_CAPABILITIES", "DISCOVER_LEGACY_CAPABILITIES", "DISCOVER_PRODUCT_PROFILES",
    "DISCOVER_C_CODING_STANDARD",
    "NEGOTIATE_FEATURE_LEVEL", "LINT_REALIZATION_CONTRACT", "LINT_AMCAS_CONTRACT",
    "TRACE_PRESERVATION", "RUN_FIELD_SMOKE", "BUILD_JOURNAL_INCLUSION_PROOF",
    "EVALUATE_CURRENT_ADMISSIBILITY", "EXPLAIN_CURRENT_ADMISSIBILITY",
    "DISCOVER_PIPPI_TURN_REQUIREMENTS", "PROJECT_PIPPI_TURN_RECORD",
    "DISCOVER_PIPPI_CMBA_BINDING", "ASSESS_PIPPI_CMBA_TURN",
}
OPERATIONAL_EXACT = {
    "ORIENT", "DISCOVER_CAPABILITIES", "DISCOVER_LEGACY_CAPABILITIES", "DISCOVER_PRODUCT_PROFILES",
    "VALIDATE_EXTERNAL_EVIDENCE", "SUMMARIZE_JOURNAL", "DIFF_JOURNALS",
    "BUILD_JOURNAL_INCLUSION_PROOF", "VERIFY_JOURNAL_INCLUSION_PROOF",
    "RUN_FIELD_SMOKE", "BUILD_OPERATIONAL_CONTRACT", "PREPARE_OPERATIONAL_GATEWAY",
    "RECORD_OPERATIONAL_DISPATCH", "RECORD_OPERATIONAL_TERMINAL",
    "FINALIZE_OPERATIONAL_TERMINAL",
    "MARK_OPERATIONAL_UNCERTAIN", "RECONCILE_OPERATIONAL_OUTCOME",
    "CANCEL_OPERATIONAL_GATEWAY", "INSPECT_OPERATIONAL_STATE",
    "BUILD_OPERATIONAL_PROOF", "EXPORT_OPERATIONAL_ARCHIVE",
    "VERIFY_OPERATIONAL_ARCHIVE", "RECOVER_OPERATIONAL_JOURNAL",
    "BUILD_ADMISSIBILITY_JURISDICTION",
    "BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER",
    "BUILD_CHC_THR_CORRESPONDENCE",
    "BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT",
    "BUILD_CURRENT_USE_SNAPSHOT", "EVALUATE_CURRENT_ADMISSIBILITY",
    "EXPLAIN_CURRENT_ADMISSIBILITY", "PREPARE_ADMISSIBILITY_BOUND_GATEWAY",
}


def _surface_sets() -> dict[str, list[str]]:
    surfaces = capability_registry()["surfaces"]
    legacy_surfaces = legacy_capability_registry()["surfaces"]
    names = {row["name"] for row in surfaces}
    authoring = sorted(row["name"] for row in surfaces
                       if row["effect_scope"] in {"PURE_COMPUTATION", "READ_ONLY"})
    verify = sorted(name for name in names
                    if name in VERIFY_EXACT or name.startswith(VERIFY_PREFIXES))
    operational = sorted(names & OPERATIONAL_EXACT)
    compatibility = sorted(
        {row["name"] for row in legacy_surfaces}
        | {"ORIENT", "DISCOVER_CAPABILITIES", "DISCOVER_LEGACY_CAPABILITIES",
           "DISCOVER_PRODUCT_PROFILES"}
    )
    return {"AUTHORING": authoring, "OPERATIONAL": operational,
            "VERIFY_ONLY": verify, "COMPATIBILITY": compatibility}


def profile_registry() -> dict[str, Any]:
    registry = capability_registry()
    selected = _surface_sets()
    body = {
        "schema": "mosaic.ucm.product-profile-registry.v0.1",
        "capability_registry_root": registry["root"],
        "profiles": [
            {"profile_id": name, **deepcopy(definition),
             "surface_names": selected[name],
             "surface_set_root": root(selected[name])}
            for name, definition in sorted(PROFILE_DEFINITIONS.items())
        ],
        "rules": [
            "PROFILE_ATTENUATES_ONLY",
            "PROFILE_DOES_NOT_GRANT_AUTHORITY",
            "UNKNOWN_SURFACE_REFUSES",
            "LEGACY_SURFACE_REQUIRES_EXPLICIT_COMPATIBILITY_PROFILE",
        ],
        **BOUNDARY,
    }
    return {**body, "profile_registry_root": root(body)}


def validate_profile_selection(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "profile_id", "capability_registry_root"})
    require(item["schema"] == "mosaic.ucm.product-profile-selection.v0.1",
            "UCM_PROFILE_SCHEMA_INVALID")
    require(item["profile_id"] in PROFILE_DEFINITIONS, "UCM_PROFILE_UNKNOWN")
    expected = profile_registry()["capability_registry_root"]
    require(item["capability_registry_root"] == expected,
            "UCM_PROFILE_REGISTRY_MISMATCH")
    definition = deepcopy(PROFILE_DEFINITIONS[item["profile_id"]])
    definition["surface_names"] = _surface_sets()[item["profile_id"]]
    definition["surface_set_root"] = root(definition["surface_names"])
    body = {**deepcopy(item), "definition": definition,
            **BOUNDARY}
    return {**body, "profile_selection_root": root(body)}


def profile_allows_surface(profile_id: str, surface_name: str) -> dict[str, Any]:
    require(profile_id in PROFILE_DEFINITIONS, "UCM_PROFILE_UNKNOWN")
    require(type(surface_name) is str and surface_name, "UCM_PROFILE_SURFACE_INVALID")
    known = ({row["name"] for row in capability_registry()["surfaces"]}
             | {row["name"] for row in legacy_capability_registry()["surfaces"]})
    require(surface_name in known, "UCM_PROFILE_SURFACE_UNKNOWN")
    allowed = surface_name in _surface_sets()[profile_id]
    body = {"schema": "mosaic.ucm.product-profile-surface-check.v0.1",
            "profile_id": profile_id, "surface_name": surface_name,
            "status": "PASS_ALLOWED" if allowed else "REFUSED_PROFILE_SURFACE",
            **BOUNDARY}
    return {**body, "check_root": root(body)}
