"""Pure, exactly bound obligation accounting over the existing bounded kernel.

Only PROOF obligations requiring solely native deductive proof can discharge.
Compilation, execution, repair and review remain explicit residual obligations;
a proof of a declared transition model never attests those real activities.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .checkers import evaluate_evidence, make_evidence_material
from .deductive_proofs import (
    MAX_ARITHMETIC, MAX_BODY, MAX_FORMULA_DEPTH, MAX_TERM_NODES,
    MAX_TRACE_ROWS, MAX_VARIABLES, THEORY_ROOT,
    compile_contract, evidence_subject, verify_proof,
)
from .obligations import conserve, inventory, validate_inventory, validate_obligation
from .maturity_semantics import BOUNDARY


PLAN_SCHEMA = "ucl.ucm.maturity.proof_gate_plan.v1"
RESULT_SCHEMA = "ucl.ucm.maturity.proof_gate_result.v1"
DOMAINS = ["COMPILATION", "EXECUTION", "PROOF", "REPAIR", "REVIEW"]
MAX_OBLIGATIONS = 256
MAX_CONTRACTS = 64
FINITE_LIMITS = {
    "obligations": MAX_OBLIGATIONS,
    "contracts": MAX_CONTRACTS,
    "variables_per_contract": MAX_VARIABLES,
    "statements_per_body": MAX_BODY,
    "syntax_nodes_per_contract": MAX_TERM_NODES,
    "formula_depth": MAX_FORMULA_DEPTH,
    "certificate_trace_rows": MAX_TRACE_ROWS,
    "arithmetic_absolute_limit": MAX_ARITHMETIC,
    "verification_conditions_per_contract": 1024,
}
_PLAN_KEYS = {"schema", "subject_root", "theory_root", "inventory", "contracts",
              "contract_bindings", "domains", "finite_limits", "standing",
              "authority_effect", "real_a5", "g0", "plan_root"}


def _obligation_ids(value: Any) -> list[str]:
    require(type(value) is list and all(type(item) is str and item for item in value)
            and value == sorted(set(value)), "MATURITY_PROOF_OBLIGATION_PINS_INVALID")
    return list(value)


def _boundary(value: dict[str, Any]) -> None:
    require(all(type(value.get(key)) is type(expected) and value[key] == expected
                for key, expected in BOUNDARY.items()), "MATURITY_PROOF_BOUNDARY_INVALID")


def make_proof_obligation(contract: Any, *, statement: str, source_ref: str,
                          severity: str = "HIGH") -> dict[str, Any]:
    """Describe only the bounded model claim; this does not discharge it."""
    compile_contract(contract)
    return validate_obligation({
        "id": contract["obligation_id"], "kind": "PROOF", "statement": statement,
        "source_ref": source_ref,
        "assumptions": [root(item) for item in contract["assumptions"]],
        "required_evidence": ["NATIVE_DEDUCTIVE_PROOF"], "severity": severity,
        "evidence_subject": evidence_subject(contract),
    })


def make_gate_plan(*, subject_root: str, obligations: list[dict[str, Any]],
                   contracts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a portable plan. Its caller must retain the returned external pins."""
    subject = require_root(subject_root)
    require(type(obligations) is list and len(obligations) <= MAX_OBLIGATIONS,
            "MATURITY_PROOF_OBLIGATION_LIMIT")
    source = inventory(obligations, subject)
    by_id = {item["id"]: item for item in source["obligations"]}
    require(all(item["kind"] in DOMAINS for item in by_id.values()),
            "MATURITY_PROOF_DOMAIN_INVALID")
    require(all(item["required_evidence"] == sorted(set(item["required_evidence"]))
                for item in by_id.values()), "MATURITY_PROOF_EVIDENCE_SET_INVALID")
    require(type(contracts) is list and len(contracts) <= MAX_CONTRACTS,
            "MATURITY_PROOF_CONTRACT_LIMIT")
    checked, bindings, contract_ids = [], [], set()
    for contract in contracts:
        compiled = compile_contract(contract)
        identifier = contract["obligation_id"]
        require(identifier not in contract_ids, "MATURITY_PROOF_CONTRACT_DUPLICATE")
        require(identifier in by_id, "MATURITY_PROOF_CONTRACT_OBLIGATION_MISMATCH")
        require(compiled["subject_root"] == subject, "MATURITY_PROOF_SUBJECT_MISMATCH")
        obligation = by_id[identifier]
        require("NATIVE_DEDUCTIVE_PROOF" in obligation["required_evidence"],
                "MATURITY_PROOF_CONTRACT_NOT_REQUIRED")
        observed = evidence_subject(contract)
        require(obligation.get("evidence_subject") == observed,
                "MATURITY_PROOF_OBLIGATION_SUBJECT_MISMATCH")
        contract_ids.add(identifier)
        checked.append(deepcopy(contract))
        bindings.append({"obligation_id": identifier, "contract_root": contract["contract_root"],
                         "evidence_subject_root": root(observed)})
    require(all("NATIVE_DEDUCTIVE_PROOF" not in item["required_evidence"]
                or item["id"] in contract_ids for item in by_id.values()),
            "MATURITY_PROOF_CONTRACT_MISSING")
    body = {"schema": PLAN_SCHEMA, "subject_root": subject, "theory_root": THEORY_ROOT,
            "inventory": source,
            "contracts": sorted(checked, key=lambda item: item["obligation_id"]),
            "contract_bindings": sorted(bindings, key=lambda item: item["obligation_id"]),
            "domains": list(DOMAINS), "finite_limits": deepcopy(FINITE_LIMITS), **BOUNDARY}
    return {**body, "plan_root": root(body)}


