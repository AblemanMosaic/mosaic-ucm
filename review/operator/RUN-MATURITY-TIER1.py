"""Operator-owned consolidated Tier 1 court.

This file is packaged by the builder but is not executed during construction.
It runs only against an exact qualification-source archive in a disposable
workspace and emits a deterministic evidence archive.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rooted(value: dict, field: str) -> dict:
    body = {key: deepcopy(raw) for key, raw in value.items() if key != field}
    return {**body, field: digest(canonical(body))}


def evidence_zip(payloads: dict[str, bytes]) -> bytes:
    rows = [{"path": name, "bytes": len(raw), "sha256": digest(raw)}
            for name, raw in sorted(payloads.items())]
    body = {"schema": "mosaic.ucm.maturity-tier1-evidence.v0.1",
            "artifact_role": "UCM_MATURITY_TIER1_EVIDENCE", "files": rows,
            **BOUNDARY}
    all_files = {**payloads, "MANIFEST.json": canonical(
        {**body, "manifest_root": digest(canonical(body))})}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--expected-subject-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.subject.read_bytes()
    if digest(raw) != args.expected_subject_sha256:
        raise SystemExit("TIER1_SUBJECT_PIN_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="ucm-maturity-tier1-") as folder:
        staged = Path(folder) / "subject"; staged.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.extractall(staged)
        sys.path[:0] = [str(staged), str(staged / "src"), str(staged / "tests")]

        from uclop.canonical import canonical_bytes, root
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from ucm.agent_adapter import AgentToolAdapter
        from ucm.architecture import check_architecture_change, validate_architecture_contract
        from ucm.authoring import inspect_policy_pack_composition
        from ucm.contract_workbench import (classify_contract_compatibility,
            doctor_contract, explain_selection, initialize_realization_contract)
        from ucm.behavioral_harness import (
            build_harness_contract, build_transition_receipt)
        from ucm.constitutional_launcher import (
            build_launch_contract, build_launch_observation, derive_launch_state)
        from ucm.development_standards import (
            build_standards_catalog, evaluate_standards)
        from ucm.evaluation import aggregate_study_results, build_run_roster
        from ucm.evidence import build_evidence_envelope, validate_evidence_envelope
        from ucm.evidence_adapters import (build_tool_evidence_subject,
                                            validate_tool_evidence_subject)
        from ucm.evolution import negotiate_feature_level, validate_feature_descriptor
        from ucm.governance import (build_external_approval,
                                    external_approval_signing_body,
                                    inspect_environment, verify_external_approval)
        from ucm.journal import GENESIS, build_event
        from ucm.journal_tools import (build_inclusion_proof, diff_event_chains,
                                       summarize_events, verify_inclusion_proof)
        from ucm.lifecycle import build_lifecycle_receipt
        from ucm.profiles import profile_allows_surface, profile_registry
        from ucm.pippi import (
            build_human_projection, build_model_draft, build_pippi_context,
            build_pippi_decision, build_turn_envelope,
            validate_human_projection, validate_model_draft,
            validate_pippi_context, validate_pippi_decision,
            validate_turn_envelope)
        from ucm.semantic_passage import (
            build_semantic_passage, resolve_semantic_passage,
            validate_semantic_passage)
        from ucm.system import capability_registry
        from uclop.maturity_mosaicos import (prepare_m1_from_m0_archive,
                                              verify_m1_preparation)

        def load(name: str):
            return json.loads((staged / name).read_text(encoding="utf-8"))

        cases = []

        def record(identifier: str, fn) -> None:
            try:
                passed, diagnostic = fn()
                status = "PASS" if passed else "FAIL"
            except Exception as error:
                status, diagnostic = "UNTYPED_ERROR", type(error).__name__ + ":" + str(error)
            row = {"id": identifier, "status": status, "diagnostic": diagnostic}
            cases.append(row)
            print(f"[case {len(cases):03d}] {identifier}: {status}", flush=True)
            print(f"[summary] completed={len(cases)} failed={sum(r['status'] != 'PASS' for r in cases)}",
                  flush=True)

        def passes(fn, predicate=lambda value: True):
            value = fn()
            return bool(predicate(value)), "EXPECTED_RESULT" if predicate(value) else "UNEXPECTED_RESULT"

        def refuses(fn, code: str):
            try:
                fn()
            except Exception as error:
                return (str(error) == code or code in str(error)), str(error)
            return False, "ACCEPTED_UNEXPECTEDLY"

        def reroot_architecture_candidate(candidate: dict) -> dict:
            """Re-seal a v0.2 candidate after a semantic mutation.

            Tier 1 cases must reach the intended architecture-policy check.  A
            changed subject or path also changes the inner change root and both
            evidence bindings, so only refreshing ``candidate_root`` would test
            malformed custody rather than the requested semantic condition.
            """
            item = deepcopy(candidate)
            change_body = {key: deepcopy(item[key]) for key in (
                "schema", "subject_root", "changed_paths",
                "existing_abstractions_used", "introduced_abstractions",
                "supersession_roots")}
            item["change_root"] = root(change_body)
            for field in ("test_evidence_receipts", "proof_evidence_receipts"):
                receipts = []
                for receipt in item[field]:
                    rebound = deepcopy(receipt)
                    rebound["subject_root"] = item["subject_root"]
                    rebound["change_root"] = item["change_root"]
                    receipts.append(rooted(rebound, "receipt_root"))
                item[field] = receipts
            return rooted(item, "candidate_root")

        contract = load("examples/architecture/reference-data-client/ARCHITECTURE-CONTRACT.json")
        good_change = load("examples/architecture/reference-data-client/CONFORMING-CHANGE.json")
        drift = load("examples/architecture/reference-data-client/DRIFTING-CHANGE.json")
        protocol = load("evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json")
        descriptor = {"schema": "mosaic.ucm.feature-descriptor.v0.1",
                      "minimum_feature_level": 1, "maximum_feature_level": 1,
                      "required_features": ["CANONICAL_JSON_V1"], "extensions": {}}

        record("CONTROL-PROFILE-REGISTRY", lambda: passes(profile_registry,
               lambda value: value["authority_effect"] == "NONE"))
        record("PROFILE-VERIFY-ONLY-OPERATIONAL-REFUSAL", lambda: passes(
               lambda: profile_allows_surface("VERIFY_ONLY", "PREPARE_OPERATIONAL_GATEWAY"),
               lambda value: value["status"] == "REFUSED_PROFILE_SURFACE"))
        record("PROFILE-UNKNOWN", lambda: refuses(
               lambda: profile_allows_surface("UNKNOWN", "ORIENT"), "UCM_PROFILE_UNKNOWN"))
        record("PROFILE-UNKNOWN-SURFACE", lambda: refuses(
               lambda: profile_allows_surface("AUTHORING", "NOT_A_SURFACE"),
               "UCM_PROFILE_SURFACE_UNKNOWN"))
        record("CONTROL-FEATURE-DESCRIPTOR", lambda: passes(
               lambda: validate_feature_descriptor(descriptor)))
        record("FEATURE-LEVEL-TOO-NEW", lambda: passes(
               lambda: negotiate_feature_level(descriptor, tool_feature_level=2),
               lambda value: value["status"].startswith("REFUSED")))
        changed_descriptor = deepcopy(descriptor); changed_descriptor["maximum_feature_level"] = 0
        record("FEATURE-RANGE-INVALID", lambda: refuses(
               lambda: validate_feature_descriptor(changed_descriptor), "UCM_FEATURE_RANGE_INVALID"))

        record("CONTROL-ARCHITECTURE-CONTRACT", lambda: passes(
               lambda: validate_architecture_contract(contract)))
        record("CONTROL-ARCHITECTURE-CONFORMING", lambda: passes(
               lambda: check_architecture_change(contract, good_change),
               lambda value: value["status"] == "PASS_ARCHITECTURE_FIDELITY"))
        record("ARCHITECTURE-DRIFT", lambda: passes(
               lambda: check_architecture_change(contract, drift),
               lambda value: value["status"] == "REFUSED_ARCHITECTURE_DRIFT"))
        for identifier, field, value, code in [
            ("ARCHITECTURE-WRONG-SUBJECT", "subject_root", "4" * 64,
             "UCM_ARCHITECTURE_SUBJECT_MISMATCH"),
            ("ARCHITECTURE-MISSING-TEST", "test_evidence_receipts", [],
             "UCM_ARCHITECTURE_TEST_EVIDENCE_MISSING"),
            ("ARCHITECTURE-MISSING-PROOF", "proof_evidence_receipts", [],
             "UCM_ARCHITECTURE_PROOF_EVIDENCE_MISSING"),
            ("ARCHITECTURE-PROTECTED-PATH", "changed_paths", ["src/identity.py"],
             "UCM_ARCHITECTURE_PROTECTED_PATH_CHANGED"),
        ]:
            mutation = deepcopy(good_change); mutation[field] = value
            mutation = reroot_architecture_candidate(mutation)
            record(identifier, lambda mutation=mutation, code=code: passes(
                   lambda: check_architecture_change(contract, mutation),
                   lambda result: code in result["reason_codes"]))
        broken_contract = deepcopy(contract); broken_contract["impact_paths"] = ["src/other.py"]
        record("ARCHITECTURE-SELF-ROOT-MISMATCH", lambda: refuses(
               lambda: validate_architecture_contract(broken_contract),
               "UCM_ARCHITECTURE_ROOT_INVALID"))

        record("CONTROL-LIFECYCLE-DRAFT", lambda: passes(lambda: build_lifecycle_receipt(
               contract_root="1" * 64, from_state="NONE", to_state="DRAFT",
               predecessor_receipt_root="0" * 64, evidence_roots=[])))
        record("LIFECYCLE-SKIP", lambda: refuses(lambda: build_lifecycle_receipt(
               contract_root="1" * 64, from_state="DRAFT", to_state="FROZEN",
               predecessor_receipt_root="2" * 64, evidence_roots=["3" * 64]),
               "UCM_LIFECYCLE_TRANSITION_REFUSED"))
        record("LIFECYCLE-EVIDENCE-MISSING", lambda: refuses(lambda: build_lifecycle_receipt(
               contract_root="1" * 64, from_state="DRAFT", to_state="VALIDATED",
               predecessor_receipt_root="2" * 64, evidence_roots=[]),
               "UCM_LIFECYCLE_EVIDENCE_REQUIRED"))

        evidence = build_evidence_envelope(evidence_id="E1", subject_root="1" * 64,
            policy_root="2" * 64, issuer_root="3" * 64, verifier_root="4" * 64,
            environment_root="5" * 64, result_root="6" * 64, result_status="PASS",
            issued_at=100, not_before=90, not_after=110)
        record("CONTROL-EVIDENCE", lambda: passes(lambda: validate_evidence_envelope(
               evidence, expected_subject_root="1" * 64, expected_policy_root="2" * 64, now=100)))
        record("EVIDENCE-WRONG-SUBJECT", lambda: refuses(lambda: validate_evidence_envelope(
               evidence, expected_subject_root="7" * 64, expected_policy_root="2" * 64, now=100),
               "UCM_EVIDENCE_SUBJECT_MISMATCH"))
        record("EVIDENCE-WRONG-POLICY", lambda: refuses(lambda: validate_evidence_envelope(
               evidence, expected_subject_root="1" * 64, expected_policy_root="7" * 64, now=100),
               "UCM_EVIDENCE_POLICY_MISMATCH"))
        record("EVIDENCE-NOT-YET-VALID", lambda: refuses(lambda: validate_evidence_envelope(
               evidence, expected_subject_root="1" * 64, expected_policy_root="2" * 64, now=80),
               "UCM_EVIDENCE_NOT_YET_VALID"))
        record("EVIDENCE-EXPIRED", lambda: refuses(lambda: validate_evidence_envelope(
               evidence, expected_subject_root="1" * 64, expected_policy_root="2" * 64, now=120),
               "UCM_EVIDENCE_EXPIRED"))
        broken_evidence = deepcopy(evidence); broken_evidence["result_status"] = "FAIL"
        record("EVIDENCE-SELF-ROOT-MISMATCH", lambda: refuses(lambda: validate_evidence_envelope(
               broken_evidence, expected_subject_root="1" * 64,
               expected_policy_root="2" * 64, now=100), "UCM_EVIDENCE_ENVELOPE_INVALID"))

        actor = {"kind": "SYSTEM", "mosaic_id": None, "session_id": None}
        first = build_event(sequence=1, predecessor=GENESIS, event_id="E1",
                            event_type="CAMPAIGN_CREATED", actor=actor,
                            payload={"operation_id": "OP1"})
        second = build_event(sequence=2, predecessor=first["event_root"], event_id="E2",
                             event_type="BASELINE_BOUND", actor=actor,
                             payload={"operation_id": "OP1"})
        chain = [first, second]
        record("CONTROL-JOURNAL", lambda: passes(lambda: summarize_events(chain),
               lambda value: value["sequence"] == 2))
        record("JOURNAL-DELETE-PREFIX", lambda: refuses(
               lambda: summarize_events(chain[1:]), "JOURNAL_EVENT_INVALID"))
        record("JOURNAL-REORDER", lambda: refuses(
               lambda: summarize_events(list(reversed(chain))), "JOURNAL_EVENT_INVALID"))
        changed_event = deepcopy(second); changed_event["payload"]["operation_id"] = "OP2"
        record("JOURNAL-RESEALED-EVENT-ABSENT", lambda: refuses(
               lambda: summarize_events([first, changed_event]), "JOURNAL_EVENT_INVALID"))
        proof = build_inclusion_proof(chain, event_root=first["event_root"])
        record("CONTROL-JOURNAL-INCLUSION", lambda: passes(lambda: verify_inclusion_proof(proof)))
        broken_proof = deepcopy(proof); broken_proof["journal_head"] = "9" * 64
        record("JOURNAL-INCLUSION-HEAD-SWAP", lambda: refuses(
               lambda: verify_inclusion_proof(broken_proof), "JOURNAL_PROOF_ROOT_INVALID"))
        fork = build_event(sequence=2, predecessor=first["event_root"], event_id="E3",
                           event_type="BASELINE_BOUND", actor=actor,
                           payload={"operation_id": "OP2"})
        record("JOURNAL-FORK-DETECTED", lambda: passes(
               lambda: diff_event_chains(chain, [first, fork]),
               lambda value: value["relation"] == "DIVERGED"))

        scaffold = initialize_realization_contract(
            contract_id="TIER1.SCAFFOLD", subject_id="TIER1.SUBJECT",
            subject_root="1" * 64, description="Tier 1 authoring scaffold")
        record("CONTROL-CONTRACT-SCAFFOLD", lambda: passes(
               lambda: doctor_contract("realization", scaffold),
               lambda value: value["readiness"] == "PASS_AUTHORING_ONLY"))
        successor = deepcopy(scaffold); successor["description"] = "Changed"
        successor = rooted(successor, "root")
        record("CONTRACT-MIGRATION-UNDECLARED", lambda: passes(
               lambda: classify_contract_compatibility(
                   predecessor=scaffold, successor=successor,
                   known_roots=[root(scaffold)]),
               lambda value: value["status"] == "NEEDS_DECLARED_MIGRATION"))
        record("SELECTION-HARD-CONSTRAINT-EXPLAINED", lambda: passes(
               lambda: explain_selection(scaffold, [{"PROFILE": "BOUND"}]),
               lambda value: value["status"] == "REFUSED_NO_SELECTION"
                   and value["ordered_evaluations"][0]["failed_constraints"]))
        record("ENVIRONMENT-UNKNOWN-STRICT", lambda: passes(
               lambda: inspect_environment({"UCM_UNDECLARED_OVERRIDE": "1"}, strict=True),
               lambda value: value["status"] == "REFUSED_ENVIRONMENT"))
        record("AGENT-SIDECAR-REGISTRY-SWAP", lambda: refuses(
               lambda: AgentToolAdapter(
                   profile_id="VERIFY_ONLY", capability_registry_root="9" * 64,
                   profile_registry_root=profile_registry()["profile_registry_root"],
                   dispatcher=lambda request: request),
               "UCM_AGENT_CAPABILITY_REGISTRY_MISMATCH"))

        pippi_context = build_pippi_context(
            session_root="1" * 64, subject_root="2" * 64,
            policy_roots=["3" * 64], capability_registry_root="4" * 64,
            profile_root="5" * 64, jurisdiction_root="6" * 64,
            retained_context_roots=[],
            mediated_channels=["MODEL_DRAFT", "MODEL_INPUT", "TOOL_PROPOSAL",
                               "VISIBLE_OUTPUT"])
        pippi_draft = build_model_draft(
            turn_id="TIER1.PIPPI.1", context=pippi_context,
            text="Write only after a declared contract authorizes the effect.",
            proposals=[{"proposal_id": "P1", "kind": "TOOL_CALL",
                        "payload_root": "7" * 64,
                        "effect_class": "WRITE_WORKSPACE"}])
        pippi_decision = build_pippi_decision(
            draft=pippi_draft, policy_evaluation_roots=["8" * 64],
            proposal_dispositions=[{
                "proposal_id": "P1", "declared": False, "effectful": True,
                "decision": "HELD", "reason_codes": ["CONSTITUTIONAL_GAP"],
                "contract_root": None}], semantic_resolution_root=None,
            semantic_status="NOT_REQUIRED")
        pippi_projection = build_human_projection(
            draft=pippi_draft, decision=pippi_decision, view="READING")
        pippi_turn = build_turn_envelope(
            sequence=1, previous_turn_root=None, context=pippi_context,
            draft=pippi_draft, decision=pippi_decision,
            projection=pippi_projection, tool_proposal_roots=["9" * 64],
            dispatch_receipt_roots=[], tool_result_roots=[])
        record("CONTROL-PIPPI-CONTEXT", lambda: passes(
               lambda: validate_pippi_context(pippi_context)))
        changed_context = deepcopy(pippi_context)
        changed_context["subject_root"] = "a" * 64
        record("PIPPI-CONTEXT-RESEALED-SUBJECT-SWAP", lambda: refuses(
               lambda: validate_pippi_context(changed_context),
               "PIPPI_CONTEXT_INVALID"))
        changed_draft = deepcopy(pippi_draft)
        changed_draft["text"] = "Different visible text."
        changed_draft = rooted(changed_draft, "draft_root")
        record("PIPPI-DRAFT-RESEALED-TEXT-SWAP", lambda: refuses(
               lambda: validate_model_draft(changed_draft),
               "PIPPI_DRAFT_TEXT_HASH_INVALID"))
        record("PIPPI-UNDECLARED-EFFECT-LAUNDER", lambda: refuses(
               lambda: build_pippi_decision(
                   draft=pippi_draft, policy_evaluation_roots=["8" * 64],
                   proposal_dispositions=[{
                       "proposal_id": "P1", "declared": False,
                       "effectful": True, "decision": "PASS",
                       "reason_codes": ["CALLER_ASSERTED"],
                       "contract_root": None}], semantic_resolution_root=None,
                   semantic_status="NOT_REQUIRED"),
               "PIPPI_UNDECLARED_EFFECT_NOT_HELD"))
        missing_disposition = deepcopy(pippi_decision)
        missing_disposition["proposal_dispositions"] = []
        missing_disposition = rooted(missing_disposition, "decision_root")
        record("PIPPI-DISPOSITION-DENOMINATOR-SHRINK", lambda: refuses(
               lambda: validate_pippi_decision(
                   missing_disposition, draft=pippi_draft),
               "PIPPI_DECISION_DRAFT_BINDING_INVALID"))
        changed_projection = deepcopy(pippi_projection)
        changed_projection["display_text"] = "Changed after mediation."
        changed_projection = rooted(changed_projection, "projection_root")
        record("PIPPI-PROJECTION-TEXT-SWAP", lambda: refuses(
               lambda: validate_human_projection(
                   changed_projection, draft=pippi_draft,
                   decision=pippi_decision), "PIPPI_PROJECTION_INVALID"))
        changed_turn = deepcopy(pippi_turn)
        changed_turn["draft_root"] = "b" * 64
        changed_turn = rooted(changed_turn, "turn_root")
        record("PIPPI-TURN-CROSS-DRAFT-SWAP", lambda: refuses(
               lambda: validate_turn_envelope(
                   changed_turn, context=pippi_context, draft=pippi_draft,
                   decision=pippi_decision, projection=pippi_projection),
               "PIPPI_TURN_INVALID"))

        semantic_text = "Stage the repair without dispatch."
        semantic_start = semantic_text.encode("utf-8").index(b"Stage")
        semantic_passage = build_semantic_passage(
            passage_id="TIER1.SEMANTIC.1", text=semantic_text,
            context_root="c" * 64, provider_mode="REFERENCE_UNBOUND",
            provider_root=None, spans=[{
                "span_id": "SPAN.STAGE", "byte_start": semantic_start,
                "byte_end": semantic_start + 5, "exact_text": "Stage",
                "requirement": "REQUIRED", "candidates": [{
                    "vocabulary_root": "d" * 64, "term_id": 17,
                    "sense_id": 1, "bound_term": "prepare-without-dispatch"}],
                "citation_roots": ["e" * 64]}])
        record("CONTROL-SEMANTIC-PASSAGE", lambda: passes(
               lambda: validate_semantic_passage(semantic_passage)))
        changed_passage = deepcopy(semantic_passage)
        changed_passage["spans"][0]["exact_text"] = "stage"
        changed_passage = rooted(changed_passage, "passage_root")
        record("SEMANTIC-SPAN-TEXT-SWAP", lambda: refuses(
               lambda: validate_semantic_passage(changed_passage),
               "SEMANTIC_SPAN_TEXT_MISMATCH"))
        record("SEMANTIC-SELECTION-WRONG-CANDIDATE", lambda: refuses(
               lambda: resolve_semantic_passage(
                   passage=semantic_passage, selections=[{
                       "span_id": "SPAN.STAGE", "vocabulary_root": "d" * 64,
                       "term_id": 17, "sense_id": 99}],
                   clarification_roots=[]),
               "SEMANTIC_SELECTION_NOT_CANDIDATE"))

        standards_subject = "f" * 64
        standards = build_standards_catalog(
            catalog_id="TIER1.STANDARDS", policy_root="1" * 64,
            obligations=[{
                "obligation_id": "VISIBLE.PROGRESS", "statement": "Show progress.",
                "class": "MANDATORY", "triggers": [],
                "check_ids": ["CHECK.PROGRESS"], "evidence_required": True}])
        record("STANDARDS-CHECK-SUBJECT-SWAP", lambda: refuses(
               lambda: evaluate_standards(
                   catalog=standards, subject_root=standards_subject,
                   active_triggers=[], check_results=[{
                       "check_id": "CHECK.PROGRESS", "role": "TARGETED",
                       "subject_root": "0" * 64, "status": "PASS",
                       "evidence_root": "2" * 64, "witness_root": "3" * 64}]),
               "STANDARDS_CHECK_SUBJECT_MISMATCH"))

        launch_contract = build_launch_contract(
            launch_id="TIER1.LAUNCH", application_id="REFERENCE_APP",
            subject_root="1" * 64, executable_root="2" * 64,
            argument_root="3" * 64, environment_policy_root="4" * 64,
            readiness_probe_id="READY.V1", readiness_contract_root="5" * 64,
            timeout_ms=30000, executor_binding_root="6" * 64,
            branding={"display_name": "Reference App",
                      "splash_asset_root": "7" * 64,
                      "phase_labels": {"PREPARED": "Preparing", "READY": "Ready"}})
        record("LAUNCH-READY-WITHOUT-EVIDENCE", lambda: refuses(
               lambda: build_launch_observation(
                   contract=launch_contract, sequence=2, state="READY",
                   previous_observation_root="f" * 64,
                   executor_receipt_root="8" * 64, g1_root="9" * 64,
                   g2_root="a" * 64, g3_root="b" * 64,
                   readiness_evidence_root=None, reason_codes=[]),
               "LAUNCH_READINESS_EVIDENCE_INVALID"))
        prepared_launch = build_launch_observation(
            contract=launch_contract, sequence=1, state="PREPARED",
            previous_observation_root=None, executor_receipt_root="8" * 64,
            g1_root="9" * 64, g2_root=None, g3_root=None,
            readiness_evidence_root=None, reason_codes=[])
        skipped_launch = build_launch_observation(
            contract=launch_contract, sequence=2, state="READY",
            previous_observation_root=prepared_launch["observation_root"],
            executor_receipt_root="a" * 64, g1_root="9" * 64,
            g2_root=None, g3_root=None,
            readiness_evidence_root="d" * 64, reason_codes=[])
        record("LAUNCH-TRANSITION-SKIP", lambda: refuses(
               lambda: derive_launch_state(
                   contract=launch_contract,
                   observations=[prepared_launch, skipped_launch]),
               "LAUNCH_TRANSITION_INVALID"))

        harness_contract = build_harness_contract(
            harness_id="TIER1.HARNESS", subject_root="1" * 64,
            state_adapter_root="2" * 64, action_generator_root="3" * 64,
            executor_binding_root="4" * 64,
            required_controls=["RNG", "TIME"],
            allowed_write_paths=["output/result.json"],
            scenario_ids=["CASE.1"])
        record("HARNESS-UNDECLARED-WRITE-PASS", lambda: refuses(
               lambda: build_transition_receipt(
                   contract=harness_contract, scenario_id="CASE.1",
                   pre_state_root="5" * 64, action_root="6" * 64,
                   post_state_root="7" * 64,
                   observed_controls=["RNG", "TIME"],
                   observed_write_paths=["outside/result.json"],
                   executor_receipt_root="8" * 64, status="PASS",
                   reason_codes=[]), "HARNESS_PASS_CLAIM_INVALID"))

        private = Ed25519PrivateKey.from_private_bytes(b"\x51" * 32)
        public_hex = private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        approval_body = external_approval_signing_body(
            approval_id="TIER1.APPROVAL", operation_root="3" * 64,
            approver_identity_root="4" * 64,
            approver_public_key_hex=public_hex, policy_root="5" * 64,
            decision="APPROVE", issued_at=10, not_after=20)
        approval = build_external_approval(
            approval_id="TIER1.APPROVAL", operation_root="3" * 64,
            approver_identity_root="4" * 64,
            approver_public_key_hex=public_hex, policy_root="5" * 64,
            decision="APPROVE", issued_at=10, not_after=20,
            signature_hex=private.sign(canonical_bytes(approval_body)).hex())
        record("CONTROL-EXTERNAL-APPROVAL", lambda: passes(
               lambda: verify_external_approval(
                   approval, expected_operation_root="3" * 64,
                   expected_policy_root="5" * 64, now=15)))
        wrong_signature = deepcopy(approval)
        wrong_signature["signature_hex"] = "0" * 128
        wrong_signature = rooted(wrong_signature, "approval_root")
        record("APPROVAL-RESEALED-WRONG-SIGNATURE", lambda: refuses(
               lambda: verify_external_approval(
                   wrong_signature, expected_operation_root="3" * 64,
                   expected_policy_root="5" * 64, now=15),
               "UCM_APPROVAL_SIGNATURE_INVALID"))
        record("APPROVAL-WRONG-OPERATION", lambda: refuses(
               lambda: verify_external_approval(
                   approval, expected_operation_root="6" * 64,
                   expected_policy_root="5" * 64, now=15),
               "UCM_APPROVAL_OPERATION_MISMATCH"))

        tool_evidence = build_tool_evidence_subject(
            tool="PYTEST", subject_root="1" * 64, invocation_root="2" * 64,
            output_root="3" * 64, environment_root="4" * 64,
            verifier_root="5" * 64, policy_root="6" * 64,
            issuer_root="7" * 64, exit_code=0, counts={"passed": 1},
            issued_at=10, not_after=20)
        record("CONTROL-EXTERNAL-TOOL-EVIDENCE", lambda: passes(
               lambda: validate_tool_evidence_subject(tool_evidence)))
        wrong_tool_evidence = deepcopy(tool_evidence)
        wrong_tool_evidence["tool_result"]["subject_root"] = "8" * 64
        wrong_tool_evidence = rooted(wrong_tool_evidence, "evidence_subject_root")
        record("TOOL-EVIDENCE-CROSS-SUBJECT", lambda: refuses(
               lambda: validate_tool_evidence_subject(wrong_tool_evidence),
               "UCM_TOOL_EVIDENCE_INVALID"))

        base_pack = load("policy-packs/NO_AUTHORITY-v0.1.json")
        conflicting_pack = deepcopy(base_pack)
        conflicting_pack["pack_id"] = "CONFLICTING_TIER1_PACK"
        conflicting_pack["requirements"][0]["statement"] = "Conflicting meaning"
        conflicting_pack = rooted(conflicting_pack, "pack_root")
        record("POLICY-PACK-CONFLICT", lambda: passes(
               lambda: inspect_policy_pack_composition([base_pack, conflicting_pack]),
               lambda value: value["status"] == "REFUSED_POLICY_CONFLICT"))

        roster = build_run_roster(protocol)
        arms = {row["arm_id"]: row for row in protocol["arms"]}
        context_body = {
            "schema": "mosaic.ucm.architecture-study-execution-context.v0.1",
            "study_root": protocol["study_root"], "model_id_root": "7" * 64,
            "model_settings_root": "6" * 64, "environment_root": "5" * 64,
            "toolchain_root": "4" * 64, "allowed_deviations": [],
            "status": "REGISTERED_BEFORE_KIT_ISSUANCE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED",
        }
        context_registration = {**context_body, "registration_root": root(context_body)}
        results = []
        for run in roster["runs"]:
            execution_context = {
                "environment_root": context_registration["environment_root"],
                "executor_session_root": f"{len(results) + 1:064x}",
                "model_id_root": context_registration["model_id_root"],
                "model_settings_root": context_registration["model_settings_root"],
                "toolchain_root": context_registration["toolchain_root"],
            }
            review_record_root = f"{len(results) + 101:064x}"
            scoring_context = {
                "review_record_root": review_record_root,
                "scorer_identity_root": "3" * 64,
                "scorer_session_root": f"{len(results) + 201:064x}",
                "scoring_rubric_root": protocol["review_policy"]["scoring_rubric_root"],
            }
            body = {"schema": "mosaic.ucm.architecture-study-run-result.v0.3",
                    "study_root": protocol["study_root"], "run_id": run["run_id"],
                    "task_root": run["task_root"], "arm_id": run["arm_id"],
                    "repetition": run["repetition"], **execution_context,
                    "execution_context_root": root(execution_context),
                    "human_oversight_policy_root": arms[run["arm_id"]]["human_oversight_policy_root"],
                    "output_root": "8" * 64, **scoring_context,
                    "scoring_context_root": root(scoring_context),
                    "review_record_root": review_record_root,
                    "follow_on_result_root": f"{len(results) + 301:064x}",
                    "context_registration_root": context_registration["registration_root"],
                    "metrics": {metric: 0 for metric in protocol["metrics"]},
                    "status": "COMPLETE"}
            results.append({**body, "result_root": root(body)})
        record("CONTROL-STUDY-DENOMINATOR", lambda: passes(
               lambda: aggregate_study_results(protocol, results, context_registration),
               lambda value: value["denominator"] == roster["denominator"]))
        record("STUDY-MISSING-RUN", lambda: refuses(
               lambda: aggregate_study_results(protocol, results[:-1], context_registration),
               "UCM_STUDY_DENOMINATOR_INCOMPLETE"))
        record("STUDY-DUPLICATE-RUN", lambda: refuses(
               lambda: aggregate_study_results(protocol, results[:-1] + [results[0]], context_registration),
               "UCM_STUDY_RUN_SET_MISMATCH"))
        wrong_oversight = deepcopy(results); wrong_oversight[0]["human_oversight_policy_root"] = "a" * 64
        wrong_oversight[0] = rooted(wrong_oversight[0], "result_root")
        record("STUDY-OVERSIGHT-SWAP", lambda: refuses(
               lambda: aggregate_study_results(protocol, wrong_oversight, context_registration),
               "UCM_STUDY_OVERSIGHT_MISMATCH"))

        m0_raw = (staged / "fixtures/mosaicos/MOSAICOS-M0-EVIDENCE.zip").read_bytes()
        m0_sha = digest(m0_raw)
        preparation = prepare_m1_from_m0_archive(
            m0_raw, expected_archive_sha256=m0_sha)
        record("CONTROL-MOSAICOS-M1-PREPARATION", lambda: passes(
               lambda: verify_m1_preparation(preparation, expected_root=preparation["root"])))
        record("MOSAICOS-WRONG-M0-PIN", lambda: refuses(
               lambda: prepare_m1_from_m0_archive(
                   m0_raw, expected_archive_sha256="0" * 64),
               "MOSAICOS_EXTERNAL_ARCHIVE_PIN_MISMATCH"))
        accepted_role = deepcopy(preparation)
        accepted_role["role_bindings"][0]["status"] = "BOUND"
        accepted_role = rooted(accepted_role, "root")
        record("MOSAICOS-ROLE-BINDING-LAUNDER", lambda: refuses(
               lambda: verify_m1_preparation(accepted_role, expected_root=accepted_role["root"]),
               "MOSAICOS_PREPARATION_BINDING_FORBIDDEN"))
        selected_target = deepcopy(preparation)
        selected_target["target_rx"]["selected_target"] = "PI"
        selected_target["target_rx"]["real_target_selected"] = True
        selected_target["target_rx"] = rooted(selected_target["target_rx"], "root")
        selected_target = rooted(selected_target, "root")
        record("MOSAICOS-TARGET-LAUNDER", lambda: refuses(
               lambda: verify_m1_preparation(selected_target, expected_root=selected_target["root"]),
               "MOSAICOS_PREPARATION_TARGET_OR_RX_FORBIDDEN"))

        failed = sum(row["status"] != "PASS" for row in cases)
        body = {"schema": "mosaic.ucm.maturity-tier1-result.v0.1",
                "subject_sha256": args.expected_subject_sha256,
                "case_count": len(cases), "cases": cases, "failed": failed,
                "status": "PASS" if failed == 0 else "HOLD_FOR_REPAIR", **BOUNDARY}
        result = {**body, "court_root": digest(canonical(body))}
        report = ("# UCM maturity Tier 1 operator evidence\n\n"
                  f"Status: `{result['status']}`  \nCases: {len(cases)}  \n"
                  "This is operator-run engineering evidence, not an authority grant or an "
                  "independent terminal verdict.\n").encode("utf-8")
        archive = evidence_zip({"TIER1-RESULT.json": canonical(result),
                                "REPORT.md": report,
                                "RUN-MATURITY-TIER1.py": Path(__file__).read_bytes()})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(archive)
        print(json.dumps({"status": result["status"], "cases": len(cases),
                          "failed": failed, "court_root": result["court_root"],
                          "evidence_sha256": digest(archive),
                          "evidence_zip": str(args.output), **BOUNDARY}, sort_keys=True), flush=True)
        return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
