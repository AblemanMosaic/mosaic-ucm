from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from ucm.capabilities import invoke
from ucm.pippi_adaptive import (build_project_capsule, build_turn_report,
    interface_conformance, mediation_library, negotiate_host_mode, prepare_turn,
    pippi_shell_completion, reconcile_turn, verify_project_capsule)
from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_portability import build_execution_context
from ucm.system import capability_registry
from uclop.canonical import canonical_bytes


ROOT = Path(__file__).resolve().parents[1]
R1 = "1" * 64
R2 = "2" * 64
R3 = "3" * 64
R4 = "4" * 64


class PippiAdaptiveTests(unittest.TestCase):
    def project(self):
        return build_project(project_id="pippi", title="P/PPI", workspace=str(ROOT),
            github_url=None, application_command=["pippi", "dashboard"],
            verification_command=["pippi", "interface-doctor"], revision="r020")

    def local_host(self):
        return negotiate_host_mode(host_id="codex-local", requested_mode="EXECUTABLE_LOCAL",
            capability_ids=["ARTIFACT_EXCHANGE", "FILESYSTEM_READ", "PROCESS_EXECUTION"],
            adapter_root=None)

    def execution_context(self):
        return build_execution_context(
            host_family="WINDOWS", shell_family="POWERSHELL",
            path_flavour="WINDOWS", filesystem_class="WINDOWS_NATIVE",
            case_sensitive=False, python_implementation="CPython",
            python_version="3.12.3", source="DECLARED_EXTERNAL_HOST",
            wsl_distribution=None)

    def opening(self):
        return prepare_turn(project=self.project(), host_profile=self.local_host(), sequence=1,
            previous_turn_root=None, scenario="CODING", requested_rule_ids=[
                "ACCEPTANCE_CASE_SELECTION", "EXECUTION_CONTEXT_DISCIPLINE",
                "UGK_CLAIM_DISCIPLINE", "VERSION_POLICY"],
            acceptance_case_roots=[R1], journal_head=R2,
            execution_context=self.execution_context())

    def report(self):
        return build_turn_report(opening=self.opening(), summary="Built adaptive turn records.",
            changed_paths=["src/ucm/pippi_adaptive.py"], artifact_roots=[R3], evidence_roots=[R4],
            unresolved_items=[{"item_id":"UGK-PIN", "fact_class":"UNRESOLVED",
                               "statement":"Exact canonical UGK release remains to be supplied."}],
            next_action="Package the exact UCM and UGK profiles.", claim_class="IMPLEMENTATION")

    def test_library_contains_ugk_and_selection_rules(self):
        library = mediation_library()
        ids = {row["rule_id"] for row in library["rules"]}
        self.assertTrue({"UGK_FGA", "UGK_THREE_HASH_RULE", "UGK_IEL",
                         "ACCEPTANCE_CASE_SELECTION"} <= ids)

    def test_scenario_mechanically_injects_required_rules(self):
        opening = prepare_turn(
            project=self.project(), host_profile=self.local_host(), sequence=1,
            previous_turn_root=None, scenario="PACKAGING", requested_rule_ids=[],
            acceptance_case_roots=[R1], journal_head=None,
            execution_context=self.execution_context())
        self.assertTrue({"ARCHIVE_POLICY", "AUTHORITY_BOUNDARY",
                         "EXECUTION_CONTEXT_DISCIPLINE",
                         "PORTABILITY_DETERMINISM", "VERSION_POLICY"}
                        <= set(opening["rule_ids"]))
        with self.assertRaisesRegex(ValueError, "PIPPI_SCENARIO_INVALID"):
            prepare_turn(
                project=self.project(), host_profile=self.local_host(), sequence=1,
                previous_turn_root=None, scenario="UNDECLARED",
                requested_rule_ids=[], acceptance_case_roots=[R1],
                journal_head=None, execution_context=self.execution_context())

    def test_web_and_local_modes_are_honest(self):
        local = self.local_host(); self.assertEqual(local["status"], "PASS")
        web = negotiate_host_mode(host_id="chatgpt-web", requested_mode="ARTIFACT_MEDIATED_WEB",
                                  capability_ids=["ARTIFACT_EXCHANGE"], adapter_root=None)
        self.assertEqual(web["effective_mode"], "ARTIFACT_MEDIATED_WEB")
        native = negotiate_host_mode(host_id="chat", requested_mode="NATIVE_ENFORCED",
                                     capability_ids=["ARTIFACT_EXCHANGE"], adapter_root=None)
        self.assertEqual(native["status"], "REFUSED_NATIVE_ENFORCEMENT_UNSUBSTANTIATED")
        self.assertFalse(native["enforced_host_verified"])
        asserted = negotiate_host_mode(host_id="declared-adapter", requested_mode="NATIVE_ENFORCED",
            capability_ids=["ARTIFACT_EXCHANGE","TOOL_INTERPOSITION","VISIBLE_OUTPUT_INTERPOSITION"],
            adapter_root=R1)
        self.assertEqual(asserted["status"], "REFUSED_NATIVE_ENFORCEMENT_UNSUBSTANTIATED")
        self.assertFalse(asserted["enforced_host_verified"])

    def test_turn_open_report_reconcile(self):
        opening = self.opening(); report = self.report()
        result = reconcile_turn(opening=opening, report=report,
            current_project_root=opening["project_root"], current_journal_head=R2)
        self.assertEqual(result["state"], "RECONCILED")
        self.assertEqual(result["accepted_evidence_roots"], [R4])
        with self.assertRaisesRegex(ValueError, "PIPPI_JOURNAL_CHANGED_DURING_TURN"):
            reconcile_turn(opening=opening, report=report,
                current_project_root=opening["project_root"], current_journal_head=R3)

    def test_capsule_manifest_binds_ucm_ugk_and_refuses_private_flag(self):
        opening = self.opening(); library = mediation_library()
        capsule = build_project_capsule(profile="WORK_CAPSULE", project=self.project(),
            host_profile=self.local_host(), ucm_root=R1, ugk_root=R2,
            mediation_library_root=library["mediation_library_root"], journal_head=R3,
            turn_root=opening["turn_opening_root"], public_identity_roots=[R4],
            members=[{"path":"BOOT/START-HERE.md", "sha256":R1, "bytes":10, "role":"ORIENTATION"}])
        self.assertEqual(verify_project_capsule(capsule)["status"], "PASS")
        capsule["private_material_present"] = True
        with self.assertRaisesRegex(ValueError, "PIPPI_CAPSULE_INVALID"):
            verify_project_capsule(capsule)

    def test_new_surfaces_work_through_public_abi(self):
        registry = capability_registry()
        request = {"schema":"mosaic.ucm.request.v0.2", "surface":"NEGOTIATE_PIPPI_HOST_MODE",
            "payload":{"host_id":"claude-web", "requested_mode":"ARTIFACT_MEDIATED_WEB",
                       "capability_ids":["ARTIFACT_EXCHANGE"], "adapter_root":None},
            "request_id":"test:host", "profile_selection":{
                "schema":"mosaic.ucm.product-profile-selection.v0.1", "profile_id":"AUTHORING",
                "capability_registry_root":registry["root"]}}
        response = invoke(request)
        self.assertEqual(response["result"]["status"], "PASS")
        self.assertEqual(response["surface"], "NEGOTIATE_PIPPI_HOST_MODE")
        policy_request = {"schema":"mosaic.ucm.request.v0.2",
            "surface":"DISCOVER_PIPPI_PORTABILITY_POLICY", "payload":{},
            "request_id":"test:portability", "profile_selection":{
                "schema":"mosaic.ucm.product-profile-selection.v0.1",
                "profile_id":"AUTHORING",
                "capability_registry_root":registry["root"]}}
        policy = invoke(policy_request)
        self.assertEqual(policy["result"]["required_leg_ids"],
                         ["WINDOWS_NATIVE", "WSL_NATIVE"])

    def test_interface_registry_is_complete(self):
        result = interface_conformance()
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["capability_count"], 100)
        self.assertEqual(result["exit_codes"]["TYPED_REFUSAL"], 3)
        self.assertFalse(result["adaptive_route_mismatches"])

    def test_cli_uses_machine_stable_usage_and_refusal_codes(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        usage = subprocess.run([sys.executable, "-m", "ucm.pippi_cli", "host-negotiate"],
            text=True, capture_output=True, env=environment, check=False)
        self.assertEqual(usage.returncode, 64)
        self.assertEqual(json.loads(usage.stdout)["code"], "PIPPI_USAGE_ERROR")
        with tempfile.TemporaryDirectory() as td:
            request = Path(td)/"request.json"
            request.write_text(json.dumps({"host_id":"web","requested_mode":"INVALID",
                "capability_ids":[],"adapter_root":None}), encoding="utf-8")
            refused = subprocess.run([sys.executable, "-m", "ucm.pippi_cli",
                "--data-root", str(Path(td)/"hub"), "host-negotiate", str(request)],
                text=True, capture_output=True, env=environment, check=False)
            self.assertEqual(refused.returncode, 3)
            self.assertEqual(json.loads(refused.stdout)["status"], "REFUSED")

    def test_completion_is_generated_from_the_command_registry(self):
        for shell in ("bash", "zsh", "fish", "powershell"):
            result = pippi_shell_completion(shell)
            self.assertIn("turn-prepare", result["commands"])
            self.assertIn("capsule-verify", result["commands"])
            self.assertIn("turn-prepare", result["script"])

    def test_local_hub_persists_turn_record_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            hub=PippiHub(Path(td)/"hub")
            hub.initialize(build_onboarding(governor_label="test",mosaic_id=None,
                dkn_public_key=None,github_account=None,github_credential_reference=None))
            project=hub.add_project(self.project())
            opening=prepare_turn(project=project,host_profile=self.local_host(),sequence=1,
                previous_turn_root=None,scenario="CODING",requested_rule_ids=["VERSION_POLICY"],
                acceptance_case_roots=[R1],journal_head=None,
                execution_context=self.execution_context())
            first=hub.store_project_record(project_id="pippi",record_kind="opening",record=opening,
                root_field="turn_opening_root",event_type="TURN_OPENED")
            second=hub.store_project_record(project_id="pippi",record_kind="opening",record=opening,
                root_field="turn_opening_root",event_type="TURN_OPENED")
            self.assertFalse(first["idempotent_replay"]);self.assertTrue(second["idempotent_replay"])
            self.assertEqual(first["hub_event_root"],second["hub_event_root"])

    def test_local_hub_recovers_record_written_before_journal_append(self):
        with tempfile.TemporaryDirectory() as td:
            hub=PippiHub(Path(td)/"hub")
            hub.initialize(build_onboarding(governor_label="test",mosaic_id=None,
                dkn_public_key=None,github_account=None,github_credential_reference=None))
            project=hub.add_project(self.project())
            opening=prepare_turn(project=project,host_profile=self.local_host(),sequence=1,
                previous_turn_root=None,scenario="CODING",requested_rule_ids=["VERSION_POLICY"],
                acceptance_case_roots=[R1],journal_head=None,
                execution_context=self.execution_context())
            path=hub.turns/"pippi"/f"opening-{opening['turn_opening_root']}.json"
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(canonical_bytes(opening)+b"\n")
            result=hub.store_project_record(project_id="pippi",record_kind="opening",record=opening,
                root_field="turn_opening_root",event_type="TURN_OPENED")
            self.assertTrue(result["recovered_interrupted_commit"])
            self.assertEqual(hub._events()[-1]["payload"]["turn_opening_root"],
                             opening["turn_opening_root"])


if __name__ == "__main__":
    unittest.main()
