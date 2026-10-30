"""Deep semantic verification shared by c4 runtime and qualification."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .native_runner_c4 import validate_preflight
from .operation_state_c4 import validate_operation_state
from .stage4_c4 import validate_run_contract


SEMANTIC_CONTRACT_SCHEMA = "mosaic.ucm.stage-i4-c4-semantic-contract.v0.1"
RUNTIME_RESULT_SCHEMA = "mosaic.ucm.stage-i4-c4-runtime-result.v0.1"
POSITIVE_CONTROL_SCHEMA = "mosaic.ucm.stage-i4-c4-positive-control.v0.1"
QUALIFICATION_SCHEMA = "mosaic.ucm.stage-i4-c4-qualification.v0.1"


def _rooted(value: Any, *, schema: str, root_field: str, code: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema,
            code, detail="SCHEMA")
    require(value.get(root_field) == root({
        key: deepcopy(raw) for key, raw in value.items() if key != root_field
    }), code, detail="ROOT")
    require({key: value.get(key) for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    return deepcopy(value)


def _gate(value: Any, *, keys: set[str], schema: str, code: str) -> dict[str, Any]:
    item = exact_keys(value, keys | set(BOUNDARY) | {"receipt_root"})
    return _rooted(item, schema=schema, root_field="receipt_root", code=code)


def validate_terminal_operation(value: Any, *, expected_run_contract: Any,
                                expected_trust_anchors_root: str) -> dict[str, Any]:
    contract = validate_run_contract(
        expected_run_contract,
        expected_trust_anchors_root=expected_trust_anchors_root)
    item = exact_keys(value, {
        "schema", "run_contract_root", "trust_anchors_root",
        "execution_context_root", "native_preflight", "g1_sentinel",
        "g2_witness", "g3_diagnostic", "terminal_status",
        "effects_observed", "native_effect_executor_preserved", "standing",
        "authority_effect", "real_a5", "g0", "operation_root",
    })
    require(item["schema"] == "mosaic.ucm.stage-i4-terminal-operation.v0.2"
            and item["run_contract_root"] == contract["run_contract_root"]
            and item["trust_anchors_root"] == expected_trust_anchors_root
            and item["execution_context_root"] == contract["execution_context"]["context_root"],
            "STAGE_I4_TERMINAL_BINDING_INVALID")
    preflight = validate_preflight(
        item["native_preflight"], expected_run_contract=contract,
        expected_trust_anchors_root=expected_trust_anchors_root)
    g1 = _gate(item["g1_sentinel"], keys={"schema", "gate",
        "run_contract_root", "context_root", "trust_anchors_root",
        "preflight_root", "decision", "reason_codes"},
        schema="mosaic.ucm.integration-g1-receipt.v0.1",
        code="STAGE_I4_G1_RECEIPT_INVALID")
    require(g1.get("gate") == "G1_SENTINEL"
            and g1.get("run_contract_root") == contract["run_contract_root"]
            and g1.get("context_root") == contract["execution_context"]["context_root"]
            and g1.get("trust_anchors_root") == expected_trust_anchors_root
            and g1.get("preflight_root") == preflight["preflight_root"]
            and g1.get("decision") == "REFUSE"
            and g1.get("reason_codes") == [preflight["reason_code"]],
            "STAGE_I4_G1_SEMANTICS_INVALID")
    g2 = _gate(item["g2_witness"], keys={"schema", "gate",
        "run_contract_root", "g1_root", "dispatch_root", "native_receipt_root",
        "completion_status", "recovery_status", "case_results",
        "observed_effect_classes"},
        schema="mosaic.ucm.integration-g2-receipt.v0.1",
        code="STAGE_I4_G2_RECEIPT_INVALID")
    require(g2.get("gate") == "G2_WITNESS"
            and g2.get("run_contract_root") == contract["run_contract_root"]
            and g2.get("g1_root") == g1["receipt_root"]
            and g2.get("dispatch_root") is None
            and g2.get("native_receipt_root") is None
            and g2.get("completion_status") == "REFUSED"
            and g2.get("recovery_status") == "NOT_REQUIRED"
            and g2.get("case_results") == []
            and g2.get("observed_effect_classes") == [],
            "STAGE_I4_G2_SEMANTICS_INVALID")
    g3 = _gate(item["g3_diagnostic"], keys={"schema", "gate",
        "run_contract_root", "g2_root", "classification", "finding_codes",
        "next_action"},
        schema="mosaic.ucm.integration-g3-receipt.v0.1",
        code="STAGE_I4_G3_RECEIPT_INVALID")
    require(g3.get("gate") == "G3_DIAGNOSTIC"
            and g3.get("run_contract_root") == contract["run_contract_root"]
            and g3.get("g2_root") == g2["receipt_root"]
            and g3.get("classification") == "REFUSED"
            and g3.get("finding_codes") == [preflight["reason_code"]]
            and g3.get("next_action") == "ESTABLISH_EXTERNAL_AUTHORITY_AND_PINNED_NATIVE_BINDING",
            "STAGE_I4_G3_SEMANTICS_INVALID")
    require(item["terminal_status"] == "REFUSED"
            and item["effects_observed"] == []
            and item["native_effect_executor_preserved"] is True,
            "STAGE_I4_TERMINAL_SEMANTICS_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    require(item["operation_root"] == root({
        key: deepcopy(raw) for key, raw in item.items() if key != "operation_root"
    }), "STAGE_I4_TERMINAL_ROOT_INVALID")
    return deepcopy(item)


def validate_runtime_result(value: Any, *, expected_source_root: str,
                            expected_source_file_count: int,
                            expected_test_ids: list[str]) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "runtime", "source_graph_root", "source_file_count",
        "source_verified_before_and_after", "test_ids", "test_count",
        "test_set_root", "failures", "errors", "skips", "cache_policy",
        "status", "standing", "authority_effect", "real_a5", "g0",
        "runtime_result_root",
    })
    require(item["schema"] == RUNTIME_RESULT_SCHEMA
            and type(item["runtime"]) is str and bool(item["runtime"])
            and item["source_graph_root"] == require_root(expected_source_root)
            and item["source_file_count"] == expected_source_file_count
            and item["source_verified_before_and_after"] is True
            and item["test_ids"] == expected_test_ids
            and item["test_count"] == len(expected_test_ids)
            and item["test_set_root"] == root(expected_test_ids)
            and (item["failures"], item["errors"], item["skips"], item["status"])
                == (0, 0, 0, "PASS")
            and item["cache_policy"] == "CACHE_DISABLED",
            "STAGE_I4_RUNTIME_RESULT_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    require(item["runtime_result_root"] == root({
        key: deepcopy(raw) for key, raw in item.items()
        if key != "runtime_result_root"
    }), "STAGE_I4_RUNTIME_RESULT_ROOT_INVALID")
    return deepcopy(item)


def validate_positive_control(value: Any, *, expected_source_root: str,
                              expected_test_ids: list[str]) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "control_class", "source_root", "test_set_root",
        "checks", "status", "standing", "authority_effect", "real_a5", "g0",
        "control_root",
    })
    require(item["schema"] == POSITIVE_CONTROL_SCHEMA
            and item["control_class"] == "BUILDER_POSITIVE_ONLY"
            and item["source_root"] == expected_source_root
            and item["test_set_root"] == root(expected_test_ids)
            and type(item["checks"]) is list and bool(item["checks"])
            and all(type(row) is dict and row.get("status") == "PASS"
                    for row in item["checks"])
            and item["status"] == "PASS",
            "STAGE_I4_POSITIVE_CONTROL_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    require(item["control_root"] == root({
        key: deepcopy(raw) for key, raw in item.items() if key != "control_root"
    }), "STAGE_I4_POSITIVE_CONTROL_ROOT_INVALID")
    return deepcopy(item)


def validate_qualification(value: Any, *, expected_source_root: str,
                           expected_source_file_count: int,
                           expected_test_ids: list[str],
                           expected_semantic_contract_root: str,
                           expected_trust_anchors_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "qualification_class", "source_root", "source_file_count",
        "test_ids", "test_count", "test_set_root", "semantic_contract_root",
        "trust_anchors_root", "positive_control", "runtime_results",
        "operation_state", "failures", "errors", "skips", "status",
        "standing", "authority_effect", "real_a5", "g0", "qualification_root",
    })
    require(item["schema"] == QUALIFICATION_SCHEMA
            and item["qualification_class"] == "BUILDER_POSITIVE_QUALIFICATION"
            and item["source_root"] == require_root(expected_source_root)
            and item["source_file_count"] == expected_source_file_count
            and item["test_ids"] == expected_test_ids
            and item["test_count"] == len(expected_test_ids)
            and item["test_set_root"] == root(expected_test_ids)
            and item["semantic_contract_root"] == require_root(expected_semantic_contract_root)
            and item["trust_anchors_root"] == require_root(expected_trust_anchors_root),
            "STAGE_I4_QUALIFICATION_SUBJECT_INVALID")
    validate_positive_control(item["positive_control"],
        expected_source_root=expected_source_root,
        expected_test_ids=expected_test_ids)
    require(type(item["runtime_results"]) is list and bool(item["runtime_results"]),
            "STAGE_I4_QUALIFICATION_RUNTIME_INVALID")
    for row in item["runtime_results"]:
        validate_runtime_result(row, expected_source_root=expected_source_root,
            expected_source_file_count=expected_source_file_count,
            expected_test_ids=expected_test_ids)
    validate_operation_state(item["operation_state"])
    require((item["failures"], item["errors"], item["skips"], item["status"])
            == (0, 0, 0, "PASS"), "STAGE_I4_QUALIFICATION_STATUS_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    require(item["qualification_root"] == root({
        key: deepcopy(raw) for key, raw in item.items()
        if key != "qualification_root"
    }), "STAGE_I4_QUALIFICATION_ROOT_INVALID")
    return deepcopy(item)

