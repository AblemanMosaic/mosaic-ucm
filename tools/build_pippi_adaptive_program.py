#!/usr/bin/env python3
"""Build the governed r020 adaptive repair work program."""
from __future__ import annotations

import argparse,hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from ucm.pippi_work_units import build_acceptance_case,build_work_selection
from ucm.program_history import check_frozen_program_directory

OUT=ROOT/"program/pippi-adaptive-r020"
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}


def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def rooted(v,field):return {**v,field:hashlib.sha256(canonical(v)).hexdigest()}
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value)+b"\n")


def records():
    files=["src/ucm/pippi_adaptive.py","src/ucm/pippi_global.py","src/ucm/pippi_cli.py",
           "src/ucm/pippi_packs.py","src/ucm/pippi_installer.py",
           "src/ucm/system.py","src/ucm/capabilities.py","tools/build_pippi_adaptive_contracts.py",
           "tools/build_pippi_cold_boot.py","tools/verify_pippi_cold_boot.py",
           "tools/build_pippi_adaptive_operator_kit.py","operator/pippi-adaptive-r020/RUN-TIER1.py",
           "tools/build_release.py","tools/run_public_release_qualification.py","VERIFY.py",
           "tests/test_pippi_adaptive.py","tests/test_pippi_cold_boot.py","tests/test_pippi_operator_kit.py",
           "tests/test_pippi_packs.py","tools/build_pippi_pack_contracts.py",
           "docs/PIPPI-ADAPTIVE-COLD-BOOT.md","PIPPI-START-HERE.md","PIPPI-AGENT-ACCESS.md",
           "docs/PIPPI-MODULAR-INSTALLATION.md","docs/PIPPI-CAPABILITY-PACKS.md",
           "spec/PIPPI-PACK-REGISTRY.json","PIPPI-INSTALLER.BAT","PIPPI-INSTALLER.vbs",
           "PIPPI-HEADLESS.BAT","PIPPI-HEADLESS.vbs","install/INSTALL-PIPPI.ps1",
           "install/INSTALL-PIPPI.vbs","tools/normalize_pippi_work_selection_history.py",
           "program/pippi-work-selection-normalization-r019/NORMALIZATION.json",
           "review/pippi-r018-review-return/FINDINGS.json",
           "review/pippi-r018-operator-return/PIPPI-r018-TIER1-EVIDENCE.zip",
           "review/pippi-r019-review-return/FINDINGS.json",
           "review/pippi-r019-review-return/DISPOSITION.json",
           "review/pippi-r019-operator-return/PIPPI-r019-TIER1-EVIDENCE.zip",
           "historical/public-vocabulary-r013-closure-preimage/WORK-SELECTION.json",
           "program/public-vocabulary-r020-normalization/NORMALIZATION.json",
           "tools/build_pippi_interface_program.py","tools/build_public_vocabulary.py",
           "tests/test_pippi_portfolio.py","tests/test_public_release_qualification.py",
           "tests/test_public_vocabulary.py","tests/test_pippi_r019_custody.py",
           "docs/PIPPI-r020-CLOSURE.md",
           "skill/ucm-pippi-mediated-agent/SKILL.md"]
    rows=[{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in files]
    denominator=rooted({"schema":"mosaic.ucm.pippi-source-denominator.v0.1","members":rows,**BOUNDARY},"source_denominator_root")
    requirements=[];cases=[];selections=[]
    definitions=[
      ("PIPPI-ADAPTIVE-01","Adaptive hosts use rooted prepare, report and reconcile records bound to the project and journal.","test_pippi_adaptive.PippiAdaptiveTests.test_turn_open_report_reconcile"),
      ("PIPPI-ABI-01","Every adaptive capability has a registry-backed ABI schema, CLI route and payload definition.","test_pippi_adaptive.PippiAdaptiveTests.test_interface_registry_is_complete"),
      ("PIPPI-COLD-BOOT-01","A slim deterministic cold boot binds and verifies its nested UCM runtime and adaptive UGK profile.","test_pippi_cold_boot.PippiColdBootTests.test_deterministic_cold_boot_and_nested_runtime_verification")]
    definitions.extend([
      ("PIPPI-CUSTODY-01","A durable turn record interrupted before journal append recovers exactly once.","test_pippi_adaptive.PippiAdaptiveTests.test_local_hub_recovers_record_written_before_journal_append"),
      ("PIPPI-CLI-01","Pippi commands use stable machine exit codes and registry-generated completion names.","test_pippi_adaptive.PippiAdaptiveTests.test_cli_uses_machine_stable_usage_and_refusal_codes"),
      ("PIPPI-PACKS-01","A fixed registry distinguishes the complete core, recommended standards, and optional external realizations.","test_pippi_packs.PippiPackTests.test_registry_separates_core_standards_and_optional_realizations"),
      ("PIPPI-PLAN-01","Install planning is deterministic and performs no downloads, bindings, or capability grants.","test_pippi_packs.PippiPackTests.test_remote_download_selection_only_names_authorization_hold"),
      ("PIPPI-PORTABILITY-01","Project pack requirements remain visible and missing optional capabilities cannot weaken them.","test_pippi_packs.PippiPackTests.test_offline_semcrys_does_not_launder_memory_vault_binding"),
      ("PIPPI-INVENTORY-01","Pack inventory mutation requires the exact predecessor head and verification evidence.","test_pippi_packs.PippiPackTests.test_pack_store_uses_exact_inventory_head"),
      ("PIPPI-INSTALLER-01","The rainbow-sun native installer has a headless correspondence and no-console VBS entrypoints.","test_pippi_packs.PippiPackTests.test_installer_probe_and_no_console_launchers")])
    definitions.extend([
      ("PIPPI-COURT-01","The operator court supplies the exact turn opening to report validation and mutates the bound opening-root field.","test_pippi_operator_kit.PippiOperatorKitTests.test_runner_binds_turn_report_to_opening"),
      ("PIPPI-PLAN-PURITY-01","Read-only pack inventory, planning, portability and installer probes leave no persistent inventory.","test_pippi_packs.PippiPackTests.test_read_only_pack_commands_do_not_initialize_inventory"),
      ("PIPPI-WORK-SELECTION-01","Active r016-r018 work selections conform to the canonical subject-bound no-effect protocol while exact preimages remain frozen.","test_pippi_work_selection_normalization.PippiWorkSelectionNormalizationTests.test_normalized_records_conform_and_preimages_are_preserved"),
      ("PIPPI-REVIEW-TRANSPORT-01","The review transport carries every release artifact, qualification input, operator kit and disposition needed for replay.","test_pippi_release_packaging.PippiReleasePackagingTests.test_complete_review_transport_inputs_are_declared"),
      ("PIPPI-RELEASE-VERIFIER-01","The SDK-bundled standalone verifier accepts every canonical archive for the current engineering revision.","test_release_artifacts.ReleaseArtifactTests.test_sdk_bundled_verifier_accepts_all_canonical_release_archives")])
    definitions.extend([
      ("R19-01","Qualification launched from an unrelated directory roots resource access in the source and allocates scratch space per run.","test_public_release_qualification.PublicReleaseQualificationTests.test_replay_is_rooted_and_run_isolated"),
      ("PIPPI-ISOLATED-TOOLS-01","The interface and work-selection checks run under Python isolated mode from an unrelated directory.","test_public_release_qualification.PublicReleaseQualificationTests.test_program_checks_run_under_isolated_mode_from_unrelated_directory"),
      ("PIPPI-COURT-AUTHORSHIP-01","The court and kit consistently identify builder authorship and separate operator execution.","test_pippi_operator_kit.PippiOperatorKitTests.test_runner_and_manifest_state_authorship_consistently"),
      ("PIPPI-VOCAB-CLOSURE-01","The public vocabulary work selection names a qualification receipt test while preserving its exact predecessor records.","test_public_vocabulary.PublicVocabularyTests.test_deterministic_regeneration_and_semantic_lint"),
      ("PIPPI-R019-CUSTODY-01","The r019 review and 31-case user-run builder-authored court are carried with exact non-independent provenance.","test_pippi_r019_custody.PippiR019CustodyTests.test_review_and_operator_return_are_exact_and_provenanced")])
    for case_id,statement,test_id in definitions:
        req=rooted({"schema":"mosaic.ucm.pippi-adaptive-requirement.v0.1","requirement_id":case_id,
            "statement":statement,"source_denominator_root":denominator["source_denominator_root"],**BOUNDARY},"requirement_root")
        case=build_acceptance_case(acceptance_case_id=case_id,
            subject_root=denominator["source_denominator_root"],requirement_root=req["requirement_root"],
            verification_surface=test_id,expected_result_code="PASS",current_status="UNMET")
        selection=build_work_selection(acceptance_case=case,work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id=test_id,infrastructure_block=None)
        requirements.append(req);cases.append(case);selections.append(selection)
    inventory=rooted({"schema":"mosaic.ucm.pippi-adaptive-program.v0.2","revision":"r020",
        "source_denominator_root":denominator["source_denominator_root"],
        "requirement_roots":[r["requirement_root"] for r in requirements],
        "acceptance_case_roots":[r["acceptance_case_root"] for r in cases],
        "work_selection_roots":[r["work_selection_root"] for r in selections],
        "qualification_status":"TARGETED_CONSTRUCTION",**BOUNDARY},"program_root")
    result={"SOURCE-DENOMINATOR.json":denominator,"PROGRAM.json":inventory}
    for index,(req,case,selection) in enumerate(zip(requirements,cases,selections),1):
        result[f"{index:02d}-{req['requirement_id']}-REQUIREMENT.json"]=req
        result[f"{index:02d}-{req['requirement_id']}-ACCEPTANCE-CASE.json"]=case
        result[f"{index:02d}-{req['requirement_id']}-WORK-SELECTION.json"]=selection
    return result


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument("--write",action="store_true");g.add_argument("--check",action="store_true");a=p.parse_args()
    registry=json.loads((ROOT/"spec/FROZEN-PROGRAM-REGISTRY.json").read_text(encoding="utf-8"))
    if a.write:
        print(json.dumps({"status":"REFUSED","reason_code":"FROZEN_PROGRAM_MUTATION_REFUSED",
            "directory":"program/pippi-adaptive-r020",**BOUNDARY},sort_keys=True));return 3
    frozen=check_frozen_program_directory(source_root=ROOT,registry=registry,
        directory="program/pippi-adaptive-r020")
    print(json.dumps({**frozen,"program_records":62},sort_keys=True));return 0
    # Historical records are never regenerated from current source.
    mismatches=[]
    for name,value in records().items():
        path=OUT/name;raw=canonical(value)+b"\n"
        if a.write:write(path,value)
        elif not path.is_file() or path.read_bytes()!=raw:mismatches.append(name)
    print(json.dumps({"status":"PASS" if not mismatches else "REFUSED","mismatches":mismatches,
        "program_records":len(records()),**BOUNDARY},sort_keys=True));return 0 if not mismatches else 3


if __name__=="__main__":raise SystemExit(main())
