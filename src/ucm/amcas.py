"""Executable AMCAS integration contract and obligation-preserving projection.

This module is an INFORMATION_ONLY candidate.  It distinguishes admissible
membership (CM1) from preference ordering (CM2), and keeps both separate from
an exact realization configuration, implementation bytes, and evidence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root
from .realization import (
    project_to_ucl_tessera,
    validate_contract as validate_realization_contract,
)


LEGACY_SCHEMA = "mosaic.amcas.integration-contract.v0.1"
SCHEMA = "mosaic.amcas.integration-contract.v0.2"
LEGACY_IR_SCHEMA = "mosaic.amcas.integration-ir.v0.1"
IR_SCHEMA = "mosaic.amcas.integration-ir.v0.2"
REPORT_SCHEMA = "mosaic.amcas.integration-report.v0.1"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
EFFECT_CLASSES = {"PURE_COMPUTATION", "READ_ONLY", "LOCAL_ARTIFACT_PREPARATION",
                  "WRITE_WORKSPACE", "DELETE_WORKSPACE", "NETWORK", "INSTALL",
                  "PERSISTENT_HOST_STATE", "AUTHORITY_CHANGE"}
REQUIREMENT_KINDS = {"IDENTITY", "CAPABILITY", "EFFECT", "DEPENDENCY", "STATE",
                     "RECOVERY", "EVIDENCE", "PORTABILITY", "AGENT_INTERFACE",
                     "SEMANTIC", "ACCEPTANCE"}
DIRECTIONS = {"MINIMIZE", "MAXIMIZE", "LEXICOGRAPHIC"}


def _text(value: Any, code: str, maximum: int = 4096) -> str:
    require(type(value) is str and 0 < len(value) <= maximum and value == value.strip(), code)
    return value


def _identifier(value: Any, code: str) -> str:
    value = _text(value, code, 128)
    require(all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _unique_rows(value: Any, fields: set[str], id_field: str, code: str) -> list[dict[str, Any]]:
    require(type(value) is list, code)
    seen: set[str] = set()
    rows = []
    for raw in value:
        row = exact_keys(raw, fields)
        identifier = _identifier(row[id_field], code)
        require(identifier not in seen, code)
        seen.add(identifier)
        rows.append(deepcopy(row))
    return rows


def validate_contract(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") in {LEGACY_SCHEMA, SCHEMA},
            "AMCAS_SCHEMA_UNSUPPORTED")
    fields = {
        "schema", "integration_id", "application", "subject", "identities",
        "cm1", "cm2", "capabilities", "effects", "dependencies", "acceptance",
        "portability", "reporting", "realization_contract", "authority_ceiling",
        "contract_root",
    }
    if value["schema"] == SCHEMA:
        fields.add("integration_boundary")
    item = exact_keys(value, fields)
    _identifier(item["integration_id"], "AMCAS_INTEGRATION_ID_INVALID")
    app = exact_keys(item["application"], {"id", "name", "version"})
    _identifier(app["id"], "AMCAS_APPLICATION_ID_INVALID")
    _text(app["name"], "AMCAS_APPLICATION_NAME_INVALID", 256)
    _text(app["version"], "AMCAS_APPLICATION_VERSION_INVALID", 128)
    subject = exact_keys(item["subject"], {"source_root", "manifest_root", "path_policy"})
    require_root(subject["source_root"]); require_root(subject["manifest_root"])
    require(subject["path_policy"] == "PORTABLE_POSIX_RELATIVE_V1", "AMCAS_PATH_POLICY_UNSUPPORTED")

    identities = exact_keys(item["identities"], {
        "user_required", "agent_required", "jurisdiction", "session_distinct",
        "possession_required", "delegation_required",
    })
    require(all(type(identities[name]) is bool for name in (
        "user_required", "agent_required", "session_distinct", "possession_required",
        "delegation_required")), "AMCAS_IDENTITY_POLICY_INVALID")
    jurisdiction = exact_keys(identities["jurisdiction"], {
        "namespace_id", "universe_root", "epoch_id", "semantic_namespace",
    })
    _identifier(jurisdiction["namespace_id"], "AMCAS_NAMESPACE_INVALID")
    require(jurisdiction["universe_root"] is None or
            require_root(jurisdiction["universe_root"]), "AMCAS_UNIVERSE_INVALID")
    require(jurisdiction["epoch_id"] is None or type(jurisdiction["epoch_id"]) is str,
            "AMCAS_EPOCH_INVALID")
    require(jurisdiction["semantic_namespace"] is None or
            type(jurisdiction["semantic_namespace"]) is str,
            "AMCAS_SEMANTIC_NAMESPACE_INVALID")

    cm1 = exact_keys(item["cm1"], {"requirements", "membership_policy"})
    require(cm1["membership_policy"] == "ALL_APPLICABLE_REQUIREMENTS_PASS",
            "AMCAS_CM1_POLICY_UNSUPPORTED")
    requirements = _unique_rows(cm1["requirements"], {
        "id", "kind", "statement", "subject_root", "verifier", "evidence_required",
        "applicability",
    }, "id", "AMCAS_CM1_REQUIREMENT_INVALID")
    for row in requirements:
        require(row["kind"] in REQUIREMENT_KINDS, "AMCAS_CM1_KIND_UNSUPPORTED")
        _text(row["statement"], "AMCAS_CM1_STATEMENT_INVALID")
        require_root(row["subject_root"])
        _identifier(row["verifier"], "AMCAS_CM1_VERIFIER_INVALID")
        require(type(row["evidence_required"]) is bool and
                row["applicability"] in {"REQUIRED", "CONDITIONAL", "NOT_APPLICABLE"},
                "AMCAS_CM1_REQUIREMENT_INVALID")

    cm2 = exact_keys(item["cm2"], {"preferences", "selection_policy"})
    require(cm2["selection_policy"] == "CM1_THEN_CM2_LEXICOGRAPHIC",
            "AMCAS_CM2_POLICY_UNSUPPORTED")
    preferences = _unique_rows(cm2["preferences"], {
        "id", "objective", "priority", "metric", "direction",
    }, "id", "AMCAS_CM2_PREFERENCE_INVALID")
    priorities = []
    for row in preferences:
        _text(row["objective"], "AMCAS_CM2_OBJECTIVE_INVALID")
        require(type(row["priority"]) is int and row["priority"] >= 0,
                "AMCAS_CM2_PRIORITY_INVALID")
        _identifier(row["metric"], "AMCAS_CM2_METRIC_INVALID")
        require(row["direction"] in DIRECTIONS, "AMCAS_CM2_DIRECTION_INVALID")
        priorities.append(row["priority"])
    require(len(priorities) == len(set(priorities)), "AMCAS_CM2_PRIORITY_DUPLICATE")

    capabilities = _unique_rows(item["capabilities"], {
        "id", "route", "effect_class", "required", "request_schema", "result_schema",
    }, "id", "AMCAS_CAPABILITY_INVALID")
    for row in capabilities:
        _identifier(row["route"], "AMCAS_CAPABILITY_ROUTE_INVALID")
        require(row["effect_class"] in EFFECT_CLASSES and type(row["required"]) is bool,
                "AMCAS_CAPABILITY_INVALID")
        _identifier(row["request_schema"], "AMCAS_CAPABILITY_SCHEMA_INVALID")
        _identifier(row["result_schema"], "AMCAS_CAPABILITY_SCHEMA_INVALID")

    effects = _unique_rows(item["effects"], {
        "id", "capability_id", "effect_class", "operation", "ceiling",
    }, "id", "AMCAS_EFFECT_INVALID")
    capability_ids = {row["id"] for row in capabilities}
    for row in effects:
        require(row["capability_id"] in capability_ids and row["effect_class"] in EFFECT_CLASSES,
                "AMCAS_EFFECT_CAPABILITY_MISMATCH")
        require(row["effect_class"] == next(capability["effect_class"] for capability in capabilities
                                             if capability["id"] == row["capability_id"]),
                "AMCAS_EFFECT_CLASS_MISMATCH")
        _identifier(row["operation"], "AMCAS_EFFECT_OPERATION_INVALID")
        require(row["ceiling"] == "NONE", "AMCAS_EFFECT_CEILING_BROADENED")

    dependencies = _unique_rows(item["dependencies"], {
        "id", "kind", "root", "required",
    }, "id", "AMCAS_DEPENDENCY_INVALID")
    for row in dependencies:
        require(row["kind"] in {"SOURCE", "TOOL", "CONTRACT", "ARTIFACT", "SERVICE"}
                and type(row["required"]) is bool, "AMCAS_DEPENDENCY_INVALID")
        require_root(row["root"])

    acceptance = _unique_rows(item["acceptance"], {
        "id", "obligation", "evidence_schema", "required",
    }, "id", "AMCAS_ACCEPTANCE_INVALID")
    for row in acceptance:
        _identifier(row["obligation"], "AMCAS_ACCEPTANCE_OBLIGATION_INVALID")
        _identifier(row["evidence_schema"], "AMCAS_ACCEPTANCE_SCHEMA_INVALID")
        require(type(row["required"]) is bool, "AMCAS_ACCEPTANCE_INVALID")

    portability = exact_keys(item["portability"], {
        "profiles", "journal_export_required", "offline_closure_required",
    })
    require(type(portability["profiles"]) is list and bool(portability["profiles"])
            and len(portability["profiles"]) == len(set(portability["profiles"]))
            and all(type(profile) is str and bool(profile) for profile in portability["profiles"]),
            "AMCAS_PORTABILITY_PROFILE_INVALID")
    require(type(portability["journal_export_required"]) is bool and
            type(portability["offline_closure_required"]) is bool,
            "AMCAS_PORTABILITY_POLICY_INVALID")
    reporting = exact_keys(item["reporting"], {"required_sections", "progress_channel"})
    require(type(reporting["required_sections"]) is list and
            len(reporting["required_sections"]) == len(set(reporting["required_sections"]))
            and all(type(name) is str and bool(name) for name in reporting["required_sections"]),
            "AMCAS_REPORTING_INVALID")
    require(reporting["progress_channel"] == "NONSEMANTIC_JSONL_V1",
            "AMCAS_PROGRESS_CHANNEL_UNSUPPORTED")

    if item["schema"] == SCHEMA:
        boundary = exact_keys(item["integration_boundary"], {
            "semantic_authority", "effect_executor", "identity_binding_status",
            "jurisdiction_binding_status", "gate_namespace", "control_plane_root",
        })
        for field in ("semantic_authority", "effect_executor"):
            _identifier(boundary[field], "AMCAS_INTEGRATION_OWNER_INVALID")
        require(boundary["identity_binding_status"] in {"UNBOUND", "PROPOSED", "BOUND"},
                "AMCAS_IDENTITY_BINDING_STATUS_INVALID")
        require(boundary["jurisdiction_binding_status"] in {"UNBOUND", "PROPOSED", "BOUND"},
                "AMCAS_JURISDICTION_BINDING_STATUS_INVALID")
        require(boundary["gate_namespace"] == "UCM.INTEGRATION",
                "AMCAS_GATE_NAMESPACE_INVALID")
        require_root(boundary["control_plane_root"])

    realization = validate_realization_contract(item["realization_contract"])
    require(item["realization_contract"] == realization,
            "AMCAS_REALIZATION_CONTRACT_ROOT_REQUIRED")
    require(item["authority_ceiling"] == BOUNDARY, "AMCAS_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "contract_root"}
    require(item["contract_root"] == root(body), "AMCAS_CONTRACT_ROOT_MISMATCH")
    return deepcopy(item)


def compile_contract(value: Any) -> dict[str, Any]:
    item = validate_contract(value)
    realization_projection = project_to_ucl_tessera(item["realization_contract"])
    obligations: list[dict[str, Any]] = []
    for requirement in item["cm1"]["requirements"]:
        if requirement["applicability"] != "NOT_APPLICABLE":
            obligations.append({
                "id": f"CM1:{requirement['id']}", "kind": requirement["kind"],
                "subject_root": requirement["subject_root"],
                "verifier": requirement["verifier"],
                "evidence_required": requirement["evidence_required"],
                "source": "CM1", "required": requirement["applicability"] == "REQUIRED",
            })
    for capability in item["capabilities"]:
        obligations.append({
            "id": f"CAPABILITY:{capability['id']}", "kind": "CAPABILITY",
            "subject_root": root(capability), "verifier": "AMCAS_CAPABILITY_BINDING_V1",
            "evidence_required": capability["required"], "source": "CAPABILITY",
            "required": capability["required"],
        })
    for effect in item["effects"]:
        obligations.append({
            "id": f"EFFECT:{effect['id']}", "kind": "EFFECT",
            "subject_root": root(effect), "verifier": "UGK_THREE_GATE_RECEIPT_V1",
            "evidence_required": True, "source": "EFFECT", "required": True,
        })
    for acceptance in item["acceptance"]:
        obligations.append({
            "id": f"ACCEPTANCE:{acceptance['id']}", "kind": "ACCEPTANCE",
            "subject_root": root(acceptance), "verifier": acceptance["evidence_schema"],
            "evidence_required": acceptance["required"], "source": "ACCEPTANCE",
            "required": acceptance["required"],
        })
    obligations.sort(key=lambda row: row["id"])
    body = {
        "schema": IR_SCHEMA if item["schema"] == SCHEMA else LEGACY_IR_SCHEMA,
        "contract_root": item["contract_root"],
        "integration_id": item["integration_id"],
        "application": deepcopy(item["application"]),
        "subject": deepcopy(item["subject"]),
        "identity_policy": deepcopy(item["identities"]),
        "cm1": {"membership_policy": item["cm1"]["membership_policy"],
                "obligation_ids": [row["id"] for row in obligations if row["source"] == "CM1"]},
        "cm2": deepcopy(item["cm2"]),
        "obligations": obligations,
        "realization_contract_root": item["realization_contract"]["root"],
        "realization_projection": realization_projection,
        "native_proof_route": {
            "capability": "VERIFY_NATIVE_PROOF",
            "proof_schema": "mosaic.ucm.native-proof.v0.1",
            "policy": "EXACT_OBLIGATION_SUBJECT_AND_FORMULA_ROOT",
        },
        "required_report_sections": deepcopy(item["reporting"]["required_sections"]),
        "portability": deepcopy(item["portability"]), **BOUNDARY,
    }
    if item["schema"] == SCHEMA:
        body["integration_boundary"] = deepcopy(item["integration_boundary"])
    return {**body, "ir_root": root(body)}


def verify_report(contract: Any, report: Any) -> dict[str, Any]:
    item = validate_contract(contract)
    compiled = compile_contract(item)
    report = exact_keys(report, {
        "schema", "contract_root", "ir_root", "journal_head", "application_source_root",
        "requirements", "capabilities", "operations", "findings", "limitations",
        "portable_artifacts", "status", "standing", "authority_effect", "real_a5", "g0",
        "report_root",
    })
    require(report["schema"] == REPORT_SCHEMA and report["contract_root"] == item["contract_root"]
            and report["ir_root"] == compiled["ir_root"], "AMCAS_REPORT_BINDING_INVALID")
    require_root(report["journal_head"]); require_root(report["application_source_root"])
    require(report["application_source_root"] == item["subject"]["source_root"],
            "AMCAS_REPORT_SUBJECT_MISMATCH")
    for field in ("requirements", "capabilities", "operations", "findings", "limitations",
                  "portable_artifacts"):
        require(type(report[field]) is list, "AMCAS_REPORT_FIELD_INVALID")
    require(report["status"] in {"IN_PROGRESS", "READY_FOR_REVIEW", "QUALIFIED_RECOMMENDATION_ONLY",
                                  "HOLD_FOR_REPAIR", "INCOMPLETE_REVIEW"},
            "AMCAS_REPORT_STATUS_INVALID")
    require({key: report[key] for key in BOUNDARY} == BOUNDARY, "AMCAS_REPORT_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in report.items() if key != "report_root"}
    require(report["report_root"] == root(body), "AMCAS_REPORT_ROOT_MISMATCH")
    return deepcopy(report)


def make_contract(**fields: Any) -> dict[str, Any]:
    body = {"schema": SCHEMA, **deepcopy(fields), "authority_ceiling": deepcopy(BOUNDARY)}
    return validate_contract({**body, "contract_root": root(body)})
