from __future__ import annotations

import json
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from uclop.canonical import root
from ucm.authoring import (apply_policy_packs, lint_amcas_contract,
                           lint_realization_contract, semantic_contract_diff,
                           validate_policy_pack)
from ucm.architecture import (check_architecture_change,
                              validate_architecture_contract)
from ucm.capabilities import invoke
from ucm.diagnostics import doctor, smoke
from ucm.evaluation import (aggregate_study_results, build_run_roster,
                            validate_run_result, validate_study_protocol)
from ucm.evidence import build_evidence_envelope, validate_evidence_envelope
from ucm.evolution import (build_migration_receipt, negotiate_feature_level,
                           validate_feature_descriptor)
from ucm.journal import GENESIS, build_event
from ucm.journal_tools import (build_inclusion_proof, diff_event_chains,
                               query_events, summarize_events,
                               verify_inclusion_proof)
from ucm.lifecycle import build_lifecycle_receipt
from ucm.profiles import (profile_allows_surface, profile_registry,
                          validate_profile_selection)
from ucm.work_package import prepare_work_package
from uclop import project_intelligence as project_intelligence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from maturity_release_common import (build_profile_overlay, build_runtime_archive,
                                     build_review_source_archive, collect_payloads)
from build_maturity_operator_kit import build as build_operator_kit
from build_architecture_study_kits import build_run_kits


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ProductProfileTests(unittest.TestCase):

    def test_runtime_excludes_session_return_evidence(self):
        runtime = collect_payloads(review=False)
        review = collect_payloads(review=True)
        for prefix in ("integration/session-returns/",
                       "integration/successor-returns/",
                       "integration/audit-returns/",
                       "integration/repair-returns/"):
            self.assertFalse(any(name.startswith(prefix) for name in runtime))
            self.assertTrue(any(name.startswith(prefix) for name in review))
    def test_profiles_are_explicit_and_non_granting(self):
        registry = profile_registry()
        self.assertEqual([row["profile_id"] for row in registry["profiles"]],
                         ["AUTHORING", "COMPATIBILITY", "OPERATIONAL", "VERIFY_ONLY"])
        self.assertEqual(registry["authority_effect"], "NONE")
        selected = validate_profile_selection({
            "schema": "mosaic.ucm.product-profile-selection.v0.1",
            "profile_id": "VERIFY_ONLY",
            "capability_registry_root": registry["capability_registry_root"],
        })
        self.assertEqual(selected["definition"]["effect_ceiling"], "READ_ONLY")
        self.assertIn("VALIDATE_EXTERNAL_EVIDENCE",
                      selected["definition"]["surface_names"])
        self.assertNotIn("PREPARE_OPERATIONAL_GATEWAY",
                         selected["definition"]["surface_names"])
        self.assertEqual(profile_allows_surface(
            "OPERATIONAL", "PREPARE_OPERATIONAL_GATEWAY")["status"], "PASS_ALLOWED")
        self.assertEqual(profile_allows_surface(
            "VERIFY_ONLY", "PREPARE_OPERATIONAL_GATEWAY")["status"],
            "REFUSED_PROFILE_SURFACE")
        self.assertEqual(profile_allows_surface(
            "COMPATIBILITY", "DERIVE_STAGE_I4_ELIGIBILITY")["status"],
            "PASS_ALLOWED")
        self.assertEqual(profile_allows_surface(
            "AUTHORING", "DERIVE_STAGE_I4_ELIGIBILITY")["status"],
            "REFUSED_PROFILE_SURFACE")

    def test_profile_registry_is_invokable(self):
        request = {"schema": "mosaic.ucm.request.v0.1",
                   "surface": "DISCOVER_PRODUCT_PROFILES", "payload": {},
                   "request_id": "profiles"}
        self.assertEqual(invoke(request)["result"]["schema"],
                         "mosaic.ucm.product-profile-registry.v0.1")

    def test_invocation_profile_is_enforced(self):
        registry = profile_registry()
        request = {"schema": "mosaic.ucm.request.v0.2",
                   "surface": "DISCOVER_PRODUCT_PROFILES", "payload": {},
                   "request_id": "profiles-v2",
                   "profile_selection": {
                       "schema": "mosaic.ucm.product-profile-selection.v0.1",
                       "profile_id": "VERIFY_ONLY",
                       "capability_registry_root": registry["capability_registry_root"],
                   }}
        response = invoke(request)
        self.assertEqual(response["profile_id"], "VERIFY_ONLY")
        self.assertEqual(response["profile_selection_root"],
                         validate_profile_selection(request["profile_selection"])[
                             "profile_selection_root"])
        refused = {**request, "surface": "PREPARE_OPERATIONAL_GATEWAY",
                   "request_id": "profile-refusal", "payload": {}}
        with self.assertRaisesRegex(ValueError, "UCM_PROFILE_SURFACE_REFUSED"):
            invoke(refused)

    def test_checked_in_profile_manifests_equal_runtime_registry(self):
        registry = load("spec/product-profiles/PROFILE-REGISTRY.json")
        self.assertEqual(registry, profile_registry())
        for profile in registry["profiles"]:
            selection = load(
                f"spec/product-profiles/{profile['profile_id']}-PROFILE.json")
            self.assertEqual(selection["definition"]["surface_names"],
                             profile["surface_names"])
            self.assertEqual(selection["definition"]["surface_set_root"],
                             profile["surface_set_root"])


