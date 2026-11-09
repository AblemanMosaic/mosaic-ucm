"""Installed UCM v0.1 console entry point."""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import time

from uclop.canonical import Refusal, canonical_bytes, strict_loads
from . import (capability_registry, invoke, legacy_capability_registry,
               orientation, select_configuration, validate_configuration,
               validate_contract)


class UCMArgumentParser(argparse.ArgumentParser):
    """Map usage failures onto the stable public CLI exit-code contract."""

    def error(self, message):
        self.print_usage(__import__("sys").stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


def _load(path: pathlib.Path):
    return strict_loads(path.read_bytes())


def _write_new(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        __import__("os").fsync(stream.fileno())


def main() -> int:
    parser = UCMArgumentParser(prog="ucm", description="Universal Constitutional Machine v0.1")
    command = parser.add_subparsers(dest="command", required=True,
                                    parser_class=UCMArgumentParser)
    command.add_parser("orient")
    command.add_parser("capabilities")
    command.add_parser("legacy-capabilities")
    command.add_parser("profiles")
    profile_check = command.add_parser("profile-check")
    profile_check.add_argument("profile_id", choices=("AUTHORING", "OPERATIONAL", "VERIFY_ONLY", "COMPATIBILITY"))
    profile_check.add_argument("surface_name")
    command.add_parser("doctor")
    command.add_parser("smoke")
    hotfix_plan = command.add_parser("hotfix-plan")
    hotfix_plan.add_argument("request", type=pathlib.Path)
    hotfix_plan.add_argument("out", type=pathlib.Path)
    hotfix_plan.add_argument("--progress", type=pathlib.Path)
    hotfix_validate = command.add_parser("hotfix-validate")
    hotfix_validate.add_argument("plan", type=pathlib.Path)
    hotfix_validate.add_argument("compilation_results", type=pathlib.Path)
    hotfix_validate.add_argument("test_results", type=pathlib.Path)
    hotfix_validate.add_argument("out", type=pathlib.Path)
    hotfix_validate.add_argument("--progress", type=pathlib.Path)
    hotfix_execute = command.add_parser("hotfix-execute")
    hotfix_execute.add_argument("plan", type=pathlib.Path)
    hotfix_execute.add_argument("workspace", type=pathlib.Path)
    hotfix_execute.add_argument("compilation_out", type=pathlib.Path)
    hotfix_execute.add_argument("tests_out", type=pathlib.Path)
    hotfix_execute.add_argument("--progress", type=pathlib.Path)
    for dependency_command in (
        "dependency-compile", "dependency-doctor", "dependency-snapshot",
        "dependency-delta", "dependency-producer-receipt", "dependency-admit",
        "dependency-evaluate", "dependency-impact",
        "dependency-explain", "dependency-export", "dependency-verify",
    ):
        dependency_parser = command.add_parser(dependency_command)
        dependency_parser.add_argument("request", type=pathlib.Path)
        dependency_parser.add_argument("--out", type=pathlib.Path)
    command.add_parser("ugel-orient")
    for ugel_command in (
        "ugel-bind", "ugel-policy", "ugel-call", "ugel-sim-add",
        "ugel-correspondence",
    ):
        ugel_parser = command.add_parser(ugel_command)
        ugel_parser.add_argument("request", type=pathlib.Path)
        ugel_parser.add_argument("--out", type=pathlib.Path)
    feature_negotiate = command.add_parser("feature-negotiate")
    feature_negotiate.add_argument("descriptor", type=pathlib.Path)
    lifecycle = command.add_parser("lifecycle-transition")
    lifecycle.add_argument("contract_root")
    lifecycle.add_argument("from_state", choices=("NONE", "DRAFT", "VALIDATED", "FROZEN"))
    lifecycle.add_argument("to_state", choices=("DRAFT", "VALIDATED", "FROZEN", "SUPERSEDED"))
    lifecycle.add_argument("predecessor_receipt_root")
    lifecycle.add_argument("evidence_roots", nargs="*")
    contract_lint = command.add_parser("contract-lint")
    contract_lint.add_argument("kind", choices=("realization", "amcas"))
    contract_lint.add_argument("contract", type=pathlib.Path)
    contract_diff = command.add_parser("contract-diff")
    contract_diff.add_argument("before", type=pathlib.Path)
    contract_diff.add_argument("after", type=pathlib.Path)
    domain_diff = command.add_parser("contract-domain-diff")
    domain_diff.add_argument("before", type=pathlib.Path)
    domain_diff.add_argument("after", type=pathlib.Path)
    contract_init = command.add_parser("contract-init")
    contract_init.add_argument("kind", choices=("realization", "amcas"))
    contract_init.add_argument("identifier")
    contract_init.add_argument("name")
    contract_init.add_argument("subject_root")
    contract_init.add_argument("manifest_root")
    contract_init.add_argument("out", type=pathlib.Path)
    contract_init.add_argument("--realization", type=pathlib.Path)
    contract_profile = command.add_parser("contract-compile-profile")
    contract_profile.add_argument("source", type=pathlib.Path)
    contract_profile.add_argument("out", type=pathlib.Path)
    contract_doctor = command.add_parser("contract-doctor")
    contract_doctor.add_argument("kind", choices=("realization", "amcas"))
    contract_doctor.add_argument("contract", type=pathlib.Path)
    contract_compat = command.add_parser("contract-compatibility")
    contract_compat.add_argument("predecessor", type=pathlib.Path)
    contract_compat.add_argument("successor", type=pathlib.Path)
    contract_compat.add_argument("--known-root", action="append", default=[])
    explain_selection = command.add_parser("explain-selection")
    explain_selection.add_argument("contract", type=pathlib.Path)
    explain_selection.add_argument("candidates", type=pathlib.Path)
    config_diff = command.add_parser("configuration-diff")
    config_diff.add_argument("contract", type=pathlib.Path)
    config_diff.add_argument("left", type=pathlib.Path)
    config_diff.add_argument("right", type=pathlib.Path)
    pretty = command.add_parser("pretty")
    pretty.add_argument("record", type=pathlib.Path)
    pretty.add_argument("--title", default="UCM record")
    command.add_parser("abi-stability")
    environment = command.add_parser("environment-check")
    environment.add_argument("--strict", action="store_true")
    completion = command.add_parser("shell-completion")
    completion.add_argument("shell", choices=("bash", "zsh", "fish", "powershell"))
    policy_apply = command.add_parser("amcas-apply-policy-packs")
    policy_apply.add_argument("contract", type=pathlib.Path)
    policy_apply.add_argument("packs", type=pathlib.Path, nargs="+")
    policy_apply.add_argument("out", type=pathlib.Path)
    evidence_validate = command.add_parser("evidence-validate")
    evidence_validate.add_argument("evidence", type=pathlib.Path)
    evidence_validate.add_argument("expected_subject_root")
    evidence_validate.add_argument("expected_policy_root")
    evidence_validate.add_argument("now", type=int)
    journal_summary = command.add_parser("journal-summary")
    journal_summary.add_argument("events", type=pathlib.Path)
    journal_query = command.add_parser("journal-query")
    journal_query.add_argument("events", type=pathlib.Path)
    journal_query.add_argument("--event-type")
    journal_query.add_argument("--operation-id")
    journal_query.add_argument("--limit", type=int)
    journal_diff = command.add_parser("journal-diff")
    journal_diff.add_argument("before", type=pathlib.Path)
    journal_diff.add_argument("after", type=pathlib.Path)
    journal_prove = command.add_parser("journal-prove")
    journal_prove.add_argument("events", type=pathlib.Path)
    journal_prove.add_argument("event_root")
    journal_prove.add_argument("out", type=pathlib.Path)
    journal_verify = command.add_parser("journal-verify-proof")
    journal_verify.add_argument("proof", type=pathlib.Path)
    study_roster = command.add_parser("study-roster")
    study_roster.add_argument("protocol", type=pathlib.Path)
    study_roster.add_argument("out", type=pathlib.Path)
    study_validate = command.add_parser("study-validate-result")
    study_validate.add_argument("protocol", type=pathlib.Path)
    study_validate.add_argument("result", type=pathlib.Path)
    study_validate.add_argument("context_registration", type=pathlib.Path)
    study_aggregate = command.add_parser("study-aggregate")
    study_aggregate.add_argument("protocol", type=pathlib.Path)
    study_aggregate.add_argument("results", type=pathlib.Path)
    study_aggregate.add_argument("context_registration", type=pathlib.Path)
    architecture_validate = command.add_parser("architecture-validate")
    architecture_validate.add_argument("contract", type=pathlib.Path)
    architecture_check = command.add_parser("architecture-check")
    architecture_check.add_argument("contract", type=pathlib.Path)
    architecture_check.add_argument("candidate", type=pathlib.Path)
    work_package = command.add_parser("work-package")
    work_package.add_argument("project", type=pathlib.Path)
    work_package.add_argument("architecture_contract", type=pathlib.Path)
    work_package.add_argument("architecture_candidate", type=pathlib.Path)
    work_package.add_argument("workspace")
    work_package.add_argument("objective")
    work_package.add_argument("out", type=pathlib.Path)
    work_package.add_argument("--changed-id", action="append", default=[])
    work_package.add_argument("--changed-path", action="append", default=[])
    workflow_compile = command.add_parser("courthouse-compile-workflow")
    workflow_compile.add_argument("request", type=pathlib.Path)
    workflow_compile.add_argument("out", type=pathlib.Path)
    workflow_verify = command.add_parser("courthouse-verify-workflow")
    workflow_verify.add_argument("request", type=pathlib.Path)
    workflow_verify.add_argument("workflow", type=pathlib.Path)
    workflow_result = command.add_parser("courthouse-import-result")
    workflow_result.add_argument("request", type=pathlib.Path)
    workflow_result.add_argument("workflow", type=pathlib.Path)
    workflow_result.add_argument("result", type=pathlib.Path)
    workflow_result.add_argument("out", type=pathlib.Path)
    admissible_compile = command.add_parser("courthouse-compile-admissible")
    admissible_compile.add_argument("request", type=pathlib.Path)
    admissible_compile.add_argument("admission", type=pathlib.Path)
    admissible_compile.add_argument("out", type=pathlib.Path)
    admission_status = command.add_parser("courthouse-admission-status")
    admission_status.add_argument("submission", type=pathlib.Path)
    admission_status.add_argument("out", type=pathlib.Path)
    admissible_result = command.add_parser(
        "courthouse-import-admissible-result")
    admissible_result.add_argument("submission", type=pathlib.Path)
    admissible_result.add_argument("result", type=pathlib.Path)
    admissible_result.add_argument("out", type=pathlib.Path)
    semantic_discover = command.add_parser("semantic-discover")
    semantic_discover.add_argument("policy", type=pathlib.Path)
    semantic_discover.add_argument("out", type=pathlib.Path)
    semantic_discover.add_argument("plans", type=pathlib.Path, nargs="+")
    semantic_packet = command.add_parser("semantic-judgment-packet")
    semantic_packet.add_argument("discovery", type=pathlib.Path)
    semantic_packet.add_argument("out", type=pathlib.Path)
    semantic_submission = command.add_parser("semantic-build-judgment-submission")
    semantic_submission.add_argument("packet", type=pathlib.Path)
    semantic_submission.add_argument("intent", type=pathlib.Path)
    semantic_submission.add_argument("out", type=pathlib.Path)
    semantic_record = command.add_parser("semantic-record-judgments")
    semantic_record.add_argument("packet", type=pathlib.Path)
    semantic_record.add_argument("submission", type=pathlib.Path)
    semantic_record.add_argument("out", type=pathlib.Path)
    semantic_compile = command.add_parser("semantic-compile-consolidation")
    semantic_compile.add_argument("discovery", type=pathlib.Path)
    semantic_compile.add_argument("register", type=pathlib.Path)
    semantic_compile.add_argument("out", type=pathlib.Path)
    adapter_validate = command.add_parser("integration-validate-adapter")
    adapter_validate.add_argument("adapter", type=pathlib.Path)
    capsule_validate = command.add_parser("integration-validate-capsule")
    capsule_validate.add_argument("capsule", type=pathlib.Path)
    control_validate = command.add_parser("integration-validate-control-plan")
    control_validate.add_argument("plan", type=pathlib.Path)
    observatory = command.add_parser("integration-observatory")
    observatory.add_argument("input", type=pathlib.Path)
    observatory.add_argument("--out", type=pathlib.Path)
    command.add_parser("c-standard")
    c_preflight = command.add_parser("c-preflight")
    c_preflight.add_argument("request", type=pathlib.Path)
    c_results = command.add_parser("c-check-results")
    c_results.add_argument("request", type=pathlib.Path)
    command.add_parser("native-profile")
    native_compile = command.add_parser("native-compile")
    native_compile.add_argument("program", type=pathlib.Path)
    native_compile.add_argument("output", type=pathlib.Path)
    native_reference = command.add_parser("native-reference")
    native_reference.add_argument("program", type=pathlib.Path)
    pippi_create = command.add_parser("pippi-create")
    pippi_create.add_argument("context", type=pathlib.Path)
    pippi_create.add_argument("workspace", type=pathlib.Path)
    pippi_turn = command.add_parser("pippi-record-turn")
    pippi_turn.add_argument("workspace", type=pathlib.Path)
    for name in ("context", "draft", "decision", "projection", "turn"):
        pippi_turn.add_argument(name, type=pathlib.Path)
    pippi_turn.add_argument("--event-id", required=True)
    pippi_status = command.add_parser("pippi-status")
    pippi_status.add_argument("workspace", type=pathlib.Path)
    pippi_status.add_argument("--view", choices=("HUMAN", "AGENT", "FORENSIC"),
                              default="HUMAN")
    pippi_next = command.add_parser("pippi-next")
    pippi_next.add_argument("workspace", type=pathlib.Path)
    pippi_explain = command.add_parser("pippi-explain")
    pippi_explain.add_argument("workspace", type=pathlib.Path)
    pippi_verify = command.add_parser("pippi-verify")
    pippi_verify.add_argument("workspace", type=pathlib.Path)
    process_build = command.add_parser("process-build",
        help="Build one pure P/PPI process-governance record from exact JSON")
    process_build.add_argument("action", choices=(
        "locality", "execution-capsule", "artifact-receipt", "baseline", "milestone", "assessment",
        "decision", "checkpoint", "replan", "standards-schedule", "observatory",
        "courthouse-binding", "thr"))
    process_build.add_argument("request", type=pathlib.Path)
    process_build.add_argument("out", type=pathlib.Path)
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
    command.add_parser("amcas-baseline")
    command.add_parser("amcas-coverage")
    amcas_baseline_compile = command.add_parser("amcas-compile-baseline")
    amcas_baseline_compile.add_argument("contract", type=pathlib.Path)
    amcas_semantic_diff = command.add_parser("amcas-semantic-diff")
    amcas_semantic_diff.add_argument("before", type=pathlib.Path)
    amcas_semantic_diff.add_argument("after", type=pathlib.Path)
    command.add_parser("amcas-parity")
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
    legacy_cli_parsers = (
        stage4_eligibility, stage4_contract, stage4_contract_validate,
        stage4_observation, stage4_c3_eligibility, stage4_c3_contract,
        stage4_c3_terminal, native_preflight, native_receipt, operation_state,
        operation_state_validate, stage4_c4_contract, stage4_c4_preflight,
        stage4_c4_terminal, stage4_c4_state, stage4_c4_state_validate,
    )
    for legacy_parser in legacy_cli_parsers:
        legacy_parser.add_argument(
            "--compatibility", action="store_true",
            help="Explicitly select the historical compatibility route.")
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
        legacy_cli_replacements = {
            "stage4-derive-eligibility": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-build-run-contract": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-validate-run-contract": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-validate-observation": "operational-invoke RECORD_OPERATIONAL_TERMINAL",
            "stage4-c3-derive-eligibility": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-c3-build-run-contract": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-c3-build-terminal-refusal": "operational-invoke CANCEL_OPERATIONAL_GATEWAY",
            "native-runner-preflight": "operational-invoke PREPARE_OPERATIONAL_GATEWAY",
            "native-runner-validate-receipt": "operational-invoke RECORD_OPERATIONAL_TERMINAL",
            "stage4-c3-derive-operation-state": "operational-invoke INSPECT_OPERATIONAL_STATE",
            "stage4-c3-validate-operation-state": "operational-invoke INSPECT_OPERATIONAL_STATE",
            "stage4-build-anchored-run-contract": "operational-invoke BUILD_OPERATIONAL_CONTRACT",
            "stage4-build-authority-safe-preflight": "operational-invoke PREPARE_OPERATIONAL_GATEWAY",
            "stage4-build-receipted-refusal": "operational-invoke CANCEL_OPERATIONAL_GATEWAY",
            "stage4-derive-receipt-state": "operational-invoke INSPECT_OPERATIONAL_STATE",
            "stage4-validate-receipt-state": "operational-invoke INSPECT_OPERATIONAL_STATE",
        }
        if args.command in legacy_cli_replacements and not args.compatibility:
            raise Refusal(
                "UCM_LEGACY_SURFACE_REQUIRES_COMPATIBILITY_PROFILE",
                detail=f"{args.command}->{legacy_cli_replacements[args.command]}")
        if args.command == "orient":
            result = orientation()
        elif args.command == "capabilities":
            result = capability_registry()
        elif args.command == "legacy-capabilities":
            result = legacy_capability_registry()
        elif args.command == "profiles":
            from .profiles import profile_registry
            result = profile_registry()
        elif args.command == "profile-check":
            from .profiles import profile_allows_surface
            result = profile_allows_surface(args.profile_id, args.surface_name)
        elif args.command == "doctor":
            from .diagnostics import doctor
            result = doctor()
        elif args.command == "smoke":
            from .diagnostics import smoke
            result = smoke()
        elif args.command == "hotfix-plan":
            from .incremental_hotfix import build_bound_hotfix_plan
            request = _load(args.request)
            result = build_bound_hotfix_plan(**request, progress_path=args.progress)
            _write_new(args.out, canonical_bytes(result) + b"\n")
        elif args.command == "hotfix-execute":
            from .incremental_hotfix import execute_hotfix_plan
            execution = execute_hotfix_plan(plan=args.plan, workspace=args.workspace, progress_path=args.progress)
            _write_new(args.compilation_out, canonical_bytes(execution["compilation_results"]) + b"\n")
            _write_new(args.tests_out, canonical_bytes(execution["test_results"]) + b"\n")
            result = {"schema": "mosaic.ucm.incremental-hotfix-execution-result.v0.1", "compilation_count": len(execution["compilation_results"]), "test_count": len(execution["test_results"]), "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        elif args.command == "hotfix-validate":
            from .incremental_hotfix import validate_hotfix_result
            result = validate_hotfix_result(plan=args.plan, compilation_results=args.compilation_results, test_results=args.test_results, progress_path=args.progress)
            _write_new(args.out, canonical_bytes(result) + b"\n")
        elif args.command in {
            "dependency-compile", "dependency-doctor", "dependency-snapshot",
            "dependency-delta", "dependency-producer-receipt", "dependency-admit",
            "dependency-evaluate", "dependency-impact",
            "dependency-explain", "dependency-export", "dependency-verify",
        }:
            from .dependency_graph import (
                apply_snapshot_delta, build_graph, build_portable_closure,
                build_producer_receipt, build_reuse_admission, build_snapshot,
                compare_evaluations, evaluate_graph,
                explain_node, verify_graph, verify_portable_closure,
            )
            routes = {
                "dependency-compile": build_graph,
                "dependency-doctor": verify_graph,
                "dependency-snapshot": build_snapshot,
                "dependency-delta": apply_snapshot_delta,
                "dependency-producer-receipt": build_producer_receipt,
                "dependency-admit": build_reuse_admission,
                "dependency-evaluate": evaluate_graph,
                "dependency-impact": compare_evaluations,
                "dependency-explain": explain_node,
                "dependency-export": build_portable_closure,
                "dependency-verify": verify_portable_closure,
            }
            result = routes[args.command](**_load(args.request))
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result) + b"\n")
        elif args.command == "ugel-orient":
            from .ugel import executor_pack_registry
            result = executor_pack_registry()
        elif args.command in {
            "ugel-bind", "ugel-policy", "ugel-call", "ugel-sim-add",
            "ugel-correspondence",
        }:
            from . import ugel
            routes = {
                "ugel-bind": ugel.build_executor_binding,
                "ugel-policy": ugel.build_component_policy,
                "ugel-call": ugel.build_guest_call,
                "ugel-sim-add": ugel.evaluate_reference_sim_add,
                "ugel-correspondence": ugel.compile_correspondence,
            }
            result = routes[args.command](**_load(args.request))
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result) + b"\n")
        elif args.command == "feature-negotiate":
            from .evolution import negotiate_feature_level
            result = negotiate_feature_level(_load(args.descriptor))
        elif args.command == "lifecycle-transition":
            from .lifecycle import build_lifecycle_receipt
            result = build_lifecycle_receipt(
                contract_root=args.contract_root, from_state=args.from_state,
                to_state=args.to_state,
                predecessor_receipt_root=args.predecessor_receipt_root,
                evidence_roots=args.evidence_roots)
        elif args.command == "contract-lint":
            from .authoring import lint_amcas_contract, lint_realization_contract
            result = (lint_realization_contract(_load(args.contract))
                      if args.kind == "realization" else lint_amcas_contract(_load(args.contract)))
        elif args.command == "contract-diff":
            from .authoring import semantic_contract_diff
            result = semantic_contract_diff(_load(args.before), _load(args.after))
        elif args.command == "contract-domain-diff":
            from .contract_workbench import domain_contract_diff
            result = domain_contract_diff(_load(args.before), _load(args.after))
        elif args.command == "contract-init":
            from uclop.canonical import canonical_bytes
            from .contract_workbench import (initialize_amcas_contract,
                                             initialize_realization_contract)
            if args.kind == "realization":
                result = initialize_realization_contract(
                    contract_id=args.identifier, subject_id=args.name,
                    subject_root=args.subject_root,
                    description=f"Draft realization contract for {args.name}.")
            else:
                if args.realization is None:
                    raise Refusal("UCM_REALIZATION_CONTRACT_REQUIRED")
                result = initialize_amcas_contract(
                    integration_id=args.identifier, application_id=args.name,
                    application_name=args.name, subject_root=args.subject_root,
                    manifest_root=args.manifest_root,
                    realization_contract=_load(args.realization))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "contract-compile-profile":
            from uclop.canonical import canonical_bytes
            from .contract_workbench import compile_authoring_profile
            result = compile_authoring_profile(args.source.read_text(encoding="utf-8"))
            _write_new(args.out, canonical_bytes(result["contract"]))
        elif args.command == "contract-doctor":
            from .contract_workbench import doctor_contract
            result = doctor_contract(args.kind, _load(args.contract))
        elif args.command == "contract-compatibility":
            from .contract_workbench import classify_contract_compatibility
            result = classify_contract_compatibility(
                predecessor=_load(args.predecessor), successor=_load(args.successor),
                known_roots=args.known_root)
        elif args.command == "explain-selection":
            from .contract_workbench import explain_selection
            result = explain_selection(_load(args.contract), _load(args.candidates))
        elif args.command == "configuration-diff":
            from .contract_workbench import compare_configurations
            result = compare_configurations(_load(args.contract), _load(args.left),
                                            _load(args.right))
        elif args.command == "pretty":
            from .presentation import pretty_record
            result = pretty_record(_load(args.record), title=args.title)
        elif args.command == "abi-stability":
            from .governance import abi_stability_table
            result = abi_stability_table()
        elif args.command == "environment-check":
            import os
            from .governance import inspect_environment
            result = inspect_environment(os.environ, strict=args.strict)
        elif args.command == "shell-completion":
            from .governance import shell_completion
            result = shell_completion(args.shell)
        elif args.command == "amcas-apply-policy-packs":
            from uclop.canonical import canonical_bytes
            from .authoring import apply_policy_packs
            result = apply_policy_packs(_load(args.contract), [_load(path) for path in args.packs])
            _write_new(args.out, canonical_bytes(result["contract"]))
        elif args.command == "evidence-validate":
            from .evidence import validate_evidence_envelope
            result = validate_evidence_envelope(_load(args.evidence),
                expected_subject_root=args.expected_subject_root,
                expected_policy_root=args.expected_policy_root, now=args.now)
        elif args.command == "journal-summary":
            from .journal_tools import summarize_events
            result = summarize_events(_load(args.events))
        elif args.command == "journal-query":
            from .journal_tools import query_events
            result = query_events(_load(args.events), event_type=args.event_type,
                                  operation_id=args.operation_id, limit=args.limit)
        elif args.command == "journal-diff":
            from .journal_tools import diff_event_chains
            result = diff_event_chains(_load(args.before), _load(args.after))
        elif args.command == "journal-prove":
            from uclop.canonical import canonical_bytes
            from .journal_tools import build_inclusion_proof
            result = build_inclusion_proof(_load(args.events), event_root=args.event_root)
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "journal-verify-proof":
            from .journal_tools import verify_inclusion_proof
            result = verify_inclusion_proof(_load(args.proof))
        elif args.command == "study-roster":
            from uclop.canonical import canonical_bytes
            from .evaluation import build_run_roster
            result = build_run_roster(_load(args.protocol))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "study-validate-result":
            from .evaluation import validate_run_result
            result = validate_run_result(_load(args.protocol), _load(args.result),
                                         _load(args.context_registration))
        elif args.command == "study-aggregate":
            from .evaluation import aggregate_study_results
            result = aggregate_study_results(_load(args.protocol), _load(args.results),
                                             _load(args.context_registration))
        elif args.command == "architecture-validate":
            from .architecture import validate_architecture_contract
            result = validate_architecture_contract(_load(args.contract))
        elif args.command == "architecture-check":
            from .architecture import check_architecture_change
            result = check_architecture_change(_load(args.contract), _load(args.candidate))
        elif args.command == "work-package":
            from uclop.canonical import canonical_bytes
            from .work_package import prepare_work_package
            result = prepare_work_package(
                project=_load(args.project), changed_ids=args.changed_id,
                changed_paths=args.changed_path, objective=args.objective,
                workspace=args.workspace,
                architecture_contract=_load(args.architecture_contract),
                architecture_candidate=_load(args.architecture_candidate))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "courthouse-compile-workflow":
            from uclop.canonical import canonical_bytes
            from .courthouse_workflow import compile_workflow_ir
            result = compile_workflow_ir(_load(args.request))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "courthouse-verify-workflow":
            from .courthouse_workflow import verify_compiled_workflow
            result = verify_compiled_workflow(_load(args.request), _load(args.workflow))
        elif args.command == "courthouse-import-result":
            from uclop.canonical import canonical_bytes
            from .courthouse_workflow import validate_workflow_result
            result = validate_workflow_result(
                _load(args.request), _load(args.workflow), _load(args.result))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "courthouse-compile-admissible":
            from uclop.canonical import canonical_bytes
            from .ccp_courthouse import compile_admissible_workflow_submission
            result = compile_admissible_workflow_submission(
                workflow_request=_load(args.request),
                admission_envelope=_load(args.admission))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "courthouse-admission-status":
            from uclop.canonical import canonical_bytes
            from .ccp_courthouse import build_pippi_admission_status
            result = build_pippi_admission_status(
                submission=_load(args.submission))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "courthouse-import-admissible-result":
            from uclop.canonical import canonical_bytes
            from .ccp_courthouse import validate_admissible_workflow_result
            result = validate_admissible_workflow_result(
                submission=_load(args.submission), result=_load(args.result))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "semantic-discover":
            from uclop.canonical import canonical_bytes
            from .semantic_consolidation import discover_candidates
            result = discover_candidates([_load(path) for path in args.plans],
                                         _load(args.policy))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "semantic-judgment-packet":
            from uclop.canonical import canonical_bytes
            from .semantic_consolidation import build_judgment_packet
            result = build_judgment_packet(_load(args.discovery))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "semantic-build-judgment-submission":
            from uclop.canonical import canonical_bytes
            from .semantic_consolidation import build_judgment_submission
            result = build_judgment_submission(_load(args.packet),
                                               _load(args.intent))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "semantic-record-judgments":
            from uclop.canonical import canonical_bytes
            from .semantic_consolidation import record_judgments
            result = record_judgments(_load(args.packet), _load(args.submission))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "semantic-compile-consolidation":
            from uclop.canonical import canonical_bytes
            from .semantic_consolidation import compile_correspondence_program
            result = compile_correspondence_program(_load(args.discovery),
                                                    _load(args.register))
            _write_new(args.out, canonical_bytes(result))
        elif args.command == "integration-validate-adapter":
            from .constitutional_runtime import validate_adapter_result
            result = validate_adapter_result(_load(args.adapter))
        elif args.command == "integration-validate-capsule":
            from .application_capsule import validate_application_capsule
            result = validate_application_capsule(_load(args.capsule))
        elif args.command == "integration-validate-control-plan":
            from .integration_control import validate_control_plan
            result = validate_control_plan(_load(args.plan))
        elif args.command == "integration-observatory":
            from uclop.canonical import canonical_bytes, exact_keys
            from .integration_observatory import build_observatory
            observation = exact_keys(_load(args.input), {"capsules", "operation_states", "journal_heads"})
            result = build_observatory(**observation)
            if args.out is not None:
                _write_new(args.out, canonical_bytes(result))
        elif args.command == "c-standard":
            from .c_preflight import c_coding_standard
            result = c_coding_standard()
        elif args.command == "c-preflight":
            from uclop.canonical import exact_keys
            from .c_preflight import build_c_change_preflight
            request = exact_keys(_load(args.request), {
                "proposal_id", "subject_root", "source_manifest_root",
                "language_standard", "compiler_profile_root",
                "architecture_contract_root", "change_classes", "changed_paths",
                "declared_write_paths", "declared_check_ids",
                "requested_effect_classes", "integration_mode",
                "mediated_channels", "native_semantic_authority", "python_role"})
            result = build_c_change_preflight(**request)
        elif args.command == "c-check-results":
            from uclop.canonical import exact_keys
            from .c_preflight import evaluate_c_check_results
            request = exact_keys(_load(args.request), {"preflight", "check_results"})
            result = evaluate_c_check_results(**request)
        elif args.command == "native-profile":
            from .native_core import native_core_profile
            result = native_core_profile()
        elif args.command == "native-compile":
            from .native_core import lower_native_program, validate_native_program
            program = validate_native_program(_load(args.program))
            projection = lower_native_program(program)
            _write_new(args.output, projection)
            result = {"status": "PASS", "program_root": program["program_root"],
                      "projection": str(args.output),
                      "projection_sha256": __import__("hashlib").sha256(projection).hexdigest(),
                      "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "real_a5": False, "g0": "CLOSED"}
        elif args.command == "native-reference":
            from .native_core import execute_native_reference
            result = execute_native_reference(_load(args.program))
        elif args.command == "pippi-create":
            from .pippi_runtime import PippiCampaign
            campaign = PippiCampaign.create(args.workspace, _load(args.context))
            result = {"status": "PASS", "context_root": campaign.context()["context_root"],
                      "workspace": str(args.workspace), "standing": "INFORMATION_ONLY",
                      "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
        elif args.command == "pippi-record-turn":
            from .pippi_runtime import PippiCampaign
            result = PippiCampaign(args.workspace).record_turn(
                context=_load(args.context), draft=_load(args.draft),
                decision=_load(args.decision), projection=_load(args.projection),
                turn=_load(args.turn), event_id=args.event_id)
        elif args.command == "pippi-status":
            from .pippi_runtime import PippiCampaign
            result = PippiCampaign(args.workspace).project(args.view)
        elif args.command == "pippi-next":
            from .pippi_runtime import PippiCampaign
            projection = PippiCampaign(args.workspace).project("AGENT")
            result = {"schema": "mosaic.ucm.pippi-next.v0.1",
                      "observatory_state_root": projection["observatory_state_root"],
                      "status": projection["content"]["status"],
                      "available_actions": projection["content"]["available_actions"],
                      "actions_are_authority": False, "standing": "INFORMATION_ONLY",
                      "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
        elif args.command == "pippi-explain":
            from .pippi_runtime import PippiCampaign
            result = PippiCampaign(args.workspace).project("FORENSIC")
        elif args.command == "pippi-verify":
            from .pippi_runtime import validate_pippi_campaign_workspace
            result = validate_pippi_campaign_workspace(args.workspace)
        elif args.command == "process-build":
            from uclop.canonical import canonical_bytes
            from . import process_governance as pg
            builders = {
                "locality": pg.build_dkn_locality_binding,
                "execution-capsule": pg.build_exact_execution_capsule,
                "artifact-receipt": pg.build_artifact_producer_receipt,
                "baseline": pg.build_process_baseline,
                "milestone": pg.build_process_milestone,
                "assessment": pg.assess_process_milestone,
                "decision": pg.record_process_milestone_decision,
                "checkpoint": pg.build_process_checkpoint,
                "replan": pg.build_governed_replan,
                "standards-schedule": pg.build_process_standards_schedule,
                "observatory": pg.build_process_observatory,
                "courthouse-binding": pg.build_courthouse_process_binding,
                "thr": pg.build_process_thr_manifest,
            }
            result = builders[args.action](**_load(args.request))
            _write_new(args.out, canonical_bytes(result) + b"\n")
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
            from .profiles import profile_registry
            payload = _load(args.payload)
            request = {"schema": "mosaic.ucm.request.v0.2",
                       "surface": args.surface, "payload": payload,
                       "profile_selection": {
                           "schema": "mosaic.ucm.product-profile-selection.v0.1",
                           "profile_id": "OPERATIONAL",
                           "capability_registry_root": profile_registry()[
                               "capability_registry_root"],
                       },
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
        elif args.command == "amcas-baseline":
            from .amcas_parity import build_amcas_registry
            result = build_amcas_registry()
        elif args.command == "amcas-coverage":
            from .amcas_parity import build_ucm_coverage_registry
            result = build_ucm_coverage_registry()
        elif args.command == "amcas-compile-baseline":
            from .amcas_parity import compile_amcas_baseline
            result = compile_amcas_baseline(_load(args.contract))
        elif args.command == "amcas-semantic-diff":
            from .amcas_parity import semantic_diff_amcas
            result = semantic_diff_amcas(_load(args.before), _load(args.after))
        elif args.command == "amcas-parity":
            from .amcas_parity import run_amcas_ucm_parity
            result = run_amcas_ucm_parity()
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
        return 3 if hasattr(error, "code") else 70


if __name__ == "__main__":
    raise SystemExit(main())

