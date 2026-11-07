from __future__ import annotations

import html
import json
import pathlib
from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, root
from .dependencies import assess_impact, build_graph, recovery_plan
from .eligibility import solve, verify_result
from .pipeline import compile_contract
from .resources import ReservationLedger


SUPPORTED_CONSTRAINTS = {
    "Use only edges carrying every required label",
    "Reserve the declared resource envelope before traversal",
    "Retain exact intent and jurisdiction roots",
}
SUPPORTED_ACCEPTANCE = {
    "Return an eligibility result with a replayable witness",
    "Preserve every CRU obligation through compilation",
    "Result must be eligible",
}
REQUIRED_EXCLUSIONS = {"ADMISSION", "EXTERNAL_EFFECTS", "G0_OPEN", "PRODUCTION", "PUBLICATION", "REAL_A5", "RELEASE"}


def validate_intent(value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "schema",
            "intent_id",
            "objective",
            "jurisdiction",
            "actors",
            "constraints",
            "acceptance",
            "exclusions",
            "source_refs",
            "problem",
            "resource_budget",
        },
        "$.intent",
    )
    require(item["schema"] == "ucl.hlir.intent.v1", "HLIR_INTENT_SCHEMA_INVALID")
    for field in ("intent_id", "objective", "jurisdiction"):
        require(type(item[field]) is str and item[field], "HLIR_INTENT_FIELD_INVALID", f"$.intent.{field}")
    for field in ("actors", "constraints", "acceptance", "exclusions", "source_refs"):
        require(type(item[field]) is list and all(type(entry) is str and entry for entry in item[field]), "HLIR_INTENT_LIST_INVALID", f"$.intent.{field}")
        require(len(item[field]) == len(set(item[field])), "HLIR_INTENT_LIST_DUPLICATE", f"$.intent.{field}")
    require(set(item["constraints"]) == SUPPORTED_CONSTRAINTS, "HLIR_CONSTRAINT_SEMANTICS_UNSUPPORTED")
    require(set(item["acceptance"]) == SUPPORTED_ACCEPTANCE, "HLIR_ACCEPTANCE_SEMANTICS_UNSUPPORTED")
    require(set(item["exclusions"]) == REQUIRED_EXCLUSIONS, "HLIR_CONSTITUTIONAL_EXCLUSIONS_UNSUPPORTED")
    from .eligibility import validate_problem
    from .resources import validate_budget

    validate_problem(item["problem"])
    validate_budget(item["resource_budget"])
    return deepcopy(item)


def tessera_projection(intent_value: dict[str, Any]) -> dict[str, Any]:
    intent = validate_intent(intent_value)
    clauses = [{"clause_id": "OBJECTIVE-001", "family": "OBJECTIVE", "text": intent["objective"]}]
    for family in ("constraints", "acceptance", "exclusions"):
        for index, text in enumerate(intent[family], 1):
            clauses.append({"clause_id": f"{family.upper()}-{index:03d}", "family": family.upper(), "text": text})
    body = {
        "schema": "ucl.tessera.intent_projection.v1",
        "intent_root": root(intent),
        "objective": intent["objective"],
        "jurisdiction": intent["jurisdiction"],
        "actors": sorted(intent["actors"]),
        "clauses": clauses,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "tessera_root": root(body)}


