"""Qualification contract for the executor-neutral Stage I4 c5 gateway."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


RUNTIME_SCHEMA = "mosaic.ucm.stage-i4-c5-runtime-result.v0.1"
QUALIFICATION_SCHEMA = "mosaic.ucm.stage-i4-c5-qualification.v0.1"


def validate_runtime_result(value: Any, *, source_root: str,
                            source_file_count: int,
                            test_ids: list[str]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "runtime", "source_root",
        "source_file_count", "source_stable", "test_ids", "test_count",
        "test_set_root", "failures", "errors", "skips", "cache_policy",
        "status", "standing", "authority_effect", "real_a5", "g0",
        "runtime_result_root"})
    require(item["schema"] == RUNTIME_SCHEMA and type(item["runtime"]) is str
            and bool(item["runtime"]) and item["source_root"] == require_root(source_root)
            and item["source_file_count"] == source_file_count
            and item["source_stable"] is True and item["test_ids"] == test_ids
            and item["test_count"] == len(test_ids)
            and item["test_set_root"] == root(test_ids)
            and (item["failures"], item["errors"], item["skips"])
                == (0, 0, 0) and item["cache_policy"] == "CACHE_DISABLED"
            and item["status"] == "PASS", "STAGE_I4_C5_RUNTIME_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_C5_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "runtime_result_root"}
    require(item["runtime_result_root"] == root(body),
            "STAGE_I4_C5_RUNTIME_ROOT_INVALID")
    return deepcopy(item)


def validate_qualification(value: Any, *, source_root: str,
                           source_file_count: int, test_ids: list[str],
                           inherited_c4_test_ids: list[str],
                           contract_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "qualification_class", "source_root",
        "source_file_count", "test_ids", "test_count", "test_set_root",
        "inherited_c4_test_ids", "inherited_c4_test_set_root",
        "operational_contract_root", "runtime_results", "failures", "errors",
        "skips", "cache_policy", "status", "operator_tier1",
        "standing", "authority_effect", "real_a5", "g0", "qualification_root"})
    require(item["schema"] == QUALIFICATION_SCHEMA
            and item["qualification_class"] == "CACHE_FREE_INHERITED_POSITIVE"
            and item["source_root"] == require_root(source_root)
            and item["source_file_count"] == source_file_count
            and item["test_ids"] == test_ids and item["test_count"] == len(test_ids)
            and item["test_set_root"] == root(test_ids)
            and item["inherited_c4_test_ids"] == inherited_c4_test_ids
            and item["inherited_c4_test_set_root"] == root(inherited_c4_test_ids)
            and item["operational_contract_root"] == require_root(contract_root)
            and item["cache_policy"] == "CACHE_DISABLED"
            and item["operator_tier1"] == "PREPARED_NOT_EXECUTED_BY_BUILDER"
            and (item["failures"], item["errors"], item["skips"], item["status"])
                == (0, 0, 0, "PASS"), "STAGE_I4_C5_QUALIFICATION_INVALID")
    require(type(item["runtime_results"]) is list and len(item["runtime_results"]) == 1,
            "STAGE_I4_C5_RUNTIME_COUNT_INVALID")
    validate_runtime_result(item["runtime_results"][0], source_root=source_root,
                            source_file_count=source_file_count, test_ids=test_ids)
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_C5_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "qualification_root"}
    require(item["qualification_root"] == root(body),
            "STAGE_I4_C5_QUALIFICATION_ROOT_INVALID")
    return deepcopy(item)
