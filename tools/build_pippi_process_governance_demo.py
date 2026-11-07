from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.development_standards import build_standards_catalog, evaluate_standards
from ucm.journal import GENESIS, build_event
from ucm.process_governance import (
    assess_process_milestone,
    build_artifact_producer_receipt,
    build_courthouse_process_binding,
    build_dkn_locality_binding,
    build_exact_execution_capsule,
    build_process_baseline,
    build_process_checkpoint,
    build_process_milestone,
    build_process_observatory,
    build_process_standards_schedule,
    build_process_thr_manifest,
)
from ucm.system import BOUNDARY, capability_registry
from process_governance_common import ROOT as PROJECT_ROOT, SOURCE_PATHS, source_manifest


FIXTURE_PUBLIC_KEY = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def add_event(events: list[dict], *, event_id: str, event_type: str,
              payload: dict) -> dict:
    predecessor = events[-1]["event_root"] if events else GENESIS
    event = build_event(sequence=len(events) + 1, predecessor=predecessor,
                        event_id=event_id, event_type=event_type,
                        actor={"kind": "SYSTEM", "mosaic_id": None,
                               "session_id": None}, payload=payload)
    events.append(event)
    return event


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qualification", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    manifest = source_manifest()
    qualification = strict_loads(args.qualification.read_bytes())
    if not (qualification.get("status") == "PASS"
            and qualification.get("source_manifest_root") == manifest["source_manifest_root"]
            and qualification.get("source_file_count") == manifest["file_count"]):
        raise SystemExit("PROCESS_QUALIFICATION_SOURCE_MISMATCH")
    args.out_dir.mkdir(parents=True, exist_ok=False)

    policy = strict_loads((ROOT / "policy-packs/PIPPI-PROCESS-GOVERNANCE-v0.1.json").read_bytes())
    contract = strict_loads((ROOT / "spec/PIPPI-PROCESS-GOVERNANCE-CONTRACT.json").read_bytes())
    policy_root = root(policy)
    contract_root = root(contract)
    registry = capability_registry()
    locality = build_dkn_locality_binding(
        phase_code="UCM.V0.1.PROCESS",
        authority_public_key_hex=FIXTURE_PUBLIC_KEY,
        semantic_namespace="mosaic.ucm.process.dogfood.fixture",
        universe_root=root({"universe": "UCM_V0_1_INFORMATION_ONLY"}),
        namespace_policy_root=policy_root,
        passport=None,
        possession_receipt_root=None,
        local_admission_root=None,
    )
    dependencies = [{"path": row["path"], "sha256": row["sha256"], "role": "SOURCE"}
                    for row in manifest["files"]]
    capsule = build_exact_execution_capsule(
        capsule_id="UCM.PROCESS.QUALIFICATION.C1",
        executable_root=root({"runtime": "DECLARED_PYTHON_3_12_TO_3_13"}),
        runner_root=next(row["sha256"] for row in manifest["files"]
                         if row["path"] == "tools/run_process_governance_qualification.py"),
        argv=["python", "tools/run_process_governance_qualification.py", "QUALIFICATION.json"],
        normalized_cwd="ucm-source",
        environment_projection={"PYTHONDONTWRITEBYTECODE": "1"},
        dependencies=dependencies,
        missing_dependency_ids=[],
        exact_input_roots=sorted([manifest["source_manifest_root"], policy_root, contract_root]),
        policy_root=policy_root,
        profile_root=registry["root"],
        authority_root=root({"authority": "NONE"}),
        jurisdiction_root=locality["locality_binding_root"],
        effect_class="LOCAL_TEST_EXECUTION",
        expected_write_paths=["artifacts/.history/QUALIFICATION.json",
                              "out/QUALIFICATION.json"],
        transaction_history_paths=["artifacts/.history/QUALIFICATION.json"],
        adapter_root=next(row["sha256"] for row in manifest["files"]
                          if row["path"] == "tools/run_process_governance_qualification.py"),
    )
    qualification_producer_receipt = build_artifact_producer_receipt(
        artifact_path="out/QUALIFICATION.json",
        artifact_sha256=sha(args.qualification.read_bytes()),
        producer_operation_root=capsule["operation_identity_root"],
        predecessor_artifact_sha256=None,
        predecessor_producer_operation_root=None,
        transaction_history_path=None,
        supersession_kind="INITIAL",
    )
    catalog = build_standards_catalog(
        catalog_id="PIPPI.PROCESS.DOGFOOD.C1",
        policy_root=policy_root,
        obligations=[{
            "obligation_id": "PROCESS.EXACT.BASELINE",
            "statement": "Bind the exact source and controlling contracts.",
            "class": "MANDATORY", "triggers": [],
            "check_ids": ["CHECK.PROCESS.SOURCE"], "evidence_required": True,
        }, {
            "obligation_id": "PROCESS.TARGETED.QUALIFICATION",
            "statement": "Run the exact positive process-governance test denominator.",
            "class": "MANDATORY", "triggers": [],
            "check_ids": ["CHECK.PROCESS.QUALIFICATION"], "evidence_required": True,
        }],
    )
    source_root = manifest["source_manifest_root"]
    evaluation = evaluate_standards(
        catalog=catalog, subject_root=source_root, active_triggers=[],
        check_results=[{
            "check_id": "CHECK.PROCESS.QUALIFICATION", "role": "TARGETED",
            "subject_root": source_root, "status": "PASS",
            "evidence_root": qualification["qualification_root"], "witness_root": None,
        }, {
            "check_id": "CHECK.PROCESS.SOURCE", "role": "STATIC",
            "subject_root": source_root, "status": "PASS",
            "evidence_root": source_root, "witness_root": None,
        }],
    )
    baseline = build_process_baseline(
        project_id="UCM.PIPPI.PROCESS.DOGFOOD.C1",
        objective="Use P/PPI process governance to govern its own portable successor.",
        subject_root=source_root, source_manifest_root=source_root,
        architecture_contract_root=contract_root,
        amcas_contract_root=root({"amcas": "UCM_INTERNAL_DOGFOOD_NO_APPLICATION_EXECUTION"}),
        standards_catalog_root=catalog["catalog_root"],
        policy_roots=[policy_root],
        requirement_roots=sorted(root({"requirement": row["id"]})
                                 for row in policy["requirements"]),
        software_generation_root=registry["root"],
        initial_journal_head_root=GENESIS,
        user_identity_root=root({"identity": "EXTERNAL_GOVERNOR_UNBOUND"}),
        session_identity_root=root({"identity": "BUILDER_SESSION_FIXTURE"}),
        locality_binding=locality,
        responsibilities=[{
            "role_id": "BUILDER", "actor_identity_root": root({"identity": "BUILDER_SESSION_FIXTURE"}),
            "responsibility_ids": ["IMPLEMENT", "PACKAGE", "TEST"],
            "acceptance_scope_ids": [],
        }, {
            "role_id": "GOVERNOR", "actor_identity_root": root({"identity": "EXTERNAL_GOVERNOR_UNBOUND"}),
            "responsibility_ids": ["ACCEPT_OR_REFUSE"],
            "acceptance_scope_ids": ["MILESTONE.PROCESS.C1"],
        }],
        deliverable_ids=["PROCESS.CODE", "PROCESS.DOCS", "PROCESS.OPERATOR.KIT"],
        execution_capsule_roots=[capsule["execution_capsule_root"]],
    )
    milestone = build_process_milestone(
        milestone_id="MILESTONE.PROCESS.C1",
        process_baseline_root=baseline["process_baseline_root"],
        title="Portable P/PPI process-governance successor",
        objective="Deliver exact records, projections, dogfood evidence and operator review material.",
        predecessor_milestone_ids=[],
        entry_criteria=[{"criterion_id": "ENTRY.BASELINE", "kind": "ARTIFACT",
                         "expected_root": baseline["process_baseline_root"]}],
        deliverables=[{"deliverable_id": "PROCESS.CODE", "artifact_role": "IMPLEMENTATION",
                       "subject_root": source_root,
                       "required_check_ids": ["CHECK.PROCESS.QUALIFICATION"]}],
        standards_obligation_ids=["PROCESS.EXACT.BASELINE", "PROCESS.TARGETED.QUALIFICATION"],
        acceptance_role_id="GOVERNOR", acceptance_policy_root=policy_root,
        rollback_required=True, rollback_plan_root=root({"rollback": "SOURCE_CONTROL_RESTORE"}),
        authority_ceiling=BOUNDARY,
    )
    assessment = assess_process_milestone(
        milestone=milestone, accepted_predecessors=[],
        entry_evidence=[{"criterion_id": "ENTRY.BASELINE",
                         "evidence_root": baseline["process_baseline_root"]}],
        check_results=[{"check_id": "CHECK.PROCESS.QUALIFICATION", "role": "TARGETED",
                        "subject_root": source_root, "status": "PASS",
                        "evidence_root": qualification["qualification_root"],
                        "witness_root": None, "freshness": "CURRENT"}],
        standards_evaluation=evaluation,
    )
    events: list[dict] = []
    add_event(events, event_id="PROCESS.BASELINE.BOUND", event_type="BASELINE_BOUND",
              payload={"process_baseline_root": baseline["process_baseline_root"]})
    checkpoints = []
    prior = None
    for sequence, state, active, assessments in (
        (1, "PROPOSED", [], []),
        (2, "READY", [], []),
        (3, "ACTIVE", ["WORK.PROCESS.C1"], []),
    ):
        checkpoint = build_process_checkpoint(
            baseline=baseline, sequence=sequence, predecessor_checkpoint=prior,
            lifecycle_state=state, plan_root=root({"plan": "PROCESS.C1"}),
            milestone_assessments=assessments, milestone_decisions=[],
            active_work_ids=active, hold_codes=[], evidence_roots=[], decision_roots=[],
            journal_head_root=events[-1]["event_root"])
        checkpoints.append(checkpoint)
        add_event(events, event_id=f"PROCESS.CHECKPOINT.{sequence}",
                  event_type="CHECKPOINT_CREATED",
                  payload={"process_checkpoint_root": checkpoint["process_checkpoint_root"]})
        prior = checkpoint
    add_event(events, event_id="PROCESS.QUALIFICATION.RECORDED", event_type="TEST_RECORDED",
              payload={"qualification_root": qualification["qualification_root"],
                       "source_manifest_root": source_root})
    awaiting = build_process_checkpoint(
        baseline=baseline, sequence=4, predecessor_checkpoint=prior,
        lifecycle_state="AWAITING_ACCEPTANCE", plan_root=root({"plan": "PROCESS.C1"}),
        milestone_assessments=[assessment], milestone_decisions=[], active_work_ids=[],
        hold_codes=[], evidence_roots=[qualification["qualification_root"]],
        decision_roots=[], journal_head_root=events[-1]["event_root"])
    checkpoints.append(awaiting)
    add_event(events, event_id="PROCESS.CHECKPOINT.4", event_type="CHECKPOINT_CREATED",
              payload={"process_checkpoint_root": awaiting["process_checkpoint_root"]})
    schedule = build_process_standards_schedule(
        catalog=catalog, subject_root=source_root,
        event_facts=[{"event_id": "EVENT.QUALIFICATION.COMPLETE", "sequence": 1,
                      "trigger": "QUALIFICATION_COMPLETE",
                      "event_root": qualification["qualification_root"]}],
        last_satisfied=[
            {"obligation_id": row["obligation_id"], "evaluation_root": evaluation["evaluation_root"],
             "subject_root": source_root, "sequence": 1}
            for row in catalog["obligations"]
        ], invalidations=[])
    observatory = build_process_observatory(
        checkpoint=awaiting, standards_schedule=schedule,
        artifact_statuses=[{"artifact_id": "PROCESS.CODE", "implementation_root": source_root,
                            "test_evidence_roots": [qualification["qualification_root"]],
                            "review_root": None, "acceptance_root": None}],
        replan_roots=[])
    courthouse_binding = build_courthouse_process_binding(
        baseline=baseline, checkpoint=awaiting, execution_capsule=capsule,
        requested_surface="COURTHOUSE.VNEXT.EXECUTE",
        authority_policy_root=policy_root,
        native_runner_binding_root=root({"runner": "COURTHOUSE.VNEXT.UNBOUND"}),
    )
    thr = build_process_thr_manifest(
        baseline=baseline, locality_binding=locality, checkpoint=awaiting,
        milestones=[milestone], assessments=[assessment], decisions=[],
        standards_evaluation_roots=[evaluation["evaluation_root"]],
        evidence_receipt_roots=[qualification["qualification_root"]],
        interpretation_profile_root=contract_root)
    records = {
        "SOURCE-MANIFEST.json": manifest,
        "QUALIFICATION.json": qualification,
        "LOCALITY.json": locality,
        "EXACT-EXECUTION-CAPSULE.json": capsule,
        "QUALIFICATION-PRODUCER-RECEIPT.json": qualification_producer_receipt,
        "STANDARDS-CATALOG.json": catalog,
        "STANDARDS-EVALUATION.json": evaluation,
        "PROCESS-BASELINE.json": baseline,
        "MILESTONE.json": milestone,
        "MILESTONE-ASSESSMENT.json": assessment,
        "PROCESS-CHECKPOINT.json": awaiting,
        "STANDARDS-SCHEDULE.json": schedule,
        "PROCESS-OBSERVATORY.json": observatory,
        "COURTHOUSE-PROCESS-BINDING.json": courthouse_binding,
        "PROCESS-THR-CAS.json": thr,
    }
    payloads = {name: canonical_bytes(value) + b"\n" for name, value in records.items()}
    payloads["JOURNAL/EVENTS.jsonl"] = b"".join(canonical_bytes(row) + b"\n" for row in events)
    payloads["REPORT.md"] = (
        "# P/PPI process-governance dogfood campaign\n\n"
        "Status: AWAITING_EXTERNAL_ACCEPTANCE.\n\n"
        "The exact implementation and targeted qualification are bound. No review or acceptance "
        "is claimed. No application or courthouse effect was executed.\n").encode("utf-8")
    payloads["VERIFY.py"] = (ROOT / "tools/verify_process_governance_archive.py").read_bytes()
    index_rows = [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
                  for name, raw in sorted(payloads.items())]
    index_body = {"schema": "mosaic.ucm.process-governance-program-index.v0.1",
                  "files": index_rows, "file_count": len(index_rows),
                  "status": "AWAITING_EXTERNAL_ACCEPTANCE", **BOUNDARY}
    payloads["INDEX.json"] = canonical_bytes({**index_body, "index_root": root(index_body)}) + b"\n"
    archive = deterministic_zip(payloads)
    for name, raw in payloads.items():
        path = args.out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    archive_path = args.out_dir / "UCM-PIPPI-PROCESS-GOVERNANCE-C1-DOGFOOD.zip"
    archive_path.write_bytes(archive)
    print(json.dumps({"status": "PASS_AWAITING_EXTERNAL_ACCEPTANCE",
                      "archive": str(archive_path), "archive_sha256": sha(archive),
                      "source_manifest_root": source_root,
                      "process_baseline_root": baseline["process_baseline_root"],
                      "checkpoint_root": awaiting["process_checkpoint_root"],
                      "thr_body_root": thr["h_body"]},
                     sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
