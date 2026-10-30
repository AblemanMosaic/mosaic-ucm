from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .ecosystem import EFFECT_CLASSES, effect_rank, verify_capability_registry, verify_policy_bundle


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")


def _id(value: Any, code: str, path: str = "$") -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code, path)
    return value


def _topological_order(nodes: dict[str, dict[str, Any]], edges: list[dict[str, str]]) -> list[str]:
    incoming = {key: 0 for key in nodes}
    outgoing: dict[str, list[str]] = {key: [] for key in nodes}
    for edge in edges:
        source, target = edge["source"], edge["target"]
        require(source in nodes and target in nodes and source != target, "COMPOSITION_EDGE_INVALID")
        incoming[target] += 1
        outgoing[source].append(target)
    ready = sorted(key for key, count in incoming.items() if count == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for target in sorted(outgoing[node]):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
                ready.sort()
    require(len(order) == len(nodes), "COMPOSITION_CYCLE")
    return order


def compile_composition(
    *,
    subject_root: str,
    registry: dict[str, Any],
    policy: dict[str, Any],
    composition_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    data_permissions: dict[str, list[str]],
) -> dict[str, Any]:
    """Compile an application/capability DAG without granting execution authority."""
    verify_capability_registry(registry, expected_subject_root=subject_root)
    verify_policy_bundle(policy, registry=registry, expected_subject_root=subject_root)
    composition_id = _id(composition_id, "COMPOSITION_ID_INVALID", "$.composition_id")
    require(type(nodes) is list and nodes, "COMPOSITION_NODE_SET_INVALID")
    applications = {item["application_id"]: item for item in policy["applications"]}
    capabilities = {item["capability_id"]: item for item in registry["capabilities"]}
    node_map: dict[str, dict[str, Any]] = {}
    for index, candidate in enumerate(nodes):
        item = exact_keys(candidate, {"node_id", "application_id", "capability_id", "input_contract_root", "output_contract_root"}, f"$.nodes[{index}]")
        node_id = _id(item["node_id"], "COMPOSITION_NODE_ID_INVALID", f"$.nodes[{index}].node_id")
        require(node_id not in node_map, "COMPOSITION_NODE_DUPLICATE")
        require(item["application_id"] in applications, "COMPOSITION_APPLICATION_UNKNOWN")
        require(item["capability_id"] in capabilities, "COMPOSITION_CAPABILITY_UNKNOWN")
        require(item["capability_id"] in policy["grants"][item["application_id"]], "COMPOSITION_CAPABILITY_NOT_GRANTED")
        input_contract_root = require_root(item["input_contract_root"])
        output_contract_root = require_root(item["output_contract_root"])
        require(input_contract_root == capabilities[item["capability_id"]]["input_schema_root"] and output_contract_root == capabilities[item["capability_id"]]["output_schema_root"], "COMPOSITION_CAPABILITY_CONTRACT_MISMATCH")
        node_map[node_id] = {
            "node_id": node_id,
            "application_id": item["application_id"],
            "capability_id": item["capability_id"],
            "input_contract_root": input_contract_root,
            "output_contract_root": output_contract_root,
            "effect_class": capabilities[item["capability_id"]]["effect_class"],
            "minimum_stage": capabilities[item["capability_id"]]["minimum_stage"],
        }
    require([item["node_id"] for item in nodes] == sorted(node_map), "COMPOSITION_NODE_ORDER_INVALID")
    require(type(data_permissions) is dict and set(data_permissions) == set(applications), "COMPOSITION_DATA_PERMISSION_SET_INVALID")
    checked_permissions: dict[str, list[str]] = {}
    for application_id in sorted(data_permissions):
        domains = data_permissions[application_id]
        require(type(domains) is list and domains == sorted(domains) and len(domains) == len(set(domains)), "COMPOSITION_DATA_PERMISSION_INVALID")
        require(set(domains).issubset(set(applications[application_id]["data_domains"])), "COMPOSITION_DATA_PERMISSION_EXCEEDS_MANIFEST")
        checked_permissions[application_id] = list(domains)
    require(type(edges) is list, "COMPOSITION_EDGE_SET_INVALID")
    checked_edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for index, candidate in enumerate(edges):
        item = exact_keys(candidate, {"source", "target", "data_domain"}, f"$.edges[{index}]")
        source, target = item["source"], item["target"]
        require(type(source) is str and type(target) is str and source in node_map and target in node_map and source != target, "COMPOSITION_EDGE_INVALID")
        _id(item["data_domain"], "COMPOSITION_DATA_DOMAIN_INVALID")
        pair = (source, target)
        require(pair not in seen_edges, "COMPOSITION_EDGE_DUPLICATE")
        seen_edges.add(pair)
        source_app, target_app = node_map[source]["application_id"], node_map[target]["application_id"]
        require(item["data_domain"] in checked_permissions[source_app] and item["data_domain"] in checked_permissions[target_app], "COMPOSITION_DATA_FLOW_NOT_GRANTED")
        require(node_map[source]["output_contract_root"] == node_map[target]["input_contract_root"], "COMPOSITION_CONTRACT_MISMATCH")
        checked_edges.append({"source": source, "target": target, "data_domain": item["data_domain"]})
    require(checked_edges == sorted(checked_edges, key=lambda item: (item["source"], item["target"], item["data_domain"])), "COMPOSITION_EDGE_ORDER_INVALID")
    order = _topological_order(node_map, checked_edges)
    maximum_effect = max((node["effect_class"] for node in node_map.values()), key=effect_rank)
    phases: list[list[str]] = []
    depth: dict[str, int] = {}
    predecessors: dict[str, list[str]] = {key: [] for key in node_map}
    for edge in checked_edges:
        predecessors[edge["target"]].append(edge["source"])
    for node_id in order:
        depth[node_id] = 0 if not predecessors[node_id] else 1 + max(depth[value] for value in predecessors[node_id])
        while len(phases) <= depth[node_id]:
            phases.append([])
        phases[depth[node_id]].append(node_id)
    body = {
        "schema": "ucl.ucm.application_composition.v1",
        "composition_id": composition_id,
        "subject_root": require_root(subject_root),
        "registry_root": registry["registry_root"],
        "policy_root": policy["policy_root"],
        "nodes": [node_map[key] for key in sorted(node_map)],
        "edges": checked_edges,
        "data_permissions": checked_permissions,
        "topological_order": order,
        "execution_phases": phases,
        "maximum_effect_class": maximum_effect,
        "executable_nodes": sorted(key for key, value in node_map.items() if value["effect_class"] == "NONE"),
        "proposal_only_nodes": sorted(key for key, value in node_map.items() if value["effect_class"] != "NONE"),
        "automatic_effects": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "composition_root": root(body)}


def verify_composition(value: Any, *, registry: dict[str, Any], policy: dict[str, Any], expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "composition_id", "subject_root", "registry_root", "policy_root", "nodes", "edges",
        "data_permissions", "topological_order", "execution_phases", "maximum_effect_class", "executable_nodes",
        "proposal_only_nodes", "automatic_effects", "standing", "authority_effect", "composition_root",
    }, "$.composition")
    body = {key: item[key] for key in item if key != "composition_root"}
    require(item["schema"] == "ucl.ucm.application_composition.v1" and item["composition_root"] == root(body), "COMPOSITION_ROOT_INVALID")
    rebuilt = compile_composition(
        subject_root=expected_subject_root,
        registry=registry,
        policy=policy,
        composition_id=item["composition_id"],
        nodes=[{key: node[key] for key in ("node_id", "application_id", "capability_id", "input_contract_root", "output_contract_root")} for node in item["nodes"]],
        edges=item["edges"],
        data_permissions=item["data_permissions"],
    )
    require(rebuilt == item, "COMPOSITION_RECOMPUTATION_MISMATCH")
    return deepcopy(body)

