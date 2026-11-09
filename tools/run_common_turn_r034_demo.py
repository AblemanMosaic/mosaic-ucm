#!/usr/bin/env python3
"""Positive two-turn P/PPI pilot; frozen inputs can replay on another host.

Only the explicitly named empty output directory is written.  Synthetic
reporting examples remain declarations.  Actual local hub custody is exported
separately from deterministic turn/CMBA outputs used for portability comparison.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "src"))

from uclop.canonical import canonical_bytes, exact_keys, require, root, strict_loads
from ucm.pippi_adaptive import build_turn_report, negotiate_host_mode, prepare_turn
from ucm.pippi_cmba import (CMBA_WHEEL_SHA256, build_cmba_turn_assessment,
    discover_cmba_binding, validate_cmba_turn_assessment)
from ucm.pippi_global import BOUNDARY, PippiHub, build_onboarding, build_project
from ucm.pippi_portability import build_execution_context
from ucm.pippi_turn_record import project_turn_record
from ucm.pippi_turn_workflow import (build_assessment_attachment,
    build_turn_submission, project_turn_history, reconcile_common_turn,
    turn_continuation_context, validate_turn_bundle)


def emit(phase, **fields):
    print(canonical_bytes({"event": "DEMO_PROGRESS", "phase": phase,
                           "progress_is_evidence": False, **fields}).decode(), flush=True)


def digest(label):
    return root({"schema": "mosaic.ucm.positive-demo-declaration.v0.1", "label": label})


def submission_input(opening, report, details):
    return {"opening": opening, "turn_details": details, **{
        key: deepcopy(report[key]) for key in ("summary", "changed_paths", "artifact_roots",
        "evidence_roots", "unresolved_items", "next_action", "claim_class")}}


def default_request(*, skip_cmba=False):
    """Freeze one declared project and two chained synthetic reporting turns."""
    project = build_project(project_id="pippi-common-turn-pilot", title="P/PPI common turn pilot",
        workspace="C:/Mosaic/Projects/Pippi", github_url=None,
        application_command=["pippi", "dashboard"],
        verification_command=["pippi", "turns"], revision="r034")
    host = negotiate_host_mode(host_id="positive-demo-declared-host",
        requested_mode="ARTIFACT_MEDIATED_WEB", capability_ids=["ARTIFACT_EXCHANGE"],
        adapter_root=None)
    execution = build_execution_context(host_family="WINDOWS", shell_family="POWERSHELL",
        path_flavour="WINDOWS", filesystem_class="WINDOWS_NATIVE", case_sensitive=False,
        python_implementation="CPython", python_version="3.12.3",
        source="DECLARED_EXTERNAL_HOST", wsl_distribution=None)
    turns = []
    previous = None
    case = digest("acceptance-case-structured-reporting")
    for sequence in (1, 2):
        opening = prepare_turn(project=project, host_profile=host, sequence=sequence,
            previous_turn_root=previous, scenario="CODING", requested_rule_ids=[],
            acceptance_case_roots=[case], journal_head=None, execution_context=execution)
        report = build_turn_report(opening=opening,
            summary=f"Positive fixture turn {sequence}: record reported construction and inspection.",
            changed_paths=[f"examples/positive-turn-{sequence}.json"],
            artifact_roots=[digest(f"declared-artifact-{sequence}")],
            evidence_roots=[digest(f"declared-check-reference-{sequence}")],
            unresolved_items=[], next_action="Review the declared facts and exact local custody.",
            claim_class="IMPLEMENTATION")
        details = {"claims": [{"claim_id": kind.lower(), "activity_kind": kind,
            "statement": f"Synthetic turn {sequence} reporting example: {kind.lower()}.",
            "declared_basis": "AGENT_REPORTED", "evidence_ids": ["reported-check"]}
            for kind in ("CHANGE", "CHECK")],
            "evidence": [{"evidence_id": "reported-check",
                "subject_root": digest(f"declared-check-reference-{sequence}"),
                "source_root": digest(f"declared-artifact-{sequence}"),
                "producer_id": "positive-fixture-declaration", "receipt_root": None,
                "declared_basis": "AGENT_REPORTED",
                "description": "Synthetic reference; no external test execution is asserted."}],
            "coverage": [{"channel": channel, "status": "PARTIAL", "evidence_ids": [],
                "limitations": ["Retrospective fixture report; host interception unproven."]}
                for channel in ("JOURNAL_WRITE", "VISIBLE_OUTPUT")],
            "objectives": [{"objective_id": "structured-turn", "statement":
                "Demonstrate the same project reporting and reconciliation workflow.",
                "acceptance_case_roots": [case]}],
            "acceptance_dispositions": [{"acceptance_case_root": case,
                "disposition": "OPEN" if sequence == 1 else "REPORTED_MET",
                "claim_ids": ["change", "check"], "evidence_ids": ["reported-check"]}],
            "native_turn_roots": []}
        bundle = build_turn_submission(submission_input(opening, report, details))
        turns.append({"opening": opening, "report": report, "turn_details": details})
        previous = bundle["turn_record_root"]
    available = discover_cmba_binding()["status"] == "AVAILABLE"
    body = {"schema": "mosaic.ucm.pippi-common-turn-demo-request.v0.1",
        "fixture_scope": "SYNTHETIC_DECLARATIONS_FOR_POSITIVE_CONSTRUCTION_ONLY",
        "onboarding": build_onboarding(governor_label="positive-pilot", mosaic_id=None,
            dkn_public_key=None, github_account=None, github_credential_reference=None,
            archive_backend="LOCAL_CONTENT_STORE"),
        "project": project, "host_profile": host, "execution_context": execution,
        "cmba_expected_wheel_sha256": CMBA_WHEEL_SHA256 if available and not skip_cmba else None,
        "turns": turns, **BOUNDARY}
    return {**body, "request_root": root(body)}


def write_json(folder, relative, value):
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def run(request, output):
    item = exact_keys(request, {"schema", "fixture_scope", "onboarding", "project",
        "host_profile", "execution_context", "cmba_expected_wheel_sha256", "turns",
        "standing", "authority_effect", "real_a5", "g0", "request_root"})
    require(item["request_root"] == root({k: v for k, v in item.items() if k != "request_root"})
        and item["schema"] == "mosaic.ucm.pippi-common-turn-demo-request.v0.1"
        and all(item[k] == v for k, v in BOUNDARY.items()), "PIPPI_DEMO_REQUEST_INVALID")
    require(type(item["turns"]) is list and len(item["turns"]) == 2,
            "PIPPI_DEMO_TWO_TURNS_REQUIRED")
    hub = PippiHub(output / "hub")
    hub.initialize(item["onboarding"])
    hub.add_project(item["project"])
    write_json(output, "REQUEST.json", request)
    semantic = []
    custody = []
    previous = None

    def store(record, kind, field, event_type):
        result = hub.store_project_record(project_id=item["project"]["project_id"],
            record_kind=kind, record=record, root_field=field, event_type=event_type)
        custody.append({"record_kind": kind, "record_root": record[field],
                        "hub_event_root": result["hub_event_root"]})

    for sequence, raw_turn in enumerate(item["turns"], 1):
        emit("TURN_START", sequence=sequence)
        raw_turn = exact_keys(raw_turn, {"opening", "report", "turn_details"})
        opening, report = raw_turn["opening"], raw_turn["report"]
        rebuilt_opening = prepare_turn(project=item["project"], host_profile=item["host_profile"],
            sequence=sequence, previous_turn_root=previous, scenario=opening["scenario"],
            requested_rule_ids=opening["rule_ids"], acceptance_case_roots=opening["acceptance_case_roots"],
            journal_head=opening["journal_head"], execution_context=item["execution_context"])
        require(opening == rebuilt_opening, "PIPPI_DEMO_OPENING_INPUT_MISMATCH")
        before = canonical_bytes({"opening": opening, "report": report})
        bundle = build_turn_submission(submission_input(opening, report, raw_turn["turn_details"]))
        validate_turn_bundle(bundle)
        require(bundle["report"] == report and before == canonical_bytes({
            "opening": opening, "report": report}), "PIPPI_DEMO_LEGACY_INPUT_CHANGED")
        record = bundle["turn_record"]
        store(opening, "opening", "turn_opening_root", "TURN_OPENED")
        store(bundle, "turn-record", "turn_bundle_root", "TURN_RECORD_SUBMITTED")
        value = {"bundle": bundle, "human": project_turn_record(record, opening=opening,
            report=report, view="HUMAN"), "machine": project_turn_record(record,
            opening=opening, report=report, view="MACHINE")}
        expected = item["cmba_expected_wheel_sha256"]
        if expected is not None:
            emit("CMBA_ASSESS", sequence=sequence)
            assessment = build_cmba_turn_assessment(opening=opening, report=report,
                turn_record=record, expected_wheel_sha256=expected)
            validate_cmba_turn_assessment(assessment, opening=opening, report=report,
                turn_record=record, expected_wheel_sha256=expected)
            attachment = build_assessment_attachment(opening=opening, report=report,
                turn_record=record, assessment=assessment, expected_wheel_sha256=expected)
            store(attachment, "turn-assessment", "attachment_root", "TURN_ASSESSMENT_ATTACHED")
            value["cmba_assessment"] = assessment
            value["cmba_attachment"] = attachment
        reconciliation = reconcile_common_turn(opening=opening, report=report,
            turn_record=record, current_project_root=item["project"]["project_root"],
            current_journal_head=opening["journal_head"])
        store(reconciliation, "reconciliation", "reconciliation_root", "TURN_RECONCILED")
        value["reconciliation"] = reconciliation
        semantic.append(value)
        previous = record["turn_record_root"]
        emit("TURN_PASS", sequence=sequence, turn_record_root=previous)

    history = project_turn_history(hub, item["project"]["project_id"])
    continuation = turn_continuation_context(hub, item["project"]["project_id"])
    require(history["record_count"] == 2 and all(row["journal_committed"] for row in history["records"])
        and continuation["status"] == "READY", "PIPPI_DEMO_CUSTODY_INCOMPLETE")
    stable_body = {"schema": "mosaic.ucm.pippi-common-turn-demo-output.v0.1",
        "request_root": item["request_root"], "turns": semantic, "history": history,
        "continuation": continuation, "cmba_executed": item["cmba_expected_wheel_sha256"] is not None,
        "reported_fixture_activity_verified": False, "per_tool_interception_established": False,
        "status": "PASS_POSITIVE_CONSTRUCTION", **BOUNDARY}
    stable = {**stable_body, "canonical_output_root": root(stable_body)}
    write_json(output, "canonical.json", stable)
    verification = hub.verify()
    receipt_body = {"schema": "mosaic.ucm.pippi-common-turn-demo-receipt.v0.1",
        "canonical_output_root": stable["canonical_output_root"], "hub_verification": verification,
        "actual_observed_hub_events": custody,
        "declared_project_journal_heads": [turn["opening"]["journal_head"] for turn in item["turns"]],
        "journal_domain_separation": "DECLARED_SOURCE_HEADS_ARE_NOT_OBSERVED_HUB_EVENT_HEADS",
        "hub_custody_is_nonportable_observation": True, "lock_file_exported": False,
        "adversarial_cases_executed": 0, "status": "PASS", **BOUNDARY}
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    write_json(output, "DEMO-RECEIPT.json", receipt)
    files = [path for path in output.rglob("*") if path.is_file() and path.name != "PIPPI.lock"]
    rows = [{"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(files, key=lambda p: p.relative_to(output).as_posix())]
    manifest_body = {"schema": "mosaic.ucm.pippi-common-turn-demo-manifest.v0.1",
        "files": rows, "members": len(rows), "canonical_output_root": stable["canonical_output_root"],
        "authority_effect": "NONE"}
    write_json(output, "MANIFEST.json", {**manifest_body, "manifest_root": root(manifest_body)})
    archive_path = output / "PIPPI-r034-POSITIVE-PILOT-EVIDENCE.zip"
    emit("SEAL", members=len(rows) + 1)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted([row["path"] for row in rows] + ["MANIFEST.json"]):
            info = zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / relative).read_bytes(), compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        require(set(archive.namelist()) == {row["path"] for row in rows} | {"MANIFEST.json"},
                "PIPPI_DEMO_EXPORT_SET_INVALID")
        for row in rows:
            raw = archive.read(row["path"])
            require(len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"],
                    "PIPPI_DEMO_EXPORT_BYTES_INVALID")
    return {"status": "PASS", "canonical_output_root": stable["canonical_output_root"],
        "receipt_root": receipt["receipt_root"], "evidence_zip": str(archive_path),
        "evidence_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "cmba_executed": stable["cmba_executed"], "adversarial_cases_executed": 0, **BOUNDARY}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--request", type=Path, help="Exact REQUEST.json from a prior positive pilot.")
    parser.add_argument("--skip-cmba", action="store_true", help="Omit optional CMBA from a new fixture.")
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.is_relative_to(SOURCE), "PIPPI_DEMO_OUTPUT_MUST_BE_OUTSIDE_SOURCE")
    require(not output.exists() or output.is_dir() and not any(output.iterdir()),
            "PIPPI_DEMO_OUTPUT_MUST_BE_EMPTY")
    require(not (args.request and args.skip_cmba), "PIPPI_DEMO_FROZEN_REQUEST_CANNOT_CHANGE")
    request = strict_loads(args.request.read_bytes()) if args.request else default_request(skip_cmba=args.skip_cmba)
    output.mkdir(parents=True, exist_ok=True)
    emit("START", frozen_input=bool(args.request))
    print(canonical_bytes(run(request, output)).decode(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