class EvolutionTests(unittest.TestCase):
    def descriptor(self):
        return {"schema": "mosaic.ucm.feature-descriptor.v0.1",
                "minimum_feature_level": 1, "maximum_feature_level": 1,
                "required_features": ["CANONICAL_JSON_V1"],
                "extensions": {"org.ableman.example": {"mode": "INFORMATION_ONLY"}}}

    def test_feature_negotiation(self):
        self.assertEqual(validate_feature_descriptor(self.descriptor()), self.descriptor())
        self.assertEqual(negotiate_feature_level(self.descriptor())["status"], "PASS_COMPATIBLE")
        self.assertEqual(negotiate_feature_level(self.descriptor(), tool_feature_level=2)["status"],
                         "REFUSED_FEATURE_LEVEL")

    def test_migration_receipt_is_non_ratifying(self):
        receipt = build_migration_receipt(predecessor_root="1" * 64,
            successor_root="2" * 64, migration_id="M1",
            semantic_changes=["ADD_LINT"], preserved_invariants=["AUTHORITY_NONE"])
        self.assertEqual(receipt["status"], "RECORDED_NOT_RATIFIED")
        self.assertIn("NOT_ADOPTION", receipt["non_claims"])

    def test_contract_lifecycle_is_forward_only_and_evidence_bound(self):
        draft = build_lifecycle_receipt(contract_root="1" * 64,
            from_state="NONE", to_state="DRAFT", predecessor_receipt_root="0" * 64,
            evidence_roots=[])
        validated = build_lifecycle_receipt(contract_root="1" * 64,
            from_state="DRAFT", to_state="VALIDATED",
            predecessor_receipt_root=draft["lifecycle_receipt_root"],
            evidence_roots=["2" * 64])
        self.assertEqual(validated["status"], "RECORDED_NOT_RATIFIED")
        with self.assertRaisesRegex(ValueError, "UCM_LIFECYCLE_TRANSITION_REFUSED"):
            build_lifecycle_receipt(contract_root="1" * 64,
                from_state="VALIDATED", to_state="DRAFT",
                predecessor_receipt_root=validated["lifecycle_receipt_root"],
                evidence_roots=["2" * 64])


