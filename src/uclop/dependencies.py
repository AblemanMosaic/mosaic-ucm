from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root


def build_graph(materials: list[dict[str, Any]], claims: list[dict[str, Any]], edges: list[dict[str, Any]], claim_edges: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    material_map: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(materials):
        value = exact_keys(item, {"id", "root", "kind"}, f"$.materials[{index}]")
        require(type(value["id"]) is str and value["id"] not in material_map, "MATERIAL_ID_INVALID")
        require_root(value["root"], f"$.materials[{index}].root")
        material_map[value["id"]] = deepcopy(value)
    claim_map: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(claims):
        value = exact_keys(item, {"id", "statement", "status"}, f"$.claims[{index}]")
        require(type(value["id"]) is str and value["id"] not in claim_map, "CLAIM_ID_INVALID")
        require(value["status"] in {"SUPPORTED", "HELD", "REVOKED"}, "CLAIM_STATUS_INVALID")
        claim_map[value["id"]] = deepcopy(value)
    checked_edges = []
    for index, item in enumerate(edges):
        value = exact_keys(item, {"material_id", "claim_id", "kind", "evidence_root"}, f"$.edges[{index}]")
        require(value["material_id"] in material_map and value["claim_id"] in claim_map, "DEPENDENCY_ENDPOINT_UNKNOWN")
        require(value["kind"] in {"DERIVES", "CHECKS", "SOLVES", "ENUMERATES", "ADMITS", "LOWERS"}, "DEPENDENCY_KIND_INVALID")
        require_root(value["evidence_root"], f"$.edges[{index}].evidence_root")
        checked_edges.append(deepcopy(value))
    checked_claim_edges = []
    for index, item in enumerate(claim_edges or []):
        value = exact_keys(item, {"from_claim_id", "to_claim_id", "kind", "evidence_root"}, f"$.claim_edges[{index}]")
        require(value["from_claim_id"] in claim_map and value["to_claim_id"] in claim_map, "DEPENDENCY_ENDPOINT_UNKNOWN")
        require(value["from_claim_id"] != value["to_claim_id"], "DEPENDENCY_SELF_EDGE_FORBIDDEN")
        require(value["kind"] in {"DERIVES", "CHECKS", "LOWERS", "REQUIRES"}, "DEPENDENCY_KIND_INVALID")
        require_root(value["evidence_root"], f"$.claim_edges[{index}].evidence_root")
        checked_claim_edges.append(deepcopy(value))
    body = {"schema": "ucl.op.dependency_graph.v2", "materials": sorted(material_map.values(), key=lambda x: x["id"]), "claims": sorted(claim_map.values(), key=lambda x: x["id"]), "edges": sorted(checked_edges, key=lambda x: (x["claim_id"], x["material_id"], x["kind"])), "claim_edges": sorted(checked_claim_edges, key=lambda x: (x["to_claim_id"], x["from_claim_id"], x["kind"]))}
    return {**body, "graph_root": root(body)}


def validate_graph(graph: Any) -> dict[str, Any]:
    value = exact_keys(graph, {"schema", "materials", "claims", "edges", "claim_edges", "graph_root"}, "$.graph")
    require(value["schema"] == "ucl.op.dependency_graph.v2", "DEPENDENCY_GRAPH_SCHEMA_INVALID")
    expected = build_graph(value["materials"], value["claims"], value["edges"], value["claim_edges"])
    require(value == expected, "DEPENDENCY_GRAPH_ROOT_MISMATCH")
    return expected


def assess_impact(graph: dict[str, Any], changed_material_roots: dict[str, str]) -> dict[str, Any]:
    graph = validate_graph(graph)
    materials = {item["id"]: item for item in graph["materials"]}
    changed = []
    for material_id, new_root in changed_material_roots.items():
        require(material_id in materials, "MATERIAL_UNKNOWN", detail=material_id)
        require_root(new_root, f"$.changed.{material_id}")
        if new_root != materials[material_id]["root"]:
            changed.append(material_id)
    affected = {edge["claim_id"] for edge in graph["edges"] if edge["material_id"] in changed}
    propagated = []
    while True:
        additions = [edge for edge in graph["claim_edges"] if edge["from_claim_id"] in affected and edge["to_claim_id"] not in affected]
        if not additions:
            break
        for edge in additions:
            affected.add(edge["to_claim_id"]); propagated.append(edge)
    direct = [edge for edge in graph["edges"] if edge["claim_id"] in affected and edge["material_id"] in changed]
    body = {"schema": "ucl.op.impact_assessment.v2", "graph_root": graph["graph_root"], "changed_material_roots": {key: changed_material_roots[key] for key in sorted(changed_material_roots)}, "changed_materials": sorted(changed), "affected_claims": sorted(affected), "decisive_edges": direct, "propagation_edges": sorted(propagated, key=lambda x: (x["to_claim_id"], x["from_claim_id"])), "unaffected_claims": sorted({item["id"] for item in graph["claims"]} - affected), "standing_effect": "NONE"}
    return {**body, "assessment_root": root(body)}


def recovery_plan(graph: dict[str, Any], impact: dict[str, Any]) -> dict[str, Any]:
    graph = validate_graph(graph)
    expected = assess_impact(graph, impact.get("changed_material_roots", {}))
    require(impact == expected, "IMPACT_ASSESSMENT_ROOT_MISMATCH")
    required = []
    for edge in impact["decisive_edges"]:
        required.append({"claim_id": edge["claim_id"], "material_id": edge["material_id"], "required_edge_kind": edge["kind"], "action": "REPLAY_EDGE_AND_DOWNSTREAM_CHECKS"})
    for edge in impact["propagation_edges"]:
        required.append({"claim_id": edge["to_claim_id"], "material_id": f"claim:{edge['from_claim_id']}", "required_edge_kind": edge["kind"], "action": "REPLAY_EDGE_AND_DOWNSTREAM_CHECKS"})
    body = {"schema": "ucl.op.recovery_plan.v1", "graph_root": graph["graph_root"], "impact_root": impact["assessment_root"], "required_replays": sorted(required, key=lambda x: (x["claim_id"], x["material_id"], x["required_edge_kind"])), "automatic_reinstatement": False, "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}
