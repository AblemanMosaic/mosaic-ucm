"""One semantic verification surface shared by runtime, qualification and freeze."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root
from .amcas import BOUNDARY
from .operation_state import validate_operation_state
from .stage4_c3 import (RUN_CONTRACT_SCHEMA, TERMINAL_SCHEMA,
                        validate_execution_context)


CONTRACT_SCHEMA = "mosaic.ucm.stage-i4-c3-semantic-contract.v0.1"
QUALIFICATION_SCHEMA = "mosaic.ucm.stage-i4-c3-qualification.v0.1"


def validate_run_contract_shape(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == RUN_CONTRACT_SCHEMA,
            "STAGE_I4_RUN_CONTRACT_SCHEMA_INVALID")
    require(value.get("run_contract_root") == root({k: deepcopy(v) for k, v in value.items()
            if k != "run_contract_root"}), "STAGE_I4_RUN_CONTRACT_ROOT_INVALID")
    require(value.get("execution_authorized") is False
            and value.get("application_contact_authorized") is False
            and value.get("composition_authorized") is False,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    validate_execution_context(value.get("execution_context"))
    require(value.get("gate_requirements") == ["UCM.INTEGRATION.G1",
            "UCM.INTEGRATION.G2", "UCM.INTEGRATION.G3"],
            "STAGE_I4_GATE_SET_INVALID")
    require({key: value.get(key) for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    return deepcopy(value)


def validate_terminal_operation(value: Any, *, expected_run_contract: Any) -> dict[str, Any]:
    contract = validate_run_contract_shape(expected_run_contract)
    require(type(value) is dict and value.get("schema") == TERMINAL_SCHEMA,
            "STAGE_I4_TERMINAL_SCHEMA_INVALID")
    require(value.get("run_contract_root") == contract["run_contract_root"],
            "STAGE_I4_TERMINAL_BINDING_INVALID")
    require(value.get("operation_root") == root({k: deepcopy(v) for k, v in value.items()
            if k != "operation_root"}), "STAGE_I4_TERMINAL_ROOT_INVALID")
    require({key: value.get(key) for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    return deepcopy(value)


def validate_qualification(value: Any, *, expected_source_root: str,
                           expected_test_ids: list[str],
                           expected_contract_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "qualification_source_sha256",
        "qualification_source_manifest_root", "source_root", "source_file_count",
        "test_ids", "test_count", "test_set_root", "failures", "errors", "skips",
        "semantic_contract_root", "operator_evidence_sha256", "operator_result_root",
        "operator_case_count", "runtime_results", "operation_state", "status",
        "standing", "authority_effect", "real_a5", "g0", "qualification_root"})
    require(item["schema"] == QUALIFICATION_SCHEMA,
            "STAGE_I4_QUALIFICATION_SCHEMA_INVALID")
    require(item["source_root"] == require_root(expected_source_root)
            and item["test_ids"] == expected_test_ids
            and item["test_count"] == len(expected_test_ids),
            "STAGE_I4_QUALIFICATION_SUBJECT_INVALID")
    require(item["test_set_root"] == root(expected_test_ids),
            "STAGE_I4_QUALIFICATION_TEST_SET_INVALID")
    require(item["semantic_contract_root"] == require_root(expected_contract_root),
            "STAGE_I4_QUALIFICATION_CONTRACT_INVALID")
    for key in ("qualification_source_sha256", "qualification_source_manifest_root",
                "operator_evidence_sha256", "operator_result_root"):
        require_root(item[key])
    require(type(item["source_file_count"]) is int and item["source_file_count"] > 0
            and type(item["operator_case_count"]) is int
            and item["operator_case_count"] > 0,
            "STAGE_I4_QUALIFICATION_COUNT_INVALID")
    require(type(item["runtime_results"]) is list and bool(item["runtime_results"])
            and all(type(row) is dict and row.get("status") == "PASS"
                    for row in item["runtime_results"]),
            "STAGE_I4_QUALIFICATION_RUNTIME_INVALID")
    validate_operation_state(item["operation_state"])
    require((item["failures"], item["errors"], item["skips"], item["status"])
            == (0, 0, 0, "PASS"), "STAGE_I4_QUALIFICATION_STATUS_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    require(item["qualification_root"] == root({k: deepcopy(v) for k, v in item.items()
            if k != "qualification_root"}), "STAGE_I4_QUALIFICATION_ROOT_INVALID")
    return deepcopy(item)
