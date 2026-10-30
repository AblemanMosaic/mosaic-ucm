"""Proof, explanation, trust-base and semantic-change records for canonical UCM."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .deductive_proofs import evidence_subject, verify_proof
from .maturity_semantics import BOUNDARY, seal
from .operational_evidence import claim_root, verify_accepted_claim_evidence

ASSERTION_STATES = {"ASSERTED", "ASSUMED", "DERIVED", "OBSERVED", "PROVED", "REVIEWED", "ADMITTED"}
TCB_STATUSES = {"PROVED", "ENFORCED", "OBSERVED", "TRUSTED_ASSUMPTION"}


def make_proof_certificate(*, contract: dict[str, Any], proof_bundle: dict[str, Any],
                           expected_contract_root: str, expected_proof_bundle_root: str) -> dict[str, Any]:
    """Issue a presentation certificate only after the native kernel rechecks the proof."""
    require(contract.get("contract_root") == require_root(expected_contract_root), "PROOF_CONTRACT_PIN_MISMATCH")
    require(proof_bundle.get("proof_bundle_root") == require_root(expected_proof_bundle_root),
            "PROOF_BUNDLE_PIN_MISMATCH")
    checked = verify_proof(contract, proof_bundle)
    require(checked["outcome"] in {"PROVED", "ASSUMPTION_BOUND"}, "PROOF_NOT_PROVED")
    return seal({"schema": "ucl.ucm.native_proof_certificate.v2",
        "subject_root": checked["evidence_subject"]["subject_root"],
        "evidence_subject": evidence_subject(contract), "contract_root": checked["contract_root"],
        "proof_bundle_root": checked["proof_bundle_root"], "check_root": checked["check_root"],
        "checker": checked["kernel"], "assertion_state": checked["outcome"], **BOUNDARY})


def make_explanation_graph(*, subject_root: str, assertions: list[dict[str, Any]], edges: list[dict[str, Any]],
                           proof_roots: list[str], evidence_contracts: list[dict[str, Any]],
                           accepted_contract_roots: list[str]) -> dict[str, Any]:
    require_root(subject_root)
    ids = []
    for item in assertions:
        exact_keys(item, {"id", "statement", "state", "source_roots", "evidence_records", "expected_evidence_roots"}, "$.assertion")
        require(type(item["id"]) is str and item["id"] and type(item["statement"]) is str and item["statement"]
                and item["state"] in ASSERTION_STATES and type(item["source_roots"]) is list, "EXPLANATION_ASSERTION_INVALID")
        for source in item["source_roots"]: require_root(source)
        require(type(item["evidence_records"]) is list and type(item["expected_evidence_roots"]) is list
                and len(item["evidence_records"]) == len(item["expected_evidence_roots"]), "EXPLANATION_EVIDENCE_INVALID")
        records=[]
        for record, expected in zip(item["evidence_records"], item["expected_evidence_roots"], strict=True):
            accepted=verify_accepted_claim_evidence(record, evidence_contracts=evidence_contracts,
                expected_contract_roots=accepted_contract_roots)
            require(accepted["root"] == require_root(expected) and subject_root in accepted["subject_roots"]
                    and accepted["claim_id"] == item["id"]
                    and accepted["claim_root"] == claim_root(item["id"], item["statement"]),
                    "EXPLANATION_EVIDENCE_PIN_MISMATCH")
            records.append(accepted)
        required_outcomes = {"DERIVED": {"PRESERVED"}, "OBSERVED": {"OBSERVED"},
                             "PROVED": {"PROVED"}, "REVIEWED": {"DOCUMENTED"},
                             "ADMITTED": {"ADMITTED"}}
        if item["state"] in required_outcomes:
            require(bool(records) and all(record.get("outcome") in required_outcomes[item["state"]]
                    for record in records), "EXPLANATION_EVIDENCE_STATE_MISMATCH")
        if item["state"] == "PROVED":
            require(all(record.get("evidence_schema") == "ucl.ucm.native_proof_claim_evidence.v1"
                    and record.get("status") == "ACCEPTED_BOUND_EVIDENCE" for record in records),
                    "EXPLANATION_PROOF_EVIDENCE_INVALID")
        if item["state"] in {"ASSERTED", "ASSUMED"}:
            require(not records, "EXPLANATION_UNEARNED_EVIDENCE_STATE")
        ids.append(item["id"])
    require(len(ids) == len(set(ids)), "EXPLANATION_ASSERTION_DUPLICATE")
    for edge in edges:
        exact_keys(edge, {"from", "to", "relation"}, "$.edge")
        require(edge["from"] in ids and edge["to"] in ids and edge["from"] != edge["to"], "EXPLANATION_EDGE_INVALID")
    for proof in proof_roots: require_root(proof)
    earned_proof_roots=sorted({expected for item in assertions if item["state"]=="PROVED" for expected in item["expected_evidence_roots"]})
    require(sorted(set(proof_roots)) == earned_proof_roots, "EXPLANATION_PROOF_SET_MISMATCH")
    return seal({"schema": "ucl.ucm.explanation_graph.v1", "subject_root": subject_root,
        "assertions": deepcopy(assertions), "edges": deepcopy(edges), "proof_roots": sorted(set(proof_roots)),
        "accepted_contract_roots": sorted(set(accepted_contract_roots)),
        "contract": "EXPLANATION_ENUMERATES_JUSTIFICATIONS; IT_IS_NOT_ITSELF_A_PROOF", **BOUNDARY})


def make_tcb_ledger(*, subject_root: str, components: list[dict[str, Any]],
                    evidence_contracts: list[dict[str, Any]], accepted_contract_roots: list[str]) -> dict[str, Any]:
    require_root(subject_root); ids = []
    for row in components:
        exact_keys(row, {"id", "artifact_root", "properties"}, "$.component")
        require(type(row["id"]) is str and row["id"], "TCB_COMPONENT_ID_INVALID"); require_root(row["artifact_root"])
        require(type(row["properties"]) is list and bool(row["properties"]), "TCB_PROPERTIES_INVALID")
        for prop in row["properties"]:
            exact_keys(prop, {"property", "status", "evidence_records", "expected_evidence_roots"}, "$.property")
            require(type(prop["property"]) is str and prop["status"] in TCB_STATUSES, "TCB_PROPERTY_INVALID")
            require(type(prop["evidence_records"]) is list and bool(prop["evidence_records"])
                    and type(prop["expected_evidence_roots"]) is list
                    and len(prop["evidence_records"]) == len(prop["expected_evidence_roots"]), "TCB_EVIDENCE_REQUIRED")
            actual=[]
            for record, expected in zip(prop["evidence_records"], prop["expected_evidence_roots"], strict=True):
                accepted=verify_accepted_claim_evidence(record, evidence_contracts=evidence_contracts,
                    expected_contract_roots=accepted_contract_roots)
                expected_claim_id=row["id"] + ":" + prop["property"]
                require(accepted["root"] == require_root(expected) and subject_root in accepted["subject_roots"]
                        and row["artifact_root"] in accepted["subject_roots"]
                        and accepted["claim_id"] == expected_claim_id
                        and accepted["claim_root"] == claim_root(expected_claim_id, prop["property"]),
                        "TCB_EVIDENCE_PIN_MISMATCH")
                actual.append(accepted)
            if prop["status"] == "PROVED":
                require(all(item.get("status") == "ACCEPTED_BOUND_EVIDENCE"
                    and item.get("outcome") == "PROVED" for item in actual), "TCB_PROOF_EVIDENCE_INVALID")
            elif prop["status"] == "ENFORCED":
                require(all(item.get("outcome") == "ENFORCED" for item in actual), "TCB_ENFORCEMENT_EVIDENCE_INVALID")
            elif prop["status"] == "OBSERVED":
                require(all(item.get("outcome") == "OBSERVED" for item in actual), "TCB_OBSERVATION_EVIDENCE_INVALID")
            else:
                require(all(item.get("outcome") == "TRUSTED_ASSUMPTION" for item in actual), "TCB_TRUST_EVIDENCE_INVALID")
        ids.append(row["id"])
    require(len(ids) == len(set(ids)), "TCB_COMPONENT_DUPLICATE")
    return seal({"schema": "ucl.ucm.tcb_ledger.v1", "subject_root": subject_root,
        "components": deepcopy(components), "status_vocabulary": sorted(TCB_STATUSES),
        "accepted_contract_roots": sorted(set(accepted_contract_roots)), **BOUNDARY})


def make_semantic_inventory_contract(*, contract_id: str, predecessor_root: str, successor_root: str,
                                     predecessor_claims: list[dict[str, Any]],
                                     successor_claims: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(contract_id) is str and bool(contract_id), "SEMANTIC_INVENTORY_CONTRACT_ID_INVALID")
    require_root(predecessor_root); require_root(successor_root)
    def inventory(rows: Any, path: str) -> list[dict[str, Any]]:
        require(type(rows) is list and bool(rows), "SEMANTIC_INVENTORY_EMPTY", path)
        result = {}
        for row in rows:
            row = exact_keys(row, {"id", "statement"}, path)
            require(type(row["id"]) is str and row["id"] and type(row["statement"]) is str
                    and row["statement"] and row["id"] not in result, "SEMANTIC_CHANGE_CLAIM_INVALID", path)
            result[row["id"]] = deepcopy(row)
        return [result[key] for key in sorted(result)]
    return seal({"schema": "ucl.ucm.semantic_inventory_contract.v1", "contract_id": contract_id,
        "predecessor_root": predecessor_root, "successor_root": successor_root,
        "predecessor_claims": inventory(predecessor_claims, "$.predecessor_claims"),
        "successor_claims": inventory(successor_claims, "$.successor_claims"),
        "scope_semantics": "EXTERNALLY_PINNED_COMPLETE_NONEMPTY_CLAIM_SCOPE", **BOUNDARY})


def verify_semantic_inventory_contract(value: Any, *, expected_root: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.semantic_inventory_contract.v1",
            "SEMANTIC_INVENTORY_CONTRACT_INVALID")
    rebuilt = make_semantic_inventory_contract(contract_id=value.get("contract_id"),
        predecessor_root=value.get("predecessor_root"), successor_root=value.get("successor_root"),
        predecessor_claims=value.get("predecessor_claims"), successor_claims=value.get("successor_claims"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt) and value["root"] == require_root(expected_root),
            "SEMANTIC_INVENTORY_CONTRACT_PIN_MISMATCH")
    return rebuilt


def make_semantic_change_plan(*, inventory_contract: dict[str, Any], expected_inventory_contract_root: str,
                              evidence_checks: dict[str, dict[str, Any]],
                              expected_evidence_roots: dict[str, str], method: str,
                              evidence_contracts: list[dict[str, Any]],
                              accepted_contract_roots: list[str]) -> dict[str, Any]:
    inventory_contract = verify_semantic_inventory_contract(inventory_contract,
        expected_root=expected_inventory_contract_root)
    predecessor_root, successor_root = inventory_contract["predecessor_root"], inventory_contract["successor_root"]
    require(type(method) is str and method, "SEMANTIC_CHANGE_METHOD_INVALID")
    def inventory(rows: Any, path: str) -> dict[str, dict[str, Any]]:
        require(type(rows) is list, "SEMANTIC_CHANGE_ROWS_INVALID", path)
        result = {}
        for row in rows:
            row = exact_keys(row, {"id", "statement"}, path)
            require(type(row["id"]) is str and row["id"] and type(row["statement"]) is str
                    and row["statement"] and row["id"] not in result, "SEMANTIC_CHANGE_CLAIM_INVALID", path)
            result[row["id"]] = deepcopy(row)
        return result
    before = inventory(inventory_contract["predecessor_claims"], "$.predecessor_claims")
    after = inventory(inventory_contract["successor_claims"], "$.successor_claims")
    require(type(evidence_checks) is dict and type(expected_evidence_roots) is dict
            and set(evidence_checks) == set(expected_evidence_roots), "SEMANTIC_CHANGE_EVIDENCE_SET_INVALID")
    preserved = sorted(identifier for identifier in before.keys() & after.keys() if before[identifier] == after[identifier])
    changed = sorted(identifier for identifier in before.keys() & after.keys() if before[identifier] != after[identifier])
    removed, added = sorted(before.keys() - after.keys()), sorted(after.keys() - before.keys())
    checked = []
    for identifier in sorted(evidence_checks):
        require(identifier in preserved, "SEMANTIC_CHANGE_EVIDENCE_SUBJECT_UNKNOWN", identifier)
        receipt=verify_accepted_claim_evidence(evidence_checks[identifier], evidence_contracts=evidence_contracts,
            expected_contract_roots=accepted_contract_roots)
        expected = require_root(expected_evidence_roots[identifier])
        require(receipt["root"] == expected and predecessor_root in receipt["subject_roots"]
                and successor_root in receipt["subject_roots"] and receipt["claim_id"] == identifier
                and receipt["claim_root"] == claim_root(identifier, before[identifier]["statement"])
                and receipt["outcome"] == "PRESERVED", "SEMANTIC_CHANGE_EVIDENCE_NOT_VERIFIED", identifier)
        checked.append({"claim_id": identifier, "accepted_evidence_root": expected,
                        "acceptance_contract_root": receipt["acceptance_contract_root"],
                        "accepted_evidence": deepcopy(receipt)})
    all_preserved_verified = set(preserved) == set(evidence_checks)
    status = ("PASS_CONSERVATIVE" if not changed and not removed and not added and all_preserved_verified
              else "FAIL_CHANGED" if changed or removed or added else "UNKNOWN")
    return seal({"schema": "ucl.ucm.semantic_change_plan.v3", "predecessor_root": predecessor_root,
        "successor_root": successor_root, "predecessor_claims": [before[k] for k in sorted(before)],
        "successor_claims": [after[k] for k in sorted(after)], "preserved_claim_ids": preserved,
        "changed_claim_ids": changed, "removed_claim_ids": removed, "added_claim_ids": added,
        "inventory_contract": deepcopy(inventory_contract), "inventory_contract_root": inventory_contract["root"],
        "verified_evidence": checked, "accepted_contract_roots": sorted(set(accepted_contract_roots)),
        "method": method, "status": status, **BOUNDARY})


def verify_semantic_change_plan(value: Any, *, expected_root: str,
                                expected_inventory_contract_root: str,
                                evidence_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.semantic_change_plan.v3",
            "SEMANTIC_CHANGE_PLAN_INVALID")
    require(value.get("inventory_contract_root") == require_root(expected_inventory_contract_root),
            "SEMANTIC_CHANGE_INVENTORY_PIN_MISMATCH")
    records = value.get("verified_evidence")
    require(type(records) is list, "SEMANTIC_CHANGE_EVIDENCE_INVALID")
    checks = {}; roots = {}
    for row in records:
        item = exact_keys(row, {"claim_id", "accepted_evidence_root", "acceptance_contract_root",
                                "accepted_evidence"}, "$.verified_evidence")
        require(item["claim_id"] not in checks, "SEMANTIC_CHANGE_EVIDENCE_DUPLICATE")
        checks[item["claim_id"]] = item["accepted_evidence"]
        roots[item["claim_id"]] = item["accepted_evidence_root"]
    rebuilt = make_semantic_change_plan(inventory_contract=value.get("inventory_contract"),
        expected_inventory_contract_root=expected_inventory_contract_root,
        evidence_checks=checks, expected_evidence_roots=roots, method=value.get("method"),
        evidence_contracts=evidence_contracts,
        accepted_contract_roots=value.get("accepted_contract_roots"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt) and value["root"] == require_root(expected_root),
            "SEMANTIC_CHANGE_PLAN_RECONSTRUCTION_MISMATCH")
    return rebuilt


def verify_external_oracle_receipt(value: Any, *, expected_subject_root: str, expected_oracle_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "oracle_root", "query_root", "result_root", "verdict", "evidence_root"})
    require(item["schema"] == "ucl.ucm.external_oracle_receipt.v1", "ORACLE_RECEIPT_SCHEMA_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root), "ORACLE_SUBJECT_MISMATCH")
    require(item["oracle_root"] == require_root(expected_oracle_root), "ORACLE_IDENTITY_MISMATCH")
    for field in ("query_root", "result_root", "evidence_root"): require_root(item[field])
    require(item["verdict"] in {"PASS", "FAIL", "UNKNOWN"}, "ORACLE_VERDICT_INVALID")
    require(item["oracle_root"] != item["evidence_root"], "ORACLE_SELF_CERTIFICATION_REFUSED")
    return deepcopy(item)