class AuthoringTests(unittest.TestCase):
    def test_realization_and_amcas_lint(self):
        realization = load("examples/realization/portable-agent-environment.json")
        amcas = load("examples/amcas/portable-agent.integration.json")
        self.assertIn(lint_realization_contract(realization)["status"],
                      {"PASS", "REFUSED_SEMANTIC_LINT"})
        self.assertEqual(lint_amcas_contract(amcas)["contract_root"], amcas["contract_root"])

    def test_linter_rejects_schema_valid_but_vacuous_realization(self):
        contract = load("examples/realization/portable-agent-environment.json")
        body = {key: value for key, value in contract.items() if key != "root"}
        body["constraints"] = []
        body["evidence"] = {"required_roots": [], "required_fields": [], "non_claims": []}
        body["root"] = root(body)
        result = lint_realization_contract(body)
        codes = {row["code"] for row in result["issues"]}
        self.assertIn("RSC_LINT_NO_HARD_CONSTRAINTS", codes)
        self.assertIn("RSC_LINT_EMPTY_EVIDENCE_CONTRACT", codes)

    def test_policy_pack_applies_as_successor_contract(self):
        contract = load("examples/amcas/portable-agent.integration.json")
        pack = load("policy-packs/ARCHITECTURE-FIDELITY-v0.1.json")
        validate_policy_pack(pack)
        result = apply_policy_packs(contract, [pack])
        self.assertNotEqual(result["contract"]["contract_root"], contract["contract_root"])
        ids = {row["id"] for row in result["contract"]["cm1"]["requirements"]}
        self.assertIn("NO_UNRELATED_PATH_CHANGES", ids)

    def test_semantic_diff_classifies_authority_and_admissibility(self):
        before = {"cm1": {"required": True}, "authority_effect": "NONE"}
        after = {"cm1": {"required": False}, "authority_effect": "WRITE"}
        result = semantic_contract_diff(before, after)
        self.assertEqual(result["change_counts"]["AUTHORITY_ADJACENT"], 1)
        self.assertEqual(result["change_counts"]["ADMISSIBILITY"], 1)


class EvidenceTests(unittest.TestCase):
    def test_subject_and_freshness_are_separate(self):
        envelope = build_evidence_envelope(evidence_id="TEST", subject_root="1" * 64,
            policy_root="2" * 64, issuer_root="3" * 64, verifier_root="4" * 64,
            environment_root="5" * 64, result_root="6" * 64, result_status="PASS",
            issued_at=100, not_before=90, not_after=110)
        self.assertEqual(validate_evidence_envelope(envelope,
            expected_subject_root="1" * 64, expected_policy_root="2" * 64,
            now=105), envelope)
        with self.assertRaisesRegex(ValueError, "UCM_EVIDENCE_EXPIRED"):
            validate_evidence_envelope(envelope, expected_subject_root="1" * 64,
                                       expected_policy_root="2" * 64, now=111)


class JournalIntelligenceTests(unittest.TestCase):
    def events(self):
        actor = {"kind": "SYSTEM", "mosaic_id": None, "session_id": None}
        first = build_event(sequence=1, predecessor=GENESIS, event_id="one",
                            event_type="CAMPAIGN_CREATED", actor=actor, payload={})
        second = build_event(sequence=2, predecessor=first["event_root"], event_id="two",
                             event_type="OPERATION_PLANNED", actor=actor,
                             payload={"operation_id": "OP-1"})
        third = build_event(sequence=3, predecessor=second["event_root"], event_id="three",
                            event_type="DIAGNOSTIC_RECORDED", actor=actor,
                            payload={"operation_id": "OP-1"})
        return [first, second, third]

    def test_summary_query_diff_and_inclusion(self):
        events = self.events()
        self.assertEqual(summarize_events(events)["sequence"], 3)
        self.assertEqual(query_events(events, operation_id="OP-1")["match_count"], 2)
        self.assertEqual(diff_event_chains(events[:2], events)["relation"], "FAST_FORWARD")
        proof = build_inclusion_proof(events, event_root=events[1]["event_root"])
        self.assertEqual(verify_inclusion_proof(proof), proof)