def verify_gate_plan(plan: Any, *, expected_subject_root: str, expected_plan_root: str,
                     expected_inventory_root: str,
                     expected_obligation_ids: list[str]) -> dict[str, Any]:
    """Rebuild the plan against subject, inventory, obligation and plan pins."""
    item = exact_keys(plan, _PLAN_KEYS, "$.proof_gate_plan")
    _boundary(item)
    require(item["plan_root"] == root({key: value for key, value in item.items() if key != "plan_root"}),
            "MATURITY_PROOF_PLAN_ROOT_MISMATCH")
    subject = require_root(expected_subject_root)
    require(item["subject_root"] == subject, "MATURITY_PROOF_SUBJECT_MISMATCH")
    source = validate_inventory(item["inventory"])
    require(source["subject_root"] == subject, "MATURITY_PROOF_INVENTORY_SUBJECT_MISMATCH")
    require(source["inventory_root"] == require_root(expected_inventory_root),
            "MATURITY_PROOF_INVENTORY_PIN_MISMATCH")
    identifiers = _obligation_ids(expected_obligation_ids)
    require([row["id"] for row in source["obligations"]] == identifiers,
            "MATURITY_PROOF_OBLIGATION_PIN_MISMATCH")
    expected = make_gate_plan(subject_root=subject, obligations=source["obligations"],
                              contracts=item["contracts"])
    require(canonical_bytes(item) == canonical_bytes(expected), "MATURITY_PROOF_PLAN_MISMATCH")
    require(item["plan_root"] == require_root(expected_plan_root),
            "MATURITY_PROOF_PLAN_PIN_MISMATCH")
    return expected


