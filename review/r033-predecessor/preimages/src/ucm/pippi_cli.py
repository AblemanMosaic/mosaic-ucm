"""P/PPI sovereign local command line."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from uclop.canonical import canonical_bytes, strict_loads

from .pippi_global import (HubRefusal, PippiHub, build_context_injection,
                           build_onboarding, build_project, default_data_root)
from .pippi_portfolio import (PortfolioStore, build_preferences, build_project_brief, build_timeline,
                              discover_campaigns, validate_preferences,
                              validate_project_profile)
from .pippi_reviews import (ReviewStore, build_review_envelope,
                            build_operator_kit_contract,
                            run_review_envelope, validate_review_spec,
                            validate_operator_kit_contract,
                            verify_review_envelope)
from .research_reviews import VALIDATORS, validate_research_record
from .pippi_work_units import build_work_selection


EXIT_SUCCESS = 0
EXIT_TYPED_REFUSAL = 3
EXIT_USAGE_ERROR = 64
EXIT_UNSUPPORTED_SURFACE = 69
EXIT_INTERNAL_FAULT = 70
EXIT_CUSTODY_FAILURE = 74


class PippiArgumentParser(argparse.ArgumentParser):
    """Emit machine-stable usage failures instead of argparse's generic 2."""
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        raise HubRefusal("PIPPI_USAGE_ERROR", message)


def _print(value) -> None:
    sys.stdout.buffer.write(canonical_bytes(value)+b"\n")