def build_cru(intent_value: dict[str, Any], tessera: dict[str, Any]) -> dict[str, Any]:
    intent = validate_intent(intent_value)
    require(tessera == tessera_projection(intent), "TESSERA_PROJECTION_MISMATCH")
    eligibility_subject = {
        "kind": "ELIGIBILITY_DECISION",
        "problem_root": root(intent["problem"]),
        "required_outcome": True,
    }
    obligations = [
        {
            "id": "O1_INTENT_IDENTITY",
            "kind": "IDENTITY",
            "statement": "The exact human intent remains bound through every representation.",
            "source_ref": f"intent:{intent['intent_id']}",
            "evidence_subject": {"kind": "INTENT_IDENTITY", "intent_root": root(intent)},
            "assumptions": [],
            "required_evidence": ["INTENT_ROOT"],
            "severity": "CRITICAL",
        },
        {
            "id": "O2_JURISDICTION",
            "kind": "AUTHORITY",
            "statement": "The computation remains within the declared jurisdiction and effect ceiling.",
            "source_ref": f"jurisdiction:{intent['jurisdiction']}",
            "assumptions": ["jurisdiction label is information-only in this experiment"],
            "required_evidence": ["JURISDICTION_BINDING"],
            "severity": "CRITICAL",
        },
        {
            "id": "O3_ELIGIBILITY_SEMANTICS",
            "kind": "SEMANTIC",
            "statement": "Only a path satisfying every required label may establish eligibility.",
            "source_ref": "intent:problem",
            "evidence_subject": eligibility_subject,
            "assumptions": ["problem snapshot is immutable"],
            "required_evidence": ["ELIGIBILITY_WITNESS"],
            "severity": "HIGH",
        },
        {
            "id": "O4_RESOURCE_ENVELOPE",
            "kind": "RESOURCE",
            "statement": "Execution stays within the exact declared resource budget.",
            "source_ref": "intent:resource_budget",
            "assumptions": ["resource accounting is local and deterministic"],
            "required_evidence": ["RESOURCE_RECEIPT"],
            "severity": "HIGH",
        },
        {
            "id": "O5_NO_EFFECT",
            "kind": "EFFECT",
            "statement": "No admission, authority, host, network, publication, or production effect occurs.",
            "source_ref": "intent:exclusions",
            "assumptions": [],
            "required_evidence": ["NO_EFFECT_RECEIPT"],
            "severity": "CRITICAL",
        },
    ]
    clause_bindings = []
    clause_to_obligations = {
        intent["objective"]: ["O1_INTENT_IDENTITY"],
        "Use only edges carrying every required label": ["O3_ELIGIBILITY_SEMANTICS"],
        "Reserve the declared resource envelope before traversal": ["O4_RESOURCE_ENVELOPE"],
        "Retain exact intent and jurisdiction roots": ["O1_INTENT_IDENTITY", "O2_JURISDICTION"],
        "Return an eligibility result with a replayable witness": ["O3_ELIGIBILITY_SEMANTICS"],
        "Preserve every CRU obligation through compilation": [item["id"] for item in obligations],
        "Result must be eligible": ["O3_ELIGIBILITY_SEMANTICS"],
    }
    for clause in tessera["clauses"]:
        targets = clause_to_obligations.get(clause["text"])
        if clause["family"] == "EXCLUSIONS":
            targets = ["O2_JURISDICTION", "O5_NO_EFFECT"]
        require(bool(targets), "TESSERA_CLAUSE_UNBOUND", clause["clause_id"])
        clause_bindings.append({"clause_id": clause["clause_id"], "obligation_ids": sorted(targets)})
    body = {
        "schema": "ucl.cru.v1",
        "intent_root": root(intent),
        "tessera_root": tessera["tessera_root"],
        "obligations": obligations,
        "clause_bindings": clause_bindings,
        "eligibility_evidence_subject": eligibility_subject,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "cru_root": root(body)}


def build_bcr(intent_value: dict[str, Any], cru: dict[str, Any]) -> dict[str, Any]:
    intent = validate_intent(intent_value)
    expected_cru = build_cru(intent, tessera_projection(intent))
    require(cru == expected_cru, "CRU_RECONSTRUCTION_MISMATCH")
    contract = {
        "schema": "ucl.op.operation_contract.v1",
        "contract_id": intent["intent_id"],
        "operation_kind": "PURE_ELIGIBILITY",
        "problem": deepcopy(intent["problem"]),
        "resource_budget": deepcopy(intent["resource_budget"]),
        "allowed_effects": [],
        "claim_ceiling": "INFORMATION_ONLY",
        "obligations": deepcopy(cru["obligations"]),
    }
    from .pipeline import validate_contract

    contract = validate_contract(contract)
    body = {
        "schema": "ucl.bcr.v1",
        "intent_root": root(intent),
        "cru_root": cru["cru_root"],
        "operation_contract": contract,
        "resource_budget": deepcopy(intent["resource_budget"]),
        "effect_ceiling": "NONE",
        "claim_ceiling": "INFORMATION_ONLY",
    }
    return {**body, "bcr_root": root(body)}


def compile_constitutional_intent(intent_value: dict[str, Any]) -> dict[str, Any]:
    intent = validate_intent(intent_value)
    tessera = tessera_projection(intent)
    cru = build_cru(intent, tessera)
    bcr = build_bcr(intent, cru)
    compilation = compile_contract(bcr["operation_contract"])
    body = {
        "schema": "ucl.constitutional_compilation.v1",
        "intent": intent,
        "tessera": tessera,
        "cru": cru,
        "bcr": bcr,
        "compilation": compilation,
        "binding_chain": [
            {"from": root(intent), "to": tessera["tessera_root"], "relation": "PROJECTS"},
            {"from": tessera["tessera_root"], "to": cru["cru_root"], "relation": "CONSTITUTES"},
            {"from": cru["cru_root"], "to": bcr["bcr_root"], "relation": "BOUNDS"},
            {"from": bcr["bcr_root"], "to": compilation["compilation_root"], "relation": "COMPILES"},
        ],
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "constitutional_compilation_root": root(body)}