def evaluate_gate(plan: Any, proof_bundles: Any, *, expected_subject_root: str,
                  expected_plan_root: str, expected_inventory_root: str,
                  expected_obligation_ids: list[str]) -> dict[str, Any]:
    """Recheck supplied proofs and conserve every obligation, without effects.

    Missing, assumption-bound and unknown proof results remain residuals.
    Malformed or substituted evidence refuses; it is never silently ignored.
    """
    checked_plan = verify_gate_plan(plan, expected_subject_root=expected_subject_root,
        expected_plan_root=expected_plan_root, expected_inventory_root=expected_inventory_root,
        expected_obligation_ids=expected_obligation_ids)
    contracts = {item["obligation_id"]: item for item in checked_plan["contracts"]}
    require(type(proof_bundles) is dict and set(proof_bundles) <= set(contracts),
            "MATURITY_PROOF_BUNDLE_SET_INVALID")
    checks = {identifier: verify_proof(contracts[identifier], proof_bundles[identifier])
              for identifier in sorted(proof_bundles)}
    source = checked_plan["inventory"]
    rows, discharged = [], set()
    for obligation in source["obligations"]:
        identifier = obligation["id"]
        check = checks.get(identifier)
        if obligation["kind"] != "PROOF":
            diagnostic = "DOMAIN_REQUIRES_ACTIVITY_EVIDENCE"
        elif obligation["required_evidence"] != ["NATIVE_DEDUCTIVE_PROOF"]:
            diagnostic = "NATIVE_PROOF_IS_NOT_COMPLETE_EVIDENCE"
        elif check is None:
            diagnostic = "NATIVE_PROOF_NOT_SUBMITTED"
        elif check["outcome"] != "PROVED":
            diagnostic = "NATIVE_PROOF_" + check["outcome"]
        elif obligation["assumptions"]:
            diagnostic = "OBLIGATION_ASSUMPTIONS_REMAIN"
        else:
            diagnostic = "UNCONDITIONAL_NATIVE_PROOF_CHECKED"
            discharged.add(identifier)
        rows.append({"obligation_id": identifier, "domain": obligation["kind"],
                     "disposition": "DISCHARGED" if identifier in discharged else "RESIDUAL",
                     "diagnostic": diagnostic,
                     "check_root": check["check_root"] if check else None})
    target = inventory([item for item in source["obligations"] if item["id"] not in discharged],
                       checked_plan["subject_root"])
    materials, receipts, edges = [], [], []
    for obligation in source["obligations"]:
        identifier = obligation["id"]
        if identifier in discharged:
            contract = contracts[identifier]
            material = make_evidence_material("EXACT_NATIVE_DEDUCTIVE_PROOF_V1",
                obligation_id=identifier, disposition="DISCHARGED",
                source_inventory_root=source["inventory_root"],
                target_inventory_root=target["inventory_root"], target_obligation_ids=[],
                evidence_subject=evidence_subject(contract),
                payload={"contract": contract, "proof_bundle": proof_bundles[identifier]})
            receipt = evaluate_evidence(material,
                source_inventory_root=source["inventory_root"],
                target_inventory_root=target["inventory_root"], source_obligation=obligation,
                target_obligations=[], disposition="DISCHARGED")
            materials.append(material); receipts.append(receipt)
            targets, refs, disposition = [], [receipt["receipt_root"]], "DISCHARGED"
            reason = "Existing bounded kernel checked the exact unconditional contract."
        else:
            targets, refs, disposition = [identifier], [], "RESIDUAL"
            reason = "Required evidence remains outstanding; original obligation retained."
        edges.append({"from_id": identifier, "to_ids": targets, "disposition": disposition,
                      "edge_kind": "CHECKS", "evidence_refs": refs, "reason": reason})
    mapping = conserve(source, target, edges, pass_id="MATURITY_C1_PROOF_GATE",
        evidence_records={item["receipt_root"]: item for item in receipts},
        evidence_materials={item["evidence_root"]: item for item in materials})
    body = {"schema": RESULT_SCHEMA, "subject_root": checked_plan["subject_root"],
            "plan_root": checked_plan["plan_root"], "theory_root": THEORY_ROOT,
            "source_inventory_root": source["inventory_root"], "target_inventory": target,
            "proof_bundles": deepcopy(proof_bundles),
            "proof_checks": [checks[identifier] for identifier in sorted(checks)],
            "obligations": rows, "evidence_materials": materials,
            "evidence_receipts": receipts, "conservation_map": mapping,
            "gate_status": "PASS_CLOSED" if not target["obligations"] else "RESIDUAL",
            "discharged_obligation_ids": sorted(discharged),
            "residual_obligation_ids": [item["id"] for item in target["obligations"]],
            "claim_scope": "DECLARED_BOUNDED_PROOF_OBLIGATIONS_ONLY",
            "activity_execution_attested": False, "review_attested": False,
            "finite_limits": deepcopy(FINITE_LIMITS), **BOUNDARY}
    return {**body, "result_root": root(body)}


def verify_gate_result(value: Any, *, plan: Any, expected_subject_root: str,
                       expected_plan_root: str, expected_inventory_root: str,
                       expected_obligation_ids: list[str]) -> dict[str, Any]:
    """Reconstruct proof checks, evidence receipts and conservation after restart."""
    require(type(value) is dict and "proof_bundles" in value,
            "MATURITY_PROOF_RESULT_INVALID")
    _boundary(value)
    require(value.get("result_root") == root({key: item for key, item in value.items() if key != "result_root"}),
            "MATURITY_PROOF_RESULT_ROOT_MISMATCH")
    expected = evaluate_gate(plan, value["proof_bundles"],
        expected_subject_root=expected_subject_root, expected_plan_root=expected_plan_root,
        expected_inventory_root=expected_inventory_root,
        expected_obligation_ids=expected_obligation_ids)
    require(canonical_bytes(value) == canonical_bytes(expected), "MATURITY_PROOF_RESULT_MISMATCH")
    return expected
