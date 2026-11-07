"""Typed, pure Dependency and Evidence Graph for UCM and P/PPI.

The graph is a constitutional description and evaluation layer.  It never
executes external tools, grants authority, dispatches effects, or replaces a
domain validator.  Every reusable result is bound to a complete invocation
identity and must be admitted from an independently expected predecessor.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from uclop.canonical import (canonical_bytes, exact_keys, require, require_root,
                             root, validate_value)


GRAPH_SCHEMA = "mosaic.ucm.dependency-graph.v0.1"
SNAPSHOT_SCHEMA = "mosaic.ucm.dependency-snapshot.v0.1"
DELTA_SCHEMA = "mosaic.ucm.dependency-snapshot-delta.v0.1"
EVALUATION_SCHEMA = "mosaic.ucm.dependency-evaluation.v0.1"
ADMISSION_SCHEMA = "mosaic.ucm.dependency-reuse-admission.v0.1"
IMPACT_SCHEMA = "mosaic.ucm.dependency-impact.v0.1"
PORTABLE_SCHEMA = "mosaic.ucm.dependency-portable-closure.v0.1"

NODE_KINDS = frozenset({
    "INPUT", "LITERAL", "PROJECT", "MERGE_MAPS", "CHECK_FIELD",
    "SEMANTIC_PROJECT", "PREPARE", "CURRENT_USE", "OBSERVATION",
})
EDGE_KINDS = frozenset({
    "EXACT_BYTES", "SEMANTIC_PROJECTION", "EVIDENCE", "POLICY",
    "ENVIRONMENT", "FRESHNESS", "AVAILABILITY", "PROVENANCE",
})
CLOSURE_COVERAGE = frozenset({"COMPLETE", "DECLARED", "INCOMPLETE"})
EVIDENCE_GRADES = frozenset({
    "DECLARED_INPUT", "DETERMINISTIC_DERIVATION", "EXACT_INPUT_CHECK",
    "CAPTURED_OBSERVATION", "NON_AUTHORIZING_PREPARATION",
})
REUSE_MODES = frozenset({"SHADOW_IMPACT", "VERIFIED_PURE_REUSE", "DISABLED"})
CURRENT_USE_EDGE_KINDS = frozenset({"POLICY", "FRESHNESS", "AVAILABILITY"})
HEX = frozenset("0123456789abcdef")


def _seal(body: dict[str, Any], field: str) -> dict[str, Any]:
    validate_value(body)
    return {**deepcopy(body), field: root(body)}


def _is_root(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(ch in HEX for ch in value)


def _typed_equal(left: Any, right: Any) -> bool:
    """Canonical equality; unlike Python equality, true != 1 and 1 != 1.0."""
    try:
        return canonical_bytes(left) == canonical_bytes(right)
    except Exception:
        return False


def _present(value: Any) -> dict[str, Any]:
    validate_value(value)
    return {"present": True, "value": deepcopy(value)}


def _absent() -> dict[str, Any]:
    return {"present": False}


def _validate_presence(value: Any, path: str) -> dict[str, Any]:
    require(type(value) is dict and type(value.get("present")) is bool,
            "DEPENDENCY_PRESENCE_INVALID", path)
    if value["present"]:
        exact_keys(value, {"present", "value"}, path)
        validate_value(value["value"], path + ".value")
    else:
        exact_keys(value, {"present"}, path)
    return value


def _normal_edge(edge: Any, path: str) -> dict[str, Any]:
    item = exact_keys(edge, {"node_id", "edge_kind", "required"}, path)
    require(type(item["node_id"]) is str and bool(item["node_id"]),
            "DEPENDENCY_EDGE_NODE_INVALID", path)
    require(item["edge_kind"] in EDGE_KINDS, "DEPENDENCY_EDGE_KIND_INVALID", path)
    require(type(item["required"]) is bool, "DEPENDENCY_EDGE_REQUIRED_INVALID", path)
    return {"node_id": item["node_id"], "edge_kind": item["edge_kind"],
            "required": item["required"]}


def build_graph(*, graph_id: str, nodes: list[dict[str, Any]],
                adapter_id: str, adapter_version: str,
                adapter_policy_root: str, schema_registry_root: str,
                trust_root: str, closure_claim: str = "DECLARED") -> dict[str, Any]:
    """Build a sorted, typed graph definition without executing it."""
    require(type(graph_id) is str and bool(graph_id), "DEPENDENCY_GRAPH_ID_INVALID")
    require(type(adapter_id) is str and bool(adapter_id), "DEPENDENCY_ADAPTER_ID_INVALID")
    require(type(adapter_version) is str and bool(adapter_version),
            "DEPENDENCY_ADAPTER_VERSION_INVALID")
    for value, name in ((adapter_policy_root, "adapter_policy_root"),
                        (schema_registry_root, "schema_registry_root"),
                        (trust_root, "trust_root")):
        require_root(value, "$.'" + name + "'")
    require(closure_claim in CLOSURE_COVERAGE, "DEPENDENCY_CLOSURE_CLAIM_INVALID")
    require(type(nodes) is list and bool(nodes), "DEPENDENCY_NODES_INVALID")
    normalized: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw_node in enumerate(nodes):
        path = f"$.nodes[{index}]"
        node = exact_keys(raw_node, {
            "node_id", "kind", "dependencies", "parameters", "transform_id",
            "transform_version", "semantic_contract_root", "policy_root",
            "jurisdiction_root", "environment_root", "closure_coverage",
            "evidence_grade", "pure",
        }, path)
        node_id = node["node_id"]
        require(type(node_id) is str and bool(node_id) and node_id not in identifiers,
                "DEPENDENCY_NODE_ID_INVALID", path)
        identifiers.add(node_id)
        require(node["kind"] in NODE_KINDS, "DEPENDENCY_NODE_KIND_INVALID", path)
        require(type(node["dependencies"]) is list, "DEPENDENCY_EDGES_INVALID", path)
        edges = [_normal_edge(edge, f"{path}.dependencies[{i}]")
                 for i, edge in enumerate(node["dependencies"])]
        require(len({edge["node_id"] for edge in edges}) == len(edges),
                "DEPENDENCY_EDGE_DUPLICATE", path)
        edges.sort(key=lambda item: (item["node_id"], item["edge_kind"], item["required"]))
        require(type(node["parameters"]) is dict, "DEPENDENCY_PARAMETERS_INVALID", path)
        validate_value(node["parameters"], path + ".parameters")
        require(type(node["transform_id"]) is str and bool(node["transform_id"]),
                "DEPENDENCY_TRANSFORM_ID_INVALID", path)
        require(type(node["transform_version"]) is str and bool(node["transform_version"]),
                "DEPENDENCY_TRANSFORM_VERSION_INVALID", path)
        for key in ("semantic_contract_root", "policy_root", "jurisdiction_root",
                    "environment_root"):
            require_root(node[key], path + "." + key)
        require(node["closure_coverage"] in CLOSURE_COVERAGE,
                "DEPENDENCY_NODE_CLOSURE_INVALID", path)
        require(node["evidence_grade"] in EVIDENCE_GRADES,
                "DEPENDENCY_EVIDENCE_GRADE_INVALID", path)
        require(type(node["pure"]) is bool, "DEPENDENCY_PURITY_INVALID", path)
        if node["kind"] in {"INPUT", "LITERAL"}:
            require(not edges, "DEPENDENCY_SOURCE_HAS_EDGES", path)
        if node["kind"] == "OBSERVATION":
            require(not node["pure"], "DEPENDENCY_OBSERVATION_CANNOT_BE_PURE", path)
        definition_body = {
            "node_id": node_id, "kind": node["kind"], "dependencies": edges,
            "parameters": deepcopy(node["parameters"]),
            "transform_id": node["transform_id"],
            "transform_version": node["transform_version"],
            "semantic_contract_root": node["semantic_contract_root"],
            "policy_root": node["policy_root"],
            "jurisdiction_root": node["jurisdiction_root"],
            "environment_root": node["environment_root"],
            "closure_coverage": node["closure_coverage"],
            "evidence_grade": node["evidence_grade"], "pure": node["pure"],
        }
        normalized.append({**definition_body, "definition_root": root(definition_body)})
    normalized.sort(key=lambda item: item["node_id"])
    by_id = {node["node_id"]: node for node in normalized}
    for node in normalized:
        for edge in node["dependencies"]:
            require(edge["node_id"] in by_id, "DEPENDENCY_EDGE_TARGET_MISSING",
                    f"$.nodes.{node['node_id']}", edge["node_id"])
    _topological(normalized)
    body = {
        "schema": GRAPH_SCHEMA, "graph_id": graph_id, "adapter_id": adapter_id,
        "adapter_version": adapter_version, "adapter_policy_root": adapter_policy_root,
        "schema_registry_root": schema_registry_root, "trust_root": trust_root,
        "closure_claim": closure_claim, "nodes": normalized,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    return _seal(body, "graph_root")


def verify_graph(graph: Any) -> dict[str, Any]:
    require(type(graph) is dict and graph.get("schema") == GRAPH_SCHEMA,
            "DEPENDENCY_GRAPH_INVALID")
    expected = graph.get("graph_root")
    require(_is_root(expected) and expected == root({k: v for k, v in graph.items()
                                                     if k != "graph_root"}),
            "DEPENDENCY_GRAPH_ROOT_MISMATCH")
    rebuilt = build_graph(
        graph_id=graph["graph_id"],
        nodes=[{k: deepcopy(v) for k, v in node.items() if k != "definition_root"}
               for node in graph["nodes"]],
        adapter_id=graph["adapter_id"], adapter_version=graph["adapter_version"],
        adapter_policy_root=graph["adapter_policy_root"],
        schema_registry_root=graph["schema_registry_root"], trust_root=graph["trust_root"],
        closure_claim=graph["closure_claim"],
    )
    require(rebuilt == graph, "DEPENDENCY_GRAPH_REBUILD_MISMATCH")
    return {"schema": "mosaic.ucm.dependency-graph-verification.v0.1",
            "status": "PASS", "graph_root": expected,
            "node_count": len(graph["nodes"]),
            "closure_claim": graph["closure_claim"],
            "authority_effect": "NONE"}


def _topological(nodes: list[dict[str, Any]]) -> list[str]:
    dependencies = {node["node_id"]: {edge["node_id"] for edge in node["dependencies"]}
                    for node in nodes}
    ready = sorted(node_id for node_id, deps in dependencies.items() if not deps)
    result: list[str] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for node_id in sorted(dependencies):
            if current in dependencies[node_id]:
                dependencies[node_id].remove(current)
                if not dependencies[node_id] and node_id not in result and node_id not in ready:
                    ready.append(node_id)
                    ready.sort()
    require(len(result) == len(nodes), "DEPENDENCY_GRAPH_CYCLE")
    return result


def build_snapshot(*, graph: dict[str, Any], snapshot_id: str,
                   inputs: list[dict[str, Any]], predecessor_snapshot_root: str | None,
                   observed_at_ns: int | None = None) -> dict[str, Any]:
    verify_graph(graph)
    require(type(snapshot_id) is str and bool(snapshot_id), "DEPENDENCY_SNAPSHOT_ID_INVALID")
    if predecessor_snapshot_root is not None:
        require_root(predecessor_snapshot_root, "$.predecessor_snapshot_root")
    if observed_at_ns is not None:
        require(type(observed_at_ns) is int and observed_at_ns >= 0,
                "DEPENDENCY_OBSERVED_TIME_INVALID")
    input_ids = {node["node_id"] for node in graph["nodes"] if node["kind"] == "INPUT"}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(inputs):
        path = f"$.inputs[{index}]"
        item = exact_keys(row, {"node_id", "presence"}, path)
        require(item["node_id"] in input_ids and item["node_id"] not in seen,
                "DEPENDENCY_SNAPSHOT_INPUT_INVALID", path)
        seen.add(item["node_id"])
        normalized.append({"node_id": item["node_id"],
                           "presence": deepcopy(_validate_presence(item["presence"], path + ".presence"))})
    require(seen == input_ids, "DEPENDENCY_SNAPSHOT_INPUT_SET_MISMATCH",
            detail=",".join(sorted(input_ids - seen)))
    normalized.sort(key=lambda item: item["node_id"])
    body = {
        "schema": SNAPSHOT_SCHEMA, "snapshot_id": snapshot_id,
        "graph_root": graph["graph_root"],
        "predecessor_snapshot_root": predecessor_snapshot_root,
        "observed_at_ns": observed_at_ns, "inputs": normalized,
        "input_map_root": root(normalized),
    }
    return _seal(body, "snapshot_root")


def verify_snapshot(snapshot: Any, graph: dict[str, Any]) -> dict[str, Any]:
    verify_graph(graph)
    require(type(snapshot) is dict and snapshot.get("schema") == SNAPSHOT_SCHEMA,
            "DEPENDENCY_SNAPSHOT_INVALID")
    require(snapshot.get("graph_root") == graph["graph_root"],
            "DEPENDENCY_SNAPSHOT_GRAPH_MISMATCH")
    require(snapshot.get("input_map_root") == root(snapshot.get("inputs")),
            "DEPENDENCY_SNAPSHOT_INPUT_ROOT_MISMATCH")
    expected = snapshot.get("snapshot_root")
    require(_is_root(expected) and expected == root({k: v for k, v in snapshot.items()
                                                     if k != "snapshot_root"}),
            "DEPENDENCY_SNAPSHOT_ROOT_MISMATCH")
    build_snapshot(graph=graph, snapshot_id=snapshot["snapshot_id"],
                   inputs=snapshot["inputs"],
                   predecessor_snapshot_root=snapshot["predecessor_snapshot_root"],
                   observed_at_ns=snapshot["observed_at_ns"])
    return {"schema": "mosaic.ucm.dependency-snapshot-verification.v0.1",
            "status": "PASS", "snapshot_root": expected,
            "input_map_root": snapshot["input_map_root"]}


def apply_snapshot_delta(*, graph: dict[str, Any], predecessor: dict[str, Any],
                         expected_predecessor_root: str, delta_id: str,
                         updates: list[dict[str, Any]], snapshot_id: str,
                         observed_at_ns: int | None = None) -> dict[str, Any]:
    verify_snapshot(predecessor, graph)
    require_root(expected_predecessor_root, "$.expected_predecessor_root")
    require(predecessor["snapshot_root"] == expected_predecessor_root,
            "DEPENDENCY_PREDECESSOR_ROOT_MISMATCH")
    require(type(delta_id) is str and bool(delta_id), "DEPENDENCY_DELTA_ID_INVALID")
    values = {row["node_id"]: deepcopy(row["presence"]) for row in predecessor["inputs"]}
    seen: set[str] = set()
    for index, update in enumerate(updates):
        item = exact_keys(update, {"node_id", "presence"}, f"$.updates[{index}]")
        require(item["node_id"] in values and item["node_id"] not in seen,
                "DEPENDENCY_DELTA_INPUT_INVALID", f"$.updates[{index}]")
        seen.add(item["node_id"])
        values[item["node_id"]] = deepcopy(_validate_presence(
            item["presence"], f"$.updates[{index}].presence"))
    delta_body = {"schema": DELTA_SCHEMA, "delta_id": delta_id,
                  "graph_root": graph["graph_root"],
                  "predecessor_snapshot_root": expected_predecessor_root,
                  "updates": sorted(deepcopy(updates), key=lambda row: row["node_id"])}
    successor = build_snapshot(
        graph=graph, snapshot_id=snapshot_id,
        inputs=[{"node_id": node_id, "presence": values[node_id]}
                for node_id in sorted(values)],
        predecessor_snapshot_root=expected_predecessor_root,
        observed_at_ns=observed_at_ns,
    )
    return {"delta": _seal(delta_body, "delta_root"), "snapshot": successor}


def _project(value: Any, field_path: list[str]) -> dict[str, Any]:
    current = value
    for field in field_path:
        if type(current) is not dict or field not in current:
            return _absent()
        current = current[field]
    return _present(current)


def _edge_identity(edge: dict[str, Any], result: dict[str, Any]) -> str:
    if edge["edge_kind"] == "SEMANTIC_PROJECTION":
        return result["semantic_root"]
    if edge["edge_kind"] == "PROVENANCE":
        return result["derivation_receipt_root"]
    return result["output_root"]


def _evaluate_node(node: dict[str, Any], dependency_results: list[tuple[dict[str, Any], dict[str, Any]]],
                   snapshot_map: dict[str, dict[str, Any]], now_ns: int | None) -> tuple[dict[str, Any], str, list[str]]:
    kind, parameters = node["kind"], node["parameters"]
    if kind == "INPUT":
        presence = deepcopy(snapshot_map[node["node_id"]])
        return presence, "PASS" if presence["present"] else "BLOCKED_ABSENT_INPUT", ([] if presence["present"] else ["REQUIRED_INPUT_ABSENT"])
    if kind == "LITERAL":
        require("value" in parameters, "DEPENDENCY_LITERAL_VALUE_MISSING", node["node_id"])
        return _present(parameters["value"]), "PASS", []
    required_blocked = [result for edge, result in dependency_results
                        if edge["required"] and result["status"] != "PASS"]
    if required_blocked:
        return _absent(), "BLOCKED_PREREQUISITE", sorted({code for result in required_blocked
                                                            for code in result["reason_codes"]} or {"PREREQUISITE_NOT_PASS"})
    present_values = [(edge, result["value"]) for edge, result in dependency_results
                      if result["value_present"]]
    if kind in {"PROJECT", "SEMANTIC_PROJECT"}:
        require(len(present_values) == 1, "DEPENDENCY_PROJECT_ARITY_INVALID", node["node_id"])
        field_path = parameters.get("field_path")
        require(type(field_path) is list and all(type(item) is str and item for item in field_path),
                "DEPENDENCY_PROJECT_PATH_INVALID", node["node_id"])
        projected = _project(present_values[0][1], field_path)
        return projected, "PASS" if projected["present"] else "BLOCKED_MISSING_FIELD", ([] if projected["present"] else ["PROJECTED_FIELD_MISSING"])
    if kind == "MERGE_MAPS":
        merged: dict[str, Any] = {}
        for _edge, value in present_values:
            require(type(value) is dict, "DEPENDENCY_MERGE_INPUT_INVALID", node["node_id"])
            for key in sorted(value):
                if key in merged:
                    require(_typed_equal(merged[key], value[key]),
                            "DEPENDENCY_MERGE_CONFLICT", node["node_id"], key)
                else:
                    merged[key] = deepcopy(value[key])
        return _present(merged), "PASS", []
    if kind == "CHECK_FIELD":
        require(len(present_values) == 1, "DEPENDENCY_CHECK_ARITY_INVALID", node["node_id"])
        field_path = parameters.get("field_path")
        require(type(field_path) is list and all(type(item) is str and item for item in field_path),
                "DEPENDENCY_CHECK_PATH_INVALID", node["node_id"])
        actual = _project(present_values[0][1], field_path)
        expected_presence = _validate_presence(parameters.get("expected"), node["node_id"] + ".expected")
        passed = _typed_equal(actual, expected_presence)
        value = {"passed": passed, "actual": actual, "expected": expected_presence}
        return _present(value), "PASS" if passed else "BLOCKED_CHECK_FAILED", ([] if passed else [parameters.get("reason_code", "CHECK_FIELD_MISMATCH")])
    if kind == "CURRENT_USE":
        require(len(present_values) == 1 and type(present_values[0][1]) is dict,
                "DEPENDENCY_CURRENT_USE_INPUT_INVALID", node["node_id"])
        evidence = present_values[0][1]
        require(type(now_ns) is int and now_ns >= 0, "DEPENDENCY_NOW_REQUIRED", node["node_id"])
        codes: list[str] = []
        if evidence.get("revoked") is True:
            codes.append("EVIDENCE_REVOKED")
        expires = evidence.get("expires_at_ns")
        if type(expires) is int and now_ns > expires:
            codes.append("EVIDENCE_EXPIRED")
        expected_checkpoint = parameters.get("expected_checkpoint_root")
        if expected_checkpoint is not None and evidence.get("checkpoint_root") != expected_checkpoint:
            codes.append("CHECKPOINT_MISMATCH")
        return _present({"current": not codes, "evaluated_at_ns": now_ns,
                         "evidence_root": root(evidence), "reason_codes": sorted(codes)}), \
               "PASS" if not codes else "BLOCKED_CURRENT_USE", sorted(codes)
    if kind == "OBSERVATION":
        require(len(present_values) == 1, "DEPENDENCY_OBSERVATION_ARITY_INVALID", node["node_id"])
        return _present({"mode": "RECORDED_RETRIEVAL", "observation": deepcopy(present_values[0][1]),
                         "fresh_execution": False, "hidden_reasoning_observed": False}), "PASS", []
    if kind == "PREPARE":
        payload = {edge["node_id"]: deepcopy(result["value"]) for edge, result in dependency_results
                   if result["value_present"]}
        return _present({"preparation_id": parameters.get("preparation_id", node["node_id"]),
                         "inputs": payload, "execution_authorized": False,
                         "dispatch_authorized": False, "authority_effect": "NONE"}), "PASS", []
    raise AssertionError(kind)


def _verify_evaluation_shape(value: Any, graph: dict[str, Any], snapshot: dict[str, Any]) -> None:
    require(type(value) is dict and value.get("schema") == EVALUATION_SCHEMA,
            "DEPENDENCY_EVALUATION_INVALID")
    require(value.get("graph_root") == graph["graph_root"] and
            value.get("snapshot_root") == snapshot["snapshot_root"],
            "DEPENDENCY_EVALUATION_BOUNDARY_MISMATCH")
    expected = value.get("evaluation_root")
    require(_is_root(expected) and expected == root({k: v for k, v in value.items()
                                                     if k != "evaluation_root"}),
            "DEPENDENCY_EVALUATION_ROOT_MISMATCH")
    require([row["node_id"] for row in value.get("results", [])] ==
            sorted(node["node_id"] for node in graph["nodes"]),
            "DEPENDENCY_EVALUATION_DENOMINATOR_MISMATCH")


def build_reuse_admission(*, graph: dict[str, Any], snapshot: dict[str, Any],
                          prior_graph: dict[str, Any], prior_snapshot: dict[str, Any],
                          prior_evaluation: dict[str, Any],
                          expected_prior_evaluation_root: str,
                          expected_producer_root: str,
                          producer_receipt: dict[str, Any],
                          consumer_trust_root: str,
                          admitted_evidence_grades: list[str],
                          reuse_mode: str) -> dict[str, Any]:
    verify_snapshot(snapshot, graph)
    verify_snapshot(prior_snapshot, prior_graph)
    require_root(expected_prior_evaluation_root, "$.expected_prior_evaluation_root")
    require_root(expected_producer_root, "$.expected_producer_root")
    require_root(consumer_trust_root, "$.consumer_trust_root")
    require(reuse_mode in REUSE_MODES, "DEPENDENCY_REUSE_MODE_INVALID")
    _verify_evaluation_shape(prior_evaluation, prior_graph, prior_snapshot)
    require(prior_evaluation["evaluation_root"] == expected_prior_evaluation_root,
            "DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED")
    require(type(producer_receipt) is dict and producer_receipt.get("producer_root") == expected_producer_root,
            "DEPENDENCY_PRODUCER_RECEIPT_UNEXPECTED")
    receipt_body = {k: v for k, v in producer_receipt.items() if k != "receipt_root"}
    require(producer_receipt.get("receipt_root") == root(receipt_body),
            "DEPENDENCY_PRODUCER_RECEIPT_INVALID")
    require(producer_receipt.get("evaluation_root") == expected_prior_evaluation_root and
            producer_receipt.get("graph_root") == prior_graph["graph_root"] and
            producer_receipt.get("snapshot_root") == prior_snapshot["snapshot_root"],
            "DEPENDENCY_PRODUCER_BINDING_MISMATCH")
    grades = sorted(set(admitted_evidence_grades))
    require(grades and all(grade in EVIDENCE_GRADES for grade in grades),
            "DEPENDENCY_ADMITTED_GRADES_INVALID")
    body = {"schema": ADMISSION_SCHEMA, "graph_root": graph["graph_root"],
            "snapshot_root": snapshot["snapshot_root"],
            "prior_graph_root": prior_graph["graph_root"],
            "prior_snapshot_root": prior_snapshot["snapshot_root"],
            "prior_evaluation_root": expected_prior_evaluation_root,
            "producer_root": expected_producer_root,
            "producer_receipt_root": producer_receipt["receipt_root"],
            "consumer_trust_root": consumer_trust_root,
            "admitted_evidence_grades": grades, "reuse_mode": reuse_mode,
            "authority_effect": "NONE", "current_authority_reuse": False}
    return _seal(body, "admission_root")


def validate_reuse_admission(*, admission: dict[str, Any],
                             graph: dict[str, Any], snapshot: dict[str, Any],
                             prior_evaluation: dict[str, Any],
                             expected_prior_evaluation_root: str,
                             expected_producer_root: str,
                             expected_producer_receipt_root: str,
                             expected_consumer_trust_root: str,
                             expected_reuse_mode: str) -> dict[str, Any]:
    """Recheck admission custody at the point where reuse would occur.

    An admission is self-rooted data.  Its root proves internal consistency,
    but cannot establish which prior evaluation, producer, producer receipt,
    or consumer trust root the caller intended to admit.  Those expected
    anchors therefore enter independently at every use.
    """
    verify_snapshot(snapshot, graph)
    require_root(expected_prior_evaluation_root,
                 "$.expected_prior_evaluation_root")
    require_root(expected_producer_root, "$.expected_producer_root")
    require_root(expected_producer_receipt_root,
                 "$.expected_producer_receipt_root")
    require_root(expected_consumer_trust_root,
                 "$.expected_consumer_trust_root")
    require(expected_reuse_mode in REUSE_MODES,
            "DEPENDENCY_REUSE_MODE_INVALID")
    require(type(prior_evaluation) is dict
            and prior_evaluation.get("schema") == EVALUATION_SCHEMA
            and prior_evaluation.get("evaluation_root")
            == root({k: v for k, v in prior_evaluation.items()
                     if k != "evaluation_root"}),
            "DEPENDENCY_PRIOR_EVALUATION_INVALID")
    require(prior_evaluation["evaluation_root"]
            == expected_prior_evaluation_root,
            "DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED_AT_USE")
    require(type(admission) is dict
            and admission.get("schema") == ADMISSION_SCHEMA,
            "DEPENDENCY_ADMISSION_INVALID")
    admission_root = admission.get("admission_root")
    require(_is_root(admission_root)
            and admission_root == root({k: v for k, v in admission.items()
                                        if k != "admission_root"}),
            "DEPENDENCY_ADMISSION_ROOT_MISMATCH")
    require(admission.get("graph_root") == graph["graph_root"]
            and admission.get("snapshot_root") == snapshot["snapshot_root"],
            "DEPENDENCY_ADMISSION_BINDING_MISMATCH")
    require(admission.get("prior_evaluation_root")
            == expected_prior_evaluation_root,
            "DEPENDENCY_ADMISSION_PRIOR_UNEXPECTED_AT_USE")
    require(admission.get("producer_root") == expected_producer_root,
            "DEPENDENCY_ADMISSION_PRODUCER_UNEXPECTED_AT_USE")
    require(admission.get("producer_receipt_root")
            == expected_producer_receipt_root,
            "DEPENDENCY_ADMISSION_RECEIPT_UNEXPECTED_AT_USE")
    require(admission.get("consumer_trust_root")
            == expected_consumer_trust_root,
            "DEPENDENCY_ADMISSION_TRUST_UNEXPECTED_AT_USE")
    require(admission.get("reuse_mode") == expected_reuse_mode,
            "DEPENDENCY_ADMISSION_MODE_MISMATCH")
    return deepcopy(admission)


def evaluate_graph(*, graph: dict[str, Any], snapshot: dict[str, Any],
                   target_ids: list[str] | None = None, now_ns: int | None = None,
                   prior_evaluation: dict[str, Any] | None = None,
                   reuse_admission: dict[str, Any] | None = None,
                   expected_prior_evaluation_root: str | None = None,
                   expected_producer_root: str | None = None,
                   expected_producer_receipt_root: str | None = None,
                   expected_consumer_trust_root: str | None = None,
                   mode: str = "SHADOW_IMPACT") -> dict[str, Any]:
    verify_snapshot(snapshot, graph)
    require(mode in REUSE_MODES, "DEPENDENCY_REUSE_MODE_INVALID")
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    targets = sorted(nodes if target_ids is None else set(target_ids))
    require(targets and all(target in nodes for target in targets), "DEPENDENCY_TARGET_INVALID")
    required: set[str] = set()
    pending = list(targets)
    while pending:
        current = pending.pop()
        if current in required:
            continue
        required.add(current)
        pending.extend(edge["node_id"] for edge in nodes[current]["dependencies"])
    prior_by_id: dict[str, dict[str, Any]] = {}
    admission_root: str | None = None
    if prior_evaluation is not None or reuse_admission is not None:
        require(prior_evaluation is not None and reuse_admission is not None,
                "DEPENDENCY_REUSE_PAIR_REQUIRED")
        require(all(value is not None for value in (
                    expected_prior_evaluation_root, expected_producer_root,
                    expected_producer_receipt_root,
                    expected_consumer_trust_root)),
                "DEPENDENCY_REUSE_EXPECTED_ANCHORS_REQUIRED")
        validated_admission = validate_reuse_admission(
            admission=reuse_admission, graph=graph, snapshot=snapshot,
            prior_evaluation=prior_evaluation,
            expected_prior_evaluation_root=expected_prior_evaluation_root,
            expected_producer_root=expected_producer_root,
            expected_producer_receipt_root=expected_producer_receipt_root,
            expected_consumer_trust_root=expected_consumer_trust_root,
            expected_reuse_mode=mode)
        admission_root = reuse_admission.get("admission_root")
        prior_by_id = {row["node_id"]: row for row in prior_evaluation["results"]}
        reuse_admission = validated_admission
    else:
        require(all(value is None for value in (
                    expected_prior_evaluation_root, expected_producer_root,
                    expected_producer_receipt_root,
                    expected_consumer_trust_root)),
                "DEPENDENCY_REUSE_ANCHORS_WITHOUT_REUSE")
    snapshot_map = {row["node_id"]: row["presence"] for row in snapshot["inputs"]}
    results: dict[str, dict[str, Any]] = {}
    order = _topological(graph["nodes"])
    for node_id in order:
        if node_id not in required:
            continue
        node = nodes[node_id]
        dependencies = [(edge, results[edge["node_id"]]) for edge in node["dependencies"]]
        invocation_body = {
            "definition_root": node["definition_root"],
            "snapshot_root": snapshot["snapshot_root"] if node["kind"] == "INPUT" else None,
            "dependency_identities": [
                {"node_id": edge["node_id"], "edge_kind": edge["edge_kind"],
                 "identity_root": _edge_identity(edge, result)}
                for edge, result in dependencies
            ],
            "adapter_policy_root": graph["adapter_policy_root"],
            "schema_registry_root": graph["schema_registry_root"],
            "trust_root": graph["trust_root"],
            "now_ns": now_ns if node["kind"] == "CURRENT_USE" else None,
        }
        invocation_root = root(invocation_body)
        prior = prior_by_id.get(node_id)
        current_use_dependent = node["kind"] == "CURRENT_USE" or any(
            edge["edge_kind"] in CURRENT_USE_EDGE_KINDS for edge in node["dependencies"])
        can_reuse = (
            mode == "VERIFIED_PURE_REUSE" and prior is not None and node["pure"]
            and not current_use_dependent
            and graph["closure_claim"] == "COMPLETE"
            and node["closure_coverage"] == "COMPLETE"
            and prior.get("invocation_root") == invocation_root
            and prior.get("evidence_grade") in reuse_admission["admitted_evidence_grades"]
            and prior.get("status") == "PASS"
        )
        if can_reuse:
            row = deepcopy(prior)
            row["evaluation_action"] = "REUSED_VERIFIED"
            row["admission_root"] = admission_root
            row["result_root"] = root({k: v for k, v in row.items() if k != "result_root"})
            results[node_id] = row
            continue
        presence, status, reason_codes = _evaluate_node(node, dependencies, snapshot_map, now_ns)
        value_present = presence["present"]
        value = deepcopy(presence.get("value")) if value_present else None
        output_body = {"present": value_present, "value": value}
        output_root = root(output_body)
        semantic_root = root({"semantic_contract_root": node["semantic_contract_root"],
                              "present": value_present, "value": value})
        derivation_body = {
            "node_id": node_id, "definition_root": node["definition_root"],
            "invocation_root": invocation_root, "output_root": output_root,
            "semantic_root": semantic_root, "status": status,
            "reason_codes": sorted(reason_codes), "evidence_grade": node["evidence_grade"],
            "dependency_receipt_roots": [result["derivation_receipt_root"]
                                         for _edge, result in dependencies],
            "authority_effect": "NONE",
        }
        receipt_root = root(derivation_body)
        row_body = {
            "node_id": node_id, "definition_root": node["definition_root"],
            "invocation_root": invocation_root, "output_root": output_root,
            "semantic_root": semantic_root, "derivation_receipt_root": receipt_root,
            "status": status, "reason_codes": sorted(reason_codes),
            "evidence_grade": node["evidence_grade"],
            "closure_coverage": node["closure_coverage"],
            "value_present": value_present, "value": value,
            "evaluation_action": "EVALUATED",
            "admission_root": None,
        }
        results[node_id] = {**row_body, "result_root": root(row_body)}
    ordered = [results[node_id] for node_id in sorted(results)]
    body = {
        "schema": EVALUATION_SCHEMA, "graph_root": graph["graph_root"],
        "snapshot_root": snapshot["snapshot_root"], "target_ids": targets,
        "mode": mode, "now_ns": now_ns, "admission_root": admission_root,
        "results": ordered,
        "partitions": {
            "evaluated": [row["node_id"] for row in ordered if row["evaluation_action"] == "EVALUATED"],
            "reused": [row["node_id"] for row in ordered if row["evaluation_action"] == "REUSED_VERIFIED"],
            "blocked": [row["node_id"] for row in ordered if row["status"] != "PASS"],
        },
        "status": "PASS" if all(results[target]["status"] == "PASS" for target in targets)
                  else "BLOCKED",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "execution_performed": False, "real_a5": False, "g0": "CLOSED",
    }
    return _seal(body, "evaluation_root")


def verify_evaluation(*, graph: dict[str, Any], snapshot: dict[str, Any],
                      evaluation: dict[str, Any], now_ns: int | None = None) -> dict[str, Any]:
    _verify_evaluation_shape(evaluation, graph, snapshot)
    rebuilt = evaluate_graph(graph=graph, snapshot=snapshot,
                             target_ids=evaluation["target_ids"], now_ns=now_ns,
                             mode="SHADOW_IMPACT")
    for left, right in zip(evaluation["results"], rebuilt["results"]):
        require(left["node_id"] == right["node_id"] and
                left["output_root"] == right["output_root"] and
                left["semantic_root"] == right["semantic_root"] and
                left["status"] == right["status"],
                "DEPENDENCY_EVALUATION_REBUILD_MISMATCH", left["node_id"])
    return {"schema": "mosaic.ucm.dependency-evaluation-verification.v0.1",
            "status": "PASS", "evaluation_root": evaluation["evaluation_root"],
            "target_ids": deepcopy(evaluation["target_ids"]),
            "authority_effect": "NONE"}


def compare_evaluations(*, graph: dict[str, Any], before: dict[str, Any],
                        after: dict[str, Any]) -> dict[str, Any]:
    verify_graph(graph)
    require(before.get("graph_root") == graph["graph_root"] and
            after.get("graph_root") == graph["graph_root"],
            "DEPENDENCY_DIFF_GRAPH_MISMATCH")
    before_map = {row["node_id"]: row for row in before["results"]}
    after_map = {row["node_id"]: row for row in after["results"]}
    require(set(before_map) == set(after_map), "DEPENDENCY_DIFF_DENOMINATOR_MISMATCH")
    changed_output = sorted(node_id for node_id in before_map
                            if before_map[node_id]["output_root"] != after_map[node_id]["output_root"])
    changed_semantic = sorted(node_id for node_id in before_map
                              if before_map[node_id]["semantic_root"] != after_map[node_id]["semantic_root"])
    changed_receipt = sorted(node_id for node_id in before_map
                             if before_map[node_id]["derivation_receipt_root"] != after_map[node_id]["derivation_receipt_root"])
    body = {"schema": IMPACT_SCHEMA, "graph_root": graph["graph_root"],
            "before_evaluation_root": before["evaluation_root"],
            "after_evaluation_root": after["evaluation_root"],
            "denominator": sorted(before_map), "changed_output": changed_output,
            "changed_semantic": changed_semantic, "changed_provenance": changed_receipt,
            "unchanged_output": sorted(set(before_map) - set(changed_output)),
            "blocked": sorted(node_id for node_id, row in after_map.items()
                              if row["status"] != "PASS"),
            "authority_effect": "NONE"}
    return _seal(body, "impact_root")


def explain_node(*, graph: dict[str, Any], evaluation: dict[str, Any], node_id: str) -> dict[str, Any]:
    verify_graph(graph)
    require(type(node_id) is str and node_id in {node["node_id"] for node in graph["nodes"]},
            "DEPENDENCY_EXPLAIN_NODE_INVALID")
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    results = {row["node_id"]: row for row in evaluation["results"]}
    require(node_id in results, "DEPENDENCY_EXPLAIN_RESULT_MISSING")
    paths: list[list[str]] = []
    def visit(current: str, path: list[str]) -> None:
        edges = nodes[current]["dependencies"]
        if not edges:
            paths.append(path + [current])
            return
        for edge in edges:
            visit(edge["node_id"], path + [current])
    visit(node_id, [])
    body = {"schema": "mosaic.ucm.dependency-explanation.v0.1",
            "graph_root": graph["graph_root"],
            "evaluation_root": evaluation["evaluation_root"], "node_id": node_id,
            "status": results[node_id]["status"],
            "reason_codes": deepcopy(results[node_id]["reason_codes"]),
            "definition_root": nodes[node_id]["definition_root"],
            "invocation_root": results[node_id]["invocation_root"],
            "output_root": results[node_id]["output_root"],
            "semantic_root": results[node_id]["semantic_root"],
            "dependency_paths": sorted(paths), "authority_effect": "NONE"}
    return _seal(body, "explanation_root")


def build_portable_closure(*, profile: str, graph: dict[str, Any], snapshot: dict[str, Any],
                           evaluation: dict[str, Any], software_root: str,
                           adapter_root: str, schema_roots: list[str],
                           evidence_roots: list[str], members: list[dict[str, Any]]) -> dict[str, Any]:
    require(profile in {"CONTEXT", "WORK", "REPLAY", "REVIEW"},
            "DEPENDENCY_PORTABLE_PROFILE_INVALID")
    verify_snapshot(snapshot, graph)
    _verify_evaluation_shape(evaluation, graph, snapshot)
    require_root(software_root); require_root(adapter_root)
    for value in schema_roots + evidence_roots:
        require_root(value)
    normalized_members: list[dict[str, Any]] = []
    for index, member in enumerate(members):
        item = exact_keys(member, {"path", "sha256", "bytes", "role"}, f"$.members[{index}]")
        require(type(item["path"]) is str and item["path"] and "\\" not in item["path"]
                and not item["path"].startswith("/") and ".." not in item["path"].split("/"),
                "DEPENDENCY_PORTABLE_PATH_INVALID", f"$.members[{index}]")
        require_root(item["sha256"])
        require(type(item["bytes"]) is int and item["bytes"] >= 0,
                "DEPENDENCY_PORTABLE_BYTES_INVALID")
        require(type(item["role"]) is str and item["role"],
                "DEPENDENCY_PORTABLE_ROLE_INVALID")
        normalized_members.append(deepcopy(item))
    normalized_members.sort(key=lambda item: item["path"])
    require(len({item["path"] for item in normalized_members}) == len(normalized_members),
            "DEPENDENCY_PORTABLE_MEMBER_DUPLICATE")
    body = {"schema": PORTABLE_SCHEMA, "profile": profile,
            "graph_root": graph["graph_root"], "snapshot_root": snapshot["snapshot_root"],
            "evaluation_root": evaluation["evaluation_root"], "software_root": software_root,
            "adapter_root": adapter_root, "schema_roots": sorted(set(schema_roots)),
            "evidence_roots": sorted(set(evidence_roots)), "members": normalized_members,
            "member_manifest_root": root(normalized_members),
            "credentials_included": False, "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
    return _seal(body, "portable_closure_root")


def verify_portable_closure(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == PORTABLE_SCHEMA,
            "DEPENDENCY_PORTABLE_CLOSURE_INVALID")
    require(value.get("credentials_included") is False,
            "DEPENDENCY_PORTABLE_CREDENTIALS_FORBIDDEN")
    require(value.get("member_manifest_root") == root(value.get("members")),
            "DEPENDENCY_PORTABLE_MANIFEST_MISMATCH")
    expected = value.get("portable_closure_root")
    require(_is_root(expected) and expected == root({k: v for k, v in value.items()
                                                     if k != "portable_closure_root"}),
            "DEPENDENCY_PORTABLE_ROOT_MISMATCH")
    return {"schema": "mosaic.ucm.dependency-portable-verification.v0.1",
            "status": "PASS", "portable_closure_root": expected,
            "profile": value["profile"], "member_count": len(value["members"]),
            "authority_effect": "NONE"}


def build_producer_receipt(*, producer_root: str, graph: dict[str, Any],
                           snapshot: dict[str, Any], evaluation: dict[str, Any],
                           execution_capsule_root: str, checker_root: str) -> dict[str, Any]:
    require_root(producer_root); require_root(execution_capsule_root); require_root(checker_root)
    _verify_evaluation_shape(evaluation, graph, snapshot)
    body = {"schema": "mosaic.ucm.dependency-producer-receipt.v0.1",
            "producer_root": producer_root, "graph_root": graph["graph_root"],
            "snapshot_root": snapshot["snapshot_root"],
            "evaluation_root": evaluation["evaluation_root"],
            "execution_capsule_root": execution_capsule_root,
            "checker_root": checker_root, "authority_effect": "NONE"}
    return _seal(body, "receipt_root")