def validate_constitutional_compilation(value: Any) -> dict[str, Any]:
    require(type(value) is dict and type(value.get("intent")) is dict, "CONSTITUTIONAL_COMPILATION_SHAPE_INVALID")
    expected = compile_constitutional_intent(value["intent"])
    require(value == expected, "CONSTITUTIONAL_COMPILATION_RECONSTRUCTION_MISMATCH")
    return expected


def execute_constitutional_intent(compiled: dict[str, Any]) -> dict[str, Any]:
    compiled = validate_constitutional_compilation(compiled)
    contract = compiled["bcr"]["operation_contract"]
    ledger = ReservationLedger(contract["resource_budget"])
    result = solve(contract["problem"], ledger)
    evidence_subject = compiled["cru"]["eligibility_evidence_subject"]
    require(
        result["eligible"] is evidence_subject["required_outcome"],
        "CONSTITUTIONAL_ACCEPTANCE_OUTCOME_MISMATCH",
    )
    verification = verify_result(contract["problem"], result)
    resources = ledger.snapshot()
    body = {
        "schema": "ucl.constitutional_execution_receipt.v1",
        "constitutional_compilation_root": compiled["constitutional_compilation_root"],
        "intent_root": root(compiled["intent"]),
        "cru_root": compiled["cru"]["cru_root"],
        "bcr_root": compiled["bcr"]["bcr_root"],
        "compilation_root": compiled["compilation"]["compilation_root"],
        "result": result,
        "verification": verification,
        "resources": resources,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "execution_receipt_root": root(body)}


def build_requalification_bundle(compiled: dict[str, Any], execution: dict[str, Any], changed_root: str) -> dict[str, Any]:
    compiled = validate_constitutional_compilation(compiled)
    require(execution == execute_constitutional_intent(compiled), "EXECUTION_RECEIPT_RECONSTRUCTION_MISMATCH")
    materials = [
        {"id": "intent", "root": root(compiled["intent"]), "kind": "HLIR_INTENT"},
        {"id": "cru", "root": compiled["cru"]["cru_root"], "kind": "CRU"},
        {"id": "bcr", "root": compiled["bcr"]["bcr_root"], "kind": "BCR"},
        {"id": "compiler", "root": compiled["compilation"]["compilation_root"], "kind": "COMPILER"},
        {"id": "execution", "root": execution["execution_receipt_root"], "kind": "EXECUTION_RECEIPT"},
    ]
    claims = [
        {"id": "meaning-bound", "statement": "The realization remains bound to the human intent and CRU.", "status": "SUPPORTED"},
        {"id": "execution-verified", "statement": "The bounded execution result was independently recomputed by its checker.", "status": "SUPPORTED"},
    ]
    graph = build_graph(materials, claims, [
        {"material_id": "intent", "claim_id": "meaning-bound", "kind": "DERIVES", "evidence_root": compiled["tessera"]["tessera_root"]},
        {"material_id": "cru", "claim_id": "meaning-bound", "kind": "CHECKS", "evidence_root": compiled["cru"]["cru_root"]},
        {"material_id": "bcr", "claim_id": "execution-verified", "kind": "LOWERS", "evidence_root": compiled["bcr"]["bcr_root"]},
        {"material_id": "compiler", "claim_id": "execution-verified", "kind": "LOWERS", "evidence_root": compiled["compilation"]["compilation_root"]},
        {"material_id": "execution", "claim_id": "execution-verified", "kind": "CHECKS", "evidence_root": execution["verification"]["verification_root"]},
    ], [{"from_claim_id": "meaning-bound", "to_claim_id": "execution-verified", "kind": "REQUIRES", "evidence_root": compiled["cru"]["cru_root"]}])
    impact = assess_impact(graph, {"compiler": changed_root})
    plan = recovery_plan(graph, impact)
    body = {
        "schema": "ucl.constitutional_requalification.v1",
        "graph": graph,
        "impact": impact,
        "recovery_plan": plan,
        "automatic_reinstatement": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "requalification_root": root(body)}


