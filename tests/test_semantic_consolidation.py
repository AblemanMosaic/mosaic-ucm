from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import root, strict_loads
from ucm.semantic_consolidation import (
    build_judgment_packet,
    build_judgment_submission,
    compile_correspondence_program,
    discover_candidates,
    record_judgments,
    validate_discovery_policy,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy-packs" / "SEMANTIC-CONSOLIDATION-CUSTODY-v0.1.json"
PLANS = ROOT / "integration" / "stage-i3" / "authoring" / "plans"


class SemanticConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = strict_loads(POLICY.read_bytes())
        cls.plans = [strict_loads(path.read_bytes())
                     for path in sorted(PLANS.glob("*.json"))]

    def test_policy_and_discovery_are_exact_and_deterministic(self):
        self.assertEqual(validate_discovery_policy(self.policy), self.policy)
        first = discover_candidates(self.plans, self.policy)
        second = discover_candidates(list(reversed(self.plans)), self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_count"], 4)
        self.assertEqual(first["comparison_pair_count"], 13)
        self.assertEqual([row["role_id"] for row in first["candidates"]],
                         ["ARCHIVE_COMPOSE", "ARCHIVE_REPLAY",
                          "READ_EVIDENCE", "VAULT_CUSTODY"])

    def test_model_hypothesis_cannot_promote_a_program(self):
        discovery = discover_candidates(self.plans, self.policy)
        packet = build_judgment_packet(discovery)
        intent = {
            "schema": "mosaic.ucm.semantic-judgment-intent.v0.1",
            "packet_root": packet["packet_root"],
            "decider_kind": "FSC_LLM_HYPOTHESIS",
            "decider_identity_root": root({"test": "model-hypothesis"}),
            "judgments": [{
                "judgment_id": question["judgment_id"],
                "decision": "PROVISIONAL_CANDIDATE",
                "rationale": "Testing the provisional, non-authorizing path.",
                "evidence_roots": [question["candidate_root"]],
                "human_confirmed": False,
            } for question in packet["questions"]],
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
            "real_a5": False,
            "g0": "CLOSED",
        }
        submission = build_judgment_submission(packet, intent)
        register = record_judgments(packet, submission)
        program = compile_correspondence_program(discovery, register)
        self.assertEqual(register["confirmed_count"], 0)
        self.assertEqual(program["ready_program_count"], 0)
        self.assertEqual({row["status"] for row in program["programs"]},
                         {"AWAITING_HUMAN_CONFIRMATION"})
        self.assertEqual(sum(len(row["cm1_obligations"])
                             for row in program["programs"]), 104)

    def test_explicit_human_confirmation_compiles_ready_programs(self):
        discovery = discover_candidates(self.plans, self.policy)
        packet = build_judgment_packet(discovery)
        intent = {
            "schema": "mosaic.ucm.semantic-judgment-intent.v0.1",
            "packet_root": packet["packet_root"],
            "decider_kind": "HUMAN",
            "decider_identity_root": root({"test": "human-reviewer"}),
            "judgments": [{
                "judgment_id": question["judgment_id"],
                "decision": "CONFIRMED_FOR_CORRESPONDENCE",
                "rationale": "Human confirmation opens evidence collection only.",
                "evidence_roots": [question["candidate_root"]],
                "human_confirmed": True,
            } for question in packet["questions"]],
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
            "real_a5": False,
            "g0": "CLOSED",
        }
        submission = build_judgment_submission(packet, intent)
        register = record_judgments(packet, submission)
        program = compile_correspondence_program(discovery, register)
        self.assertEqual(register["confirmed_count"], 4)
        self.assertEqual(program["ready_program_count"], 4)
        self.assertTrue(all(not row["execution_authorized"]
                            and not row["composition_authorized"]
                            for row in program["programs"]))

    def test_semantic_cli_help_is_observation_only(self):
        commands = [
            "semantic-discover",
            "semantic-judgment-packet",
            "semantic-build-judgment-submission",
            "semantic-record-judgments",
            "semantic-compile-consolidation",
        ]
        with tempfile.TemporaryDirectory() as raw:
            workspace = pathlib.Path(raw)
            before = list(workspace.iterdir())
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            for command in commands:
                result = subprocess.run(
                    [sys.executable, "-m", "ucm.cli", command, "--help"],
                    cwd=workspace, env=env, capture_output=True, text=True,
                    check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())
            self.assertEqual(list(workspace.iterdir()), before)


    def test_source_manifest_refresh_help_is_observation_only(self):
        manifest = ROOT / "release" / "SOURCE-MANIFEST.json"
        identity = ROOT / "release" / "RELEASE-IDENTITY.json"
        before = {path: path.read_bytes() if path.is_file() else None
                  for path in (manifest, identity)}
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "refresh_release_identity.py"),
             "--help"],
            cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())
        self.assertNotIn("source_manifest_root", result.stdout)
        after = {path: path.read_bytes() if path.is_file() else None
                 for path in (manifest, identity)}
        self.assertEqual(after, before)

if __name__ == "__main__":
    unittest.main()
