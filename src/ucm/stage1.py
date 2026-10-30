"""Portable Stage I1 return bundle contract and verifier."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from typing import Any
import zipfile

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root, strict_loads

from .amcas import BOUNDARY, compile_contract, validate_contract
from .artifacts import deterministic_zip, verify_deterministic_zip
from .control_planes import verify_control_plane_disposition
from .correspondence import verify_correspondence_court
from .subject import verify_subject_binding
from .thr_cas import build_thr_manifest, verify_thr_manifest


SCHEMA_V1 = "mosaic.ucm.stage-i1-bundle.v0.1"
SCHEMA = "mosaic.ucm.stage-i1-bundle.v0.2"
ROLE = "APPLICATION_STAGE_I1_RETURN"
INDEX_SCHEMA_V1 = "mosaic.ucm.stage-i1-index.v0.1"
INDEX_SCHEMA = "mosaic.ucm.stage-i1-index.v0.2"
REQUIRED_BASE = {
    "SUBJECT-BINDING.json",
    "AMCAS-CONTRACT.json",
    "INTEGRATION-IR.json",
    "CONTROL-PLANE-DISPOSITION.json",
    "CORRESPONDENCE-COURT.json",
    "CAPABILITY-EFFECT-INVENTORY.json",
    "CONTENT-GRAPH.json",
    "JOURNAL.zip",
    "SESSION-REPORT.json",
}
REQUIRED_V1 = REQUIRED_BASE | {"STAGE-I1-INDEX.json"}
REQUIRED = REQUIRED_BASE | {"THR-CAS-MANIFEST.json", "STAGE-I1-INDEX.json"}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _rooted(value: Any, schema: str, root_field: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema, "STAGE_I1_RECORD_SCHEMA_INVALID")
    require(root_field in value, "STAGE_I1_RECORD_ROOT_MISSING")
    body = {key: deepcopy(raw) for key, raw in value.items() if key != root_field}
    require(value[root_field] == root(body), "STAGE_I1_RECORD_ROOT_INVALID")
    return deepcopy(value)


def _archive_schema(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = strict_loads(archive.read("MANIFEST.json"))
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError) as error:
        raise ValueError("ARTIFACT_ARCHIVE_INVALID") from error
    require(type(manifest) is dict and type(manifest.get("schema")) is str,
            "ARTIFACT_MANIFEST_SCHEMA_INVALID")
    return manifest["schema"]


def _verify_stage1_bundle(raw: bytes, *, schema: str, required: set[str],
                          thr_required: bool) -> dict[str, Any]:
    manifest = verify_deterministic_zip(raw, expected_schema=schema, expected_role=ROLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = set(archive.namelist())
        require(names == required | {"MANIFEST.json"}, "STAGE_I1_FILE_SET_INVALID")
        payloads = {name: archive.read(name) for name in required}
    records = {name: strict_loads(data) for name, data in payloads.items()
               if name.endswith(".json")}
    subject = verify_subject_binding(records["SUBJECT-BINDING.json"])
    require(subject["binding_status"] != "UNBOUND"
            and subject["source_root"] != "0" * 64
            and subject["manifest_root"] != "0" * 64,
            "STAGE_I1_SUBJECT_UNBOUND")
    contract = validate_contract(records["AMCAS-CONTRACT.json"])
    require(contract["subject"]["source_root"] == subject["source_root"]
            and contract["subject"]["manifest_root"] == subject["manifest_root"],
            "STAGE_I1_CONTRACT_SUBJECT_MISMATCH")
    compiled = compile_contract(contract)
    require(records["INTEGRATION-IR.json"] == compiled, "STAGE_I1_IR_MISMATCH")
    control = verify_control_plane_disposition(records["CONTROL-PLANE-DISPOSITION.json"])
    require(control["application_id"] == contract["application"]["id"],
            "STAGE_I1_CONTROL_APPLICATION_MISMATCH")
    boundary = contract.get("integration_boundary")
    require(type(boundary) is dict
            and boundary["control_plane_root"] == control["root"]
            and boundary["semantic_authority"] == control["semantic_authority"]
            and boundary["effect_executor"] == control["effect_executor"]
            and boundary["identity_binding_status"] == control["identity_binding_status"]
            and boundary["jurisdiction_binding_status"] == control["jurisdiction_binding_status"]
            and control["gate_namespace"].startswith(boundary["gate_namespace"] + "."),
            "STAGE_I1_CONTROL_CONTRACT_MISMATCH")
    court = verify_correspondence_court(records["CORRESPONDENCE-COURT.json"])
    require(court["application_id"] == contract["application"]["id"]
            and court["subject_root"] == subject["source_root"],
            "STAGE_I1_CORRESPONDENCE_SUBJECT_MISMATCH")
    replacement_roots = [row["equivalence_evidence_root"]
                         for row in control["native_control_planes"]
                         if row["disposition"] == "REPLACE_AFTER_EQUIVALENCE"]
    require(all(value == court["court_root"] for value in replacement_roots),
            "STAGE_I1_REPLACEMENT_EVIDENCE_MISMATCH")
    inventory = _rooted(records["CAPABILITY-EFFECT-INVENTORY.json"],
                        "mosaic.ucm.capability-effect-inventory.v0.1", "inventory_root")
    exact_keys(inventory, {"schema", "application_id", "capabilities", "effects",
                           "standing", "authority_effect", "real_a5", "g0",
                           "inventory_root"})
    require(inventory["application_id"] == contract["application"]["id"]
            and inventory["capabilities"] == sorted(row["id"] for row in contract["capabilities"])
            and inventory["effects"] == sorted(row["id"] for row in contract["effects"]),
            "STAGE_I1_INVENTORY_CONTRACT_MISMATCH")
    graph = _rooted(records["CONTENT-GRAPH.json"],
                    "mosaic.ucm.integration-content-graph.v0.1", "graph_root")
    report = _rooted(records["SESSION-REPORT.json"],
                     "mosaic.ucm.stage-i1-session-report.v0.1", "report_root")
    require(report.get("application_id") == contract["application"]["id"],
            "STAGE_I1_REPORT_APPLICATION_MISMATCH")
    verify_deterministic_zip(
        payloads["JOURNAL.zip"],
        expected_schema="mosaic.ucm.integration-journal-archive.v0.1",
        expected_role="CANONICAL_INTEGRATION_JOURNAL",
    )
    thr = None
    if thr_required:
        thr = verify_thr_manifest(
            records["THR-CAS-MANIFEST.json"],
            payloads={name: payloads[name] for name in REQUIRED_BASE},
        )
        require(thr["application_id"] == contract["application"]["id"],
                "STAGE_I1_THR_APPLICATION_MISMATCH")
        exact_keys(thr["meaning"], {
            "schema", "subject_root", "subject_manifest_root", "contract_root",
            "ir_root", "inventory_root", "content_graph_root",
        })
        require(thr["meaning"] == {
            "schema": "mosaic.ucm.thr.meaning.v0.1",
            "subject_root": subject["source_root"],
            "subject_manifest_root": subject["manifest_root"],
            "contract_root": contract["contract_root"],
            "ir_root": compiled["ir_root"],
            "inventory_root": inventory["inventory_root"],
            "content_graph_root": graph["graph_root"],
        }, "STAGE_I1_THR_MEANING_MISMATCH")
        exact_keys(thr["admissibility"], {
            "schema", "control_plane_root", "correspondence_court_root",
            "correspondence_status", "stage_i1_status", "standing",
            "authority_effect", "real_a5", "g0",
        })
        exact_keys(thr["locality"], {
            "schema", "application_id", "subject_id", "identity_binding_status",
            "jurisdiction_binding_status", "gate_namespace",
        })
        require(thr["locality"] == {
            "schema": "mosaic.ucm.thr.locality.v0.1",
            "application_id": contract["application"]["id"],
            "subject_id": subject["subject_id"],
            "identity_binding_status": control["identity_binding_status"],
            "jurisdiction_binding_status": control["jurisdiction_binding_status"],
            "gate_namespace": control["gate_namespace"],
        }, "STAGE_I1_THR_LOCALITY_MISMATCH")
        exact_keys(thr["receipt_identity"], {
            "schema", "journal_sha256", "session_report_root",
        })
        require(thr["receipt_identity"] == {
            "schema": "mosaic.ucm.thr.receipt-identity.v0.1",
            "journal_sha256": _sha(payloads["JOURNAL.zip"]),
            "session_report_root": report["report_root"],
        }, "STAGE_I1_THR_RECEIPT_MISMATCH")
    index_keys = {
        "schema", "application_id", "subject_binding_root", "contract_root", "ir_root",
        "control_plane_root", "correspondence_court_root", "inventory_root",
        "content_graph_root", "journal_sha256", "session_report_root", "status",
        "limitations", "standing", "authority_effect", "real_a5", "g0", "index_root",
    }
    if thr_required:
        index_keys |= {"thr_manifest_root", "H_s", "H_c", "H_m", "H_j", "H_r"}
    index = exact_keys(records["STAGE-I1-INDEX.json"], index_keys)
    require(index["schema"] == (INDEX_SCHEMA if thr_required else INDEX_SCHEMA_V1)
            and index["application_id"] == contract["application"]["id"],
            "STAGE_I1_INDEX_IDENTITY_INVALID")
    expected_roots = {
        "subject_binding_root": subject["binding_root"],
        "contract_root": contract["contract_root"],
        "ir_root": compiled["ir_root"],
        "control_plane_root": control["root"],
        "correspondence_court_root": court["court_root"],
        "inventory_root": inventory["inventory_root"],
        "content_graph_root": graph["graph_root"],
        "journal_sha256": _sha(payloads["JOURNAL.zip"]),
        "session_report_root": report["report_root"],
    }
    if thr_required:
        expected_admissibility = {
            "schema": "mosaic.ucm.thr.admissibility.v0.1",
            "control_plane_root": control["root"],
            "correspondence_court_root": court["court_root"],
            "correspondence_status": court["status"],
            "stage_i1_status": index["status"],
            **BOUNDARY,
        }
        require(thr["admissibility"] == expected_admissibility,
                "STAGE_I1_THR_ADMISSIBILITY_MISMATCH")
        expected_roots |= {
            "thr_manifest_root": thr["h_body"],
            **thr["commitments"],
        }
    require(all(index[key] == value for key, value in expected_roots.items()),
            "STAGE_I1_INDEX_BINDING_MISMATCH")
    require(index["status"] in {"READY_FOR_REVIEW", "HOLD_FOR_REPAIR"}
            and type(index["limitations"]) is list
            and all(type(row) is str for row in index["limitations"]),
            "STAGE_I1_INDEX_STATUS_INVALID")
    require(index["status"] != "READY_FOR_REVIEW" or court["status"] == "PASS_EQUIVALENT",
            "STAGE_I1_READY_WITH_DIVERGENCE")
    require({key: index[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I1_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(value) for key, value in index.items() if key != "index_root"}
    require(index["index_root"] == root(body), "STAGE_I1_INDEX_ROOT_INVALID")
    result = {
        "schema": ("mosaic.ucm.stage-i1-verification.v0.2" if thr_required
                   else "mosaic.ucm.stage-i1-verification.v0.1"),
        "application_id": index["application_id"],
        "subject_root": subject["source_root"],
        "status": "PASS_VERIFIED",
        "stage_i1_status": index["status"],
        "manifest_root": manifest["manifest_root"],
        "index_root": index["index_root"],
        "correspondence_status": court["status"],
        **BOUNDARY,
    }
    if thr_required:
        result |= {"thr_status": "PASS_SEPARATED",
                   "thr_manifest_root": thr["h_body"],
                   "thr_commitments": deepcopy(thr["commitments"])}
    else:
        result |= {"thr_status": "NOT_PRESENT_LEGACY", "thr_manifest_root": None,
                   "thr_commitments": None}
    return result


def verify_stage1_bundle(raw: bytes) -> dict[str, Any]:
    schema = _archive_schema(raw)
    require(schema in {SCHEMA_V1, SCHEMA}, "STAGE_I1_SCHEMA_UNSUPPORTED")
    return _verify_stage1_bundle(
        raw,
        schema=schema,
        required=REQUIRED if schema == SCHEMA else REQUIRED_V1,
        thr_required=schema == SCHEMA,
    )


def upgrade_stage1_bundle(raw: bytes) -> bytes:
    """Wrap a verified v0.1 return in the v0.2 THR-separated envelope."""
    schema = _archive_schema(raw)
    if schema == SCHEMA:
        verify_stage1_bundle(raw)
        return raw
    require(schema == SCHEMA_V1, "STAGE_I1_SCHEMA_UNSUPPORTED")
    verify_stage1_bundle(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        base = {name: archive.read(name) for name in REQUIRED_BASE}
        index = strict_loads(archive.read("STAGE-I1-INDEX.json"))
    return assemble_stage1_bundle(
        base,
        status=index["status"],
        limitations=deepcopy(index["limitations"]),
    )


def assemble_stage1_bundle(payloads: dict[str, bytes], *, status: str,
                           limitations: list[str]) -> bytes:
    """Assemble the C3 Stage I1 envelope from exact pre-index payloads."""
    require(set(payloads) == REQUIRED_BASE, "STAGE_I1_BASE_FILE_SET_INVALID")
    require(status in {"READY_FOR_REVIEW", "HOLD_FOR_REPAIR"}
            and type(limitations) is list
            and all(type(row) is str for row in limitations),
            "STAGE_I1_INDEX_STATUS_INVALID")
    records = {name: strict_loads(raw) for name, raw in payloads.items()
               if name.endswith(".json")}
    subject = verify_subject_binding(records["SUBJECT-BINDING.json"])
    contract = validate_contract(records["AMCAS-CONTRACT.json"])
    compiled = compile_contract(contract)
    require(records["INTEGRATION-IR.json"] == compiled, "STAGE_I1_IR_MISMATCH")
    control = verify_control_plane_disposition(records["CONTROL-PLANE-DISPOSITION.json"])
    court = verify_correspondence_court(records["CORRESPONDENCE-COURT.json"])
    inventory = _rooted(records["CAPABILITY-EFFECT-INVENTORY.json"],
                        "mosaic.ucm.capability-effect-inventory.v0.1", "inventory_root")
    graph = _rooted(records["CONTENT-GRAPH.json"],
                    "mosaic.ucm.integration-content-graph.v0.1", "graph_root")
    report = _rooted(records["SESSION-REPORT.json"],
                     "mosaic.ucm.stage-i1-session-report.v0.1", "report_root")
    thr = build_thr_manifest(
        application_id=contract["application"]["id"],
        payloads=payloads,
        meaning={
            "subject_root": subject["source_root"],
            "subject_manifest_root": subject["manifest_root"],
            "contract_root": contract["contract_root"],
            "ir_root": compiled["ir_root"],
            "inventory_root": inventory["inventory_root"],
            "content_graph_root": graph["graph_root"],
        },
        admissibility={
            "control_plane_root": control["root"],
            "correspondence_court_root": court["court_root"],
            "correspondence_status": court["status"],
            "stage_i1_status": status,
            **BOUNDARY,
        },
        locality={
            "application_id": contract["application"]["id"],
            "subject_id": subject["subject_id"],
            "identity_binding_status": control["identity_binding_status"],
            "jurisdiction_binding_status": control["jurisdiction_binding_status"],
            "gate_namespace": control["gate_namespace"],
        },
        receipts={
            "journal_sha256": _sha(payloads["JOURNAL.zip"]),
            "session_report_root": report["report_root"],
        },
    )
    index_body = {
        "schema": INDEX_SCHEMA,
        "application_id": contract["application"]["id"],
        "subject_binding_root": subject["binding_root"],
        "contract_root": contract["contract_root"],
        "ir_root": compiled["ir_root"],
        "control_plane_root": control["root"],
        "correspondence_court_root": court["court_root"],
        "inventory_root": inventory["inventory_root"],
        "content_graph_root": graph["graph_root"],
        "journal_sha256": _sha(payloads["JOURNAL.zip"]),
        "session_report_root": report["report_root"],
        "thr_manifest_root": thr["h_body"],
        **thr["commitments"],
        "status": status,
        "limitations": deepcopy(limitations),
        **BOUNDARY,
    }
    index = {**index_body, "index_root": root(index_body)}
    complete = {**payloads,
                "THR-CAS-MANIFEST.json": canonical_bytes(thr),
                "STAGE-I1-INDEX.json": canonical_bytes(index)}
    return build_stage1_bundle(complete)


def build_stage1_bundle(payloads: dict[str, bytes]) -> bytes:
    require(set(payloads) == REQUIRED, "STAGE_I1_FILE_SET_INVALID")
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    verify_stage1_bundle(raw)
    return raw