class DiagnosticsAndEvaluationTests(unittest.TestCase):
    @staticmethod
    def context_registration(protocol):
        body = {
            "schema": "mosaic.ucm.architecture-study-execution-context.v0.1",
            "study_root": protocol["study_root"],
            "model_id_root": "7" * 64,
            "model_settings_root": "6" * 64,
            "environment_root": "5" * 64,
            "toolchain_root": "4" * 64,
            "allowed_deviations": [],
            "status": "REGISTERED_BEFORE_KIT_ISSUANCE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED",
        }
        return {**body, "registration_root": root(body)}

    def test_smoke_and_doctor(self):
        self.assertEqual(smoke()["status"], "PASS")
        self.assertEqual(doctor()["canary"]["status"], "PASS")

    def test_study_protocol_has_fixed_denominator(self):
        protocol = load("evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json")
        validate_study_protocol(protocol)
        roster = build_run_roster(protocol)
        self.assertEqual(roster["denominator"], 6)
        self.assertEqual({row["arm_id"] for row in roster["runs"]},
                         {"BASELINE", "CONVENTIONAL_ENFORCEMENT", "UCM_GOVERNED"})
        self.assertEqual(roster["status"], "PLANNED_NOT_EXECUTED")

    def test_study_material_is_exact_and_run_kits_isolate_arms(self):
        protocol = load("evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json")
        task = load("evaluation/tasks/reference-data-client/TASK.json")
        self.assertEqual(protocol["tasks"][0]["task_root"], task["task_root"])
        self.assertTrue((ROOT / "evaluation/tasks/reference-data-client/SUBJECT.zip").is_file())
        with tempfile.TemporaryDirectory(prefix="ucm-study-kits-") as folder:
            first = Path(folder) / "first"
            second = Path(folder) / "second"
            registration = self.context_registration(protocol)
            inventory = build_run_kits(ROOT, first, registration)
            repeated = build_run_kits(ROOT, second, registration)
            self.assertEqual(inventory, repeated)
            self.assertEqual(
                {path.name: path.read_bytes() for path in first.iterdir()},
                {path.name: path.read_bytes() for path in second.iterdir()})
            self.assertEqual(inventory["denominator"], 6)
            self.assertEqual(inventory["status"], "READY_NOT_EXECUTED")
            self.assertEqual(len(inventory["runs"]), 6)
            for row in inventory["runs"]:
                with zipfile.ZipFile(first / row["archive"]) as package:
                    names = set(package.namelist())
                    self.assertIn("CONDITION-CONTEXT.json", names)
                    self.assertIn("ASSIGNMENT.json", names)
                    self.assertIn("EXECUTION-CONTEXT-REGISTRATION.json", names)
                    self.assertIn("FOLLOW-ON-TASK.md", names)
                    for hidden in ("ARM-CONTEXTS.json", "ARM-CONTEXT.json",
                                   "STUDY-PROTOCOL.json", "STUDY-ROSTER.json",
                                   "SCORING-RUBRIC.json", "RESULT-TEMPLATE.json"):
                        self.assertNotIn(hidden, names)
                    assignment = json.loads(package.read("ASSIGNMENT.json"))
                    condition = json.loads(package.read("CONDITION-CONTEXT.json"))
                    self.assertEqual(assignment["run_id"], row["run_id"])
                    self.assertNotIn("arm_id", assignment)
                    self.assertNotIn("arm_id", condition)
                    output = json.loads(package.read("RUN-OUTPUT.template.json"))
                    self.assertEqual(output["run_id"], row["run_id"])
                    has_contract = "ARCHITECTURE-CONTRACT.json" in names
                    has_ucm_policy = "UCM-ARCHITECTURE-POLICY-PACK.json" in names
                    self.assertEqual(has_contract,
                        row["arm_id"] in {"CONVENTIONAL_ENFORCEMENT", "UCM_GOVERNED"})
                    self.assertEqual(has_ucm_policy, row["arm_id"] == "UCM_GOVERNED")

    def test_study_results_require_the_full_registered_denominator(self):
        protocol = load("evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json")
        roster = build_run_roster(protocol)
        arms = {row["arm_id"]: row for row in protocol["arms"]}
        registration = self.context_registration(protocol)
        results = []
        for index, run in enumerate(roster["runs"], start=1):
            execution_context = {
                "environment_root": "5" * 64,
                "executor_session_root": f"{index:064x}",
                "model_id_root": "7" * 64,
                "model_settings_root": "6" * 64,
                "toolchain_root": "4" * 64,
            }
            review_record_root = f"{index + 100:064x}"
            scoring_context = {
                "review_record_root": review_record_root,
                "scorer_identity_root": "3" * 64,
                "scorer_session_root": f"{index + 200:064x}",
                "scoring_rubric_root": protocol["review_policy"]["scoring_rubric_root"],
            }
            body = {"schema": "mosaic.ucm.architecture-study-run-result.v0.3",
                    "study_root": protocol["study_root"], "run_id": run["run_id"],
                    "task_root": run["task_root"], "arm_id": run["arm_id"],
                    "repetition": run["repetition"], "model_id_root": "7" * 64,
                    "model_settings_root": "6" * 64,
                    "executor_session_root": execution_context["executor_session_root"],
                    "environment_root": "5" * 64, "toolchain_root": "4" * 64,
                    "execution_context_root": root(execution_context),
                    "human_oversight_policy_root": arms[run["arm_id"]]["human_oversight_policy_root"],
                    "output_root": "8" * 64,
                    "scorer_identity_root": "3" * 64,
                    "scorer_session_root": scoring_context["scorer_session_root"],
                    "scoring_rubric_root": scoring_context["scoring_rubric_root"],
                    "scoring_context_root": root(scoring_context),
                    "review_record_root": review_record_root,
                    "follow_on_result_root": f"{index + 300:064x}",
                    "context_registration_root": registration["registration_root"],
                    "metrics": {metric: 0 for metric in protocol["metrics"]},
                    "status": "COMPLETE"}
            results.append({**body, "result_root": root(body)})
        self.assertEqual(validate_run_result(protocol, results[0], registration), results[0])
        aggregate = aggregate_study_results(protocol, results, registration)
        self.assertEqual(aggregate["denominator"], roster["denominator"])
        self.assertEqual(aggregate["status"], "OBSERVED_NOT_CAUSAL_CONCLUSION")
        self.assertEqual(aggregate["matched_model_settings_root"], "6" * 64)
        with self.assertRaisesRegex(ValueError, "UCM_STUDY_DENOMINATOR_INCOMPLETE"):
            aggregate_study_results(protocol, results[:-1], registration)
        mismatched = json.loads(json.dumps(results))
        mismatched[0]["model_settings_root"] = "a" * 64
        execution = {key: mismatched[0][key] for key in (
            "environment_root", "executor_session_root", "model_id_root",
            "model_settings_root", "toolchain_root")}
        mismatched[0]["execution_context_root"] = root(execution)
        body = {key: value for key, value in mismatched[0].items()
                if key != "result_root"}
        mismatched[0]["result_root"] = root(body)
        with self.assertRaisesRegex(ValueError, "UCM_STUDY_MATCHED_CONTEXT_MISMATCH"):
            aggregate_study_results(protocol, mismatched, registration)
        reused = json.loads(json.dumps(results))
        reused[1]["executor_session_root"] = reused[0]["executor_session_root"]
        execution = {key: reused[1][key] for key in (
            "environment_root", "executor_session_root", "model_id_root",
            "model_settings_root", "toolchain_root")}
        reused[1]["execution_context_root"] = root(execution)
        body = {key: value for key, value in reused[1].items()
                if key != "result_root"}
        reused[1]["result_root"] = root(body)
        with self.assertRaisesRegex(ValueError, "UCM_STUDY_EXECUTOR_SESSION_REUSED"):
            aggregate_study_results(protocol, reused, registration)


