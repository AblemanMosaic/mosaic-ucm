"""Shared semantic verification for Stage I4 c2 qualification and freeze."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from typing import Any
import zipfile

from uclop.canonical import exact_keys, require, require_root, root, strict_loads
from .amcas import BOUNDARY
from .artifacts import verify_deterministic_zip

QUALIFICATION_SCHEMA = "mosaic.ucm.amcas-stage-i4-c2-qualification.v0.1"
QUALIFICATION_SOURCE_SCHEMA = "mosaic.ucm.amcas.qualification-source-archive.v0.1"
CHECKPOINT_SCHEMA = "mosaic.ucm.amcas-stage-i4-c2-checkpoint.v0.1"
CHECKPOINT_ROLE = "UCM_AMCAS_STAGE_I4_C2_PREPARATION"
OPERATOR_EVIDENCE_ROLE = "UCM_AMCAS_STAGE_I4_C2_OPERATOR_EVIDENCE"
OPERATOR_EVIDENCE_SCHEMA = "mosaic.ucm.amcas-stage-i4-c2-operator-evidence.v0.1"


def sha(raw: bytes) -> str:
    require(type(raw) is bytes, "QUALIFICATION_BYTES_REQUIRED")
    return hashlib.sha256(raw).hexdigest()


def _member(raw: bytes, path: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(archive.namelist().count(path) == 1,
                    "QUALIFICATION_MEMBER_INVALID", detail=path)
            return archive.read(path)
    except (zipfile.BadZipFile, KeyError, OSError) as error:
        require(False, "QUALIFICATION_ARCHIVE_INVALID", detail=type(error).__name__)
    raise AssertionError("unreachable")


def validate_checkpoint(raw: bytes) -> dict[str, Any]:
    verify_deterministic_zip(raw, expected_schema=CHECKPOINT_SCHEMA,
                             expected_role=CHECKPOINT_ROLE)
    status = strict_loads(_member(raw, "STAGE-I4-C2-STATUS.json"))
    require(type(status) is dict and status.get("fixed_application_denominator") == 7
            and status.get("stage_i3_preparation_ready") == 4
            and status.get("shadow_execution_eligible") == 0
            and status.get("run_contracts_issued") == 0
            and status.get("application_contacts") == 0
            and status.get("shadow_executions") == 0,
            "QUALIFICATION_CHECKPOINT_STATE_INVALID")
    require({key: status.get(key) for key in BOUNDARY} == BOUNDARY,
            "QUALIFICATION_AUTHORITY_CEILING_INVALID")
    body = {key: value for key, value in status.items() if key != "status_root"}
    require(status.get("status_root") == root(body),
            "QUALIFICATION_CHECKPOINT_ROOT_INVALID")
    return status


def validate_operator_evidence(raw: bytes) -> dict[str, Any]:
    verify_deterministic_zip(raw, expected_schema=OPERATOR_EVIDENCE_SCHEMA,
                             expected_role=OPERATOR_EVIDENCE_ROLE)
    result = strict_loads(_member(raw, "RESULT.json"))
    require(result.get("status") == "PASS" and result.get("failed") == 0
            and result.get("skips") == 0 and result.get("case_count", 0) > 0,
            "QUALIFICATION_OPERATOR_EVIDENCE_INVALID")
    require({key: result.get(key) for key in BOUNDARY} == BOUNDARY,
            "QUALIFICATION_AUTHORITY_CEILING_INVALID")
    body = {key: value for key, value in result.items() if key != "result_root"}
    require(result.get("result_root") == root(body),
            "QUALIFICATION_OPERATOR_RESULT_ROOT_INVALID")
    return result


def validate_qualification(value: Any, *, qualification_source_raw: bytes,
                           checkpoint_raw: bytes, operator_evidence_raw: bytes) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "qualification_source_sha256",
        "qualification_source_manifest_root", "source_graph_root", "source_file_count",
        "test_ids", "test_count", "test_set_root", "failures", "errors", "skips",
        "operator_evidence_sha256", "operator_result_root", "operator_case_count",
        "checkpoint_sha256", "checkpoint_status_root", "fixed_application_denominator",
        "preparation_ready", "execution_eligible", "source_verified_before_and_after",
        "cache_policy", "runtime_results", "status", "standing", "authority_effect",
        "real_a5", "g0", "qualification_root"})
    require(item["schema"] == QUALIFICATION_SCHEMA,
            "QUALIFICATION_SCHEMA_INVALID")
    source_manifest = verify_deterministic_zip(qualification_source_raw,
        expected_schema=QUALIFICATION_SOURCE_SCHEMA, expected_role="QUALIFICATION_SOURCE")
    operator = validate_operator_evidence(operator_evidence_raw)
    checkpoint = validate_checkpoint(checkpoint_raw)
    require(item["qualification_source_sha256"] == sha(qualification_source_raw)
            and item["qualification_source_manifest_root"] == source_manifest["manifest_root"]
            and item["operator_evidence_sha256"] == sha(operator_evidence_raw)
            and item["operator_result_root"] == operator["result_root"]
            and item["operator_case_count"] == operator["case_count"]
            and item["checkpoint_sha256"] == sha(checkpoint_raw)
            and item["checkpoint_status_root"] == checkpoint["status_root"],
            "QUALIFICATION_ARTIFACT_BINDING_INVALID")
    require_root(item["source_graph_root"])
    require(type(item["source_file_count"]) is int and item["source_file_count"] > 0,
            "QUALIFICATION_SOURCE_COUNT_INVALID")
    require(type(item["test_ids"]) is list and bool(item["test_ids"])
            and all(type(value) is str and value for value in item["test_ids"])
            and item["test_ids"] == sorted(set(item["test_ids"])),
            "QUALIFICATION_TEST_IDS_INVALID")
    require(item["test_count"] == len(item["test_ids"])
            and item["test_set_root"] == root(item["test_ids"])
            and item["failures"] == item["errors"] == item["skips"] == 0,
            "QUALIFICATION_TEST_RESULT_INVALID")
    require(item["fixed_application_denominator"] == 7
            and item["preparation_ready"] == 4
            and item["execution_eligible"] == 0,
            "QUALIFICATION_CHECKPOINT_COUNTS_INVALID")
    require(item["source_verified_before_and_after"] is True
            and item["cache_policy"] == "DISABLED" and item["status"] == "PASS",
            "QUALIFICATION_STATUS_INVALID")
    require(type(item["runtime_results"]) is list and bool(item["runtime_results"]),
            "QUALIFICATION_RUNTIME_RESULTS_INVALID")
    runtimes: set[str] = set()
    for raw in item["runtime_results"]:
        row = exact_keys(raw, {"runtime", "test_set_root", "status"})
        require(type(row["runtime"]) is str and row["runtime"] not in runtimes
                and row["test_set_root"] == item["test_set_root"]
                and row["status"] == "PASS", "QUALIFICATION_RUNTIME_RESULT_INVALID")
        runtimes.add(row["runtime"])
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "QUALIFICATION_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "qualification_root"}
    require(item["qualification_root"] == root(body), "QUALIFICATION_ROOT_INVALID")
    return deepcopy(item)
