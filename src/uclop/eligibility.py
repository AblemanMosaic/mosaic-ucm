from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any

from .canonical import Refusal, exact_keys, require, root
from .resources import ReservationLedger


def validate_problem(value: Any) -> dict[str, Any]:
    problem = exact_keys(value, {"schema", "nodes", "edges", "source", "target", "required_labels", "max_visits"}, "$.problem")
    require(problem["schema"] == "ucl.op.eligibility_problem.v1", "ELIGIBILITY_SCHEMA_INVALID")
    require(type(problem["nodes"]) is list and all(type(x) is str and x for x in problem["nodes"]), "ELIGIBILITY_NODES_INVALID")
    require(len(problem["nodes"]) == len(set(problem["nodes"])), "ELIGIBILITY_NODE_DUPLICATE")
    nodes = set(problem["nodes"])
    require(problem["source"] in nodes and problem["target"] in nodes, "ELIGIBILITY_ENDPOINT_UNKNOWN")
    require(type(problem["required_labels"]) is list and all(type(x) is str and x for x in problem["required_labels"]), "ELIGIBILITY_LABELS_INVALID")
    require(type(problem["max_visits"]) is int and type(problem["max_visits"]) is not bool and 1 <= problem["max_visits"] <= 4096, "ELIGIBILITY_BOUND_INVALID")
    require(type(problem["edges"]) is list, "ELIGIBILITY_EDGES_INVALID")
    seen: set[str] = set()
    for index, edge in enumerate(problem["edges"]):
        item = exact_keys(edge, {"id", "from", "to", "labels"}, f"$.problem.edges[{index}]")
        require(type(item["id"]) is str and item["id"] and item["id"] not in seen, "ELIGIBILITY_EDGE_ID_INVALID")
        seen.add(item["id"])
        require(item["from"] in nodes and item["to"] in nodes, "ELIGIBILITY_EDGE_ENDPOINT_INVALID")
        require(type(item["labels"]) is list and all(type(x) is str and x for x in item["labels"]), "ELIGIBILITY_EDGE_LABELS_INVALID")
    return deepcopy(problem)


def solve(problem_value: dict[str, Any], ledger: ReservationLedger) -> dict[str, Any]:
    problem = validate_problem(problem_value)
    problem_root = root(problem)
    required = set(problem["required_labels"])
    adjacency: dict[str, list[dict[str, Any]]] = {node: [] for node in problem["nodes"]}
    for edge in problem["edges"]:
        if required <= set(edge["labels"]):
            adjacency[edge["from"]].append(edge)
    for rows in adjacency.values():
        rows.sort(key=lambda edge: edge["id"])
    reserved = ledger.reserve({"steps": problem["max_visits"], "memory_bytes": max(1, len(problem["nodes"])) * 128, "solver_calls": 0, "tool_invocations": 0}, "eligibility.solve")
    ledger.consume(reserved["reservation_root"], {"steps": 0, "memory_bytes": max(1, len(problem["nodes"])) * 128, "solver_calls": 0, "tool_invocations": 0}, "eligibility.workspace")
    queue = deque([problem["source"]])
    predecessor: dict[str, tuple[str, str] | None] = {problem["source"]: None}
    visit_order: list[str] = []
    while queue:
        node = queue.popleft()
        visit_order.append(node)
        if len(visit_order) > problem["max_visits"]:
            ledger.release(reserved["reservation_root"], "eligibility.refused")
            raise Refusal("ELIGIBILITY_VISIT_BOUND_EXHAUSTED")
        ledger.consume(reserved["reservation_root"], {"steps": 1, "memory_bytes": 0, "solver_calls": 0, "tool_invocations": 0}, "eligibility.visit")
        if node == problem["target"]:
            edge_ids: list[str] = []
            nodes = [node]
            while predecessor[node] is not None:
                prior, edge_id = predecessor[node]
                edge_ids.append(edge_id)
                nodes.append(prior)
                node = prior
            nodes.reverse(); edge_ids.reverse()
            body = {"schema": "ucl.op.eligibility_result.v1", "problem_root": problem_root, "eligible": True, "path_nodes": nodes, "path_edges": edge_ids, "visited": visit_order, "effect": "NONE", "standing": "INFORMATION_ONLY"}
            result = {**body, "result_root": root(body)}; ledger.release(reserved["reservation_root"], "eligibility.complete"); return result
        for edge in adjacency[node]:
            target = edge["to"]
            if target not in predecessor:
                predecessor[target] = (node, edge["id"])
                queue.append(target)
    body = {"schema": "ucl.op.eligibility_result.v1", "problem_root": problem_root, "eligible": False, "path_nodes": [], "path_edges": [], "visited": visit_order, "effect": "NONE", "standing": "INFORMATION_ONLY"}
    result = {**body, "result_root": root(body)}; ledger.release(reserved["reservation_root"], "eligibility.complete"); return result


def verify_result(problem_value: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    problem = validate_problem(problem_value)
    require(type(result) is dict, "ELIGIBILITY_RESULT_OBJECT_REQUIRED")
    exact_keys(result, {"schema", "problem_root", "eligible", "path_nodes", "path_edges", "visited", "effect", "standing", "result_root"}, "$.result")
    require(result["schema"] == "ucl.op.eligibility_result.v1", "ELIGIBILITY_RESULT_SCHEMA_INVALID")
    require(type(result["eligible"]) is bool, "ELIGIBILITY_RESULT_INVALID")
    require(result.get("problem_root") == root(problem), "ELIGIBILITY_PROBLEM_ROOT_MISMATCH")
    required = set(problem["required_labels"])
    allowed = {(edge["from"], edge["to"], edge["id"]) for edge in problem["edges"] if required <= set(edge["labels"])}
    if result.get("eligible") is True:
        nodes, edges = result.get("path_nodes"), result.get("path_edges")
        require(type(nodes) is list and type(edges) is list and len(nodes) == len(edges) + 1, "ELIGIBILITY_PATH_SHAPE_INVALID")
        require(nodes[0] == problem["source"] and nodes[-1] == problem["target"], "ELIGIBILITY_PATH_ENDPOINT_INVALID")
        require(all((nodes[i], nodes[i + 1], edges[i]) in allowed for i in range(len(edges))), "ELIGIBILITY_PATH_EDGE_INVALID")
    elif result.get("eligible") is False:
        reached = {problem["source"]}
        changed = True
        while changed:
            changed = False
            for source, target, _ in sorted(allowed):
                if source in reached and target not in reached:
                    reached.add(target); changed = True
        require(problem["target"] not in reached, "ELIGIBILITY_NEGATIVE_FALSE")
        require(set(result.get("visited", [])) == reached, "ELIGIBILITY_NEGATIVE_WITNESS_INCOMPLETE")
    else:
        raise Refusal("ELIGIBILITY_RESULT_INVALID")
    require(result["result_root"] == root({key: value for key, value in result.items() if key != "result_root"}), "ELIGIBILITY_RESULT_ROOT_MISMATCH")
    body = {"schema": "ucl.op.eligibility_verification.v1", "problem_root": root(problem), "result_root": result.get("result_root"), "status": "PASS", "authority_effect": "NONE"}
    return {**body, "verification_root": root(body)}
