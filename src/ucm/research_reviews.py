"""Deterministic, application-owned research-review records for P/PPI.

These records describe research review semantics without changing P/PPI's
strict v0.1 custody envelope.  They are information-only objects: validation,
adjudication, or saturation never grants author standing, publication
permission, or implementation authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from uclop.canonical import exact_keys, require, require_root, root

from .pippi_global import BOUNDARY


LENS_PACK_SCHEMA = "mosaic.research.review-lens-pack.v0.1"
FINDING_SCHEMA = "mosaic.research.review-finding.v0.1"
ADJUDICATION_SCHEMA = "mosaic.research.finding-adjudication.v0.1"
SUCCESSOR_LEDGER_SCHEMA = "mosaic.research.successor-ledger.v0.1"
SATURATION_SCHEMA = "mosaic.research.saturation-assessment.v0.1"

SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
CHANGE_CLASSES = {
    "PROCESS", "SEMANTIC", "EVIDENCE", "REFERENCE", "EDITORIAL", "FORMATTING"
}
DISPOSITIONS = {"ACCEPTED", "REJECTED", "DEFERRED", "SUPERSEDED", "DUPLICATE"}


def _identifier(value: Any, code: str) -> str:
    require(
        type(value) is str and bool(value) and value == value.strip() and len(value) <= 192
        and all(ch.isalnum() or ch in "._:-/@+" for ch in value), code
    )
    return value


def _text(value: Any, code: str, *, maximum: int = 16384) -> str:
    require(type(value) is str and bool(value.strip()) and len(value.encode("utf-8")) <= maximum, code)
    return value


def _sorted_ids(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    rows = [_identifier(item, code) for item in value]
    require(rows == sorted(set(rows)), code)
    return rows


def _sorted_roots(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    rows = [require_root(item) for item in value]
    require(rows == sorted(set(rows)), code)
    return rows


def _ordered_roots(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    rows = [require_root(item) for item in value]
    require(len(rows) == len(set(rows)), code)
    return rows


def _sorted_text(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    rows = [_text(item, code) for item in value]
    require(rows == sorted(set(rows)), code)
    return rows


def _optional_root(value: Any) -> str | None:
    if value is None:
        return None
    return require_root(value)


def _rooted(value: Any, *, schema: str, root_field: str, fields: set[str], code: str) -> dict[str, Any]:
    expected = fields | set(BOUNDARY) | {root_field}
    item = exact_keys(value, expected)
    require(item["schema"] == schema, code)
    require(all(item.get(key) == expected_value for key, expected_value in BOUNDARY.items()), code)
    body = {key: deepcopy(row) for key, row in item.items() if key != root_field}
    require(item[root_field] == root(body), code)
    return item


def build_review_lens_pack(*, lens_pack_id: str, subject_class: str,
                           lenses: list[dict[str, Any]], limitations: list[str]) -> dict[str, Any]:
    _identifier(lens_pack_id, "RESEARCH_LENS_PACK_ID_INVALID")
    _identifier(subject_class, "RESEARCH_SUBJECT_CLASS_INVALID")
    require(type(lenses) is list and bool(lenses), "RESEARCH_LENSES_INVALID")
    normalized = []
    seen: set[str] = set()
    for raw in lenses:
        row = exact_keys(raw, {
            "lens_id", "title", "objective", "review_class", "required_context_roles",
            "deterministic_check_ids", "review_questions", "exclusions",
        })
        lens_id = _identifier(row["lens_id"], "RESEARCH_LENS_ID_INVALID")
        require(lens_id not in seen, "RESEARCH_LENS_DUPLICATE")
        seen.add(lens_id)
        normalized.append({
            "lens_id": lens_id,
            "title": _text(row["title"], "RESEARCH_LENS_TITLE_INVALID", maximum=512),
            "objective": _text(row["objective"], "RESEARCH_LENS_OBJECTIVE_INVALID"),
            "review_class": _identifier(row["review_class"], "RESEARCH_REVIEW_CLASS_INVALID"),
            "required_context_roles": _sorted_ids(row["required_context_roles"], "RESEARCH_CONTEXT_ROLES_INVALID"),
            "deterministic_check_ids": _sorted_ids(row["deterministic_check_ids"], "RESEARCH_CHECK_IDS_INVALID"),
            "review_questions": _sorted_text(row["review_questions"], "RESEARCH_REVIEW_QUESTIONS_INVALID", allow_empty=False),
            "exclusions": _sorted_text(row["exclusions"], "RESEARCH_LENS_EXCLUSIONS_INVALID"),
        })
    normalized.sort(key=lambda row: row["lens_id"])
    body = {
        "schema": LENS_PACK_SCHEMA,
        "lens_pack_id": lens_pack_id,
        "subject_class": subject_class,
        "lenses": normalized,
        "limitations": _sorted_text(limitations, "RESEARCH_LENS_LIMITATIONS_INVALID"),
        **BOUNDARY,
    }
    return {**body, "lens_pack_root": root(body)}


def validate_review_lens_pack(value: Any) -> dict[str, Any]:
    fields = {"schema", "lens_pack_id", "subject_class", "lenses", "limitations"}
    item = _rooted(value, schema=LENS_PACK_SCHEMA, root_field="lens_pack_root",
                   fields=fields, code="RESEARCH_LENS_PACK_INVALID")
    expected = build_review_lens_pack(
        lens_pack_id=item["lens_pack_id"], subject_class=item["subject_class"],
        lenses=item["lenses"], limitations=item["limitations"],
    )
    require(item == expected, "RESEARCH_LENS_PACK_INVALID")
    return deepcopy(item)


def build_review_finding(*, finding_id: str, review_id: str, lens_pack_root: str,
                         lens_id: str, subject_root: str, source_anchor: dict[str, Any],
                         severity: str, change_class: str, summary: str, rationale: str,
                         evidence_roots: list[str], counterevidence_roots: list[str],
                         affected_concept_ids: list[str], affected_artifact_ids: list[str],
                         proposed_action: str, reviewer_identity_root: str,
                         limitations: list[str], status: str = "REPORTED") -> dict[str, Any]:
    _identifier(finding_id, "RESEARCH_FINDING_ID_INVALID")
    _identifier(review_id, "RESEARCH_REVIEW_ID_INVALID")
    require_root(lens_pack_root); _identifier(lens_id, "RESEARCH_LENS_ID_INVALID"); require_root(subject_root)
    anchor = exact_keys(source_anchor, {"path", "section", "location_start", "location_end", "excerpt_sha256"})
    require(type(anchor["path"]) is str and bool(anchor["path"]) and "\\" not in anchor["path"], "RESEARCH_FINDING_ANCHOR_INVALID")
    _text(anchor["section"], "RESEARCH_FINDING_ANCHOR_INVALID", maximum=1024)
    require(type(anchor["location_start"]) is int and type(anchor["location_end"]) is int
            and 0 <= anchor["location_start"] <= anchor["location_end"], "RESEARCH_FINDING_ANCHOR_INVALID")
    require_root(anchor["excerpt_sha256"])
    require(severity in SEVERITIES and change_class in CHANGE_CLASSES and status == "REPORTED",
            "RESEARCH_FINDING_CLASSIFICATION_INVALID")
    body = {
        "schema": FINDING_SCHEMA,
        "finding_id": finding_id,
        "review_id": review_id,
        "lens_pack_root": lens_pack_root,
        "lens_id": lens_id,
        "subject_root": subject_root,
        "source_anchor": deepcopy(anchor),
        "severity": severity,
        "change_class": change_class,
        "summary": _text(summary, "RESEARCH_FINDING_SUMMARY_INVALID"),
        "rationale": _text(rationale, "RESEARCH_FINDING_RATIONALE_INVALID"),
        "evidence_roots": _sorted_roots(evidence_roots, "RESEARCH_FINDING_EVIDENCE_INVALID"),
        "counterevidence_roots": _sorted_roots(counterevidence_roots, "RESEARCH_FINDING_COUNTEREVIDENCE_INVALID"),
        "affected_concept_ids": _sorted_ids(affected_concept_ids, "RESEARCH_FINDING_CONCEPTS_INVALID"),
        "affected_artifact_ids": _sorted_ids(affected_artifact_ids, "RESEARCH_FINDING_ARTIFACTS_INVALID"),
        "proposed_action": _text(proposed_action, "RESEARCH_FINDING_ACTION_INVALID"),
        "reviewer_identity_root": require_root(reviewer_identity_root),
        "limitations": _sorted_text(limitations, "RESEARCH_FINDING_LIMITATIONS_INVALID"),
        "status": status,
        **BOUNDARY,
    }
    return {**body, "finding_root": root(body)}


def validate_review_finding(value: Any) -> dict[str, Any]:
    fields = {
        "schema", "finding_id", "review_id", "lens_pack_root", "lens_id", "subject_root",
        "source_anchor", "severity", "change_class", "summary", "rationale", "evidence_roots",
        "counterevidence_roots", "affected_concept_ids", "affected_artifact_ids", "proposed_action",
        "reviewer_identity_root", "limitations", "status",
    }
    item = _rooted(value, schema=FINDING_SCHEMA, root_field="finding_root", fields=fields,
                   code="RESEARCH_FINDING_INVALID")
    expected = build_review_finding(**{key: item[key] for key in fields if key != "schema"})
    require(item == expected, "RESEARCH_FINDING_INVALID")
    return deepcopy(item)


def build_finding_adjudication(*, finding_root: str, disposition: str,
                               reason_codes: list[str], author_decision_root: str | None,
                               applied_change_root: str | None,
                               superseded_by_finding_root: str | None,
                               remaining_obligation_ids: list[str],
                               regression_review_required: bool, notes: str) -> dict[str, Any]:
    require_root(finding_root)
    require(disposition in DISPOSITIONS, "RESEARCH_ADJUDICATION_DISPOSITION_INVALID")
    author = _optional_root(author_decision_root); applied = _optional_root(applied_change_root)
    superseded = _optional_root(superseded_by_finding_root)
    require(type(regression_review_required) is bool, "RESEARCH_ADJUDICATION_INVALID")
    if disposition == "ACCEPTED":
        require(author is not None, "RESEARCH_ADJUDICATION_AUTHOR_DECISION_REQUIRED")
    if disposition == "SUPERSEDED":
        require(superseded is not None, "RESEARCH_ADJUDICATION_SUPERSEDING_FINDING_REQUIRED")
    body = {
        "schema": ADJUDICATION_SCHEMA,
        "finding_root": finding_root,
        "disposition": disposition,
        "reason_codes": _sorted_ids(reason_codes, "RESEARCH_ADJUDICATION_REASONS_INVALID", allow_empty=False),
        "author_decision_root": author,
        "applied_change_root": applied,
        "superseded_by_finding_root": superseded,
        "remaining_obligation_ids": _sorted_ids(remaining_obligation_ids, "RESEARCH_ADJUDICATION_OBLIGATIONS_INVALID"),
        "regression_review_required": regression_review_required,
        "notes": _text(notes, "RESEARCH_ADJUDICATION_NOTES_INVALID"),
        **BOUNDARY,
    }
    return {**body, "adjudication_root": root(body)}


def validate_finding_adjudication(value: Any) -> dict[str, Any]:
    fields = {
        "schema", "finding_root", "disposition", "reason_codes", "author_decision_root",
        "applied_change_root", "superseded_by_finding_root", "remaining_obligation_ids",
        "regression_review_required", "notes",
    }
    item = _rooted(value, schema=ADJUDICATION_SCHEMA, root_field="adjudication_root",
                   fields=fields, code="RESEARCH_ADJUDICATION_INVALID")
    expected = build_finding_adjudication(**{key: item[key] for key in fields if key != "schema"})
    require(item == expected, "RESEARCH_ADJUDICATION_INVALID")
    return deepcopy(item)


def build_successor_ledger(*, ledger_id: str, logical_work_id: str, source_root: str,
                           successor_status: str, successor_root: str | None,
                           lens_pack_root: str, accepted_finding_roots: list[str],
                           adjudication_roots: list[str], accepted_change_roots: list[str],
                           semantic_change_roots: list[str], editorial_change_roots: list[str],
                           added_claim_roots: list[str], removed_claim_roots: list[str],
                           cross_reference_delta_roots: list[str],
                           regression_evidence_roots: list[str],
                           unresolved_finding_roots: list[str],
                           predecessor_ledger_root: str | None,
                           producer_operation_root: str, status: str) -> dict[str, Any]:
    _identifier(ledger_id, "RESEARCH_LEDGER_ID_INVALID")
    _identifier(logical_work_id, "RESEARCH_LOGICAL_WORK_ID_INVALID")
    require_root(source_root); require_root(lens_pack_root); require_root(producer_operation_root)
    successor = _optional_root(successor_root); predecessor = _optional_root(predecessor_ledger_root)
    require(successor_status in {"NOT_CREATED", "CREATED"}, "RESEARCH_SUCCESSOR_STATUS_INVALID")
    require(status in {"REVIEW_ONLY", "SUCCESSOR_CREATED"}, "RESEARCH_LEDGER_STATUS_INVALID")
    if successor_status == "NOT_CREATED":
        require(successor is None and status == "REVIEW_ONLY", "RESEARCH_LEDGER_NO_SUCCESSOR_INVALID")
        require(not any((accepted_change_roots, semantic_change_roots, editorial_change_roots,
                         added_claim_roots, removed_claim_roots, cross_reference_delta_roots)),
                "RESEARCH_LEDGER_NO_SUCCESSOR_CHANGES_INVALID")
    else:
        require(successor is not None and status == "SUCCESSOR_CREATED", "RESEARCH_LEDGER_SUCCESSOR_INVALID")
    body = {
        "schema": SUCCESSOR_LEDGER_SCHEMA,
        "ledger_id": ledger_id,
        "logical_work_id": logical_work_id,
        "source_root": source_root,
        "successor_status": successor_status,
        "successor_root": successor,
        "lens_pack_root": lens_pack_root,
        "accepted_finding_roots": _sorted_roots(accepted_finding_roots, "RESEARCH_LEDGER_FINDINGS_INVALID"),
        "adjudication_roots": _sorted_roots(adjudication_roots, "RESEARCH_LEDGER_ADJUDICATIONS_INVALID"),
        "accepted_change_roots": _sorted_roots(accepted_change_roots, "RESEARCH_LEDGER_CHANGES_INVALID"),
        "semantic_change_roots": _sorted_roots(semantic_change_roots, "RESEARCH_LEDGER_CHANGES_INVALID"),
        "editorial_change_roots": _sorted_roots(editorial_change_roots, "RESEARCH_LEDGER_CHANGES_INVALID"),
        "added_claim_roots": _sorted_roots(added_claim_roots, "RESEARCH_LEDGER_CLAIMS_INVALID"),
        "removed_claim_roots": _sorted_roots(removed_claim_roots, "RESEARCH_LEDGER_CLAIMS_INVALID"),
        "cross_reference_delta_roots": _sorted_roots(cross_reference_delta_roots, "RESEARCH_LEDGER_REFERENCES_INVALID"),
        "regression_evidence_roots": _sorted_roots(regression_evidence_roots, "RESEARCH_LEDGER_REGRESSION_INVALID"),
        "unresolved_finding_roots": _sorted_roots(unresolved_finding_roots, "RESEARCH_LEDGER_UNRESOLVED_INVALID"),
        "predecessor_ledger_root": predecessor,
        "producer_operation_root": producer_operation_root,
        "status": status,
        **BOUNDARY,
    }
    return {**body, "successor_ledger_root": root(body)}


def validate_successor_ledger(value: Any) -> dict[str, Any]:
    fields = {
        "schema", "ledger_id", "logical_work_id", "source_root", "successor_status",
        "successor_root", "lens_pack_root", "accepted_finding_roots", "adjudication_roots",
        "accepted_change_roots", "semantic_change_roots", "editorial_change_roots",
        "added_claim_roots", "removed_claim_roots", "cross_reference_delta_roots",
        "regression_evidence_roots", "unresolved_finding_roots", "predecessor_ledger_root",
        "producer_operation_root", "status",
    }
    item = _rooted(value, schema=SUCCESSOR_LEDGER_SCHEMA, root_field="successor_ledger_root",
                   fields=fields, code="RESEARCH_SUCCESSOR_LEDGER_INVALID")
    expected = build_successor_ledger(**{key: item[key] for key in fields if key != "schema"})
    require(item == expected, "RESEARCH_SUCCESSOR_LEDGER_INVALID")
    return deepcopy(item)


def build_saturation_assessment(*, assessment_id: str, subject_root: str,
                                lens_pack_root: str, pass_roots: list[str],
                                new_substantive_findings_by_pass: list[int],
                                accepted_substantive_changes_by_pass: list[int],
                                severity_weighted_yield_by_pass: list[int],
                                repeated_finding_count_by_pass: list[int],
                                regression_count_by_pass: list[int],
                                coverage_delta_basis_points: dict[str, int],
                                unresolved_high_severity_roots: list[str],
                                thresholds: dict[str, int], nonclaims: list[str]) -> dict[str, Any]:
    _identifier(assessment_id, "RESEARCH_SATURATION_ID_INVALID")
    require_root(subject_root); require_root(lens_pack_root)
    passes = _ordered_roots(pass_roots, "RESEARCH_SATURATION_PASSES_INVALID", allow_empty=False)
    series = {
        "new_substantive_findings_by_pass": new_substantive_findings_by_pass,
        "accepted_substantive_changes_by_pass": accepted_substantive_changes_by_pass,
        "severity_weighted_yield_by_pass": severity_weighted_yield_by_pass,
        "repeated_finding_count_by_pass": repeated_finding_count_by_pass,
        "regression_count_by_pass": regression_count_by_pass,
    }
    for key, values in series.items():
        require(type(values) is list and len(values) == len(passes)
                and all(type(row) is int and row >= 0 for row in values), "RESEARCH_SATURATION_SERIES_INVALID", detail=key)
    coverage = exact_keys(coverage_delta_basis_points, {
        "corpus_linkage", "counterevidence", "evidence", "pedagogical_accessibility",
    })
    require(all(type(row) is int and -10000 <= row <= 10000 for row in coverage.values()),
            "RESEARCH_SATURATION_COVERAGE_INVALID")
    threshold_values = exact_keys(thresholds, {
        "minimum_passes", "window_size", "maximum_new_findings",
        "maximum_accepted_changes", "maximum_weighted_yield", "maximum_regressions",
    })
    require(all(type(row) is int and row >= 0 for row in threshold_values.values())
            and threshold_values["minimum_passes"] >= 2 and threshold_values["window_size"] >= 2,
            "RESEARCH_SATURATION_THRESHOLDS_INVALID")
    unresolved = _sorted_roots(unresolved_high_severity_roots, "RESEARCH_SATURATION_UNRESOLVED_INVALID")
    if len(passes) < threshold_values["minimum_passes"]:
        result, reason = "INSUFFICIENT_PASSES", "MINIMUM_PASS_COUNT_NOT_MET"
    elif unresolved:
        result, reason = "CONTINUE", "UNRESOLVED_HIGH_SEVERITY_FINDINGS"
    else:
        window = min(threshold_values["window_size"], len(passes))
        recent = {key: values[-window:] for key, values in series.items()}
        stable = (
            max(recent["new_substantive_findings_by_pass"]) <= threshold_values["maximum_new_findings"]
            and max(recent["accepted_substantive_changes_by_pass"]) <= threshold_values["maximum_accepted_changes"]
            and max(recent["severity_weighted_yield_by_pass"]) <= threshold_values["maximum_weighted_yield"]
            and max(recent["regression_count_by_pass"]) <= threshold_values["maximum_regressions"]
        )
        result, reason = (("REVIEW_SATURATED_FOR_DECLARED_LENS_SET", "DECLARED_THRESHOLDS_MET")
                          if stable else ("CONTINUE", "MARGINAL_YIELD_REMAINS_ABOVE_THRESHOLD"))
    body = {
        "schema": SATURATION_SCHEMA,
        "assessment_id": assessment_id,
        "subject_root": subject_root,
        "lens_pack_root": lens_pack_root,
        "pass_roots": passes,
        "assessment_window": min(threshold_values["window_size"], len(passes)),
        **{key: deepcopy(values) for key, values in series.items()},
        "coverage_delta_basis_points": deepcopy(coverage),
        "unresolved_high_severity_roots": unresolved,
        "thresholds": deepcopy(threshold_values),
        "result": result,
        "stop_reason": reason,
        "nonclaims": _sorted_text(nonclaims, "RESEARCH_SATURATION_NONCLAIMS_INVALID", allow_empty=False),
        **BOUNDARY,
    }
    return {**body, "saturation_assessment_root": root(body)}


def validate_saturation_assessment(value: Any) -> dict[str, Any]:
    fields = {
        "schema", "assessment_id", "subject_root", "lens_pack_root", "pass_roots",
        "assessment_window", "new_substantive_findings_by_pass",
        "accepted_substantive_changes_by_pass", "severity_weighted_yield_by_pass",
        "repeated_finding_count_by_pass", "regression_count_by_pass",
        "coverage_delta_basis_points", "unresolved_high_severity_roots", "thresholds",
        "result", "stop_reason", "nonclaims",
    }
    item = _rooted(value, schema=SATURATION_SCHEMA, root_field="saturation_assessment_root",
                   fields=fields, code="RESEARCH_SATURATION_INVALID")
    expected = build_saturation_assessment(**{
        key: item[key] for key in fields
        if key not in {"schema", "assessment_window", "result", "stop_reason"}
    })
    require(item == expected, "RESEARCH_SATURATION_INVALID")
    return deepcopy(item)


VALIDATORS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "lens-pack": validate_review_lens_pack,
    "finding": validate_review_finding,
    "adjudication": validate_finding_adjudication,
    "successor-ledger": validate_successor_ledger,
    "saturation": validate_saturation_assessment,
}


def validate_research_record(kind: str, value: Any) -> dict[str, Any]:
    require(kind in VALIDATORS, "RESEARCH_RECORD_KIND_INVALID")
    return VALIDATORS[kind](value)


__all__ = [
    "LENS_PACK_SCHEMA", "FINDING_SCHEMA", "ADJUDICATION_SCHEMA",
    "SUCCESSOR_LEDGER_SCHEMA", "SATURATION_SCHEMA", "build_review_lens_pack",
    "validate_review_lens_pack", "build_review_finding", "validate_review_finding",
    "build_finding_adjudication", "validate_finding_adjudication",
    "build_successor_ledger", "validate_successor_ledger",
    "build_saturation_assessment", "validate_saturation_assessment",
    "validate_research_record",
]