def main(argv: list[str] | None=None) -> int:
    parser=PippiArgumentParser(prog="pippi",description="Mosaic Project / Process Pipeline Interface v0.1 r033")
    parser.add_argument("--data-root",type=Path,default=default_data_root())
    sub=parser.add_subparsers(dest="command",required=True)
    onboard=sub.add_parser("onboard")
    onboard.add_argument("--governor-label",required=True)
    onboard.add_argument("--mosaic-id")
    onboard.add_argument("--dkn-public-key")
    onboard.add_argument("--github-account")
    onboard.add_argument("--github-credential-reference")
    project=sub.add_parser("project-add")
    project.add_argument("project_id");project.add_argument("title");project.add_argument("workspace")
    project.add_argument("--github-url");project.add_argument("--application-command",nargs="+")
    project.add_argument("--verification-command",nargs="+");project.add_argument("--readme")
    project.add_argument("--doc",action="append",default=[]);project.add_argument("--revision",default="r001")
    revise=sub.add_parser("project-revise");revise.add_argument("project_id");revise.add_argument("revision")
    sub.add_parser("projects");sub.add_parser("verify");sub.add_parser("dashboard");sub.add_parser("dashboard-probe");sub.add_parser("serve")
    profiles=sub.add_parser("profile-show");profiles.add_argument("project_id")
    brief=sub.add_parser("project-brief");brief.add_argument("project_id")
    profile_set=sub.add_parser("profile-set");profile_set.add_argument("profile_json",type=Path)
    sessions=sub.add_parser("sessions");sessions.add_argument("--project-id")
    discover=sub.add_parser("migrate-discover");discover.add_argument("root",type=Path,nargs="+")
    migrate=sub.add_parser("migrate-import");migrate.add_argument("project_id");migrate.add_argument("root",type=Path,nargs="+")
    sub.add_parser("preferences-show")
    preferences=sub.add_parser("preferences-set")
    preferences.add_argument("--session-navigation",choices=("LEFT","TOP"),default="LEFT")
    preferences.add_argument("--theme",choices=("signature-dark","high-contrast-dark","signature-light"),default="signature-dark")
    preferences.add_argument("--density",choices=("comfortable","compact"),default="comfortable")
    preferences.add_argument("--default-tab",choices=("OVERVIEW","SESSIONS","TIMELINE","EVIDENCE","REVIEWS","CONSTITUTION"),default="OVERVIEW")
    preferences.add_argument("--hash-display",choices=("ABBREVIATED","FULL"),default="ABBREVIATED")
    timeline=sub.add_parser("timeline");timeline.add_argument("project_id")
    context=sub.add_parser("context")
    context.add_argument("project_id");context.add_argument("session_root");context.add_argument("scenario")
    context.add_argument("--rule",action="append",default=[])
    review_build=sub.add_parser("review-envelope-build")
    review_build.add_argument("project_id");review_build.add_argument("spec_json",type=Path);review_build.add_argument("output",type=Path)
    review_verify=sub.add_parser("review-envelope-verify");review_verify.add_argument("envelope",type=Path)
    review_verify.add_argument("--expected-sha256",required=True)
    operator_contract=sub.add_parser("operator-kit-contract")
    operator_contract.add_argument("request_json",type=Path)
    operator_verify=sub.add_parser("operator-kit-verify")
    operator_verify.add_argument("contract_json",type=Path)
    reviews=sub.add_parser("reviews");reviews.add_argument("--project-id")
    review_run=sub.add_parser("review-run-local")
    review_run.add_argument("project_id");review_run.add_argument("review_id");review_run.add_argument("evidence",type=Path)
    review_dispatch=sub.add_parser("review-dispatch-courthouse")
    review_dispatch.add_argument("project_id");review_dispatch.add_argument("review_id");review_dispatch.add_argument("destination_jurisdiction")
    review_import=sub.add_parser("review-import-return")
    review_import.add_argument("project_id");review_import.add_argument("review_id");review_import.add_argument("return_zip",type=Path)
    review_compare=sub.add_parser("review-compare")
    review_compare.add_argument("project_id");review_compare.add_argument("left_review_id");review_compare.add_argument("right_review_id")
    review_publish=sub.add_parser("review-publication-proposal")
    review_publish.add_argument("project_id");review_publish.add_argument("review_id");review_publish.add_argument("artifact_path",type=Path)
    review_publish.add_argument("artifact_sha256")
    review_publish.add_argument("--target",action="append",required=True);review_publish.add_argument("--dkn-public-namespace")
    research_verify=sub.add_parser("research-record-verify")
    research_verify.add_argument("kind",choices=sorted(VALIDATORS));research_verify.add_argument("record_json",type=Path)
    work_selection=sub.add_parser("work-selection-verify")
    work_selection.add_argument("selection_json",type=Path)
    sub.add_parser("mediation-library")
    sub.add_parser("standards")
    sub.add_parser("pipeline-model")
    standard_explain=sub.add_parser("standard-explain");standard_explain.add_argument("rule_id")
    transition_explain=sub.add_parser("transition-explain");transition_explain.add_argument("transition_id")
    for constitution_command in ("context-explain", "collaborator-bind", "credential-reference",
            "change-capsule-build", "change-capsule-verify", "storage-locator",
            "publication-receipt", "publication-receipt-verify", "retrieval-receipt",
            "retrieval-receipt-verify", "ccp-transition"):
        constitution_parser=sub.add_parser(constitution_command)
        constitution_parser.add_argument("request_json",type=Path)
    sub.add_parser("credential-policy")
    host_negotiate=sub.add_parser("host-negotiate")
    host_negotiate.add_argument("request_json",type=Path)
    turn_prepare=sub.add_parser("turn-prepare")
    turn_prepare.add_argument("request_json",type=Path)
    turn_report=sub.add_parser("turn-report")
    turn_report.add_argument("request_json",type=Path)
    turn_reconcile=sub.add_parser("turn-reconcile")
    turn_reconcile.add_argument("request_json",type=Path)
    capsule_build=sub.add_parser("capsule-build")
    capsule_build.add_argument("request_json",type=Path)
    capsule_verify=sub.add_parser("capsule-verify")
    capsule_verify.add_argument("capsule_json",type=Path)
    sub.add_parser("interface-doctor")
    completion=sub.add_parser("completion")
    completion.add_argument("shell",choices=("bash","zsh","fish","powershell"))
    sub.add_parser("pack-list")
    sub.add_parser("pack-inventory")
    install_plan=sub.add_parser("install-plan")
    install_plan.add_argument("profile",choices=("MINIMAL_CORE","RECOMMENDED_LOCAL","PORTABLE_AGENT",
                                                  "TRANSTEMPORAL_PROJECT","COURTHOUSE_CONNECTED","FULL_MOSAIC"))
    install_plan.add_argument("--pack",action="append",default=[])
    install_plan.add_argument("--offline-root",action="append",default=[])
    install_plan.add_argument("--allow-remote-downloads",action="store_true")
    portability=sub.add_parser("project-portability")
    portability.add_argument("--required-pack",action="append",required=True)
    environment=sub.add_parser("environment-observe")
    environment.add_argument("--shell-family",required=True,
                             choices=("POWERSHELL","CMD","BASH","ZSH","FISH","UNKNOWN"))
    sub.add_parser("portability-policy")
    portability_witness=sub.add_parser("portability-witness")
    portability_witness.add_argument("request_json",type=Path)
    portability_gate=sub.add_parser("portability-gate")
    portability_gate.add_argument("request_json",type=Path)
    portability_doctor=sub.add_parser("portability-source-doctor")
    portability_doctor.add_argument("request_json",type=Path)
    pack_record=sub.add_parser("pack-record")
    pack_record.add_argument("pack_id");pack_record.add_argument("state")
    pack_record.add_argument("--expected-inventory-root",required=True)
    pack_record.add_argument("--installed-root");pack_record.add_argument("--binding-root")
    pack_record.add_argument("--evidence-root",action="append",default=[])
    archive_ingest=sub.add_parser("archive-ingest")
    archive_ingest.add_argument("source",type=Path);archive_ingest.add_argument("repository",type=Path)
    archive_ingest.add_argument("revision");archive_ingest.add_argument("semantic_root")
    archive_ingest.add_argument("governance_root");archive_ingest.add_argument("jurisdiction_root")
    archive_ingest.add_argument("--parent-revision")
    archive_verify=sub.add_parser("archive-verify")
    archive_verify.add_argument("repository",type=Path);archive_verify.add_argument("revision")
    archive_materialize=sub.add_parser("archive-materialize")
    archive_materialize.add_argument("repository",type=Path);archive_materialize.add_argument("revision")
    archive_materialize.add_argument("destination",type=Path)
    archive_diff=sub.add_parser("archive-diff")
    archive_diff.add_argument("repository",type=Path);archive_diff.add_argument("before");archive_diff.add_argument("after")
    archive_report=sub.add_parser("archive-report");archive_report.add_argument("repository",type=Path)
    semcrys_plan=sub.add_parser("archive-semcrys-plan")
    semcrys_plan.add_argument("repository",type=Path);semcrys_plan.add_argument("revision")
    semcrys_plan.add_argument("--semcrys-manifest-root");semcrys_plan.add_argument("--memory-vault-binding-root")
    native_manifest=sub.add_parser("archive-native-manifest")
    native_manifest.add_argument("repository",type=Path);native_manifest.add_argument("revision")
    native_manifest.add_argument("out",type=Path)
    sub.add_parser("installer");sub.add_parser("installer-probe")
    try:
        args=parser.parse_args(argv);hub=PippiHub(args.data_root);portfolio=PortfolioStore(hub);review_store=ReviewStore(hub)
        if args.command=="onboard":
            result=hub.initialize(build_onboarding(governor_label=args.governor_label,mosaic_id=args.mosaic_id,
                dkn_public_key=args.dkn_public_key,github_account=args.github_account,
                github_credential_reference=args.github_credential_reference))
        elif args.command=="project-add":
            result=hub.add_project(build_project(project_id=args.project_id,title=args.title,workspace=args.workspace,
                github_url=args.github_url,application_command=args.application_command,
                verification_command=args.verification_command,readme=args.readme,docs=args.doc,revision=args.revision))
        elif args.command=="projects": result=hub.list_projects()
        elif args.command=="project-revise":
            current=hub.get_project(args.project_id)
            result=hub.transition_project_identity(project_id=args.project_id,
                requested_public_version=current["public_version"],requested_revision=args.revision)
        elif args.command=="profile-show": result=portfolio.profile(hub.get_project(args.project_id))
        elif args.command=="project-brief":
            project=hub.get_project(args.project_id)
            result=build_project_brief(project=project,profile=portfolio.profile(project),
                sessions=portfolio.list_sessions(project["project_id"]),
                reviews=review_store.list(project["project_id"]),
                gateway_status=hub.integration("UCM_OPERATIONAL_GATEWAY")["status"])
        elif args.command=="profile-set":
            result=portfolio.save_profile(validate_project_profile(strict_loads(args.profile_json.read_bytes())))
        elif args.command=="sessions": result=portfolio.list_sessions(args.project_id)
        elif args.command=="migrate-discover": result=discover_campaigns(args.root)
        elif args.command=="migrate-import":
            discovered=discover_campaigns(args.root);imported=[];refused=[]
            for record in discovered:
                if record.get("discovery_status")=="VERIFIED":
                    imported.append(portfolio.import_session(record,project_id=args.project_id))
                else: refused.append(record)
            result={"schema":"mosaic.ucm.pippi-migration-result.v0.1","project_id":args.project_id,
                    "imported":imported,"refused":refused,"source_roots":[str(p.resolve()) for p in args.root],
                    "migration_mode":"REFERENCE_ONLY_NO_REWRITE","standing":"INFORMATION_ONLY",
                    "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
        elif args.command=="preferences-show": result=portfolio.preferences()
        elif args.command=="preferences-set":
            result=portfolio.save_preferences(build_preferences(session_navigation=args.session_navigation,
                theme=args.theme,density=args.density,default_tab=args.default_tab,hash_display=args.hash_display))
        elif args.command=="timeline":
            hub.get_project(args.project_id)
            result=build_timeline(project_id=args.project_id,hub_events=hub._events(),
                                  sessions=portfolio.list_sessions(args.project_id))
        elif args.command=="verify": result=hub.verify()
        elif args.command=="context":
            result=build_context_injection(project=hub.get_project(args.project_id),session_root=args.session_root,
                                           scenario=args.scenario,requested_rules=args.rule)
            hub.append("CONTEXT_INJECTION_BUILT",{"project_id":args.project_id,
                                                   "context_injection_root":result["context_injection_root"]})
        elif args.command=="review-envelope-build":
            spec=validate_review_spec(strict_loads(args.spec_json.read_bytes()))
            build_review_envelope(project=hub.get_project(args.project_id),spec=spec,
                                  spec_dir=args.spec_json.parent,output_path=args.output)
            result=review_store.register(project_id=args.project_id,envelope_path=args.output)
        elif args.command=="review-envelope-verify":
            result=verify_review_envelope(args.envelope,expected_sha256=args.expected_sha256)
        elif args.command=="operator-kit-contract":
            request=strict_loads(args.request_json.read_bytes())
            result=build_operator_kit_contract(**request)
        elif args.command=="operator-kit-verify":
            value=validate_operator_kit_contract(strict_loads(args.contract_json.read_bytes()))
            result={"schema":"mosaic.ucm.pippi-operator-kit-verification.v0.1",
                    "status":"PASS","operator_kit_root":value["operator_kit_root"],
                    "standing":"INFORMATION_ONLY","authority_effect":"NONE",
                    "real_a5":False,"g0":"CLOSED"}
        elif args.command=="reviews": result=review_store.list(args.project_id)
        elif args.command=="review-run-local":
            record=review_store.get(args.project_id,args.review_id)
            def progress(event):
                sys.stderr.buffer.write(canonical_bytes(event)+b"\n");sys.stderr.buffer.flush()
            result=run_review_envelope(Path(record["envelope_path"]),args.evidence,
                                       expected_sha256=record["envelope_sha256"],progress=progress)
            hub.append("REVIEW_LOCAL_RUN_COMPLETED",{"project_id":args.project_id,"review_id":args.review_id,
                                                      "run_root":result["run_root"],"status":result["status"]})
        elif args.command=="review-dispatch-courthouse":
            result=review_store.prepare_courthouse(project_id=args.project_id,review_id=args.review_id,
                                                    destination_jurisdiction=args.destination_jurisdiction)
        elif args.command=="review-import-return":
            result=review_store.import_return(project_id=args.project_id,review_id=args.review_id,return_path=args.return_zip)
        elif args.command=="review-compare":
            result=review_store.compare(project_id=args.project_id,left_review_id=args.left_review_id,
                                        right_review_id=args.right_review_id)
        elif args.command=="review-publication-proposal":
            result=review_store.propose_publication(project_id=args.project_id,review_id=args.review_id,
                artifact_path=args.artifact_path,artifact_sha256=args.artifact_sha256,
                targets=sorted(set(args.target)),
                dkn_public_namespace=args.dkn_public_namespace)
        elif args.command=="research-record-verify":
            record=validate_research_record(args.kind,strict_loads(args.record_json.read_bytes()))
            root_fields={
                "lens-pack":"lens_pack_root","finding":"finding_root",
                "adjudication":"adjudication_root","successor-ledger":"successor_ledger_root",
                "saturation":"saturation_assessment_root",
            }
            result={"status":"PASS","kind":args.kind,"record_root":record[root_fields[args.kind]],
                    "standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
        elif args.command=="work-selection-verify":
            selection=strict_loads(args.selection_json.read_bytes())
            if not isinstance(selection,dict) or set(selection)!={
                    "acceptance_case","work_class","direct_closure_check_id","infrastructure_block"}:
                raise HubRefusal("PIPPI_WORK_SELECTION_INPUT_INVALID")
            result=build_work_selection(**selection)
            if not hub.onboarding.is_file():
                raise HubRefusal("PIPPI_ONBOARDING_REQUIRED")
            event=hub.append("WORK_SELECTION_VERIFIED",{
                "work_selection_root":result["work_selection_root"],
                "acceptance_case_root":result["acceptance_case_root"],
                "work_class":result["work_class"],
                "selection_basis":result["selection_basis"]})
            result={**result,"hub_event_root":event["event_root"]}
        elif args.command=="mediation-library":
            from .pippi_adaptive import mediation_library
            result=mediation_library()
        elif args.command=="standards":
            from .pippi_constitution import build_constitutional_standards_atlas
            result=build_constitutional_standards_atlas()
        elif args.command=="pipeline-model":
            from .pippi_constitution import build_pipeline_model
            result=build_pipeline_model()
        elif args.command=="standard-explain":
            from .pippi_constitution import explain_standard_rule
            result=explain_standard_rule(args.rule_id)
        elif args.command=="transition-explain":
            from .pippi_constitution import explain_pipeline_transition
            result=explain_pipeline_transition(args.transition_id)
        elif args.command in {"context-explain", "collaborator-bind", "credential-reference",
                "change-capsule-build", "storage-locator", "publication-receipt",
                "retrieval-receipt", "ccp-transition"}:
            from . import pippi_constitution as constitution
            routes={"context-explain":constitution.explain_context_selection,
                    "collaborator-bind":constitution.build_collaborator_binding,
                    "credential-reference":constitution.build_credential_reference,
                    "change-capsule-build":constitution.build_signed_change_capsule,
                    "storage-locator":constitution.build_storage_locator,
                    "publication-receipt":constitution.build_signed_publication_receipt,
                    "retrieval-receipt":constitution.build_signed_retrieval_receipt,
                    "ccp-transition":constitution.build_ccp_transition_binding}
            result=routes[args.command](**strict_loads(args.request_json.read_bytes()))
        elif args.command=="change-capsule-verify":
            from .pippi_constitution import validate_signed_change_capsule
            result=validate_signed_change_capsule(strict_loads(args.request_json.read_bytes()))
        elif args.command=="publication-receipt-verify":
            from .pippi_constitution import validate_signed_publication_receipt
            result=validate_signed_publication_receipt(strict_loads(args.request_json.read_bytes()))
        elif args.command=="retrieval-receipt-verify":
            from .pippi_constitution import validate_signed_retrieval_receipt
            request=strict_loads(args.request_json.read_bytes())
            if not isinstance(request,dict) or set(request)!={"value","publication_receipt"}:
                raise HubRefusal("PIPPI_RETRIEVAL_VERIFICATION_INPUT_INVALID")
            result=validate_signed_retrieval_receipt(
                request["value"], publication_receipt=request["publication_receipt"])
        elif args.command=="credential-policy":
            from .pippi_constitution import credential_broker_policy
            result=credential_broker_policy()
        elif args.command=="host-negotiate":
            from .pippi_adaptive import negotiate_host_mode
            result=negotiate_host_mode(**strict_loads(args.request_json.read_bytes()))
        elif args.command=="turn-prepare":
            from .pippi_adaptive import prepare_turn
            request=strict_loads(args.request_json.read_bytes())
            project=hub.get_project(request["project"]["project_id"])
            if request["project"] != project: raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
            record=prepare_turn(**request)
            result=hub.store_project_record(project_id=project["project_id"],record_kind="opening",
                record=record,root_field="turn_opening_root",event_type="TURN_OPENED")
        elif args.command=="turn-report":
            from .pippi_adaptive import build_turn_report, validate_turn_opening
            request=strict_loads(args.request_json.read_bytes());opening=validate_turn_opening(request["opening"])
            project=hub.get_project(opening["project_id"])
            if opening["project_root"] != project["project_root"]: raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
            record=build_turn_report(**request)
            result=hub.store_project_record(project_id=project["project_id"],record_kind="report",
                record={**record,"project_root":opening["project_root"]},root_field="turn_report_root",
                event_type="TURN_REPORT_SUBMITTED")
        elif args.command=="turn-reconcile":
            from .pippi_adaptive import reconcile_turn, validate_turn_opening
            request=strict_loads(args.request_json.read_bytes());opening=validate_turn_opening(request["opening"])
            project=hub.get_project(opening["project_id"])
            record=reconcile_turn(**request)
            result=hub.store_project_record(project_id=project["project_id"],record_kind="reconciliation",
                record=record,root_field="reconciliation_root",event_type="TURN_RECONCILED")
        elif args.command=="capsule-build":
            from .pippi_adaptive import build_project_capsule
            request=strict_loads(args.request_json.read_bytes())
            project=hub.get_project(request["project"]["project_id"])
            if request["project"] != project: raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
            record=build_project_capsule(**request)
            result=hub.store_project_record(project_id=project["project_id"],record_kind="capsule",
                record=record,root_field="capsule_root",event_type="PROJECT_CAPSULE_BUILT")
        elif args.command=="capsule-verify":
            from .pippi_adaptive import verify_project_capsule
            result=verify_project_capsule(strict_loads(args.capsule_json.read_bytes()))
        elif args.command=="interface-doctor":
            from .pippi_adaptive import interface_conformance
            result=interface_conformance()
        elif args.command=="completion":
            from .pippi_adaptive import pippi_shell_completion
            result=pippi_shell_completion(args.shell)
        elif args.command=="pack-list":
            from .pippi_packs import pack_registry
            result=pack_registry()
        elif args.command=="pack-inventory":
            from .pippi_packs import PackStore
            result=PackStore(args.data_root).inventory()
        elif args.command=="install-plan":
            from .pippi_packs import PackStore,build_install_plan
            result=build_install_plan(profile=args.profile,inventory=PackStore(args.data_root).inventory(),
                requested_packs=args.pack,offline_artifact_roots=args.offline_root,
                allow_remote_downloads=args.allow_remote_downloads)
        elif args.command=="project-portability":
            from .pippi_packs import PackStore,explain_project_portability
            result=explain_project_portability(required_packs=args.required_pack,
                                                inventory=PackStore(args.data_root).inventory())
        elif args.command=="environment-observe":
            from .pippi_portability import observe_execution_context
            result=observe_execution_context(shell_family=args.shell_family)
        elif args.command=="portability-policy":
            from .pippi_portability import portability_policy
            result=portability_policy()
        elif args.command=="portability-witness":
            from .pippi_portability import build_portability_witness
            result=build_portability_witness(**strict_loads(args.request_json.read_bytes()))
        elif args.command=="portability-gate":
            from .pippi_portability import evaluate_portability_gate
            result=evaluate_portability_gate(**strict_loads(args.request_json.read_bytes()))
        elif args.command=="portability-source-doctor":
            from .pippi_portability import inspect_portable_python_sources
            result=inspect_portable_python_sources(**strict_loads(args.request_json.read_bytes()))
        elif args.command=="pack-record":
            from .pippi_packs import PackStore
            result=PackStore(args.data_root).record(expected_inventory_root=args.expected_inventory_root,
                pack_id=args.pack_id,state=args.state,installed_root=args.installed_root,
                binding_root=args.binding_root,evidence_roots=args.evidence_root)
        elif args.command=="archive-ingest":
            from .transtemporal_archive import ingest_tree
            result=ingest_tree(source=args.source,repository=args.repository,revision=args.revision,
                semantic_root=args.semantic_root,governance_root=args.governance_root,
                jurisdiction_root=args.jurisdiction_root,parent_revision=args.parent_revision)
        elif args.command=="archive-verify":
            from .transtemporal_archive import verify_revision
            result=verify_revision(repository=args.repository,revision=args.revision)
        elif args.command=="archive-materialize":
            from .transtemporal_archive import materialize_revision
            result=materialize_revision(repository=args.repository,revision=args.revision,destination=args.destination)
        elif args.command=="archive-diff":
            from .transtemporal_archive import diff_revisions
            result=diff_revisions(repository=args.repository,before=args.before,after=args.after)
        elif args.command=="archive-report":
            from .transtemporal_archive import storage_report
            result=storage_report(repository=args.repository)
        elif args.command=="archive-semcrys-plan":
            from .transtemporal_archive import build_semcrys_plan
            result=build_semcrys_plan(repository=args.repository,revision=args.revision,
                semcrys_manifest_root=args.semcrys_manifest_root,
                memory_vault_binding_root=args.memory_vault_binding_root)
        elif args.command=="archive-native-manifest":
            from .transtemporal_archive import (build_native_manifest,
                                                 build_native_manifest_binding)
            raw=build_native_manifest(repository=args.repository,revision=args.revision)
            binding=build_native_manifest_binding(repository=args.repository,revision=args.revision)
            binding_path=Path(str(args.out)+".binding.json")
            args.out.parent.mkdir(parents=True,exist_ok=True)
            if args.out.exists() or binding_path.exists(): raise HubRefusal("PIPPI_OUTPUT_EXISTS")
            manifest_created=False
            try:
                with args.out.open("xb") as stream: stream.write(raw)
                manifest_created=True
                with binding_path.open("xb") as stream: stream.write(canonical_bytes(binding)+b"\n")
            except (FileExistsError,OSError) as exc:
                if manifest_created and args.out.exists(): args.out.unlink()
                raise HubRefusal("PIPPI_OUTPUT_WRITE_REFUSED") from exc
            result={"schema":"mosaic.ucm.native-manifest-export.v0.1","status":"PASS",
                    "path":str(args.out),"sha256":__import__("hashlib").sha256(raw).hexdigest(),
                    "binding_path":str(binding_path),"binding":binding,
                    "bytes":len(raw),"standing":"INFORMATION_ONLY","authority_effect":"NONE",
                    "real_a5":False,"g0":"CLOSED"}
        elif args.command=="installer":
            from .pippi_installer import launch_installer
            return launch_installer(args.data_root)
        elif args.command=="installer-probe":
            from .pippi_installer import probe_installer
            result=probe_installer(args.data_root)
        elif args.command=="dashboard":
            from .pippi_dashboard import launch_dashboard
            return launch_dashboard(args.data_root)
        elif args.command=="dashboard-probe":
            from .pippi_dashboard import probe_dashboard
            result=probe_dashboard(args.data_root)
        elif args.command=="serve":
            from .pippi_service import serve
            return serve(args.data_root)
        else: raise HubRefusal("PIPPI_COMMAND_REFUSED")
        _print(result);return EXIT_SUCCESS
    except HubRefusal as exc:
        _print({"status":"REFUSED","code":getattr(exc,"code","PIPPI_INTERNAL_REFUSAL"),
                "detail":getattr(exc,"detail",str(exc)),"standing":"INFORMATION_ONLY",
                "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"})
        if exc.code == "PIPPI_USAGE_ERROR": return EXIT_USAGE_ERROR
        if exc.code in {"PIPPI_COMMAND_REFUSED", "PIPPI_INTEGRATION_UNKNOWN"}: return EXIT_UNSUPPORTED_SURFACE
        if "CUSTODY" in exc.code or "ROOT_COLLISION" in exc.code: return EXIT_CUSTODY_FAILURE
        return EXIT_TYPED_REFUSAL
    except ValueError as exc:
        _print({"status":"REFUSED","code":"PIPPI_CONTRACT_REFUSED",
                "detail":str(exc),"standing":"INFORMATION_ONLY",
                "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"})
        return EXIT_TYPED_REFUSAL
    except OSError as exc:
        _print({"status":"REFUSED","code":"PIPPI_INTERNAL_FAULT",
                "detail":str(exc),"standing":"INFORMATION_ONLY",
                "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"})
        return EXIT_INTERNAL_FAULT


if __name__=="__main__": raise SystemExit(main())