class ArchitectureFidelityTests(unittest.TestCase):
    def test_reference_change_conforms_and_drift_is_refused(self):
        contract = load("examples/architecture/reference-data-client/ARCHITECTURE-CONTRACT.json")
        conforming = load("examples/architecture/reference-data-client/CONFORMING-CHANGE.json")
        drift = load("examples/architecture/reference-data-client/DRIFTING-CHANGE.json")
        self.assertEqual(validate_architecture_contract(contract), contract)
        accepted = check_architecture_change(contract, conforming)
        refused = check_architecture_change(contract, drift)
        self.assertEqual(accepted["status"], "PASS_ARCHITECTURE_FIDELITY")
        self.assertEqual(refused["status"], "REFUSED_ARCHITECTURE_DRIFT")
        self.assertIn("UCM_ARCHITECTURE_SCOPE_VIOLATION", refused["reason_codes"])
        self.assertIn("UCM_ARCHITECTURE_REQUIRED_ABSTRACTION_MISSING", refused["reason_codes"])
        self.assertIn("UCM_ARCHITECTURE_PROOF_EVIDENCE_MISSING", refused["reason_codes"])

    def test_architecture_surfaces_are_invokable(self):
        contract = load("examples/architecture/reference-data-client/ARCHITECTURE-CONTRACT.json")
        candidate = load("examples/architecture/reference-data-client/CONFORMING-CHANGE.json")
        validate_request = {"schema": "mosaic.ucm.request.v0.1",
                            "surface": "VALIDATE_ARCHITECTURE_CONTRACT",
                            "payload": {"contract": contract}, "request_id": "architecture-contract"}
        check_request = {"schema": "mosaic.ucm.request.v0.1",
                         "surface": "CHECK_ARCHITECTURE_CHANGE",
                         "payload": {"contract": contract, "candidate": candidate},
                         "request_id": "architecture-change"}
        self.assertEqual(invoke(validate_request)["result"]["contract_root"],
                         contract["contract_root"])
        self.assertEqual(invoke(check_request)["result"]["status"],
                         "PASS_ARCHITECTURE_FIDELITY")

    def test_project_intelligence_and_planner_share_one_work_package(self):
        records = [
            {"id": "ART-CLIENT", "kind": "IMPLEMENTATION_ARTIFACT",
             "title": "Reference client", "summary": "Use the existing client.",
             "state": "PLANNED", "depends_on": ["REQ-CLIENT"],
             "path": "src/reference_client.py", "sha256": None},
            {"id": "ART-CLIENT-TEST", "kind": "IMPLEMENTATION_ARTIFACT",
             "title": "Reference client tests", "summary": "Verify the existing client.",
             "state": "PLANNED", "depends_on": ["REQ-CLIENT"],
             "path": "tests/test_reference_client.py", "sha256": None},
            {"id": "AUTH-REVIEW", "kind": "AUTHORIZATION_DECISION",
             "title": "Review only", "summary": "Keep release authority closed.",
             "state": "CLOSED", "depends_on": ["VER-CLIENT"],
             "scope": "REVIEW_RECOMMENDATION_ONLY", "condition": "Independent review required."},
            {"id": "REQ-CLIENT", "kind": "REQUIREMENT", "title": "Reuse client",
             "summary": "Keep one reference client.", "state": "DOCUMENTED",
             "depends_on": [], "criterion": "The existing client remains the integration point."},
            {"id": "VER-CLIENT", "kind": "VERIFICATION_OBLIGATION",
             "title": "Client tests", "summary": "Re-run client checks.", "state": "OPEN",
             "depends_on": ["ART-CLIENT-TEST"], "evidence": []},
        ]
        body = {"schema": "ucl.ucm.project_intelligence.snapshot.v1",
                "project_id": "REFERENCE-CLIENT", "baseline": {
                    "subject": "Reference data client", "source_root": "1" * 64,
                    "review_disposition": "UNREVIEWED"},
                "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                "records": records}
        project = {**body, "snapshot_root": project_intelligence.rooted(body)}
        result = prepare_work_package(
            project=project, changed_ids=[], changed_paths=[
                "src/reference_client.py", "tests/test_reference_client.py"],
            objective="Review the reference client change", workspace=str(ROOT),
            architecture_contract=load(
                "examples/architecture/reference-data-client/ARCHITECTURE-CONTRACT.json"),
            architecture_candidate=load(
                "examples/architecture/reference-data-client/CONFORMING-CHANGE.json"))
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["simulation_plan"]["execution_mode"], "SIMULATION_ONLY")
        self.assertFalse(result["work_order"]["advance_authority"])


