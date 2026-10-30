"""Native control-plane disposition and collision checking."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


SCHEMA = "mosaic.ucm.control-plane-disposition.v0.1"
DISPOSITIONS = {"RETAIN", "ADAPT", "REPLACE_AFTER_EQUIVALENCE"}


def verify_control_plane_disposition(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "application_id", "semantic_authority",
                              "effect_executor", "identity_binding_status",
                              "jurisdiction_binding_status", "gate_namespace",
                              "native_control_planes", "standing", "authority_effect",
                              "real_a5", "g0", "root"})
    require(item["schema"] == SCHEMA, "CONTROL_PLANE_SCHEMA_INVALID")
    require(type(item["application_id"]) is str and bool(item["application_id"]),
            "CONTROL_PLANE_APPLICATION_INVALID")
    for field in ("semantic_authority", "effect_executor", "gate_namespace"):
        require(type(item[field]) is str and bool(item[field]), "CONTROL_PLANE_OWNER_INVALID")
    require(item["identity_binding_status"] in {"UNBOUND", "PROPOSED", "BOUND"},
            "CONTROL_PLANE_IDENTITY_STATUS_INVALID")
    require(item["jurisdiction_binding_status"] in {"UNBOUND", "PROPOSED", "BOUND"},
            "CONTROL_PLANE_JURISDICTION_STATUS_INVALID")
    require(item["gate_namespace"].startswith("UCM.INTEGRATION."),
            "CONTROL_PLANE_GATE_NAMESPACE_INVALID")
    require(type(item["native_control_planes"]) is list and bool(item["native_control_planes"]),
            "CONTROL_PLANE_SET_EMPTY")
    ids: set[str] = set()
    effect_owners: dict[str, list[str]] = {}
    semantic_owners = []
    for raw in item["native_control_planes"]:
        row = exact_keys(raw, {"id", "role", "disposition", "semantic_authority",
                               "effect_classes", "equivalence_evidence_root"})
        require(type(row["id"]) is str and row["id"] and row["id"] not in ids,
                "CONTROL_PLANE_ID_INVALID")
        ids.add(row["id"])
        require(type(row["role"]) is str and bool(row["role"])
                and row["disposition"] in DISPOSITIONS
                and type(row["semantic_authority"]) is bool,
                "CONTROL_PLANE_ROW_INVALID")
        require(type(row["effect_classes"]) is list
                and len(row["effect_classes"]) == len(set(row["effect_classes"]))
                and all(type(effect) is str and effect for effect in row["effect_classes"]),
                "CONTROL_PLANE_EFFECT_SET_INVALID")
        if row["semantic_authority"]:
            semantic_owners.append(row["id"])
        for effect in row["effect_classes"]:
            effect_owners.setdefault(effect, []).append(row["id"])
        if row["disposition"] == "REPLACE_AFTER_EQUIVALENCE":
            require(row["equivalence_evidence_root"] is not None
                    and require_root(row["equivalence_evidence_root"]),
                    "CONTROL_PLANE_EQUIVALENCE_EVIDENCE_REQUIRED")
        else:
            require(row["equivalence_evidence_root"] is None
                    or require_root(row["equivalence_evidence_root"]),
                    "CONTROL_PLANE_EQUIVALENCE_ROOT_INVALID")
    require(semantic_owners == [item["semantic_authority"]],
            "CONTROL_PLANE_SEMANTIC_AUTHORITY_COLLISION")
    collisions = {effect: owners for effect, owners in effect_owners.items() if len(owners) > 1}
    require(not collisions, "CONTROL_PLANE_EFFECT_EXECUTOR_COLLISION")
    require(item["effect_executor"] in ids, "CONTROL_PLANE_EFFECT_EXECUTOR_UNKNOWN")
    require(item["effect_executor"] != "UCM", "CONTROL_PLANE_UCM_EXECUTOR_REFUSED")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "root"}
    require({key: body[key] for key in BOUNDARY} == BOUNDARY,
            "CONTROL_PLANE_AUTHORITY_CEILING_INVALID")
    require(item["root"] == root(body), "CONTROL_PLANE_ROOT_MISMATCH")
    return deepcopy(item)


def make_control_plane_disposition(**fields: Any) -> dict[str, Any]:
    body = {"schema": SCHEMA, **deepcopy(fields), **BOUNDARY}
    return verify_control_plane_disposition({**body, "root": root(body)})
