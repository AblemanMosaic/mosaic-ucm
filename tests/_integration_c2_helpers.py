from __future__ import annotations

from copy import deepcopy
import io
from pathlib import Path
import zipfile

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY, compile_contract
from ucm.artifacts import deterministic_zip
from ucm.control_planes import make_control_plane_disposition
from ucm.correspondence import run_correspondence_court
from ucm.stage1 import assemble_stage1_bundle
from ucm.subject import bind_subject

from _amcas_helpers import contract as legacy_contract


def rooted(schema: str, field: str, **values):
    body = {"schema": schema, **deepcopy(values), **BOUNDARY}
    return {**body, field: root(body)}


def control(application_id: str = "EXAMPLE.PORTABLE_AGENT"):
    return make_control_plane_disposition(
        application_id=application_id,
        semantic_authority="APP.NATIVE",
        effect_executor="APP.NATIVE",
        identity_binding_status="UNBOUND",
        jurisdiction_binding_status="UNBOUND",
        gate_namespace="UCM.INTEGRATION.EXAMPLE.PORTABLE.AGENT",
        native_control_planes=[{
            "id": "APP.NATIVE",
            "role": "APPLICATION_SEMANTICS_AND_EFFECTS",
            "disposition": "RETAIN",
            "semantic_authority": True,
            "effect_classes": ["LOCAL_ARTIFACT_PREPARATION"],
            "equivalence_evidence_root": None,
        }],
    )


def current_contract(control_value=None):
    control_value = control_value or control()
    value = legacy_contract()
    value["schema"] = "mosaic.amcas.integration-contract.v0.2"
    value["integration_boundary"] = {
        "semantic_authority": control_value["semantic_authority"],
        "effect_executor": control_value["effect_executor"],
        "identity_binding_status": control_value["identity_binding_status"],
        "jurisdiction_binding_status": control_value["jurisdiction_binding_status"],
        "gate_namespace": "UCM.INTEGRATION",
        "control_plane_root": control_value["root"],
    }
    body = {key: raw for key, raw in value.items() if key != "contract_root"}
    value["contract_root"] = root(body)
    return value


def stage1_bundle(tmp_path: Path):
    subject_dir = tmp_path / "subject"
    subject_dir.mkdir()
    (subject_dir / "app.txt").write_text("bound subject\n", encoding="utf-8")
    subject = bind_subject(subject_dir, {
        "schema": "mosaic.ucm.subject-binding-policy.v0.1",
        "subject_id": "EXAMPLE.PORTABLE.AGENT",
        "mode": "IMMUTABLE_SNAPSHOT",
        "include": ["**/*"],
        "exclude": [],
        "allow_symlinks": False,
        "git_observation": "NONE",
    })
    control_value = control()
    contract = current_contract(control_value)
    contract["subject"]["source_root"] = subject["source_root"]
    contract["subject"]["manifest_root"] = subject["manifest_root"]
    contract["contract_root"] = root({key: raw for key, raw in contract.items()
                                      if key != "contract_root"})
    compiled = compile_contract(contract)
    decision_root = root({"decision": "PASS", "meaning": "same"})
    court = run_correspondence_court({
        "schema": "mosaic.ucm.native-correspondence-cases.v0.1",
        "application_id": contract["application"]["id"],
        "subject_root": subject["source_root"],
        "native_validator_id": "APP.NATIVE",
        "ucm_validator_id": "UCM.SHADOW",
        "cases": [{
            "case_id": "C001",
            "input_root": root({"input": 1}),
            "native": {"decision": "PASS", "result_root": decision_root},
            "ucm": {"decision": "PASS", "result_root": decision_root},
        }],
    })
    inventory = rooted(
        "mosaic.ucm.capability-effect-inventory.v0.1", "inventory_root",
        application_id=contract["application"]["id"], capabilities=["ORIENT"], effects=[])
    graph = rooted(
        "mosaic.ucm.integration-content-graph.v0.1", "graph_root",
        application_id=contract["application"]["id"], nodes=[], edges=[])
    report = rooted(
        "mosaic.ucm.stage-i1-session-report.v0.1", "report_root",
        application_id=contract["application"]["id"], findings=[], limitations=[])
    journal = deterministic_zip(
        {"JOURNAL-HEAD.json": canonical_bytes({"schema": "test.journal-head.v1",
                                                "head": "0" * 64})},
        schema="mosaic.ucm.integration-journal-archive.v0.1",
        artifact_role="CANONICAL_INTEGRATION_JOURNAL")
    payloads = {
        "SUBJECT-BINDING.json": canonical_bytes(subject),
        "AMCAS-CONTRACT.json": canonical_bytes(contract),
        "INTEGRATION-IR.json": canonical_bytes(compiled),
        "CONTROL-PLANE-DISPOSITION.json": canonical_bytes(control_value),
        "CORRESPONDENCE-COURT.json": canonical_bytes(court),
        "CAPABILITY-EFFECT-INVENTORY.json": canonical_bytes(inventory),
        "CONTENT-GRAPH.json": canonical_bytes(graph),
        "JOURNAL.zip": journal,
        "SESSION-REPORT.json": canonical_bytes(report),
    }
    raw = assemble_stage1_bundle(
        payloads, status="READY_FOR_REVIEW", limitations=["INFORMATION_ONLY"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        complete = {name: archive.read(name) for name in archive.namelist()
                    if name != "MANIFEST.json"}
    return raw, complete


def legacy_stage1_bundle(tmp_path: Path):
    raw, payloads = stage1_bundle(tmp_path)
    index = __import__("json").loads(payloads["STAGE-I1-INDEX.json"])
    for field in ("thr_manifest_root", "H_s", "H_c", "H_m", "H_j", "H_r",
                  "index_root"):
        index.pop(field)
    index["schema"] = "mosaic.ucm.stage-i1-index.v0.1"
    index["index_root"] = root(index)
    legacy = {name: data for name, data in payloads.items()
              if name != "THR-CAS-MANIFEST.json"}
    legacy["STAGE-I1-INDEX.json"] = canonical_bytes(index)
    return deterministic_zip(
        legacy,
        schema="mosaic.ucm.stage-i1-bundle.v0.1",
        artifact_role="APPLICATION_STAGE_I1_RETURN",
    )