def constitutional_flow(compiled: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    compiled = validate_constitutional_compilation(compiled)
    expected_execution = execute_constitutional_intent(compiled)
    require(execution == expected_execution, "CONSTITUTIONAL_EXECUTION_RECEIPT_INVALID")
    stage_nodes = [
        {"id": "HLIR", "kind": "HUMAN_INTENT", "status": "PASS_DERIVED", "root": root(compiled["intent"])},
        {"id": "TESSERA", "kind": "INTENT_PROJECTION", "status": "PASS_DERIVED", "root": compiled["tessera"]["tessera_root"]},
        {"id": "CRU", "kind": "CONSTITUTIONAL_REQUIREMENTS", "status": "PASS_DERIVED", "root": compiled["cru"]["cru_root"]},
        {"id": "BCR", "kind": "BOUNDED_COMPUTATION_REQUEST", "status": "PASS_DERIVED", "root": compiled["bcr"]["bcr_root"]},
        *[
            {"id": stage["pass_id"], "kind": "COMPILER_PASS", "status": stage["status"], "root": stage["output_root"]}
            for stage in compiled["compilation"]["stages"]
        ],
        {"id": "EXECUTE", "kind": "BOUNDED_EXECUTION", "status": "PASS_VERIFIED", "root": execution["result"]["result_root"]},
        {"id": "VERIFY", "kind": "RESULT_CHECKER", "status": execution["verification"]["status"], "root": execution["verification"]["verification_root"]},
        {"id": "RECEIPT", "kind": "EXECUTION_RECEIPT", "status": "PASS_DERIVED", "root": execution["execution_receipt_root"]},
    ]
    body = {
        "schema": "ucl.constitutional_flow.v1",
        "nodes": stage_nodes,
        "edges": [{"from": stage_nodes[index - 1]["id"], "to": stage_nodes[index]["id"]} for index in range(1, len(stage_nodes))],
        "derived_from": [compiled["constitutional_compilation_root"], execution["execution_receipt_root"]],
        "all_statuses_recomputed": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "flow_root": root(body)}


def constitutional_flow_html(compiled: dict[str, Any], execution: dict[str, Any], flow: dict[str, Any]) -> bytes:
    expected = constitutional_flow(compiled, execution)
    require(flow == expected, "CONSTITUTIONAL_FLOW_RECONSTRUCTION_MISMATCH")
    cards = "".join(
        "<article class='stage' data-status='" + html.escape(node["status"]) + "'>"
        + "<b>" + html.escape(node["id"]) + "</b><span>" + html.escape(node["kind"]) + "</span>"
        + "<em>" + html.escape(node["status"]) + "</em><code>" + html.escape(node["root"][:16]) + "…</code></article>"
        for node in flow["nodes"]
    )
    payload = html.escape(json.dumps(flow, sort_keys=True, separators=(",", ":")))
    document = f"""<!doctype html><meta charset=utf-8><title>UCL constitutional computation</title>
<style>body{{font:15px system-ui;margin:0;background:#0d1320;color:#e9f1ff}}header{{padding:1.5rem 2rem;background:#151f31;position:sticky;top:0}}main{{padding:2rem;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1rem}}.stage{{padding:1rem;border:1px solid #32435f;border-radius:12px;background:#172337;display:grid;gap:.45rem}}.stage:after{{content:'↓';position:absolute}}b{{color:#80d8ff}}span{{color:#bdcbe1}}em{{color:#9ee6a8;font-style:normal}}code{{font-size:.8rem;color:#ffd580}}details{{margin:0 2rem 2rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<header><h1>Executable constitutional computation</h1><p>Every status is recomputed from exact bound artifacts. Standing: INFORMATION_ONLY. Authority effect: NONE.</p><p>Flow root <code>{flow['flow_root']}</code></p></header><main>{cards}</main><details><summary>Exact canonical projection</summary><pre>{payload}</pre></details>"""
    return document.encode("utf-8")


def write_constitutional_outputs(workspace: pathlib.Path, evidence: pathlib.Path, visualization: pathlib.Path) -> dict[str, Any]:
    intent = json.loads((workspace / "fixtures" / "constitutional-intent.json").read_text(encoding="utf-8"))
    compiled = compile_constitutional_intent(intent)
    execution = execute_constitutional_intent(compiled)
    requalification = build_requalification_bundle(compiled, execution, root({"successor": compiled["compilation"]["compilation_root"]}))
    flow = constitutional_flow(compiled, execution)
    evidence.mkdir(parents=True, exist_ok=True); visualization.mkdir(parents=True, exist_ok=True)
    (evidence / "CONSTITUTIONAL-COMPILATION.json").write_bytes(canonical_bytes(compiled) + b"\n")
    (evidence / "CONSTITUTIONAL-EXECUTION-RECEIPT.json").write_bytes(canonical_bytes(execution) + b"\n")
    (evidence / "CONSTITUTIONAL-REQUALIFICATION.json").write_bytes(canonical_bytes(requalification) + b"\n")
    (visualization / "constitutional-flow.json").write_bytes(canonical_bytes(flow) + b"\n")
    (visualization / "constitutional-flow.html").write_bytes(constitutional_flow_html(compiled, execution, flow))
    return {
        "constitutional_compilation_root": compiled["constitutional_compilation_root"],
        "execution_receipt_root": execution["execution_receipt_root"],
        "requalification_root": requalification["requalification_root"],
        "constitutional_flow_root": flow["flow_root"],
    }
