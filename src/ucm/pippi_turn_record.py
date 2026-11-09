"""Pure, evidence-aware turn records over immutable P/PPI opening/report records.

The richer record preserves what a caller declares and what remains unknown.
Labels, receipt references, and native-turn references establish no observation
or interception proof.  Verification can be attached later as separate evidence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, root, validate_value
from .pippi_adaptive import SCENARIO_TRIGGERS, validate_turn_opening, validate_turn_report
from .pippi_global import BOUNDARY


PROVENANCE_BASES = ("AGENT_REPORTED", "HOST_CAPTURED", "VERIFIER_DERIVED",
                    "EXTERNALLY_ATTESTED", "UNKNOWN")
ACTIVITY_KINDS = ("PROPOSAL", "CHANGE", "CHECK", "TOOL_RESULT", "EXTERNAL_RECEIPT", "OTHER")
CHANNELS = ("MODEL_INPUT", "DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL",
            "TOOL_DISPATCH", "TOOL_RESULT", "JOURNAL_WRITE")
COVERAGE_STATUSES = ("UNKNOWN", "PARTIAL", "COMPLETE", "NOT_APPLICABLE")
DISPOSITIONS = ("UNKNOWN", "OPEN", "REPORTED_MET", "REPORTED_UNMET", "DEFERRED")
_CLAIM = {"claim_id", "activity_kind", "statement", "declared_basis", "evidence_ids"}
_EVIDENCE = {"evidence_id", "subject_root", "source_root", "producer_id", "receipt_root",
             "declared_basis", "description"}


def _text(value: Any) -> str:
    require(type(value) is str and bool(value.strip()), "PIPPI_TURN_RECORD_TEXT_INVALID")
    return value


def _root(value: Any, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    require(type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value),
            "PIPPI_TURN_RECORD_REFERENCE_INVALID")
    return value


def _strings(value: Any, *, roots: bool = False) -> list[str]:
    require(type(value) is list, "PIPPI_TURN_RECORD_LIST_INVALID")
    for item in value:
        _root(item) if roots else _text(item)
    require(len(value) == len(set(value)), "PIPPI_TURN_RECORD_DUPLICATE")
    return sorted(value)


def _rows(value: Any, keys: set[str], identifier: str) -> list[dict[str, Any]]:
    require(type(value) is list, "PIPPI_TURN_RECORD_ROWS_INVALID")
    rows = [deepcopy(exact_keys(row, keys)) for row in value]
    ids = [_text(row[identifier]) for row in rows]
    require(len(ids) == len(set(ids)), "PIPPI_TURN_RECORD_DUPLICATE")
    return sorted(rows, key=lambda row: row[identifier])


def reporting_requirements(scenario: str) -> dict[str, Any]:
    """Return scenario-selected information requests, never authority or effects."""
    require(type(scenario) is str and scenario in SCENARIO_TRIGGERS, "PIPPI_SCENARIO_INVALID")
    activities = {
        "CODING": ["CHANGE", "CHECK"], "PACKAGING": ["CHECK"],
        "RELEASE_PLANNING": ["CHECK"], "PORTABILITY_CLAIM": ["CHECK"],
        "REVIEW": ["CHECK"], "RECOVERY": ["CHECK"], "REMOTE_WORK": ["EXTERNAL_RECEIPT"],
    }[scenario]
    body = {"schema": "mosaic.ucm.pippi-turn-reporting-requirements.v0.1",
            "scenario": scenario, "required_sections": ["ACCEPTANCE_DISPOSITIONS",
                "ACTIVITY", "CONSTITUTIONAL_CONTEXT", "COVERAGE", "OBJECTIVES", "REPORT"],
            "required_activity_kinds": activities,
            "evidence_references_required": scenario != "CODING",
            "required_coverage_channels": ["JOURNAL_WRITE", "VISIBLE_OUTPUT"],
            "per_tool_interception_required": False,
            "missing_information_policy": "PRESERVE_UNKNOWN_AND_REQUEST_INFORMATION", **BOUNDARY}
    return {**body, "requirements_root": root(body)}


def build_turn_record(*, opening: dict[str, Any], report: dict[str, Any],
                      claims: list[dict[str, Any]], evidence: list[dict[str, Any]],
                      coverage: list[dict[str, Any]], objectives: list[dict[str, Any]],
                      acceptance_dispositions: list[dict[str, Any]],
                      native_turn_roots: list[str]) -> dict[str, Any]:
    """Build a richer report without promoting caller statements to observations.

    All collections have unique stable identifiers and canonical output order.
    Omitted channels and acceptance cases remain explicitly UNKNOWN.  Reported
    acceptance results never close an acceptance case or grant a capability.
    """
    for item in (claims, evidence, coverage, objectives, acceptance_dispositions, native_turn_roots):
        validate_value(item)
    opening = validate_turn_opening(opening)
    report = validate_turn_report(report, opening=opening)
    evidence_rows = _rows(evidence, _EVIDENCE, "evidence_id")
    for row in evidence_rows:
        _root(row["subject_root"]); _root(row["source_root"], optional=True)
        _root(row["receipt_root"], optional=True)
        _text(row["producer_id"]); _text(row["description"])
        require(row["declared_basis"] in PROVENANCE_BASES, "PIPPI_TURN_RECORD_BASIS_INVALID")
        row["assurance"] = "DECLARED_NOT_VERIFIED"
    evidence_ids = {row["evidence_id"] for row in evidence_rows}

    def references(values: Any, allowed: set[str]) -> list[str]:
        result = _strings(values)
        require(set(result) <= allowed, "PIPPI_TURN_RECORD_REFERENCE_UNBOUND")
        return result

    claim_rows = _rows(claims, _CLAIM, "claim_id")
    for row in claim_rows:
        _text(row["statement"])
        require(row["activity_kind"] in ACTIVITY_KINDS, "PIPPI_TURN_RECORD_ACTIVITY_INVALID")
        require(row["declared_basis"] in PROVENANCE_BASES, "PIPPI_TURN_RECORD_BASIS_INVALID")
        row["evidence_ids"] = references(row["evidence_ids"], evidence_ids)
        row["assurance"] = "DECLARED_NOT_VERIFIED"
    claim_ids = {row["claim_id"] for row in claim_rows}
    cases = set(opening["acceptance_case_roots"])
    objective_rows = _rows(objectives, {"objective_id", "statement", "acceptance_case_roots"}, "objective_id")
    for row in objective_rows:
        _text(row["statement"])
        row["acceptance_case_roots"] = references(row["acceptance_case_roots"], cases)

    disposition_rows = _rows(acceptance_dispositions,
        {"acceptance_case_root", "disposition", "claim_ids", "evidence_ids"}, "acceptance_case_root")
    for row in disposition_rows:
        require(row["acceptance_case_root"] in cases, "PIPPI_TURN_RECORD_CASE_UNBOUND")
        require(row["disposition"] in DISPOSITIONS, "PIPPI_TURN_RECORD_DISPOSITION_INVALID")
        row["claim_ids"] = references(row["claim_ids"], claim_ids)
        row["evidence_ids"] = references(row["evidence_ids"], evidence_ids)
    supplied = {row["acceptance_case_root"] for row in disposition_rows}
    disposition_rows.extend({"acceptance_case_root": case, "disposition": "UNKNOWN",
        "claim_ids": [], "evidence_ids": []} for case in sorted(cases - supplied))
    disposition_rows.sort(key=lambda row: row["acceptance_case_root"])

    coverage_rows = _rows(coverage, {"channel", "status", "evidence_ids", "limitations"}, "channel")
    for row in coverage_rows:
        require(row["channel"] in CHANNELS, "PIPPI_TURN_RECORD_CHANNEL_INVALID")
        require(row["status"] in COVERAGE_STATUSES, "PIPPI_TURN_RECORD_COVERAGE_INVALID")
        row["evidence_ids"] = references(row["evidence_ids"], evidence_ids)
        row["limitations"] = _strings(row["limitations"])
    supplied_channels = {row["channel"] for row in coverage_rows}
    coverage_rows.extend({"channel": channel, "status": "UNKNOWN", "evidence_ids": [],
        "limitations": ["No coverage statement supplied."]}
        for channel in sorted(set(CHANNELS) - supplied_channels))
    coverage_rows.sort(key=lambda row: row["channel"])
    native_roots = _strings(native_turn_roots, roots=True)
    requirements = reporting_requirements(opening["scenario"])
    missing = []
    if not objective_rows:
        missing.append("OBJECTIVES")
    for kind in requirements["required_activity_kinds"]:
        if not any(row["activity_kind"] == kind for row in claim_rows):
            missing.append("ACTIVITY:" + kind)
    if requirements["evidence_references_required"] and not evidence_rows:
        missing.append("EVIDENCE_REFERENCES")
    missing.extend("ACCEPTANCE_DISPOSITION:" + row["acceptance_case_root"]
                   for row in disposition_rows if row["disposition"] == "UNKNOWN")
    missing.extend("COVERAGE:" + row["channel"] for row in coverage_rows
                   if row["channel"] in requirements["required_coverage_channels"]
                   and row["status"] == "UNKNOWN")
    body = {"schema": "mosaic.ucm.pippi-turn-record.v0.1",
            "project_id": opening["project_id"], "project_root": opening["project_root"],
            "turn_opening_root": opening["turn_opening_root"],
            "turn_report_root": report["turn_report_root"], "sequence": opening["sequence"],
            "previous_turn_root": opening["previous_turn_root"], "journal_head": opening["journal_head"],
            "scenario": opening["scenario"], "host_profile_root": opening["host_profile_root"],
            "execution_context_root": opening["execution_context_root"],
            "mediation_library_root": opening["mediation_library_root"],
            "context": deepcopy(opening["context"]), "rule_ids": list(opening["rule_ids"]),
            "acceptance_case_roots": list(opening["acceptance_case_roots"]),
            "objectives": objective_rows, "claims": claim_rows, "evidence": evidence_rows,
            "coverage": coverage_rows, "acceptance_dispositions": disposition_rows,
            "native_turn_roots": native_roots, "native_turn_roots_are_references": True,
            "source_roots": sorted({row["source_root"] for row in evidence_rows if row["source_root"]}),
            "source_roots_are_references": True, "requirements": requirements,
            "summary": report["summary"], "changed_paths": list(report["changed_paths"]),
            "artifact_roots": list(report["artifact_roots"]), "evidence_roots": list(report["evidence_roots"]),
            "unresolved_items": deepcopy(report["unresolved_items"]), "next_action": report["next_action"],
            "claim_class": report["claim_class"], "missing_information": sorted(missing),
            "status": "NEEDS_INFORMATION" if missing else "INFORMATION_COMPLETE",
            "reporting_completeness_is_not_verification": True,
            "verified_channel_ids": [],
            "record_assurance": "STRUCTURE_AND_LINKS_ONLY",
            "coverage_assurance": "DECLARED_NOT_VERIFIED", "enforced_host_verified": False,
            "acceptance_case_closed": False, "effect_authorized": False,
            "observable_scope": "COMMON_TURN_REPORTED_ACTIVITY", **BOUNDARY}
    return {**body, "turn_record_root": root(body)}


def validate_turn_record(value: Any, *, opening: dict[str, Any],
                         report: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the entire record against its exact opening and legacy report."""
    validate_value(value)
    require(type(value) is dict, "PIPPI_TURN_RECORD_INVALID")
    claims = _rows(value.get("claims"), _CLAIM | {"assurance"}, "claim_id")
    evidence = _rows(value.get("evidence"), _EVIDENCE | {"assurance"}, "evidence_id")
    expected = build_turn_record(opening=opening, report=report,
        claims=[{k: v for k, v in row.items() if k != "assurance"} for row in claims],
        evidence=[{k: v for k, v in row.items() if k != "assurance"} for row in evidence],
        coverage=value.get("coverage"), objectives=value.get("objectives"),
        acceptance_dispositions=value.get("acceptance_dispositions"),
        native_turn_roots=value.get("native_turn_roots"))
    exact_keys(value, set(expected))
    require(value == expected, "PIPPI_TURN_RECORD_INVALID")
    return deepcopy(value)


