from __future__ import annotations
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from ucm.pippi_work_units import *
from ucm.pippi_global import HubRefusal


class WorkUnitTests(unittest.TestCase):
    def acceptance(self,status="UNMET"):
        return build_acceptance_case(acceptance_case_id="ACCEPT:WP22:WINDOWS",
            subject_root="a"*64,requirement_root="b"*64,
            verification_surface="WINDOWS_INSTALL_SMOKE",
            expected_result_code="PASS",current_status=status)

    def state(self,**kw):
        values=dict(work_unit_id="WP22",lifecycle_phase="DORMANT_CANDIDATE",
            acceptance_case=self.acceptance(),work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id="WINDOWS_INSTALL_SMOKE",infrastructure_block=None,
            execution_holds=[],
            release_blockers=["LIVE_INSTALL_NOT_AUTHORIZED"],qualification_gaps=["WINDOWS_PENDING"],
            user_acceptance_pending=True,allowed_effect_classes=["LOCAL_ARTIFACT_PREPARATION"],
            forbidden_targets=["LIVE_REAPER_PROFILE"],retry_limit=3,repair_attempts=1,
            implemented_work_packages=12,total_work_packages=24,proof_level="QUALIFIED_SLICE",
            operational_maturity="DORMANT",required_next_gate="ISOLATED_INSTALL_AUTHORIZATION")
        values.update(kw);return build_work_unit_state(**values)

    def test_release_blocker_does_not_hold_active_construction(self):
        state=self.state();self.assertEqual(state["process_state"],"ACTIVE")
        self.assertEqual(state["progress"],{"implemented_work_packages":12,"total_work_packages":24})

    def test_execution_hold_does_hold(self):
        self.assertEqual(self.state(execution_holds=["SOURCE_MISSING"])["process_state"],"HELD")

    def test_no_replay_capsule_binds_receipts_and_heads(self):
        state=self.state();receipt="1"*64
        capsule=build_no_replay_capsule(work_unit_state=state,completed_effects=[{
            "effect_id":"copy","effect_class":"LOCAL_ARTIFACT_PREPARATION","receipt_root":receipt}],
            remaining_operations=["APPEND_RESULT","ADVANCE_CHECKPOINT"],expected_journal_head="2"*64,
            expected_process_head="3"*64)
        self.assertEqual(capsule["retry_budget_remaining"],2)

    def test_preflight_requires_rooted_records(self):
        with self.assertRaisesRegex(HubRefusal,"PIPPI_BUNDLE_RECORD_ROOT_MISSING"):
            preflight_record_bundle(expected_head="2"*64,records=[{"schema":"x"}],planned_effect_classes=[])

    def test_prepared_bundle_is_explicit_intermediate(self):
        state=self.state();pre=preflight_record_bundle(expected_head="2"*64,records=[state],planned_effect_classes=[])
        prepared=build_prepared_bundle(preflight=pre,no_replay_capsule=None)
        self.assertEqual(prepared["bundle_state"],"PREPARED")

    def test_every_work_unit_binds_one_acceptance_case(self):
        state=self.state()
        self.assertEqual(state["acceptance_case_root"],self.acceptance()["acceptance_case_root"])
        self.assertEqual(state["selection_basis"],"DIRECT_CASE_CLOSURE")

    def test_shared_infrastructure_requires_demonstrated_blocker(self):
        blocked=self.acceptance("BLOCKED")
        with self.assertRaisesRegex(HubRefusal,"PIPPI_INFRASTRUCTURE_BLOCK_REQUIRED"):
            self.state(acceptance_case=blocked,work_class="SHARED_INFRASTRUCTURE")
        proof=build_infrastructure_block(acceptance_case=blocked,
            blocker_code="MISSING_PORTABLE_ARCHIVE_READER",blocker_evidence_roots=["c"*64],
            required_capability="PORTABLE_ARCHIVE_READER",
            unblock_criterion="ARCHIVE_READER_POSITIVE_CASE_PASS")
        state=self.state(acceptance_case=blocked,work_class="SHARED_INFRASTRUCTURE",
            infrastructure_block=proof)
        self.assertEqual(state["selection_basis"],"DEMONSTRATED_ACCEPTANCE_BLOCKER")

    def test_shared_infrastructure_never_claims_case_closed(self):
        blocked=self.acceptance("BLOCKED")
        proof=build_infrastructure_block(acceptance_case=blocked,
            blocker_code="MISSING_PORTABLE_ARCHIVE_READER",blocker_evidence_roots=["c"*64],
            required_capability="PORTABLE_ARCHIVE_READER",
            unblock_criterion="ARCHIVE_READER_POSITIVE_CASE_PASS")
        state=self.state(acceptance_case=blocked,work_class="SHARED_INFRASTRUCTURE",
            infrastructure_block=proof)
        outcome=assess_work_unit_outcome(work_unit_state=state,acceptance_case=blocked,
            observed_result_code="ARCHIVE_READER_POSITIVE_CASE_PASS",evidence_roots=["d"*64],
            infrastructure_block=proof)
        self.assertFalse(outcome["acceptance_case_closed"])
        self.assertEqual(outcome["outcome"],"PREREQUISITE_SATISFIED_FOLLOW_ON_DIRECT_STEP_REQUIRED")
        self.assertEqual(outcome["expected_result_code"],proof["unblock_criterion"])
        self.assertEqual(outcome["infrastructure_block_root"],proof["infrastructure_block_root"])

    def test_shared_infrastructure_uses_bound_unblock_criterion(self):
        blocked=self.acceptance("BLOCKED")
        proof=build_infrastructure_block(acceptance_case=blocked,
            blocker_code="MISSING_PORTABLE_ARCHIVE_READER",blocker_evidence_roots=["c"*64],
            required_capability="PORTABLE_ARCHIVE_READER",
            unblock_criterion="ARCHIVE_READER_POSITIVE_CASE_PASS")
        state=self.state(acceptance_case=blocked,work_class="SHARED_INFRASTRUCTURE",
            infrastructure_block=proof)
        unmet=assess_work_unit_outcome(work_unit_state=state,acceptance_case=blocked,
            observed_result_code="PASS",evidence_roots=["d"*64],infrastructure_block=proof)
        self.assertEqual(unmet["outcome"],"PREREQUISITE_UNMET")
        self.assertFalse(unmet["acceptance_case_closed"])

    def test_direct_step_closes_only_matching_case(self):
        case=self.acceptance();state=self.state(acceptance_case=case)
        outcome=assess_work_unit_outcome(work_unit_state=state,acceptance_case=case,
            observed_result_code="PASS",evidence_roots=["d"*64])
        self.assertTrue(outcome["acceptance_case_closed"])
        self.assertEqual(outcome["outcome"],"ACCEPTANCE_CASE_CLOSED")

    def test_cli_verifies_acceptance_bound_selection(self):
        case=self.acceptance()
        value={"acceptance_case":case,"work_class":"DIRECT_ACCEPTANCE_CLOSURE",
            "direct_closure_check_id":"WINDOWS_INSTALL_SMOKE","infrastructure_block":None}
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/"selection.json";path.write_text(json.dumps(value),encoding="utf-8")
            env=dict(os.environ);env["PYTHONPATH"]=str(Path(__file__).resolve().parents[1]/"src")
            onboard=subprocess.run([sys.executable,"-m","ucm.pippi_cli","--data-root",str(Path(raw)/"data"),
                "onboard","--governor-label","TEST_GOVERNOR"],capture_output=True,text=True,env=env)
            self.assertEqual(onboard.returncode,0,onboard.stderr)
            run=subprocess.run([sys.executable,"-m","ucm.pippi_cli","--data-root",str(Path(raw)/"data"),
                "work-selection-verify",str(path)],capture_output=True,text=True,env=env)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(run.stdout)
            self.assertEqual(result["selection_basis"],"DIRECT_CASE_CLOSURE")
            self.assertEqual(len(result["hub_event_root"]),64)


if __name__=="__main__":unittest.main()

