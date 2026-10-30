from __future__ import annotations

from copy import deepcopy
from typing import Any

from .c_backend import generate_eligibility_c
from .canonical import exact_keys, require, root
from .eligibility import validate_problem
from .obligations import conserve, inventory


PASS_GRAPH = ("P00_CONTRACT", "P01_GOML", "P02_GSOL", "P03_MCIR", "P04_CEIR", "P05_PEIR", "P06_RESTRICTED_C", "P07_VERIFY")


def validate_contract(value: Any) -> dict[str, Any]:
    contract = exact_keys(value, {"schema", "contract_id", "operation_kind", "problem", "obligations", "resource_budget", "allowed_effects", "claim_ceiling"}, "$.contract")
    require(contract["schema"] == "ucl.op.operation_contract.v1", "CONTRACT_SCHEMA_INVALID")
    require(type(contract["contract_id"]) is str and contract["contract_id"], "CONTRACT_ID_INVALID")
    require(contract["operation_kind"] == "PURE_ELIGIBILITY", "CONTRACT_OPERATION_UNSUPPORTED")
    validate_problem(contract["problem"])
    require(contract["allowed_effects"] == [], "CONTRACT_EFFECT_FORBIDDEN")
    require(contract["claim_ceiling"] == "INFORMATION_ONLY", "CONTRACT_CLAIM_CEILING_INVALID")
    return deepcopy(contract)


def compile_contract(value: dict[str, Any]) -> dict[str, Any]:
    contract = validate_contract(value)
    contract_root = root(contract)
    stages: list[dict[str, Any]] = []
    maps: list[dict[str, Any]] = []
    source_inventory = inventory(contract["obligations"], contract_root)
    prior_inventory = source_inventory
    prior_root = contract_root
    representations = {
        "P00_CONTRACT": contract,
        "P01_GOML": {"schema": "ucl.op.goml.v1", "operation": "GRAPH_REACHABILITY", "problem": contract["problem"], "effects": []},
        "P02_GSOL": {"schema": "ucl.op.gsol.v1", "meaning": "eligible iff target is reachable through edges containing every required label", "problem": contract["problem"], "refusals": ["ELIGIBILITY_VISIT_BOUND_EXHAUSTED"], "effects": []},
        "P03_MCIR": {"schema": "ucl.op.mcir.v1", "algorithm": "BOUNDED_BFS", "problem": contract["problem"], "resources": contract["resource_budget"]},
        "P04_CEIR": {"schema": "ucl.op.ceir.v1", "proof_obligations": [item["id"] for item in contract["obligations"]], "checker": "ELIGIBILITY_WITNESS_V1"},
        "P05_PEIR": {"schema": "ucl.op.peir.v1", "required_evidence": sorted({e for item in contract["obligations"] for e in item["required_evidence"]}), "standing": "INFORMATION_ONLY"},
    }
    representations["P06_RESTRICTED_C"] = generate_eligibility_c(contract["problem"])
    representations["P07_VERIFY"] = {"schema": "ucl.op.verification_plan.v1", "checks": ["REFERENCE_RESULT", "WITNESS", "C_CORRESPONDENCE", "OBLIGATION_CONSERVATION"], "authority_effect": "NONE"}
    for index, pass_id in enumerate(PASS_GRAPH):
        representation = deepcopy(representations[pass_id])
        representation["obligation_carriers"] = [
            {"obligation_id": item["id"], "content_root": root({key: value for key, value in item.items() if key != "source_ref"})}
            for item in sorted(contract["obligations"], key=lambda row: row["id"])
        ]
        if "realization_root" in representation:
            representation["realization_root"] = root({key: item for key, item in representation.items() if key != "realization_root"})
        representations[pass_id] = representation
        representation_root = root(representation)
        target_items = []
        for item in contract["obligations"]:
            copied = deepcopy(item)
            copied["source_ref"] = f"{pass_id}:{representation_root}"
            target_items.append(copied)
        target_inventory = inventory(target_items, representation_root)
        edges = [{"from_id": item["id"], "to_ids": [item["id"]], "disposition": "PRESERVED", "edge_kind": "LOWERS" if index < 6 else "CHECKS", "evidence_refs": [representation_root], "reason": f"{pass_id} retains the named obligation"} for item in contract["obligations"]]
        mapping = conserve(prior_inventory, target_inventory, edges, pass_id=pass_id)
        stage = {"sequence": index + 1, "pass_id": pass_id, "input_root": prior_root, "output_root": representation_root, "obligation_map_root": mapping["map_root"], "status": "PASS", "effect": "NONE"}
        stages.append(stage); maps.append(mapping)
        prior_inventory, prior_root = target_inventory, representation_root
    body = {"schema": "ucl.op.compilation.v1", "contract_root": contract_root, "pass_graph": list(PASS_GRAPH), "stages": stages, "representations": representations, "source_inventory": source_inventory, "obligation_maps": maps, "final_inventory": prior_inventory, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "compilation_root": root(body)}