class ConformanceAssetTests(unittest.TestCase):
    def test_track_a_reviews_and_repair_disposition_are_exact_and_non_authorizing(self):
        folder = ROOT / "review" / "unified-maturity" / "track-a"
        register = json.loads((folder / "REVIEW-REGISTER.json").read_text(
            encoding="utf-8"))
        register_body = {key: value for key, value in register.items()
                         if key != "register_root"}
        self.assertEqual(register["register_root"], root(register_body))
        for row in register["reviews"]:
            raw = (folder / row["archive"]).read_bytes()
            self.assertEqual(len(raw), row["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
        disposition = json.loads((folder / "REPAIR-DISPOSITION.json").read_text(
            encoding="utf-8"))
        body = {key: value for key, value in disposition.items()
                if key != "disposition_root"}
        self.assertEqual(disposition["disposition_root"], root(body))
        self.assertEqual(disposition["review_register_root"], register["register_root"])
        self.assertEqual(disposition["status"],
                         "BUILDER_REPAIRED_PENDING_INDEPENDENT_TIER1")
        self.assertEqual(disposition["authority_effect"], "NONE")

    def test_successor_archives_are_deterministic_and_carry_maturity_assets(self):
        runtime_a, anchor_a = build_runtime_archive()
        runtime_b, anchor_b = build_runtime_archive()
        self.assertEqual((runtime_a, anchor_a), (runtime_b, anchor_b))
        self.assertEqual(anchor_a["profile_registry_root"],
                         profile_registry()["profile_registry_root"])
        review_a, review_anchor_a = build_review_source_archive()
        review_b, review_anchor_b = build_review_source_archive()
        self.assertEqual((review_a, review_anchor_a), (review_b, review_anchor_b))
        for profile_id in ("AUTHORING", "COMPATIBILITY", "OPERATIONAL", "VERIFY_ONLY"):
            first = build_profile_overlay(profile_id)
            second = build_profile_overlay(profile_id)
            self.assertEqual(first, second)

    def test_canonical_runtime_stages_and_orients_from_its_own_bytes(self):
        runtime, _ = build_runtime_archive()
        with tempfile.TemporaryDirectory(prefix="ucm-maturity-runtime-") as folder:
            staged = Path(folder) / "runtime"; staged.mkdir()
            archive = Path(folder) / "runtime.zip"; archive.write_bytes(runtime)
            with zipfile.ZipFile(archive) as package:
                package.extractall(staged)
            run = subprocess.run([sys.executable, "-I", "-B",
                                  str(staged / "tools/ucm.py"), "orient"],
                                 cwd=staged, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)["authority_effect"], "NONE")
            for relative in ("program/UNIFIED-MATURITY-PROGRAM.json",
                             "evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json",
                             "integration/ECOSYSTEM-INTEGRATION-BASELINE.json",
                             "integration/stage-i3/STAGE-I3-REBIND-RECONCILIATION.json",
                             "spec/product-profiles/PROFILE-REGISTRY.json",
                             "tools/build_architecture_study_kits.py",
                             "tools/reconcile_ecosystem_stage3.py"):
                self.assertTrue((staged / relative).is_file(), relative)

    def test_operator_delivery_builds_deterministically_without_running_court(self):
        subject, anchor = build_review_source_archive()
        qualification = {
            "status": "PASS",
            "operator_adversarial_status": "SEPARATE_USER_RUN_REQUIRED",
            "qualification_source_anchor": anchor,
        }
        with tempfile.TemporaryDirectory(prefix="ucm-maturity-operator-build-") as folder:
            base = Path(folder); qualification_dir = base / "qualification"
            qualification_dir.mkdir()
            (qualification_dir / "QUALIFICATION.json").write_text(
                json.dumps(qualification, sort_keys=True, separators=(",", ":")),
                encoding="utf-8")
            (qualification_dir / "QUALIFICATION-SOURCE.zip").write_bytes(subject)
            first = base / "first"; second = base / "second"
            result_a = build_operator_kit(qualification_dir, first)
            result_b = build_operator_kit(qualification_dir, second)
            files_a = {path.relative_to(first).as_posix(): path.read_bytes()
                       for path in first.rglob("*") if path.is_file()}
            files_b = {path.relative_to(second).as_posix(): path.read_bytes()
                       for path in second.rglob("*") if path.is_file()}
            self.assertEqual(result_a, result_b)
            self.assertEqual(files_a, files_b)
            self.assertFalse(result_a["operator_court_executed"])
            with zipfile.ZipFile(first / "UCM-MATURITY-TIER1-OPERATOR-KIT.zip") as package:
                contract = json.loads(
                    package.read("OPERATOR-RUNNER-IMPORT-CONTRACT.json"))
            self.assertEqual(contract["status"], "PASS_STATIC_IMPORT_CONTRACT")
            self.assertEqual(contract["contract_root"],
                             result_a["runner_import_contract_root"])
            mosaicos = next(row for row in contract["imports"]
                            if row["module"] == "uclop.maturity_mosaicos")
            self.assertIn("prepare_m1_from_m0_archive", mosaicos["import_names"])

    def test_schema_documents_and_golden_vectors_are_well_formed(self):
        schemas = sorted((ROOT / "spec" / "schemas").glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 6)
        for path in schemas:
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["$schema"],
                             "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(document["type"], "object")
        corpus = load("conformance/MATURITY-CONFORMANCE-v0.1.json")
        body = {key: value for key, value in corpus.items() if key != "conformance_root"}
        self.assertEqual(corpus["conformance_root"], root(body))
        self.assertEqual(len(corpus["vectors"]), 6)
        for vector in corpus["vectors"]:
            self.assertEqual(vector["output_root"], root(vector["output"]))

    def test_ecosystem_baseline_is_fixed_denominator_and_non_authorizing(self):
        baseline = load("integration/ECOSYSTEM-INTEGRATION-BASELINE.json")
        body = {key: value for key, value in baseline.items() if key != "baseline_root"}
        self.assertEqual(baseline["baseline_root"], root(body))
        self.assertEqual(baseline["fixed_denominator"], 7)
        self.assertEqual(baseline["stage_i3_plan_counts"],
                         {"HOLD_FOR_REPAIR": 3, "READY_FOR_SHADOW_REVIEW": 4})
        self.assertFalse(baseline["stage_i3_shadow_authorized"])
        self.assertFalse(baseline["composition_authorized"])

    def test_mosaicos_m0_prepares_only_unbound_m1_roles(self):
        raw = (ROOT / "fixtures" / "mosaicos" / "MOSAICOS-M0-EVIDENCE.zip").read_bytes()
        request = {"schema": "mosaic.ucm.request.v0.1", "request_id": "mosaicos-m1",
                   "surface": "PREPARE_MOSAICOS_M1", "payload": {
                       "expected_archive_sha256": "5b38c2b67f8fac067b2275af9bb6c6de98950078c6803cdd1522cd3f9d36ac32",
                       "m0_archive_base64": base64.b64encode(raw).decode("ascii")}}
        preparation = invoke(request)["result"]
        self.assertEqual(preparation["status"], "PREPARATION_ONLY")
        self.assertEqual(preparation["m1_acceptance"], "NOT_EARNED")
        self.assertEqual({row["status"] for row in preparation["role_bindings"]}, {"UNBOUND"})
        verify = {"schema": "mosaic.ucm.request.v0.1", "request_id": "mosaicos-verify",
                  "surface": "VERIFY_MOSAICOS_M1_PREPARATION", "payload": {
                      "preparation": preparation, "expected_root": preparation["root"]}}
        self.assertEqual(invoke(verify)["result"], preparation)
if __name__ == "__main__":
    unittest.main()
