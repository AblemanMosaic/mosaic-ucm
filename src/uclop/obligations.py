from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root


OBLIGATION_STATES = {"OPEN", "PRESERVED", "DISCHARGED", "REPLACED", "RESIDUAL"}
EDGE_KINDS = {"LOWERS", "DERIVES", "CHECKS", "SOLVES", "ENUMERATES", "ADMITS"}
SUBJECT_BOUND_EVIDENCE = {
    "PROPOSITIONAL_PROOF",
    "ELIGIBILITY_WITNESS",
    "NATIVE_DEDUCTIVE_PROOF",
}


def validate_obligation(item: Any, path: str = "$.obligation") -> dict[str, Any]:
    base_keys = {"id", "kind", "statement", "source_ref", "assumptions", "required_evidence", "severity"}
    require(type(item) is dict, "OBLIGATION_SHAPE_INVALID", path)
    require(frozenset(item) in {frozenset(base_keys), frozenset(base_keys | {"evidence_subject"})}, "OBLIGATION_KEYS_INVALID", path)
    value = deepcopy(item)
    require(type(value["id"]) is str and value["id"], "OBLIGATION_ID_INVALID", f"{path}.id")
    require(type(value["kind"]) is str and value["kind"], "OBLIGATION_KIND_INVALID", f"{path}.kind")
    require(type(value["statement"]) is str and value["statement"], "OBLIGATION_STATEMENT_INVALID", f"{path}.statement")
    require(type(value["source_ref"]) is str and value["source_ref"], "OBLIGATION_SOURCE_INVALID", f"{path}.source_ref")
    require(type(value["assumptions"]) is list and all(type(x) is str and x for x in value["assumptions"]), "OBLIGATION_ASSUMPTIONS_INVALID", f"{path}.assumptions")
    require(type(value["required_evidence"]) is list and all(type(x) is str and x for x in value["required_evidence"]), "OBLIGATION_EVIDENCE_INVALID", f"{path}.required_evidence")
    require(value["severity"] in {"LOW", "MED", "HIGH", "CRITICAL"}, "OBLIGATION_SEVERITY_INVALID", f"{path}.severity")
    if SUBJECT_BOUND_EVIDENCE & set(value["required_evidence"]):
        require(type(value.get("evidence_subject")) is dict and type(value["evidence_subject"].get("kind")) is str and value["evidence_subject"]["kind"], "OBLIGATION_EVIDENCE_SUBJECT_REQUIRED", f"{path}.evidence_subject")
    return deepcopy(value)


def inventory(items: list[dict[str, Any]], subject_root: str) -> dict[str, Any]:
    require_root(subject_root, "$.subject_root")
    validated = [validate_obligation(item, f"$.obligations[{index}]") for index, item in enumerate(items)]
    ids = [item["id"] for item in validated]
    require(len(ids) == len(set(ids)), "OBLIGATION_ID_DUPLICATE")
    body = {"schema": "ucl.op.obligation_inventory.v1", "subject_root": subject_root, "obligations": sorted(validated, key=lambda x: x["id"])}
    return {**body, "inventory_root": root(body)}


def validate_inventory(value: Any, path: str = "$.inventory") -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "obligations", "inventory_root"}, path)
    require(item["schema"] == "ucl.op.obligation_inventory.v1", "OBLIGATION_INVENTORY_SCHEMA_INVALID", path)
    require_root(item["subject_root"], f"{path}.subject_root")
    require(type(item["obligations"]) is list, "OBLIGATION_INVENTORY_ITEMS_INVALID", f"{path}.obligations")
    expected = inventory(item["obligations"], item["subject_root"])
    require(item == expected, "OBLIGATION_INVENTORY_ROOT_MISMATCH", path)
    return expected


def validate_edge(edge: Any, path: str = "$.edge") -> dict[str, Any]:
    value = exact_keys(edge, {"from_id", "to_ids", "disposition", "edge_kind", "evidence_refs", "reason"}, path)
    require(type(value["from_id"]) is str and value["from_id"], "EDGE_SOURCE_INVALID", f"{path}.from_id")
    require(type(value["to_ids"]) is list and all(type(x) is str and x for x in value["to_ids"]), "EDGE_TARGETS_INVALID", f"{path}.to_ids")
    require(value["disposition"] in OBLIGATION_STATES - {"OPEN"}, "EDGE_DISPOSITION_INVALID", f"{path}.disposition")
    require(value["edge_kind"] in EDGE_KINDS, "EDGE_KIND_INVALID", f"{path}.edge_kind")
    require(type(value["evidence_refs"]) is list and all(type(x) is str and x for x in value["evidence_refs"]), "EDGE_EVIDENCE_INVALID", f"{path}.evidence_refs")
    require(type(value["reason"]) is str and value["reason"], "EDGE_REASON_INVALID", f"{path}.reason")
    if value["disposition"] == "DISCHARGED":
        require(bool(value["evidence_refs"]), "DISCHARGE_EVIDENCE_REQUIRED", path)
        require(not value["to_ids"], "DISCHARGE_TARGET_FORBIDDEN", path)
    elif value["disposition"] in {"PRESERVED", "REPLACED", "RESIDUAL"}:
        require(bool(value["to_ids"]), "EDGE_TARGET_REQUIRED", path)
    return deepcopy(value)


