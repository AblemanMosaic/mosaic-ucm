"""Frozen Mosaic UI 1.0-RC1 public contract and Track A independence witness."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import commitment, read_json
from .localization import SCHEMA as LOCALIZATION_SCHEMA
from .model import UIRefusal
from .realizer import PROTOCOL_SCHEMA
from mosaic_ui_std.catalog import (
    RUNTIME_CATALOG_SCHEMA,
    RUNTIME_PROFILE_CATALOG_SCHEMA,
    load_catalog,
    load_runtime_catalog,
)
from mosaic_ui_std.lifecycle import LIFECYCLE_SCHEMA


CONTRACT_SCHEMA = "mosaic.ui.public-contract.v1"
CONTRACT_ID = "MOSAIC-UI-PUBLIC-1.0-RC1"
CONTRACT_PATH = Path(__file__).resolve().parent / "source" / "public-contract-1.0-rc1.json"
DEPENDENCY_PATH = Path(__file__).resolve().parent / "components" / "dependencies.json"
RELEASE_POLICY_PATH = Path(__file__).resolve().parent / "source" / "release-policy.json"
OPTIONAL_DOMAINS = ("PLAY_2D", "PLAY_ADAPTERS", "PLAY_RUNTIME_QUALIFICATION", "SPATIAL_3D")


class PublicContractRefusal(UIRefusal):
    pass


def _pathway_closure(graph: dict[str, Any], root: str) -> list[str]:
    optional = graph.get("optional_pathways", {})
    if root not in optional:
        raise PublicContractRefusal("PUBLIC_CONTRACT_RELEASE_PATHWAY_REFUSED", root)
    resolved: set[str] = set()
    active: set[str] = set()

    def include(name: str) -> None:
        if name in resolved:
            return
        if name in active or name not in optional:
            raise PublicContractRefusal("PUBLIC_CONTRACT_DEPENDENCY_GRAPH_REFUSED", name)
        active.add(name)
        spec = optional[name]
        if not isinstance(spec, dict) or not isinstance(spec.get("requires"), list):
            raise PublicContractRefusal("PUBLIC_CONTRACT_DEPENDENCY_GRAPH_REFUSED", name)
        for dependency in spec["requires"]:
            include(str(dependency))
        active.remove(name)
        resolved.add(name)

    include(root)
    return sorted(resolved)


def public_contract_witness() -> dict[str, Any]:
    contract = read_json(CONTRACT_PATH)
    expected_keys = {
        "schema", "contract_id", "component_contract", "protocols", "compatibility",
        "release_scope", "standing", "authority_effect", "claim_boundary", "commitment",
    }
    if set(contract) != expected_keys:
        raise PublicContractRefusal(
            "PUBLIC_CONTRACT_SHAPE_REFUSED", ",".join(sorted(set(contract) ^ expected_keys)),
        )
    body = dict(contract)
    observed_commitment = body.pop("commitment", None)
    frozen = load_catalog()
    runtime = load_runtime_catalog()
    graph = read_json(DEPENDENCY_PATH)
    policy = read_json(RELEASE_POLICY_PATH)
    closure = _pathway_closure(graph, "RELEASE")
    policy_text = str(policy).upper()
    component = contract.get("component_contract", {})
    protocols = contract.get("protocols", {})
    release_scope = contract.get("release_scope", {})
    compatibility = contract.get("compatibility", {})
    checks = {
        "CONTRACT_COMMITMENT_VALID": observed_commitment
        == commitment("MOSAIC.UI.PUBLIC_CONTRACT.v1", body),
        "CONTRACT_ID_FROZEN": contract.get("schema") == CONTRACT_SCHEMA
        and contract.get("contract_id") == CONTRACT_ID,
        "AUTHORITY_NONE": contract.get("authority_effect") == "NONE",
        "EXACT_25_KIND_CATALOG": component.get("kinds")
        == [item["kind"] for item in runtime["components"]]
        and len(component.get("kinds", ())) == 25,
        "CATALOG_ROOT_BOUND": component.get("catalog_root")
        == commitment("MOSAIC.UI.STD.CATALOG.v0.1", runtime),
        "LEGACY_17_KIND_ROOT_PRESERVED": compatibility.get("legacy_catalog_root")
        == commitment("MOSAIC.UI.STD.CATALOG.v0.1", frozen),
        "STATE_MODEL_BOUND": component.get("states") == runtime["states"],
        "REALIZERS_BOUND": component.get("realizers") == runtime["realizers"],
        "CATALOG_SCHEMAS_BOUND": component.get("schema") == RUNTIME_CATALOG_SCHEMA
        and compatibility.get("application_profile_schema") == RUNTIME_PROFILE_CATALOG_SCHEMA,
        "PUBLIC_PROTOCOLS_BOUND": protocols == {
            "lifecycle": LIFECYCLE_SCHEMA,
            "localization": LOCALIZATION_SCHEMA,
            "realizer": PROTOCOL_SCHEMA,
        },
        "UNKNOWN_INPUTS_FAIL_CLOSED": compatibility.get("unknown_component_kind") == "REFUSE"
        and compatibility.get("unknown_protocol") == "REFUSE"
        and compatibility.get("breaking_change") == "NEW_CONTRACT_ID_AND_EXPLICIT_MIGRATION_REQUIRED",
        "RELEASE_PATHWAY_CLOSED": release_scope.get("pathway") == "RELEASE"
        and release_scope.get("resolved_pathways") == closure,
        "OPTIONAL_DOMAINS_EXCLUDED": release_scope.get("excluded_optional_pathways")
        == list(OPTIONAL_DOMAINS) and not set(OPTIONAL_DOMAINS) & set(closure),
        "RELEASE_POLICY_DOMAIN_INDEPENDENT": "PLAY" not in policy_text and "SPATIAL" not in policy_text,
        "TRACKS_NOT_MUTUALLY_GATING": release_scope.get("track_a_requires_track_b") is False,
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    if failures:
        raise PublicContractRefusal("PUBLIC_CONTRACT_REFUSED", ",".join(failures))
    witness = {
        "schema": "mosaic.ui.public-contract-witness.v1",
        "contract_id": CONTRACT_ID,
        "contract_commitment": observed_commitment,
        "component_count": len(runtime["components"]),
        "release_pathway": "RELEASE",
        "release_closure_pathways": closure,
        "excluded_optional_pathways": list(OPTIONAL_DOMAINS),
        "release_gate_count": len(policy.get("required_gates", ())),
        "checks": checks,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "FROZEN_1_0_RC1_CANDIDATE",
        "authority_effect": "NONE",
        "claim_boundary": "CONTRACT_FREEZE_AND_TRACK_INDEPENDENCE_DO_NOT_ESTABLISH_RELEASE_ADMISSION",
    }
    witness["commitment"] = commitment("MOSAIC.UI.PUBLIC_CONTRACT_WITNESS.v1", witness)
    return witness


__all__ = [
    "CONTRACT_ID", "CONTRACT_PATH", "CONTRACT_SCHEMA", "OPTIONAL_DOMAINS",
    "PublicContractRefusal", "public_contract_witness",
]