def project_turn_record(value: Any, *, opening: dict[str, Any], report: dict[str, Any],
                        view: str = "HUMAN") -> dict[str, Any]:
    """Produce a deterministic projection; the rooted turn record remains primary."""
    record = validate_turn_record(value, opening=opening, report=report)
    require(view in {"HUMAN", "MACHINE"}, "PIPPI_TURN_RECORD_VIEW_INVALID")
    lines = [record["summary"], "Reporting: " + record["status"],
             "Claim basis is declared; referenced receipts do not establish verification."]
    lines.extend("Objective: " + row["statement"] for row in record["objectives"])
    lines.extend("Case " + row["acceptance_case_root"] + ": " + row["disposition"]
                 for row in record["acceptance_dispositions"])
    lines.extend("Missing information: " + item for item in record["missing_information"])
    lines.append("Next: " + record["next_action"])
    body = {"schema": "mosaic.ucm.pippi-turn-record-projection.v0.1", "view": view,
            "turn_record_root": record["turn_record_root"], "project_id": record["project_id"],
            "summary": record["summary"], "status": record["status"],
            "missing_information": record["missing_information"],
            "lines": lines if view == "HUMAN" else [],
            "facts": {"acceptance_cases": len(record["acceptance_case_roots"]),
                "claims": len(record["claims"]), "evidence_references": len(record["evidence"]),
                "unknown_channels": sum(row["status"] == "UNKNOWN" for row in record["coverage"])},
            "projection_is_evidence": False, **BOUNDARY}
    return {**body, "projection_root": root(body)}
