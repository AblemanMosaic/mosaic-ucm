"""Shadow-mode comparison of native application and UCM decisions."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


SCHEMA = "mosaic.ucm.native-correspondence-cases.v0.1"
RESULT_SCHEMA = "mosaic.ucm.native-correspondence-court.v0.1"


def run_correspondence_court(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "application_id", "subject_root",
                              "native_validator_id", "ucm_validator_id", "cases"})
    require(item["schema"] == SCHEMA, "CORRESPONDENCE_SCHEMA_INVALID")
    require_root(item["subject_root"])
    for field in ("application_id", "native_validator_id", "ucm_validator_id"):
        require(type(item[field]) is str and bool(item[field]),
                "CORRESPONDENCE_ID_INVALID")
    require(type(item["cases"]) is list and bool(item["cases"]),
            "CORRESPONDENCE_CASE_SET_EMPTY")
    seen = set()
    rows = []
    for raw in item["cases"]:
        case = exact_keys(raw, {"case_id", "input_root", "native", "ucm"})
        require(type(case["case_id"]) is str and case["case_id"]
                and case["case_id"] not in seen, "CORRESPONDENCE_CASE_ID_INVALID")
        seen.add(case["case_id"])
        require_root(case["input_root"])
        native = exact_keys(case["native"], {"decision", "result_root"})
        ucm = exact_keys(case["ucm"], {"decision", "result_root"})
        require(native["decision"] in {"PASS", "REFUSED", "FAIL", "UNKNOWN"}
                and ucm["decision"] in {"PASS", "REFUSED", "FAIL", "UNKNOWN"},
                "CORRESPONDENCE_DECISION_INVALID")
        require_root(native["result_root"]); require_root(ucm["result_root"])
        equivalent = (native["decision"] == ucm["decision"]
                      and native["result_root"] == ucm["result_root"])
        rows.append({"case_id": case["case_id"], "input_root": case["input_root"],
                     "native": deepcopy(native), "ucm": deepcopy(ucm),
                     "equivalent": equivalent,
                     "diagnostic": "EQUIVALENT" if equivalent else "DECISION_DIVERGENCE"})
    body = {
        "schema": RESULT_SCHEMA,
        "application_id": item["application_id"],
        "subject_root": item["subject_root"],
        "native_validator_id": item["native_validator_id"],
        "ucm_validator_id": item["ucm_validator_id"],
        "rows": rows,
        "case_count": len(rows),
        "divergence_count": sum(not row["equivalent"] for row in rows),
        "status": "PASS_EQUIVALENT" if all(row["equivalent"] for row in rows)
                  else "HOLD_DIVERGENCE",
        "claim": "SHADOW_CORRESPONDENCE_ONLY",
        **BOUNDARY,
    }
    return {**body, "court_root": root(body)}


def verify_correspondence_court(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "application_id", "subject_root",
                              "native_validator_id", "ucm_validator_id", "rows",
                              "case_count", "divergence_count", "status", "claim",
                              "standing", "authority_effect", "real_a5", "g0",
                              "court_root"})
    cases = {
        "schema": SCHEMA,
        "application_id": item["application_id"],
        "subject_root": item["subject_root"],
        "native_validator_id": item["native_validator_id"],
        "ucm_validator_id": item["ucm_validator_id"],
        "cases": [{"case_id": row["case_id"], "input_root": row["input_root"],
                   "native": row["native"], "ucm": row["ucm"]}
                  for row in item["rows"]],
    }
    expected = run_correspondence_court(cases)
    require(item == expected, "CORRESPONDENCE_COURT_INVALID")
    return deepcopy(item)
