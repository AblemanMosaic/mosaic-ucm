"""Installed UCM v0.1 console entry point."""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import time

from uclop.canonical import strict_loads
from . import capability_registry, invoke, orientation, select_configuration, validate_configuration, validate_contract


def _load(path: pathlib.Path):
    return strict_loads(path.read_bytes())


def _write_new(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        __import__("os").fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(prog="ucm", description="Universal Constitutional Machine v0.1")
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("orient")
    command.add_parser("capabilities")
    validate = command.add_parser("validate-realization")
    validate.add_argument("contract", type=pathlib.Path)
    check = command.add_parser("check-realization")
    check.add_argument("contract", type=pathlib.Path)
    check.add_argument("configuration", type=pathlib.Path)
    select = command.add_parser("select-realization")
    select.add_argument("contract", type=pathlib.Path)
    select.add_argument("candidates", type=pathlib.Path)
    invoke_command = command.add_parser("invoke")
    invoke_command.add_argument("request", type=pathlib.Path)
    operational = command.add_parser("operational-invoke",
        help="Invoke one operational gateway surface from an exact JSON payload")
    operational.add_argument("surface")
    operational.add_argument("payload", type=pathlib.Path)
    operational.add_argument("--out", type=pathlib.Path)
    amcas_validate = command.add_parser("validate-amcas")
    amcas_validate.add_argument("contract", type=pathlib.Path)
    amcas_compile = command.add_parser("compile-amcas")
    amcas_compile.add_argument("contract", type=pathlib.Path)
    campaign_init = command.add_parser("campaign-init")
    campaign_init.add_argument("contract", type=pathlib.Path)
    campaign_init.add_argument("workspace", type=pathlib.Path)
    campaign_init.add_argument("--user-passport", type=pathlib.Path)
    campaign_init.add_argument("--expected-user-id")
    campaign_init.add_argument("--agent-passport", type=pathlib.Path)
    campaign_init.add_argument("--expected-agent-id")
    campaign_status = command.add_parser("campaign-status")
    campaign_status.add_argument("workspace", type=pathlib.Path)
    challenge = command.add_parser("campaign-challenge")
    challenge.add_argument("workspace", type=pathlib.Path)
    challenge.add_argument("passport", type=pathlib.Path)
    challenge.add_argument("--expected-id", required=True)
    challenge.add_argument("--session-id", required=True)
    challenge.add_argument("--audience", required=True)
    challenge.add_argument("--event-id", required=True)
    challenge.add_argument("--out", type=pathlib.Path, required=True)
    authenticate = command.add_parser("campaign-authenticate")
    authenticate.add_argument("workspace", type=pathlib.Path)
    authenticate.add_argument("passport", type=pathlib.Path)
    authenticate.add_argument("proof", type=pathlib.Path)
    authenticate.add_argument("challenge", type=pathlib.Path)
    authenticate.add_argument("--expected-id", required=True)
    authenticate.add_argument("--event-id", required=True)
    plan = command.add_parser("operation-plan")
    plan.add_argument("workspace", type=pathlib.Path)
    plan.add_argument("operation", type=pathlib.Path)
    plan.add_argument("--event-id", required=True)
    plan.add_argument("--actor-id")
    plan.add_argument("--session-id")
    witness = command.add_parser("operation-witness")
    witness.add_argument("workspace", type=pathlib.Path)
    witness.add_argument("witness", type=pathlib.Path)
    witness.add_argument("--event-id", required=True)
    witness.add_argument("--actor-id")
    witness.add_argument("--session-id")
    diagnostic = command.add_parser("operation-diagnostic")
    diagnostic.add_argument("workspace", type=pathlib.Path)
    diagnostic.add_argument("diagnostic", type=pathlib.Path)
    diagnostic.add_argument("--event-id", required=True)
    diagnostic.add_argument("--actor-id")
    diagnostic.add_argument("--session-id")
    disposition = command.add_parser("requirement-disposition")
    disposition.add_argument("workspace", type=pathlib.Path)
    disposition.add_argument("obligation_id")
    disposition.add_argument("status")
    disposition.add_argument("evidence_roots", nargs="*")
    disposition.add_argument("--event-id", required=True)
    disposition.add_argument("--actor-id")
    disposition.add_argument("--session-id")
    export = command.add_parser("campaign-export")
    export.add_argument("workspace", type=pathlib.Path)
    export.add_argument("software_anchor", type=pathlib.Path)
    export.add_argument("out", type=pathlib.Path)
    kit = command.add_parser("build-integration-kit")
    kit.add_argument("workspace", type=pathlib.Path)
    kit.add_argument("out", type=pathlib.Path)
    verify_archive = command.add_parser("verify-integration-archive")
    verify_archive.add_argument("archive", type=pathlib.Path)
    verify_archive.add_argument("schema")
    verify_archive.add_argument("role")
    import_report = command.add_parser("campaign-import-report")
    import_report.add_argument("workspace", type=pathlib.Path)
    import_report.add_argument("report", type=pathlib.Path)
    import_report.add_argument("--event-id-prefix", required=True)
    campaign_plan = command.add_parser("campaign-plan")
    campaign_plan.add_argument("workspace", type=pathlib.Path)
    campaign_plan.add_argument("objective")
    campaign_plan.add_argument("changed_paths", nargs="*")
    subject_bind = command.add_parser("integration-bind-subject")
    subject_bind.add_argument("subject", type=pathlib.Path)
    subject_bind.add_argument("policy", type=pathlib.Path)
    subject_bind.add_argument("--out", type=pathlib.Path)
    control_planes = command.add_parser("integration-check-control-planes")
    control_planes.add_argument("disposition", type=pathlib.Path)
    correspondence = command.add_parser("integration-correspondence-court")
    correspondence.add_argument("cases", type=pathlib.Path)
    correspondence.add_argument("--out", type=pathlib.Path)
    stage1 = command.add_parser("integration-verify-stage1")
    stage1.add_argument("bundle", type=pathlib.Path)
    stage1_upgrade = command.add_parser("integration-upgrade-stage1")
    stage1_upgrade.add_argument("bundle", type=pathlib.Path)
    stage1_upgrade.add_argument("--out", type=pathlib.Path, required=True)
    portfolio_init = command.add_parser("portfolio-init")
    portfolio_init.add_argument("roster", type=pathlib.Path)
    portfolio_init.add_argument("workspace", type=pathlib.Path)
    portfolio_intake = command.add_parser("portfolio-record-intake")
    portfolio_intake.add_argument("workspace", type=pathlib.Path)
    portfolio_intake.add_argument("intake", type=pathlib.Path)
    portfolio_intake.add_argument("--event-id-prefix", required=True)
    portfolio_instruction = command.add_parser("portfolio-record-instruction")
    portfolio_instruction.add_argument("workspace", type=pathlib.Path)
    portfolio_instruction.add_argument("instruction", type=pathlib.Path)
    portfolio_instruction.add_argument("--event-id-prefix", required=True)
    portfolio_stage1 = command.add_parser("portfolio-import-stage1")
    portfolio_stage1.add_argument("workspace", type=pathlib.Path)
    portfolio_stage1.add_argument("bundle", type=pathlib.Path)
    portfolio_stage1.add_argument("--event-id-prefix", required=True)
    portfolio_stage2 = command.add_parser("portfolio-import-stage2")
    portfolio_stage2.add_argument("workspace", type=pathlib.Path)
    portfolio_stage2.add_argument("declaration", type=pathlib.Path)
    portfolio_stage2.add_argument("--event-id-prefix", required=True)
    portfolio_court = command.add_parser("portfolio-import-correspondence-court")
    portfolio_court.add_argument("workspace", type=pathlib.Path)
    portfolio_court.add_argument("evidence", type=pathlib.Path)
    portfolio_court.add_argument("--expected-handoff-sha256", required=True)
    portfolio_court.add_argument("--expected-portfolio-sha256", required=True)
    portfolio_court.add_argument("--event-id-prefix", required=True)
    portfolio_stage3_issue = command.add_parser("portfolio-issue-stage3-instructions")
    portfolio_stage3_issue.add_argument("workspace", type=pathlib.Path)
    portfolio_stage3_issue.add_argument("predecessor_snapshot", type=pathlib.Path)
    portfolio_stage3_issue.add_argument("out", type=pathlib.Path)
    portfolio_stage3_issue.add_argument("--pipeline-release-sha256", required=True)
    portfolio_stage3_issue.add_argument("--predecessor-portfolio-sha256", required=True)
    portfolio_stage3_issue.add_argument("--expected-status-root", required=True)
    portfolio_stage3_issue.add_argument("--event-id-prefix", required=True)
    portfolio_stage3_import = command.add_parser("portfolio-import-stage3-plan")
    portfolio_stage3_import.add_argument("workspace", type=pathlib.Path)
    portfolio_stage3_import.add_argument("plan", type=pathlib.Path)
    portfolio_stage3_import.add_argument("--event-id-prefix", required=True)
    stage3_validate = command.add_parser("stage3-validate-plan")
    stage3_validate.add_argument("instruction", type=pathlib.Path)
    stage3_validate.add_argument("plan", type=pathlib.Path)
    stage4_eligibility = command.add_parser("stage4-derive-eligibility")
    stage4_eligibility.add_argument("instruction", type=pathlib.Path)
    stage4_eligibility.add_argument("plan", type=pathlib.Path)
    stage4_eligibility.add_argument("review_archive", type=pathlib.Path)
    stage4_eligibility.add_argument("out", type=pathlib.Path)
    stage4_contract = command.add_parser("stage4-build-run-contract")
    stage4_contract.add_argument("instruction", type=pathlib.Path)
    stage4_contract.add_argument("plan", type=pathlib.Path)
    stage4_contract.add_argument("eligibility", type=pathlib.Path)
    stage4_contract.add_argument("review_archive", type=pathlib.Path)
    stage4_contract.add_argument("out", type=pathlib.Path)
    stage4_contract_validate = command.add_parser("stage4-validate-run-contract")
    stage4_contract_validate.add_argument("instruction", type=pathlib.Path)
    stage4_contract_validate.add_argument("plan", type=pathlib.Path)
    stage4_contract_validate.add_argument("eligibility", type=pathlib.Path)
    stage4_contract_validate.add_argument("run_contract", type=pathlib.Path)
    stage4_contract_validate.add_argument("review_archive", type=pathlib.Path)
    stage4_observation = command.add_parser("stage4-validate-observation")
    stage4_observation.add_argument("instruction", type=pathlib.Path)
    stage4_observation.add_argument("plan", type=pathlib.Path)
    stage4_observation.add_argument("eligibility", type=pathlib.Path)
    stage4_observation.add_argument("run_contract", type=pathlib.Path)
    stage4_observation.add_argument("observation", type=pathlib.Path)
    stage4_observation.add_argument("review_archive", type=pathlib.Path)
    stage4_c3_eligibility = command.add_parser("stage4-c3-derive-eligibility")
    stage4_c3_eligibility.add_argument("instruction", type=pathlib.Path)
    stage4_c3_eligibility.add_argument("plan", type=pathlib.Path)
    stage4_c3_eligibility.add_argument("review_archive", type=pathlib.Path)
    stage4_c3_eligibility.add_argument("review_policy", type=pathlib.Path)
    stage4_c3_eligibility.add_argument("out", type=pathlib.Path)
    stage4_c3_contract = command.add_parser("stage4-c3-build-run-contract")
    for name in ("instruction", "plan", "eligibility", "review_archive",
                 "review_policy", "relation_case_map", "execution_context",
                 "native_runner_binding", "selection"):
        stage4_c3_contract.add_argument(name, type=pathlib.Path)
    stage4_c3_contract.add_argument("out", type=pathlib.Path)
    stage4_c3_terminal = command.add_parser("stage4-c3-build-terminal-refusal")
    stage4_c3_terminal.add_argument("run_contract", type=pathlib.Path)
    stage4_c3_terminal.add_argument("out", type=pathlib.Path)
    native_preflight = command.add_parser("native-runner-preflight")
    native_preflight.add_argument("run_contract", type=pathlib.Path)
    native_preflight.add_argument("binding", type=pathlib.Path)
    native_preflight.add_argument("out", type=pathlib.Path)
    native_receipt = command.add_parser("native-runner-validate-receipt")
    native_receipt.add_argument("preflight", type=pathlib.Path)
    native_receipt.add_argument("receipt", type=pathlib.Path)
    operation_state = command.add_parser("stage4-c3-derive-operation-state")
    operation_state.add_argument("operation_id")
    operation_state.add_argument("run_contract_root")
    operation_state.add_argument("events", type=pathlib.Path)
    operation_state.add_argument("out", type=pathlib.Path)
    operation_state_validate = command.add_parser("stage4-c3-validate-operation-state")
    operation_state_validate.add_argument("state", type=pathlib.Path)
    stage4_c4_contract = command.add_parser("stage4-build-anchored-run-contract")
    for name in ("instruction", "plan", "eligibility", "review_archive",
                 "review_policy", "relation_case_map", "execution_context",
                 "native_runner_binding", "selection", "trust_anchors",
                 "execution_authority_policy"):
        stage4_c4_contract.add_argument(name, type=pathlib.Path)
    stage4_c4_contract.add_argument("expected_trust_anchors_root")
    stage4_c4_contract.add_argument("out", type=pathlib.Path)
    stage4_c4_preflight = command.add_parser("stage4-build-authority-safe-preflight")
    stage4_c4_preflight.add_argument("run_contract", type=pathlib.Path)
    stage4_c4_preflight.add_argument("trust_anchors", type=pathlib.Path)
    stage4_c4_preflight.add_argument("execution_authority_policy", type=pathlib.Path)
    stage4_c4_preflight.add_argument("expected_trust_anchors_root")
    stage4_c4_preflight.add_argument("out", type=pathlib.Path)
    stage4_c4_terminal = command.add_parser("stage4-build-receipted-refusal")
    stage4_c4_terminal.add_argument("run_contract", type=pathlib.Path)
    stage4_c4_terminal.add_argument("expected_trust_anchors_root")
    stage4_c4_terminal.add_argument("out", type=pathlib.Path)
    stage4_c4_state = command.add_parser("stage4-derive-receipt-state")
    stage4_c4_state.add_argument("operation_id")
    stage4_c4_state.add_argument("run_contract_root")
    stage4_c4_state.add_argument("events", type=pathlib.Path)
    stage4_c4_state.add_argument("out", type=pathlib.Path)
    stage4_c4_state_validate = command.add_parser("stage4-validate-receipt-state")
    stage4_c4_state_validate.add_argument("state", type=pathlib.Path)
    portfolio_status = command.add_parser("portfolio-status")
    portfolio_status.add_argument("workspace", type=pathlib.Path)
    campaign_preflight = command.add_parser("portfolio-campaign-preflight")
    campaign_preflight.add_argument("workspace", type=pathlib.Path)
    campaign_preflight.add_argument("--out", type=pathlib.Path)
    composition_preflight = command.add_parser("portfolio-composition-preflight")
    composition_preflight.add_argument("bundles", type=pathlib.Path, nargs="+")
    composition_preflight.add_argument("--declarations", type=pathlib.Path, nargs="*", default=[])
    composition_preflight.add_argument("--out", type=pathlib.Path)
    composition_template = command.add_parser("portfolio-composition-template")
    composition_template.add_argument("bundle", type=pathlib.Path)
    composition_template.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.command == "orient":
            result = orientation()
        elif args.command == "capabilities":
            result = capability_registry()
        elif args.command == "validate-realization":
            result = validate_contract(_load(args.contract))
        elif args.command == "check-realization":
            result = validate_configuration(_load(args.contract), _load(args.configuration))
        elif args.command == "select-realization":
            result = select_configuration(_load(args.contract), _load(args.candidates))
        elif args.command == "invoke":
            result = invoke(_load(args.request))
        elif args.command == "operational-invoke":
            from uclop.canonical import canonical_bytes, root
            payload = _load(args.payload)
            request = {"schema": "mosaic.ucm.request.v0.1",
                       "surface": args.surface, "payload": payload,
                       "request_id": root({"surface": args.surface,
                                           "payload": payload})}
            result = invoke(request)
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "validate-amcas":
            from .amcas import validate_contract as validate_amcas
            result = validate_amcas(_load(args.contract))
        elif args.command == "compile-amcas":
            from .amcas import compile_contract
            result = compile_contract(_load(args.contract))
        elif args.command == "campaign-init":
            from .integration import IntegrationCampaign
            campaign = IntegrationCampaign.create(args.workspace, _load(args.contract),
                user_passport=args.user_passport, expected_user_id=args.expected_user_id,
                agent_passport=args.agent_passport, expected_agent_id=args.expected_agent_id)
            result = campaign.status()
        elif args.command == "campaign-status":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).status()
        elif args.command == "campaign-challenge":
            from .identity import issue_durable_challenge, load_passport
            from .integration import IntegrationCampaign
            campaign = IntegrationCampaign(args.workspace)
            issued = issue_durable_challenge(campaign.journal, load_passport(args.passport),
                expected_mosaic_id=args.expected_id, session_mosaic_id=args.session_id,
                audience=args.audience, context_sha256=campaign.contract()["contract_root"],
                issued_at=int(time.time()), expires_at=int(time.time()) + 300,
                nonce=secrets.token_hex(32), event_id=args.event_id)
            _write_new(args.out, json.dumps(issued["challenge"], sort_keys=True,
                separators=(",", ":")).encode("utf-8"))
            result = issued
        elif args.command == "campaign-authenticate":
            from .identity import consume_durable_proof, load_passport
            from .integration import IntegrationCampaign
            campaign = IntegrationCampaign(args.workspace)
            result = consume_durable_proof(campaign.journal, load_passport(args.passport),
                _load(args.proof), expected_challenge=_load(args.challenge),
                expected_mosaic_id=args.expected_id, now=int(time.time()), event_id=args.event_id)
        elif args.command == "operation-plan":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).plan_operation(_load(args.operation),
                event_id=args.event_id, actor_mosaic_id=args.actor_id, session_id=args.session_id)
        elif args.command == "operation-witness":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).record_witness(_load(args.witness),
                event_id=args.event_id, actor_mosaic_id=args.actor_id, session_id=args.session_id)
        elif args.command == "operation-diagnostic":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).record_diagnostic(_load(args.diagnostic),
                event_id=args.event_id, actor_mosaic_id=args.actor_id, session_id=args.session_id)
        elif args.command == "requirement-disposition":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).disposition(args.obligation_id, args.status,
                args.evidence_roots, event_id=args.event_id,
                actor_mosaic_id=args.actor_id, session_id=args.session_id)
        elif args.command == "campaign-export":
            from .artifacts import export_journal_archive
            from .integration import IntegrationCampaign
            raw = export_journal_archive(IntegrationCampaign(args.workspace),
                                         software_anchor=_load(args.software_anchor))
            _write_new(args.out, raw)
            result = {"status": "PASS", "path": str(args.out),
                      "sha256": __import__("hashlib").sha256(raw).hexdigest()}
        elif args.command == "build-integration-kit":
            from .artifacts import build_integration_kit
            from .integration import IntegrationCampaign
            raw = build_integration_kit(IntegrationCampaign(args.workspace))
            _write_new(args.out, raw)
            result = {"status": "PASS", "path": str(args.out),
                      "sha256": __import__("hashlib").sha256(raw).hexdigest()}
        elif args.command == "verify-integration-archive":
            from .artifacts import verify_deterministic_zip
            raw = args.archive.read_bytes()
            result = verify_deterministic_zip(raw, expected_schema=args.schema,
                                              expected_role=args.role)
        elif args.command == "campaign-import-report":
            from .integration import IntegrationCampaign
            result = IntegrationCampaign(args.workspace).import_session_report(
                _load(args.report), event_id_prefix=args.event_id_prefix)
        elif args.command == "campaign-plan":
            from .integration import IntegrationCampaign
            from .planning import prepare_plan
            result = prepare_plan(IntegrationCampaign(args.workspace),
                                  changed_paths=args.changed_paths, objective=args.objective)
        elif args.command == "integration-bind-subject":
            from uclop.canonical import canonical_bytes
            from .subject import bind_subject
            result = bind_subject(args.subject, _load(args.policy))
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "integration-check-control-planes":
            from .control_planes import verify_control_plane_disposition
            result = verify_control_plane_disposition(_load(args.disposition))
        elif args.command == "integration-correspondence-court":
            from uclop.canonical import canonical_bytes
            from .correspondence import run_correspondence_court
            result = run_correspondence_court(_load(args.cases))
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "integration-verify-stage1":
            from .stage1 import verify_stage1_bundle
            result = verify_stage1_bundle(args.bundle.read_bytes())
        elif args.command == "integration-upgrade-stage1":
            from .stage1 import upgrade_stage1_bundle, verify_stage1_bundle
            raw = upgrade_stage1_bundle(args.bundle.read_bytes())
            _write_new(args.out, raw)
            result = {"status": "PASS", "path": str(args.out),
                      "sha256": __import__("hashlib").sha256(raw).hexdigest(),
                      "stage_i1": verify_stage1_bundle(raw)}
        elif args.command == "portfolio-init":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign.create(args.workspace, _load(args.roster)).status()
        elif args.command == "portfolio-record-intake":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).record_intake(
                _load(args.intake), event_id_prefix=args.event_id_prefix)
        elif args.command == "portfolio-record-instruction":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).record_instruction(
                _load(args.instruction), event_id_prefix=args.event_id_prefix)
        elif args.command == "portfolio-import-stage1":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).import_stage1(
                args.bundle.read_bytes(), event_id_prefix=args.event_id_prefix)
        elif args.command == "portfolio-import-stage2":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).import_stage2(
                args.declaration.read_bytes(), event_id_prefix=args.event_id_prefix)
        elif args.command == "portfolio-import-correspondence-court":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).import_correspondence_court(
                args.evidence.read_bytes(), event_id_prefix=args.event_id_prefix,
                expected_handoff_sha256=args.expected_handoff_sha256,
                expected_portfolio_sha256=args.expected_portfolio_sha256)
        elif args.command == "portfolio-issue-stage3-instructions":
            from uclop.canonical import canonical_bytes
            from .portfolio import PortfolioCampaign
            rows = PortfolioCampaign(args.workspace).issue_stage3_instructions(
                pipeline_release_sha256=args.pipeline_release_sha256,
                predecessor_portfolio_raw=args.predecessor_snapshot.read_bytes(),
                predecessor_portfolio_sha256=args.predecessor_portfolio_sha256,
                expected_status_root=args.expected_status_root,
                event_id_prefix=args.event_id_prefix)
            for row in rows:
                stem = row["application_id"].replace(".", "-")
                _write_new(args.out / (stem + "-STAGE-I3-INSTRUCTION.json"),
                           canonical_bytes(row["instruction"]))
                _write_new(args.out / (stem + "-STAGE-I3-PLAN-TEMPLATE.json"),
                           canonical_bytes(row["template"]))
            result = {"status": "PASS", "applications": len(rows),
                      "output": str(args.out), "stage_i3_shadow_authorized": False,
                      "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "real_a5": False, "g0": "CLOSED"}
        elif args.command == "portfolio-import-stage3-plan":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).import_stage3_plan(
                args.plan.read_bytes(), event_id_prefix=args.event_id_prefix)
        elif args.command == "stage3-validate-plan":
            from .stage3 import validate_plan
            result = validate_plan(_load(args.plan), expected_instruction=_load(args.instruction))
        elif args.command == "stage4-derive-eligibility":
            from uclop.canonical import canonical_bytes
            from .stage4 import derive_eligibility
            result = derive_eligibility(instruction=_load(args.instruction),
                plan=_load(args.plan), review_archive=args.review_archive.read_bytes())
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-build-run-contract":
            from uclop.canonical import canonical_bytes
            from .stage4 import build_run_contract
            result = build_run_contract(instruction=_load(args.instruction),
                plan=_load(args.plan), eligibility=_load(args.eligibility),
                review_archive=args.review_archive.read_bytes())
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-validate-run-contract":
            from .stage4 import validate_run_contract
            result = validate_run_contract(_load(args.run_contract),
                expected_eligibility=_load(args.eligibility),
                expected_plan=_load(args.plan),
                expected_instruction=_load(args.instruction),
                expected_review_archive=args.review_archive.read_bytes())
        elif args.command == "stage4-validate-observation":
            from .stage4 import validate_observation
            result = validate_observation(_load(args.observation),
                expected_run_contract=_load(args.run_contract),
                expected_eligibility=_load(args.eligibility),
                expected_plan=_load(args.plan),
                expected_instruction=_load(args.instruction),
                expected_review_archive=args.review_archive.read_bytes())
        elif args.command == "stage4-c3-derive-eligibility":
            from uclop.canonical import canonical_bytes
            from .stage4_c3 import derive_eligibility
            result = derive_eligibility(instruction=_load(args.instruction),
                plan=_load(args.plan), review_archive=args.review_archive.read_bytes(),
                review_policy=_load(args.review_policy))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-c3-build-run-contract":
            from uclop.canonical import canonical_bytes
            from .stage4_c3 import build_run_contract
            result = build_run_contract(
                instruction=_load(args.instruction), plan=_load(args.plan),
                eligibility=_load(args.eligibility),
                review_archive=args.review_archive.read_bytes(),
                review_policy=_load(args.review_policy),
                relation_case_map=_load(args.relation_case_map),
                execution_context=_load(args.execution_context),
                native_runner_binding=_load(args.native_runner_binding),
                selection=_load(args.selection))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-c3-build-terminal-refusal":
            from uclop.canonical import canonical_bytes
            from .stage4_c3 import build_terminal_refusal
            result = build_terminal_refusal(run_contract=_load(args.run_contract))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "native-runner-preflight":
            from uclop.canonical import canonical_bytes
            from .native_runner import build_preflight
            contract = _load(args.run_contract)
            result = build_preflight(
                run_contract_root=contract["run_contract_root"],
                execution_context_root=contract["execution_context"]["context_root"],
                binding=_load(args.binding),
                requested_effect_classes=sorted({
                    row["effect_class"] for row in contract["case_schedule"]
                }),
                execution_authorized=contract["execution_authorized"])
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "native-runner-validate-receipt":
            from .native_runner import validate_terminal_receipt
            result = validate_terminal_receipt(_load(args.receipt),
                                               expected_preflight=_load(args.preflight))
        elif args.command == "stage4-c3-derive-operation-state":
            from uclop.canonical import canonical_bytes
            from .operation_state import derive_operation_state
            result = derive_operation_state(operation_id=args.operation_id,
                run_contract_root=args.run_contract_root, events=_load(args.events))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-c3-validate-operation-state":
            from .operation_state import validate_operation_state
            result = validate_operation_state(_load(args.state))
        elif args.command == "stage4-build-anchored-run-contract":
            from uclop.canonical import canonical_bytes
            from .stage4_c4 import build_run_contract
            result = build_run_contract(
                instruction=_load(args.instruction), plan=_load(args.plan),
                eligibility=_load(args.eligibility),
                review_archive=args.review_archive.read_bytes(),
                review_policy=_load(args.review_policy),
                relation_case_map=_load(args.relation_case_map),
                execution_context=_load(args.execution_context),
                native_runner_binding=_load(args.native_runner_binding),
                selection=_load(args.selection),
                trust_anchors=_load(args.trust_anchors),
                expected_trust_anchors_root=args.expected_trust_anchors_root,
                execution_authority_policy=_load(args.execution_authority_policy))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-build-authority-safe-preflight":
            from uclop.canonical import canonical_bytes
            from .native_runner_c4 import build_preflight
            result = build_preflight(run_contract=_load(args.run_contract),
                trust_anchors=_load(args.trust_anchors),
                expected_trust_anchors_root=args.expected_trust_anchors_root,
                execution_authority_policy=_load(args.execution_authority_policy))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-build-receipted-refusal":
            from uclop.canonical import canonical_bytes
            from .stage4_c4 import build_terminal_refusal
            result = build_terminal_refusal(run_contract=_load(args.run_contract),
                expected_trust_anchors_root=args.expected_trust_anchors_root)
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-derive-receipt-state":
            from uclop.canonical import canonical_bytes
            from .operation_state_c4 import derive_operation_state
            result = derive_operation_state(operation_id=args.operation_id,
                run_contract_root=args.run_contract_root, events=_load(args.events))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "stage4-validate-receipt-state":
            from .operation_state_c4 import validate_operation_state
            result = validate_operation_state(_load(args.state))
        elif args.command == "portfolio-status":
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).status()
        elif args.command == "portfolio-campaign-preflight":
            from uclop.canonical import canonical_bytes
            from .portfolio import PortfolioCampaign
            result = PortfolioCampaign(args.workspace).composition_preflight()
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "portfolio-composition-template":
            from uclop.canonical import canonical_bytes
            from .composition import declaration_template
            result = declaration_template(args.bundle.read_bytes())
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "portfolio-composition-preflight":
            from uclop.canonical import canonical_bytes
            from .composition import build_preflight
            result = build_preflight(args.bundles, [_load(path) for path in args.declarations])
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        else:
            raise ValueError("UCM_COMMAND_UNREACHABLE")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.command == "check-realization" and result.get("status") != "PASS_ADMISSIBLE":
            return 3
        return 0
    except Exception as error:
        print(json.dumps({"status": "REFUSED", "diagnostic": getattr(error, "code", type(error).__name__),
                          "detail": str(error), "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                          "real_a5": False, "g0": "CLOSED"}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

