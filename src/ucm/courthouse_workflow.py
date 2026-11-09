"""Deterministic UCM boundary for Courthouse vNext Workflow IR.

UCM compiles repository-owned constitutional constraints into a portable
workflow envelope.  Courthouse vNext owns realization, authority,
execution, witnessing, and adjudication.  This module never selects an
executor, grants authority, or performs an effect.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


PROTOCOL = "UCM_AOK_VNEXT_WORKFLOW_IR_V0_1"
WORKFLOW_STEPS = [
    "ORIENT",
    "RESOLVE_CAPABILITIES",
    "ADJUDICATE_PREFLIGHT",
    "DURABLY_RECORD_INTENT",
    "EXECUTE_EXTERNALLY",
    "WITNESS_EFFECTS",
    "DIAGNOSE_RESULT",
    "ADJUDICATE_DISPOSITION",
]
REQUIRED_VNEXT_UNITS = [
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:OBJECTIVE_IR",
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:WORKFLOW_IR",
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:CAPABILITY_IR",
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:CCBA_LATTICE_BINDING",
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:REALIZATION_ROUTE",
    "AOK:CRU:WORKFLOW_CAPABILITY_IR:EFFECT_COVENANT",
    "AOK:CRU:UGK:ADMISSIBILITY_GATE",
    "AOK:CRU:UGK:RECEIPT_LEDGER",
    "AOK:CRU:UWK:EVIDENCE_RECEIPT",
]
EFFECT_CLASSES = {
    "NONE", "READ", "WRITE_WORKSPACE", "WRITE_EXTERNAL", "NETWORK",
    "INSTALL", "PROCESS", "DEVICE", "AUTHORITY_CHANGE",
}


def _rooted(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: root(body)}


def _strings(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    require(all(type(item) is str and bool(item) for item in value), code)
    require(len(value) == len(set(value)), code)
    return list(value)


def _head(value: Any, code: str) -> dict[str, Any]:
    item = exact_keys(value, {"sequence", "head"})
    require(type(item["sequence"]) is int and type(item["sequence"]) is not bool
            and item["sequence"] >= 0, code)
    if item["sequence"] == 0:
        require(item["head"] == "GENESIS", code)
    else:
        require_root(item["head"])
    return deepcopy(item)


def validate_workflow_request(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "request_id", "campaign_root", "operation_id",
        "application_id", "subject_root", "expected_journal_head",
        "architecture_contract_root", "architecture_candidate_root",
        "work_package_root", "objective", "cm1_obligations",
        "cm2_preferences", "requested_capabilities", "policy_pack_roots",
        "identity_binding", "authority_ceiling", "request_root",
    })
    require(item["schema"] == "mosaic.ucm.courthouse-workflow-request.v0.1",
            "UCM_COURTHOUSE_REQUEST_SCHEMA_INVALID")
    for field in ("request_id", "operation_id", "application_id", "objective"):
        require(type(item[field]) is str and bool(item[field]),
                "UCM_COURTHOUSE_REQUEST_FIELD_INVALID")
    for field in ("campaign_root", "subject_root", "architecture_contract_root",
                  "architecture_candidate_root", "work_package_root"):
        require_root(item[field])
    _head(item["expected_journal_head"], "UCM_COURTHOUSE_JOURNAL_HEAD_INVALID")

    identity = exact_keys(item["identity_binding"], {
        "requester_mosaic_id_root", "session_mosaic_id_root", "jurisdiction_root",
        "courthouse_identity_root", "courthouse_protocol_root"})
    for value_root in identity.values():
        require_root(value_root)

    cm1 = item["cm1_obligations"]
    require(type(cm1) is list and bool(cm1), "UCM_COURTHOUSE_CM1_INVALID")
    cm1_ids = []
    for row in cm1:
        checked = exact_keys(row, {"obligation_id", "obligation_root",
                                   "evidence_kind", "required"})
        require(type(checked["obligation_id"]) is str and checked["obligation_id"],
                "UCM_COURTHOUSE_CM1_INVALID")
        require_root(checked["obligation_root"])
        require(checked["evidence_kind"] in {
            "STATIC_CHECK", "TEST_RECEIPT", "PROOF_RECEIPT",
            "EXTERNAL_EVIDENCE", "HUMAN_WITNESS"},
            "UCM_COURTHOUSE_CM1_INVALID")
        require(type(checked["required"]) is bool,
                "UCM_COURTHOUSE_CM1_INVALID")
        cm1_ids.append(checked["obligation_id"])
    require(len(cm1_ids) == len(set(cm1_ids)), "UCM_COURTHOUSE_CM1_DUPLICATE")

    cm2 = item["cm2_preferences"]
    require(type(cm2) is list, "UCM_COURTHOUSE_CM2_INVALID")
    cm2_ids = []
    for row in cm2:
        checked = exact_keys(row, {"preference_id", "objective_root", "priority"})
        require(type(checked["preference_id"]) is str and checked["preference_id"],
                "UCM_COURTHOUSE_CM2_INVALID")
        require_root(checked["objective_root"])
        require(type(checked["priority"]) is int
                and type(checked["priority"]) is not bool
                and checked["priority"] >= 0, "UCM_COURTHOUSE_CM2_INVALID")
        cm2_ids.append(checked["preference_id"])
    require(len(cm2_ids) == len(set(cm2_ids)), "UCM_COURTHOUSE_CM2_DUPLICATE")

    capabilities = item["requested_capabilities"]
    require(type(capabilities) is list, "UCM_COURTHOUSE_CAPABILITY_INVALID")
    capability_ids = []
    for row in capabilities:
        checked = exact_keys(row, {"capability_id", "effect_class", "budget_root"})
        require(type(checked["capability_id"]) is str and checked["capability_id"],
                "UCM_COURTHOUSE_CAPABILITY_INVALID")
        require(checked["effect_class"] in EFFECT_CLASSES,
                "UCM_COURTHOUSE_EFFECT_CLASS_INVALID")
        require_root(checked["budget_root"])
        capability_ids.append(checked["capability_id"])
    require(len(capability_ids) == len(set(capability_ids)),
            "UCM_COURTHOUSE_CAPABILITY_DUPLICATE")
    _strings(item["policy_pack_roots"], "UCM_COURTHOUSE_POLICY_PACK_INVALID")
    for policy_root in item["policy_pack_roots"]:
        require_root(policy_root)

    ceiling = exact_keys(item["authority_ceiling"], {
        "standing", "authority_effect", "real_a5", "g0",
        "execution_authority_owner"})
    require({key: ceiling[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_COURTHOUSE_AUTHORITY_CEILING_INVALID")
    require(ceiling["execution_authority_owner"] == "COURTHOUSE_VNEXT_EXTERNAL",
            "UCM_COURTHOUSE_AUTHORITY_OWNER_INVALID")

    body = {key: deepcopy(raw) for key, raw in item.items() if key != "request_root"}
    require(item["request_root"] == root(body), "UCM_COURTHOUSE_REQUEST_ROOT_INVALID")
    return deepcopy(item)


def compile_workflow_ir(value: Any) -> dict[str, Any]:
    request = validate_workflow_request(value)
    objective_ir = _rooted({
        "schema": "aok.workflow.objective-ir.v0.1",
        "objective_id": request["operation_id"],
        "objective": request["objective"],
        "subject_root": request["subject_root"],
        "architecture_contract_root": request["architecture_contract_root"],
    }, "objective_ir_root")
    workflow_ir = _rooted({
        "schema": "aok.workflow.workflow-ir.v0.1",
        "ordered_steps": list(WORKFLOW_STEPS),
        "expected_journal_head": deepcopy(request["expected_journal_head"]),
        "durable_intent_before_effect": True,
        "uncertain_requires_reconciliation": True,
        "redispatch_after_uncertain": False,
    }, "workflow_ir_root")
    capability_ir = _rooted({
        "schema": "aok.workflow.capability-ir.v0.1",
        "requested_capabilities": deepcopy(request["requested_capabilities"]),
        "resolution_owner": "COURTHOUSE_VNEXT",
        "unresolved_capabilities_refuse": True,
    }, "capability_ir_root")
    lattice = _rooted({
        "schema": "aok.workflow.ccba-lattice-binding.v0.1",
        "required_units": list(REQUIRED_VNEXT_UNITS),
        "binding_owner": "COURTHOUSE_VNEXT",
        "binding_status": "EXTERNAL_RESOLUTION_REQUIRED",
    }, "ccba_lattice_binding_root")
    route = _rooted({
        "schema": "aok.workflow.realization-route.v0.1",
        "selector_owner": "COURTHOUSE_VNEXT",
        "selected_realization_root": None,
        "selected_executor_root": None,
        "status": "UNRESOLVED",
    }, "realization_route_root")
    effect_covenant = _rooted({
        "schema": "aok.workflow.effect-covenant.v0.1",
        "allowed_effect_classes": sorted({
            row["effect_class"] for row in request["requested_capabilities"]}),
        "capability_budget_roots": sorted({
            row["budget_root"] for row in request["requested_capabilities"]}),
        "authority_effect": "NONE",
        "external_authority_required": True,
        "three_gate_receipts_required": ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"],
    }, "effect_covenant_root")
    obligations = _rooted({
        "schema": "mosaic.ucm.workflow-obligation-contract.v0.1",
        "cm1": deepcopy(request["cm1_obligations"]),
        "cm2": deepcopy(request["cm2_preferences"]),
        "cm1_precedes_cm2": True,
        "architecture_candidate_root": request["architecture_candidate_root"],
        "work_package_root": request["work_package_root"],
        "policy_pack_roots": deepcopy(request["policy_pack_roots"]),
    }, "obligation_contract_root")
    body = {
        "schema": "mosaic.ucm.aok-vnext-workflow-ir.v0.1",
        "protocol": PROTOCOL,
        "request_root": request["request_root"],
        "campaign_root": request["campaign_root"],
        "application_id": request["application_id"],
        "identity_binding": deepcopy(request["identity_binding"]),
        "objective_ir": objective_ir,
        "workflow_ir": workflow_ir,
        "capability_ir": capability_ir,
        "ccba_lattice_binding": lattice,
        "realization_route": route,
        "effect_covenant": effect_covenant,
        "obligation_contract": obligations,
        "ownership": {
            "ucm": ["ARCHITECTURE_CONTRACT", "CM1", "CM2", "EVIDENCE_OBLIGATIONS", "IMPORT_VALIDATION"],
            "courthouse_vnext": ["CAPABILITY_RESOLUTION", "AUTHORITY", "EXECUTOR_SELECTION", "EFFECT_CUSTODY", "ADJUDICATION"],
            "shared_boundary": "WORKFLOW_IR_AND_THREE_GATE_RECEIPTS",
        },
        "non_claims": ["NOT_EXECUTION", "NOT_AUTHORITY_GRANT", "NOT_EXECUTOR_SELECTION", "NOT_COURTHOUSE_DISPOSITION"],
        **BOUNDARY,
    }
    return {**body, "workflow_root": root(body)}


def verify_compiled_workflow(request: Any, compiled: Any) -> dict[str, Any]:
    expected = compile_workflow_ir(request)
    require(compiled == expected, "UCM_COURTHOUSE_WORKFLOW_IR_MISMATCH")
    return deepcopy(expected)


def _gate_receipt(value: Any, *, gate: str, workflow_root: str,
                  predecessor: str, allowed_effects: set[str]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "gate", "workflow_root", "decision",
                              "predecessor_receipt_root", "observed_effect_classes",
                              "evidence_roots", "receipt_root"})
    require(item["schema"] == "mosaic.ucm.aok-vnext-gate-receipt.v0.1"
            and item["gate"] == gate and item["workflow_root"] == workflow_root,
            "UCM_COURTHOUSE_GATE_RECEIPT_INVALID")
    require(item["predecessor_receipt_root"] == predecessor,
            "UCM_COURTHOUSE_GATE_CHAIN_INVALID")
    require(item["decision"] in {"PASS", "REFUSED", "UNCERTAIN", "HOLD"},
            "UCM_COURTHOUSE_GATE_DECISION_INVALID")
    observed = set(_strings(item["observed_effect_classes"],
                            "UCM_COURTHOUSE_OBSERVED_EFFECT_INVALID"))
    require(observed <= allowed_effects, "UCM_COURTHOUSE_EFFECT_COVENANT_EXCEEDED")
    _strings(item["evidence_roots"], "UCM_COURTHOUSE_GATE_EVIDENCE_INVALID")
    for evidence_root in item["evidence_roots"]:
        require_root(evidence_root)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "receipt_root"}
    require(item["receipt_root"] == root(body), "UCM_COURTHOUSE_GATE_ROOT_INVALID")
    return deepcopy(item)


def validate_workflow_result(request_value: Any, compiled_value: Any,
                             result_value: Any) -> dict[str, Any]:
    request = validate_workflow_request(request_value)
    compiled = verify_compiled_workflow(request, compiled_value)
    item = exact_keys(result_value, {
        "schema", "workflow_root", "request_root", "courthouse_identity_root",
        "selected_realization_root", "selected_executor_root", "g1", "g2", "g3",
        "obligation_dispositions", "cm2_evaluated", "expected_journal_head",
        "successor_journal_head", "terminal_status", "standing", "authority_effect",
        "real_a5", "g0", "result_root",
    })
    require(item["schema"] == "mosaic.ucm.aok-vnext-workflow-result.v0.1"
            and item["workflow_root"] == compiled["workflow_root"]
            and item["request_root"] == request["request_root"],
            "UCM_COURTHOUSE_RESULT_BINDING_INVALID")
    for field in ("courthouse_identity_root", "selected_realization_root",
                  "selected_executor_root"):
        require_root(item[field])
    require(item["courthouse_identity_root"]
            == request["identity_binding"]["courthouse_identity_root"],
            "UCM_COURTHOUSE_IDENTITY_MISMATCH")
    allowed_effects = set(compiled["effect_covenant"]["allowed_effect_classes"])
    g1 = _gate_receipt(item["g1"], gate="G1_SENTINEL",
                       workflow_root=compiled["workflow_root"],
                       predecessor="GENESIS", allowed_effects=allowed_effects)
    require(not g1["observed_effect_classes"], "UCM_COURTHOUSE_G1_EFFECT_INVALID")
    g2 = _gate_receipt(item["g2"], gate="G2_WITNESS",
                       workflow_root=compiled["workflow_root"],
                       predecessor=g1["receipt_root"], allowed_effects=allowed_effects)
    g3 = _gate_receipt(item["g3"], gate="G3_DIAGNOSTIC",
                       workflow_root=compiled["workflow_root"],
                       predecessor=g2["receipt_root"], allowed_effects=allowed_effects)
    require(g1["decision"] in {"PASS", "REFUSED"},
            "UCM_COURTHOUSE_G1_DECISION_INVALID")
    require(g1["decision"] == "PASS" or not g2["observed_effect_classes"],
            "UCM_COURTHOUSE_EFFECT_WITHOUT_G1")

    declared = {row["obligation_id"] for row in request["cm1_obligations"]}
    required = {row["obligation_id"] for row in request["cm1_obligations"]
                if row["required"]}
    dispositions = item["obligation_dispositions"]
    require(type(dispositions) is list, "UCM_COURTHOUSE_DISPOSITION_INVALID")
    by_id = {}
    for row in dispositions:
        checked = exact_keys(row, {"obligation_id", "status", "evidence_roots"})
        require(type(checked["obligation_id"]) is str and checked["obligation_id"],
                "UCM_COURTHOUSE_DISPOSITION_INVALID")
        require(checked["status"] in {"PASS", "REFUSED", "NOT_EVALUATED"},
                "UCM_COURTHOUSE_DISPOSITION_INVALID")
        require(checked["obligation_id"] not in by_id,
                "UCM_COURTHOUSE_DISPOSITION_DUPLICATE")
        _strings(checked["evidence_roots"], "UCM_COURTHOUSE_DISPOSITION_INVALID")
        for evidence_root in checked["evidence_roots"]:
            require_root(evidence_root)
        by_id[checked["obligation_id"]] = checked
    require(set(by_id) <= declared, "UCM_COURTHOUSE_DISPOSITION_UNDECLARED")
    require(required <= set(by_id), "UCM_COURTHOUSE_REQUIRED_DISPOSITION_MISSING")
    require(type(item["cm2_evaluated"]) is bool, "UCM_COURTHOUSE_CM2_RESULT_INVALID")
    cm1_pass = all(by_id[obligation_id]["status"] == "PASS"
                   for obligation_id in required)
    require(not item["cm2_evaluated"] or cm1_pass,
            "UCM_COURTHOUSE_CM2_BEFORE_CM1")

    expected = _head(item["expected_journal_head"],
                     "UCM_COURTHOUSE_JOURNAL_HEAD_INVALID")
    successor = _head(item["successor_journal_head"],
                      "UCM_COURTHOUSE_JOURNAL_HEAD_INVALID")
    require(expected == request["expected_journal_head"],
            "UCM_COURTHOUSE_EXPECTED_HEAD_MISMATCH")
    require(successor["sequence"] >= expected["sequence"],
            "UCM_COURTHOUSE_SUCCESSOR_HEAD_INVALID")
    require(item["terminal_status"] in {"PASS", "REFUSED", "UNCERTAIN", "HOLD"},
            "UCM_COURTHOUSE_TERMINAL_STATUS_INVALID")
    if item["terminal_status"] == "PASS":
        require(g1["decision"] == g2["decision"] == g3["decision"] == "PASS"
                and cm1_pass, "UCM_COURTHOUSE_PASS_UNSUPPORTED")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_COURTHOUSE_RESULT_AUTHORITY_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "result_root"}
    require(item["result_root"] == root(body), "UCM_COURTHOUSE_RESULT_ROOT_INVALID")

    imported = {
        "schema": "mosaic.ucm.courthouse-result-import.v0.1",
        "workflow_root": compiled["workflow_root"],
        "result_root": item["result_root"],
        "expected_journal_head": expected,
        "successor_journal_head": successor,
        "cm1_status": "PASS" if cm1_pass else "REFUSED",
        "cm2_status": "EVALUATED" if item["cm2_evaluated"] else "NOT_EVALUATED",
        "terminal_status": item["terminal_status"],
        "status": "PASS_CORRESPONDENCE" if item["terminal_status"] == "PASS"
                  else "RECORDED_NONPASS",
        "non_claims": ["NOT_COURTHOUSE_AUTHORITY", "NOT_MERGE_AUTHORITY",
                       "NOT_REEXECUTION_OF_EVIDENCE"],
        **BOUNDARY,
    }
    return {**imported, "import_root": root(imported)}
