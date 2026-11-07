"""Deterministic development-standard obligations and evaluations.

The standards plane is descriptive and diagnostic.  It does not execute an
effect or turn a recommendation into authority.  Every decision is derived
from a fixed obligation denominator and exact check subjects.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


CATALOG_SCHEMA = "mosaic.ucm.development-standards-catalog.v0.1"
EVALUATION_SCHEMA = "mosaic.ucm.development-standards-evaluation.v0.1"
CLASSES = {"MANDATORY", "CONDITIONAL", "PREFERENCE", "RECOMMENDATION"}
CHECK_ROLES = {"STATIC", "TARGETED", "COURT", "QUALIFICATION", "WITNESS", "REVIEW"}
CHECK_STATUSES = {"PASS", "FAIL", "NOT_RUN"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _identifiers(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(type(value) is list and value == sorted(set(value))
            and (allow_empty or bool(value)), code)
    return [_identifier(item, code) for item in value]


def build_standards_catalog(*, catalog_id: str, policy_root: str,
                            obligations: list[dict[str, Any]]) -> dict[str, Any]:
    _identifier(catalog_id, "STANDARDS_CATALOG_ID_INVALID")
    require_root(policy_root)
    require(type(obligations) is list and bool(obligations),
            "STANDARDS_OBLIGATIONS_INVALID")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in obligations:
        item = exact_keys(raw, {"obligation_id", "statement", "class", "triggers",
                                "check_ids", "evidence_required"})
        obligation_id = _identifier(item["obligation_id"], "STANDARDS_OBLIGATION_ID_INVALID")
        require(obligation_id not in seen, "STANDARDS_OBLIGATION_DUPLICATE")
        seen.add(obligation_id)
        require(type(item["statement"]) is str and item["statement"] == item["statement"].strip()
                and bool(item["statement"]), "STANDARDS_STATEMENT_INVALID")
        require(item["class"] in CLASSES, "STANDARDS_CLASS_INVALID")
        triggers = _identifiers(item["triggers"], "STANDARDS_TRIGGERS_INVALID",
                                allow_empty=item["class"] != "CONDITIONAL")
        check_ids = _identifiers(item["check_ids"], "STANDARDS_CHECK_IDS_INVALID",
                                 allow_empty=item["class"] in {"PREFERENCE", "RECOMMENDATION"})
        require(type(item["evidence_required"]) is bool, "STANDARDS_EVIDENCE_FLAG_INVALID")
        normalized.append({"obligation_id": obligation_id, "statement": item["statement"],
                           "class": item["class"], "triggers": triggers,
                           "check_ids": check_ids,
                           "evidence_required": item["evidence_required"]})
    normalized.sort(key=lambda row: row["obligation_id"])
    body = {"schema": CATALOG_SCHEMA, "catalog_id": catalog_id,
            "policy_root": policy_root, "obligations": normalized,
            "fixed_denominator": len(normalized), **BOUNDARY}
    return {**body, "catalog_root": root(body)}


def validate_standards_catalog(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "catalog_id", "policy_root", "obligations",
                              "fixed_denominator", "standing", "authority_effect",
                              "real_a5", "g0", "catalog_root"})
    expected = build_standards_catalog(catalog_id=item["catalog_id"],
        policy_root=item["policy_root"], obligations=item["obligations"])
    require(item == expected, "STANDARDS_CATALOG_INVALID")
    return deepcopy(item)


def evaluate_standards(*, catalog: dict[str, Any], subject_root: str,
                       active_triggers: list[str],
                       check_results: list[dict[str, Any]]) -> dict[str, Any]:
    catalog = validate_standards_catalog(catalog)
    require_root(subject_root)
    active = set(_identifiers(active_triggers, "STANDARDS_ACTIVE_TRIGGERS_INVALID",
                              allow_empty=True))
    known_checks = {check_id for row in catalog["obligations"] for check_id in row["check_ids"]}
    by_check: dict[str, dict[str, Any]] = {}
    require(type(check_results) is list, "STANDARDS_CHECK_RESULTS_INVALID")
    for raw in check_results:
        item = exact_keys(raw, {"check_id", "role", "subject_root", "status",
                                "evidence_root", "witness_root"})
        check_id = _identifier(item["check_id"], "STANDARDS_CHECK_ID_INVALID")
        require(check_id in known_checks and check_id not in by_check,
                "STANDARDS_CHECK_UNKNOWN_OR_DUPLICATE")
        require(item["role"] in CHECK_ROLES and item["status"] in CHECK_STATUSES,
                "STANDARDS_CHECK_RESULT_INVALID")
        require(item["subject_root"] == subject_root, "STANDARDS_CHECK_SUBJECT_MISMATCH")
        for field in ("evidence_root", "witness_root"):
            require(item[field] is None or require_root(item[field]),
                    "STANDARDS_CHECK_ROOT_INVALID")
        require((item["status"] == "NOT_RUN") == (item["evidence_root"] is None),
                "STANDARDS_CHECK_EVIDENCE_INVALID")
        by_check[check_id] = deepcopy(item)

    dispositions = []
    hard_failure = False
    advisory = False
    for obligation in catalog["obligations"]:
        applicable = obligation["class"] != "CONDITIONAL" or bool(
            active.intersection(obligation["triggers"]))
        rows = [by_check[check_id] for check_id in obligation["check_ids"] if check_id in by_check]
        missing = sorted(set(obligation["check_ids"]) - set(by_check))
        passed = applicable and not missing and all(row["status"] == "PASS" for row in rows)
        evidence_ok = (not obligation["evidence_required"] or
                       all(row["evidence_root"] is not None for row in rows))
        if not applicable:
            status = "NOT_APPLICABLE"
        elif passed and evidence_ok:
            status = "PASS"
        else:
            status = "FAIL" if any(row["status"] == "FAIL" for row in rows) else "INCOMPLETE"
        if status not in {"PASS", "NOT_APPLICABLE"}:
            if obligation["class"] in {"MANDATORY", "CONDITIONAL"}:
                hard_failure = True
            else:
                advisory = True
        dispositions.append({"obligation_id": obligation["obligation_id"],
                             "class": obligation["class"], "applicable": applicable,
                             "status": status, "missing_check_ids": missing,
                             "evidence_roots": sorted({row["evidence_root"] for row in rows
                                                       if row["evidence_root"] is not None})})
    decision = "REFUSED" if hard_failure else "ADVISORY" if advisory else "PASS"
    body = {"schema": EVALUATION_SCHEMA, "catalog_root": catalog["catalog_root"],
            "subject_root": subject_root, "active_triggers": sorted(active),
            "check_results": [by_check[key] for key in sorted(by_check)],
            "obligation_dispositions": dispositions,
            "completed_denominator": sum(row["status"] in {"PASS", "NOT_APPLICABLE"}
                                         for row in dispositions),
            "fixed_denominator": catalog["fixed_denominator"],
            "decision": decision, **BOUNDARY}
    return {**body, "evaluation_root": root(body)}
