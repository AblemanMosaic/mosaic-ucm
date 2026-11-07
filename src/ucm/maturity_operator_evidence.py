"""Bind operator-run maturity evidence back to its exact frozen review subject.

The operator owns execution of the adversarial court.  This module performs a
positive custody/contract check after the run; it never runs court cases and it
does not turn operator evidence into independent review or authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import canonical_bytes, require, require_root, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip


KIT_SCHEMA = "mosaic.ucm.maturity-tier1-operator-kit.v0.1"
KIT_REPAIR_SCHEMA = "mosaic.ucm.maturity-tier1-operator-kit.v0.2"
KIT_SCHEMAS = {KIT_SCHEMA, KIT_REPAIR_SCHEMA}
KIT_ROLE = "UCM_MATURITY_TIER1_OPERATOR_KIT"
EVIDENCE_SCHEMA = "mosaic.ucm.maturity-tier1-evidence.v0.1"
EVIDENCE_ROLE = "UCM_MATURITY_TIER1_EVIDENCE"
ADDENDUM_SCHEMA = "mosaic.ucm.maturity-operator-evidence-addendum.v0.1"
ADDENDUM_ROLE = "UCM_MATURITY_OPERATOR_EVIDENCE_ADDENDUM"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_record(archive: zipfile.ZipFile, name: str,
                      diagnostic: str) -> dict[str, Any]:
    raw = archive.read(name)
    value = strict_loads(raw)
    require(type(value) is dict and canonical_bytes(value) == raw, diagnostic)
    return value


def _v02_predecessor_disposition(archive: zipfile.ZipFile) -> dict[str, Any]:
    """Read the v0.2 kit's provenance record.

    The first v0.2 operator kit encoded its otherwise canonical record with one
    terminal LF.  Its exact archive is externally pinned and already executed,
    so the importer accepts only that bounded representation.  Successor kits
    are emitted without the compatibility newline.
    """
    raw = archive.read("PREDECESSOR-TIER1-DISPOSITION.json")
    value = strict_loads(raw)
    encoded = canonical_bytes(value)
    require(type(value) is dict and raw in {encoded, encoded + b"\n"},
            "MATURITY_OPERATOR_PREDECESSOR_DISPOSITION_NONCANONICAL")
    return value


def _boundary(value: dict[str, Any], diagnostic: str) -> None:
    require(all(value.get(key) == expected for key, expected in BOUNDARY.items()),
            diagnostic)


def verify_maturity_operator_evidence(
    *, kit_raw: bytes, evidence_raw: bytes, expected_kit_sha256: str,
) -> dict[str, Any]:
    """Verify PASS evidence against the exact pinned kit and embedded subject."""
    require_root(expected_kit_sha256)
    require(_sha(kit_raw) == expected_kit_sha256,
            "MATURITY_OPERATOR_KIT_PIN_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(kit_raw)) as kit_probe:
        kit_schema = _canonical_record(
            kit_probe, "MANIFEST.json", "MATURITY_OPERATOR_KIT_MANIFEST_NONCANONICAL"
        ).get("schema")
    require(kit_schema in KIT_SCHEMAS, "MATURITY_OPERATOR_KIT_SCHEMA_INVALID")
    kit_manifest = verify_deterministic_zip(
        kit_raw, expected_schema=kit_schema, expected_role=KIT_ROLE)
    evidence_manifest = verify_deterministic_zip(
        evidence_raw, expected_schema=EVIDENCE_SCHEMA, expected_role=EVIDENCE_ROLE)

    with zipfile.ZipFile(io.BytesIO(kit_raw)) as kit:
        source_raw = kit.read("QUALIFICATION-SOURCE.zip")
        runner_raw = kit.read("RUN-MATURITY-TIER1.py")
        qualification = _canonical_record(
            kit, "QUALIFICATION.json", "MATURITY_OPERATOR_QUALIFICATION_NONCANONICAL")
        if kit_schema == KIT_REPAIR_SCHEMA:
            predecessor_raw = kit.read("PREDECESSOR-TIER1-EVIDENCE.zip")
            disposition = _v02_predecessor_disposition(kit)
            verify_deterministic_zip(
                predecessor_raw, expected_schema=EVIDENCE_SCHEMA,
                expected_role=EVIDENCE_ROLE)
            with zipfile.ZipFile(io.BytesIO(predecessor_raw)) as predecessor:
                predecessor_result = _canonical_record(
                    predecessor, "TIER1-RESULT.json",
                    "MATURITY_OPERATOR_PREDECESSOR_RESULT_NONCANONICAL")
            require(_sha(predecessor_raw) == disposition.get("evidence_sha256")
                    and disposition.get("status")
                        == "BUILDER_REPAIRED_PENDING_OPERATOR_RERUN"
                    and disposition.get("operator_subject_sha256")
                        == predecessor_result.get("subject_sha256")
                    and disposition.get("court_root")
                        == predecessor_result.get("court_root")
                    and predecessor_result.get("status") == "HOLD_FOR_REPAIR",
                    "MATURITY_OPERATOR_PREDECESSOR_DISPOSITION_INVALID")
    source_sha256 = _sha(source_raw)
    require(qualification.get("status") == "PASS"
            and qualification.get("failures") == 0
            and qualification.get("errors") == 0
            and qualification.get("skips") == 0
            and qualification.get("operator_adversarial_status")
                == "SEPARATE_USER_RUN_REQUIRED",
            "MATURITY_OPERATOR_QUALIFICATION_INVALID")
    anchor = qualification.get("qualification_source_anchor")
    require(type(anchor) is dict
            and anchor.get("archive_sha256") == source_sha256,
            "MATURITY_OPERATOR_SUBJECT_ANCHOR_INVALID")
    require_root(qualification.get("qualification_root"))

    with zipfile.ZipFile(io.BytesIO(evidence_raw)) as evidence:
        result = _canonical_record(
            evidence, "TIER1-RESULT.json", "MATURITY_OPERATOR_RESULT_NONCANONICAL")
        evidence_runner = evidence.read("RUN-MATURITY-TIER1.py")
    require(evidence_runner == runner_raw,
            "MATURITY_OPERATOR_RUNNER_MISMATCH")
    _boundary(result, "MATURITY_OPERATOR_RESULT_BOUNDARY_INVALID")
    result_body = {key: deepcopy(value) for key, value in result.items()
                   if key != "court_root"}
    require_root(result.get("court_root"))
    require(result["court_root"] == root(result_body),
            "MATURITY_OPERATOR_RESULT_ROOT_INVALID")
    cases = result.get("cases")
    require(type(cases) is list and len(cases) > 0
            and result.get("case_count") == len(cases)
            and result.get("failed") == 0 and result.get("status") == "PASS",
            "MATURITY_OPERATOR_RESULT_STATUS_INVALID")
    identifiers = []
    for row in cases:
        require(type(row) is dict and set(row) == {"id", "status", "diagnostic"}
                and type(row["id"]) is str and row["id"]
                and row["status"] == "PASS"
                and type(row["diagnostic"]) is str,
                "MATURITY_OPERATOR_CASE_INVALID")
        identifiers.append(row["id"])
    require(len(set(identifiers)) == len(identifiers),
            "MATURITY_OPERATOR_CASE_DUPLICATE")
    require(result.get("subject_sha256") == source_sha256,
            "MATURITY_OPERATOR_SUBJECT_MISMATCH")

    body = {
        "schema": "mosaic.ucm.maturity-operator-evidence-acceptance.v0.1",
        "operator_evidence_class": "OPERATOR_REPRODUCED_BUILDER_AUTHORED",
        "operator_kit_sha256": expected_kit_sha256,
        "operator_kit_manifest_root": kit_manifest["manifest_root"],
        "qualification_source_sha256": source_sha256,
        "qualification_root": qualification["qualification_root"],
        "operator_evidence_sha256": _sha(evidence_raw),
        "operator_evidence_manifest_root": evidence_manifest["manifest_root"],
        "operator_result_root": result["court_root"],
        "operator_case_count": len(cases),
        "operator_failed_count": 0,
        "operator_status": "PASS",
        "independent_review_status": "PENDING",
        "application_execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "acceptance_root": root(body)}


def build_maturity_operator_evidence_addendum(
    *, kit_raw: bytes, evidence_raw: bytes, review_handoff_raw: bytes,
    freeze_receipt_raw: bytes, expected_kit_sha256: str,
    expected_review_handoff_sha256: str,
) -> tuple[bytes, dict[str, Any]]:
    """Seal verified operator evidence beside, not into, the frozen handoff."""
    require_root(expected_review_handoff_sha256)
    require(_sha(review_handoff_raw) == expected_review_handoff_sha256,
            "MATURITY_OPERATOR_REVIEW_HANDOFF_PIN_MISMATCH")
    acceptance = verify_maturity_operator_evidence(
        kit_raw=kit_raw, evidence_raw=evidence_raw,
        expected_kit_sha256=expected_kit_sha256)
    freeze = strict_loads(freeze_receipt_raw)
    require(type(freeze) is dict and freeze.get("qualification_root")
            == acceptance["qualification_root"],
            "MATURITY_OPERATOR_FREEZE_QUALIFICATION_MISMATCH")
    require_root(freeze.get("freeze_root"))
    require(root({key: deepcopy(value) for key, value in freeze.items()
                  if key != "freeze_root"}) == freeze["freeze_root"],
            "MATURITY_OPERATOR_FREEZE_ROOT_INVALID")
    index_body = {
        "schema": "mosaic.ucm.maturity-operator-evidence-addendum-index.v0.1",
        "review_handoff_sha256": expected_review_handoff_sha256,
        "freeze_root": freeze["freeze_root"],
        "acceptance_root": acceptance["acceptance_root"],
        "operator_evidence_sha256": _sha(evidence_raw),
        "independent_review_status": "PENDING",
        **BOUNDARY,
    }
    index = {**index_body, "index_root": root(index_body)}
    payloads = {
        "OPERATOR-EVIDENCE.zip": evidence_raw,
        "OPERATOR-EVIDENCE-ACCEPTANCE.json": canonical_bytes(acceptance),
        "ADDENDUM-INDEX.json": canonical_bytes(index),
        "FREEZE-RECEIPT.json": freeze_receipt_raw,
        "README.md": (
            "# UCM maturity operator-evidence addendum\n\n"
            "This archive binds operator-reproduced builder-authored Tier 1 evidence "
            "to the exact frozen review subject. It is not independent review and "
            "grants no authority.\n").encode("utf-8"),
    }
    first = deterministic_zip(payloads, schema=ADDENDUM_SCHEMA,
                              artifact_role=ADDENDUM_ROLE)
    second = deterministic_zip(payloads, schema=ADDENDUM_SCHEMA,
                               artifact_role=ADDENDUM_ROLE)
    require(first == second, "MATURITY_OPERATOR_ADDENDUM_NONDETERMINISTIC")
    verify_deterministic_zip(first, expected_schema=ADDENDUM_SCHEMA,
                             expected_role=ADDENDUM_ROLE)
    return first, acceptance
