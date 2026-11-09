"""Portable application constitutionalization capsule."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import require, require_root, root

from .amcas import BOUNDARY
SCHEMA = "mosaic.ucm.application-constitutionalization-capsule.v0.1"


def build_application_capsule(*, application_id: str, source_root: str,
                              amcas_plan: dict[str, Any], runtime_contract_root: str,
                              policy_pack_roots: list[str],
                              adapter_results: list[dict[str, Any]],
                              active_surfaces: list[str],
                              integration_commands: list[str]) -> dict[str, Any]:
    # Local import keeps the capsule validator usable while the integration
    # runtime imports it to bind the permit subject to the exact capsule.
    from .constitutional_runtime import validate_adapter_result
    require(type(application_id) is str and application_id and application_id == application_id.strip(),
            "CAPSULE_APPLICATION_ID_INVALID")
    require_root(source_root)
    require_root(runtime_contract_root)
    require(type(amcas_plan) is dict, "CAPSULE_AMCAS_PLAN_INVALID")
    plan_root = amcas_plan.get("plan_root") or root(amcas_plan)
    require_root(plan_root)
    require(type(policy_pack_roots) is list
            and policy_pack_roots == sorted(set(policy_pack_roots))
            and bool(policy_pack_roots), "CAPSULE_POLICY_PACKS_INVALID")
    for value in policy_pack_roots:
        require_root(value)
    adapters = sorted((validate_adapter_result(row) for row in adapter_results),
                      key=lambda row: row["adapter_id"])
    require(bool(adapters), "CAPSULE_ADAPTER_RESULTS_INVALID")
    require(type(active_surfaces) is list and active_surfaces == sorted(set(active_surfaces))
            and bool(active_surfaces)
            and all(type(row) is str and row and row == row.strip()
                    and all(ch.isalnum() or ch in "._:-" for ch in row)
                    for row in active_surfaces), "CAPSULE_SURFACES_INVALID")
    require(type(integration_commands) is list and bool(integration_commands)
            and all(type(row) is str and row.strip() == row and row for row in integration_commands),
            "CAPSULE_COMMANDS_INVALID")
    body = {"schema": SCHEMA, "application_id": application_id,
            "source_root": source_root, "amcas_plan_root": plan_root,
            "runtime_contract_root": runtime_contract_root,
            "policy_pack_roots": list(policy_pack_roots),
            "adapter_result_roots": sorted(row["adapter_result_root"] for row in adapters),
            "active_surfaces": list(active_surfaces),
            "integration_commands": list(integration_commands),
            "native_authority_preserved": True,
            "execution_authorized": False, "composition_authorized": False,
            **BOUNDARY}
    return {**body, "capsule_root": root(body)}


def validate_application_capsule(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == SCHEMA,
            "CAPSULE_SCHEMA_INVALID")
    body = {key: deepcopy(item) for key, item in value.items() if key != "capsule_root"}
    require(set(body) == {"schema", "application_id", "source_root", "amcas_plan_root",
        "runtime_contract_root", "policy_pack_roots", "adapter_result_roots",
        "active_surfaces", "integration_commands", "native_authority_preserved",
        "execution_authorized", "composition_authorized", "standing",
        "authority_effect", "real_a5", "g0"}, "CAPSULE_FIELDS_INVALID")
    for name in ("source_root", "amcas_plan_root", "runtime_contract_root"):
        require_root(body[name])
    require(type(body["application_id"]) is str and body["application_id"]
            and body["application_id"] == body["application_id"].strip(),
            "CAPSULE_APPLICATION_ID_INVALID")
    require(type(body["active_surfaces"]) is list
            and body["active_surfaces"] == sorted(set(body["active_surfaces"]))
            and bool(body["active_surfaces"])
            and all(type(row) is str and row and row == row.strip()
                    and all(ch.isalnum() or ch in "._:-" for ch in row)
                    for row in body["active_surfaces"]), "CAPSULE_SURFACES_INVALID")
    require(type(body["integration_commands"]) is list
            and bool(body["integration_commands"])
            and all(type(row) is str and row and row == row.strip()
                    for row in body["integration_commands"]),
            "CAPSULE_COMMANDS_INVALID")
    for name in ("policy_pack_roots", "adapter_result_roots"):
        require(type(body[name]) is list and body[name] == sorted(set(body[name])),
                "CAPSULE_ROOT_LIST_INVALID")
        for value_root in body[name]:
            require_root(value_root)
    require(bool(body["policy_pack_roots"]) and bool(body["adapter_result_roots"]),
            "CAPSULE_ROOT_LIST_EMPTY")
    require(body["native_authority_preserved"] is True
            and body["execution_authorized"] is False
            and body["composition_authorized"] is False
            and {key: body[key] for key in BOUNDARY} == BOUNDARY,
            "CAPSULE_AUTHORITY_CEILING_INVALID")
    require(value.get("capsule_root") == root(body), "CAPSULE_ROOT_INVALID")
    return deepcopy(value)

