from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import json
import os
import subprocess
import sys

from uclop.canonical import root
from ucm.behavioral_harness import build_harness_contract, build_transition_receipt
from ucm.constitutional_launcher import (
    build_launch_contract,
    build_launch_observation,
    derive_launch_state,
)
from ucm.development_standards import build_standards_catalog, evaluate_standards
from ucm.development_observatory import (
    build_development_observatory,
    project_development_observatory,
)
from ucm.pippi import (
    build_constitutional_exception,
    build_human_projection,
    build_model_draft,
    build_pippi_context,
    build_pippi_decision,
    build_turn_envelope,
)
from ucm.pippi_runtime import PippiCampaign, validate_pippi_campaign_workspace
from ucm.semantic_passage import (
    build_clarification_request,
    build_semantic_passage,
    resolve_semantic_passage,
)


def h(label: str) -> str:
    return root({"label": label})


class PippiFoundationTests(unittest.TestCase):
    def test_standards_catalog_evaluates_fixed_denominator(self) -> None:
        catalog = build_standards_catalog(catalog_id="PIPPI.C1", policy_root=h("policy"),
            obligations=[
                {"obligation_id": "OBS.VISIBLE_PROGRESS", "statement": "Show progress.",
                 "class": "MANDATORY", "triggers": [], "check_ids": ["CHECK.PROGRESS"],
                 "evidence_required": True},
                {"obligation_id": "OBS.LAUNCH", "statement": "Check launcher when used.",
                 "class": "CONDITIONAL", "triggers": ["LAUNCH"],
                 "check_ids": ["CHECK.LAUNCH"], "evidence_required": True},
            ])
        result = evaluate_standards(catalog=catalog, subject_root=h("subject"),
            active_triggers=[], check_results=[
                {"check_id": "CHECK.PROGRESS", "role": "TARGETED",
                 "subject_root": h("subject"), "status": "PASS",
                 "evidence_root": h("progress-evidence"), "witness_root": h("witness")},
            ])
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["fixed_denominator"], 2)
        dispositions = {row["obligation_id"]: row for row in result["obligation_dispositions"]}
        self.assertEqual(dispositions["OBS.LAUNCH"]["status"], "NOT_APPLICABLE")

    def test_semantic_passage_preserves_text_and_resolves_qualified_integer(self) -> None:
        text = "The agent may stage a repair."
        start = text.encode().index(b"stage")
        vocab = h("reference-vocabulary")
        passage = build_semantic_passage(passage_id="TURN.1.TEXT", text=text,
            context_root=h("context"), provider_mode="REFERENCE_UNBOUND",
            provider_root=None, spans=[{
                "span_id": "SPAN.STAGE", "byte_start": start, "byte_end": start + 5,
                "exact_text": "stage", "requirement": "REQUIRED",
                "candidates": [
                    {"vocabulary_root": vocab, "term_id": 17, "sense_id": 1,
                     "bound_term": "prepare-without-dispatch"},
                    {"vocabulary_root": vocab, "term_id": 17, "sense_id": 2,
                     "bound_term": "authorize-dispatch"},
                ], "citation_roots": [h("definition")],
            }])
        clarification = build_clarification_request(passage=passage, turn=1,
            unresolved_span_ids=["SPAN.STAGE"], remaining_turns=1)
        result = resolve_semantic_passage(passage=passage, selections=[{
            "span_id": "SPAN.STAGE", "vocabulary_root": vocab,
            "term_id": 17, "sense_id": 1,
        }], clarification_roots=[clarification["clarification_root"]])
        self.assertEqual(result["status"], "PASS_RESOLVED")
        self.assertTrue(result["original_text_preserved"])
        self.assertEqual(passage["text"], text)

    def test_pippi_holds_undeclared_effect_and_projects_original_text(self) -> None:
        channels = sorted({"MODEL_INPUT", "MODEL_DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL"})
        context = build_pippi_context(session_root=h("session"), subject_root=h("subject"),
            policy_roots=[h("policy")], capability_registry_root=h("registry"),
            profile_root=h("profile"), jurisdiction_root=h("jurisdiction"),
            retained_context_roots=[], mediated_channels=channels)
        draft = build_model_draft(turn_id="TURN.1", context=context,
            text="I will write the file after authorization.", proposals=[{
                "proposal_id": "P1", "kind": "TOOL_CALL", "payload_root": h("payload"),
                "effect_class": "WRITE_WORKSPACE",
            }])
        decision = build_pippi_decision(draft=draft,
            policy_evaluation_roots=[h("evaluation")], proposal_dispositions=[{
                "proposal_id": "P1", "declared": False, "effectful": True,
                "decision": "HELD", "reason_codes": ["CONSTITUTIONAL_GAP"],
                "contract_root": None,
            }], semantic_resolution_root=None, semantic_status="NOT_REQUIRED")
        projection = build_human_projection(draft=draft, decision=decision, view="READING")
        exception = build_constitutional_exception(draft_root=draft["draft_root"],
            proposal_id="P1", missing_rule_id="RULE.WRITE", requested_decision="BIND_OR_REFUSE",
            affected_obligation_ids=["CM1:EFFECT_GATE"])
        self.assertEqual(context["integration_mode"], "SIDECAR_PARTIAL")
        self.assertEqual(decision["status"], "HELD")
        self.assertEqual(projection["display_text"], draft["text"])
        self.assertEqual(exception["status"], "OPEN")
        self.assertFalse(exception["exception_grants_authority"])

        turn = build_turn_envelope(sequence=1, previous_turn_root=None,
            context=context, draft=draft, decision=decision, projection=projection,
            tool_proposal_roots=[h("tool-proposal")], dispatch_receipt_roots=[],
            tool_result_roots=[])
        observatory = build_development_observatory(subject_root=h("subject"),
            standards_evaluations=[], pippi_decisions=[decision], launch_states=[],
            constitutional_exceptions=[exception], journal_head_roots=[turn["turn_root"]])
        view = project_development_observatory(state=observatory, view="HUMAN")
        self.assertEqual(observatory["status"], "ATTENTION_REQUIRED")
        self.assertFalse(view["projection_is_authority"])

    def test_pippi_context_is_available_through_stable_abi(self) -> None:
        from ucm.capabilities import invoke
        from ucm.profiles import validate_profile_selection
        from ucm.system import capability_registry
        selection = validate_profile_selection({
            "schema": "mosaic.ucm.product-profile-selection.v0.1",
            "profile_id": "AUTHORING",
            "capability_registry_root": capability_registry()["root"],
        })
        payload = {"session_root": h("session"), "subject_root": h("subject"),
                   "policy_roots": [h("policy")],
                   "capability_registry_root": capability_registry()["root"],
                   "profile_root": selection["profile_selection_root"],
                   "jurisdiction_root": h("jurisdiction"),
                   "retained_context_roots": [],
                   "mediated_channels": ["MODEL_DRAFT", "MODEL_INPUT"]}
        response = invoke({"schema": "mosaic.ucm.request.v0.2",
            "surface": "BUILD_PIPPI_CONTEXT", "payload": payload,
            "profile_selection": {"schema": "mosaic.ucm.product-profile-selection.v0.1",
                                  "profile_id": "AUTHORING",
                                  "capability_registry_root": capability_registry()["root"]},
            "request_id": "TEST.PIPPI.CONTEXT"})
        self.assertEqual(response["result"]["integration_mode"], "SIDECAR_PARTIAL")

    def test_launcher_reaches_ready_only_with_readiness_evidence(self) -> None:
        contract = build_launch_contract(launch_id="LAUNCH.1", application_id="MEMORY_VAULT",
            subject_root=h("subject"), executable_root=h("exe"), argument_root=h("args"),
            environment_policy_root=h("environment"), readiness_probe_id="HEALTH.V1",
            readiness_contract_root=h("ready"), timeout_ms=30_000,
            executor_binding_root=h("executor"), branding={
                "display_name": "Mosaic Memory Vault", "splash_asset_root": h("splash"),
                "phase_labels": {"PREPARED": "Preparing", "READY": "Ready"},
            })
        first = build_launch_observation(contract=contract, sequence=1, state="PREPARED",
            previous_observation_root=None, executor_receipt_root=h("executor-1"),
            g1_root=h("g1"), g2_root=None, g3_root=None,
            readiness_evidence_root=None, reason_codes=[])
        second = build_launch_observation(contract=contract, sequence=2, state="STARTING",
            previous_observation_root=first["observation_root"],
            executor_receipt_root=h("executor-2"), g1_root=h("g1"),
            g2_root=None, g3_root=None, readiness_evidence_root=None, reason_codes=[])
        third = build_launch_observation(contract=contract, sequence=3, state="READY",
            previous_observation_root=second["observation_root"],
            executor_receipt_root=h("executor-3"), g1_root=h("g1"),
            g2_root=None, g3_root=None, readiness_evidence_root=h("readiness"), reason_codes=[])
        state = derive_launch_state(contract=contract, observations=[first, second, third])
        self.assertTrue(state["ready"])
        self.assertFalse(state["relaunch_allowed"])

    def test_behavioral_harness_records_external_effect_boundary(self) -> None:
        contract = build_harness_contract(harness_id="HARNESS.C1", subject_root=h("subject"),
            state_adapter_root=h("state-adapter"), action_generator_root=h("actions"),
            executor_binding_root=h("executor"), required_controls=["RNG", "TIME"],
            allowed_write_paths=["output/result.json"], scenario_ids=["CASE.1"])
        receipt = build_transition_receipt(contract=contract, scenario_id="CASE.1",
            pre_state_root=h("before"), action_root=h("action"), post_state_root=h("after"),
            observed_controls=["RNG", "TIME"],
            observed_write_paths=["output/result.json"],
            executor_receipt_root=h("receipt"), status="PASS", reason_codes=[])
        self.assertEqual(receipt["effect_claim"], "OBSERVED_EXTERNAL_EXECUTOR_ONLY")

    def test_pippi_campaign_persists_turn_and_projects_observatory(self) -> None:
        context = build_pippi_context(session_root=h("session"), subject_root=h("subject"),
            policy_roots=[h("policy")], capability_registry_root=h("registry"),
            profile_root=h("profile"), jurisdiction_root=h("jurisdiction"),
            retained_context_roots=[],
            mediated_channels=["MODEL_DRAFT", "MODEL_INPUT", "VISIBLE_OUTPUT"])
        draft = build_model_draft(turn_id="TURN.1", context=context, text="Status is ready.",
                                  proposals=[])
        decision = build_pippi_decision(draft=draft,
            policy_evaluation_roots=[h("evaluation")], proposal_dispositions=[],
            semantic_resolution_root=None, semantic_status="NOT_REQUIRED")
        projection = build_human_projection(draft=draft, decision=decision, view="READING")
        turn = build_turn_envelope(sequence=1, previous_turn_root=None, context=context,
            draft=draft, decision=decision, projection=projection, tool_proposal_roots=[],
            dispatch_receipt_roots=[], tool_result_roots=[])
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "campaign"
            campaign = PippiCampaign.create(workspace, context)
            campaign.record_turn(context=context, draft=draft, decision=decision,
                                 projection=projection, turn=turn, event_id="turn-1")
            state = campaign.observatory()
            verification = validate_pippi_campaign_workspace(workspace)
            self.assertEqual(state["status"], "CURRENT")
            self.assertEqual(verification["status"], "PASS")

    def test_pippi_cli_creates_projects_and_verifies_campaign(self) -> None:
        context = build_pippi_context(session_root=h("cli-session"), subject_root=h("cli-subject"),
            policy_roots=[h("cli-policy")], capability_registry_root=h("cli-registry"),
            profile_root=h("cli-profile"), jurisdiction_root=h("cli-jurisdiction"),
            retained_context_roots=[], mediated_channels=["MODEL_DRAFT", "MODEL_INPUT"])
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            context_path = base / "context.json"
            workspace = base / "workspace"
            context_path.write_text(json.dumps(context, sort_keys=True, separators=(",", ":")),
                                    encoding="utf-8")
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            def run(*arguments: str) -> dict:
                completed = subprocess.run([sys.executable, "-m", "ucm", *arguments],
                    cwd=base, env=environment, text=True, capture_output=True, check=False)
                self.assertEqual(0, completed.returncode,
                                 f"stdout={completed.stdout}\nstderr={completed.stderr}")
                return json.loads(completed.stdout)
            created = run("pippi-create", str(context_path), str(workspace))
            status = run("pippi-status", str(workspace), "--view", "HUMAN")
            verified = run("pippi-verify", str(workspace))
            self.assertEqual(created["status"], "PASS")
            self.assertEqual(status["content"]["status"], "CURRENT")
            self.assertEqual(verified["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