def conserve(
    source_inventory: dict[str, Any],
    target_inventory: dict[str, Any],
    edges: list[dict[str, Any]],
    *,
    pass_id: str,
    evidence_records: dict[str, dict[str, Any]] | None = None,
    evidence_materials: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    require(type(pass_id) is str and pass_id, "PASS_ID_INVALID")
    source_inventory = validate_inventory(source_inventory, "$.source")
    target_inventory = validate_inventory(target_inventory, "$.target")
    source_by_id = {item["id"]: item for item in source_inventory["obligations"]}
    target_by_id = {item["id"]: item for item in target_inventory["obligations"]}
    source_ids, target_ids = set(source_by_id), set(target_by_id)
    checked = [validate_edge(edge, f"$.edges[{index}]") for index, edge in enumerate(edges)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in checked:
        require(edge["from_id"] in source_ids, "EDGE_SOURCE_UNKNOWN", detail=edge["from_id"])
        require(all(target in target_ids for target in edge["to_ids"]), "EDGE_TARGET_UNKNOWN", detail=edge["from_id"])
        if edge["disposition"] in {"PRESERVED", "RESIDUAL"}:
            require(len(edge["to_ids"]) == 1, "PRESERVED_TARGET_CARDINALITY_INVALID", detail=edge["from_id"])
            source = deepcopy(source_by_id[edge["from_id"]]); target = deepcopy(target_by_id[edge["to_ids"][0]])
            require(source.get("evidence_subject") == target.get("evidence_subject"), "OBLIGATION_EVIDENCE_SUBJECT_CHANGED", detail=edge["from_id"])
            source.pop("source_ref"); target.pop("source_ref")
            require(source == target, "PRESERVED_OBLIGATION_CONTENT_MISMATCH" if edge["disposition"] == "PRESERVED" else "RESIDUAL_OBLIGATION_CONTENT_MISMATCH", detail=edge["from_id"])
        if edge["disposition"] in {"DISCHARGED", "REPLACED"}:
            from .checkers import evaluate_evidence

            require(bool(edge["evidence_refs"]), "TRANSFORMATION_EVIDENCE_REQUIRED", detail=edge["from_id"])
            require(evidence_records is not None and evidence_materials is not None, "TRANSFORMATION_EVIDENCE_UNRESOLVED", detail=edge["from_id"])
            for reference in edge["evidence_refs"]:
                receipt = evidence_records.get(reference)
                require(type(receipt) is dict, "TRANSFORMATION_EVIDENCE_UNRESOLVED", detail=reference)
                material = evidence_materials.get(receipt.get("evidence_root"))
                require(type(material) is dict, "TRANSFORMATION_EVIDENCE_MATERIAL_UNRESOLVED", detail=reference)
                expected = evaluate_evidence(
                    material,
                    source_inventory_root=source_inventory["inventory_root"],
                    target_inventory_root=target_inventory["inventory_root"],
                    source_obligation=source_by_id[edge["from_id"]],
                    target_obligations=[target_by_id[target_id] for target_id in edge["to_ids"]],
                    disposition=edge["disposition"],
                )
                require(receipt == expected, "TRANSFORMATION_EVIDENCE_RECEIPT_INVALID", detail=reference)
                require(receipt["receipt_root"] == reference, "TRANSFORMATION_EVIDENCE_RECEIPT_ROOT_MISMATCH", detail=reference)
        grouped.setdefault(edge["from_id"], []).append(edge)
    missing = sorted(source_ids - set(grouped))
    require(not missing, "OBLIGATION_DROPPED", detail=",".join(missing))
    require(all(len(rows) == 1 for rows in grouped.values()), "OBLIGATION_MULTIPLE_DISPOSITIONS")
    body = {
        "schema": "ucl.op.obligation_map.v1",
        "pass_id": pass_id,
        "source_inventory_root": source_inventory["inventory_root"],
        "target_inventory_root": target_inventory["inventory_root"],
        "edges": sorted(checked, key=lambda x: x["from_id"]),
        "status": "PASS_CONSERVED",
        "authority_effect": "NONE",
    }
    return {**body, "map_root": root(body)}


def ensure_no_open_residue(inventory_value: dict[str, Any], maps: list[dict[str, Any]]) -> None:
    covered = {edge["from_id"] for mapping in maps for edge in mapping.get("edges", [])}
    expected = {item["id"] for item in inventory_value["obligations"]}
    missing = sorted(expected - covered)
    if missing:
        raise Refusal("OBLIGATION_RESIDUE_UNACCOUNTED", detail=",".join(missing))
