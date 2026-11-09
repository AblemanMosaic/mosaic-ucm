from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import Refusal
from ucm.operation_state import derive_operation_state, validate_operation_state
from ucm.progress import Progress


class OperationStatePositiveTests(unittest.TestCase):
    def setUp(self):
        self.contract = "1" * 64

    def row(self, i, transition, receipt):
        return {"event_id": f"event-{i}", "transition": transition,
                "run_contract_root": self.contract, "receipt_root": receipt * 64}

    def test_complete_gate_chain_has_one_terminal_state(self):
        rows = [self.row(1, "G1_ALLOWED", "2"), self.row(2, "NATIVE_DISPATCHED", "3"),
                self.row(3, "G2_RECORDED", "4"), self.row(4, "G3_PASS", "5")]
        state = derive_operation_state(operation_id="op.1", run_contract_root=self.contract,
                                       events=rows)
        self.assertEqual(state["state"], "COMPLETED")
        self.assertFalse(state["native_redispatch_allowed"])
        self.assertEqual(validate_operation_state(state), state)

    def test_uncertain_dispatch_requires_operator_resolution(self):
        rows = [self.row(1, "G1_ALLOWED", "2"), self.row(2, "NATIVE_DISPATCHED", "3"),
                self.row(3, "OUTCOME_UNCERTAIN", "4")]
        state = derive_operation_state(operation_id="op.2", run_contract_root=self.contract,
                                       events=rows)
        self.assertEqual(state["state"], "UNCERTAIN")
        self.assertTrue(state["requires_operator_resolution"])

    def test_nonsemantic_progress_failure_cannot_fail_work(self):
        with tempfile.TemporaryDirectory() as folder:
            progress = Progress(Path(folder) / "progress.jsonl")
            progress.emit("TEST_START", phase="positive")
            progress.emit("TEST_PASS", phase="positive")
            summary = progress.summary(total=1, status="PASS")
            self.assertEqual((summary["completed"], summary["remaining"]), (1, 0))
            self.assertEqual(summary["semantic_effect"], "NONE")
