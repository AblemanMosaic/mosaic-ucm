import json
import tempfile
import unittest
from pathlib import Path

from ucm.correction_transaction import begin, build_patch, inventory, restore, seal, status, verify


class CorrectionTransactionTests(unittest.TestCase):
    def test_positive_begin_seal_restore_verify_cycle(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            tx = base / "transaction"
            source.mkdir()
            (source / "keep.txt").write_text("keep\n", encoding="utf-8")
            (source / "change.txt").write_text("before\n", encoding="utf-8")
            (source / "delete.txt").write_text("remove\n", encoding="utf-8")
            replacement = base / "replacement.txt"
            addition = base / "addition.txt"
            replacement.write_text("after\n", encoding="utf-8")
            addition.write_text("added\n", encoding="utf-8")
            pre = inventory(source)
            begin(source, tx, "fixture-correction")
            patch = base / "PATCH.zip"
            built = build_patch(
                tx,
                patch,
                [("change.txt", replacement), ("nested/add.txt", addition)],
                ["delete.txt"],
            )
            sealed = seal(tx, patch)
            self.assertEqual((source / "change.txt").read_text("utf-8"), "after\n")
            self.assertEqual((source / "nested/add.txt").read_text("utf-8"), "added\n")
            self.assertFalse((source / "delete.txt").exists())
            self.assertEqual(inventory(source)["source_root"], built["post_source_root"])
            self.assertEqual(sealed["kind"], "SEALED")
            restored = restore(tx)
            self.assertEqual(restored["recovered_source_root"], pre["source_root"])
            self.assertEqual(inventory(source), pre)
            final = verify(tx)
            self.assertEqual(final["kind"], "VERIFIED")
            self.assertEqual(status(tx)["transaction"]["state"], "VERIFIED")
            events = [json.loads(line) for line in (tx / "PROGRESS.jsonl").read_text("utf-8").splitlines()]
            phases = {event["phase"] for event in events}
            self.assertTrue({
                "inventory", "snapshot", "precondition_verification",
                "patch_application", "post_apply_verification", "rollback",
                "member_restoration", "whole_root_proof", "verification",
            }.issubset(phases))
            self.assertTrue(all(event["nonsemantic"] is True for event in events))
            receipts = [json.loads(line) for line in (tx / "RECEIPTS.jsonl").read_text("utf-8").splitlines()]
            self.assertEqual([r["kind"] for r in receipts], ["BEGIN", "PATCH_BOUND", "SEALED", "RESTORED", "VERIFIED"])
            self.assertTrue(all(r["authority_effect"] == "NONE" for r in receipts))

    def test_help_has_no_filesystem_effect(self):
        from ucm.correction_transaction import parser
        with self.assertRaises(SystemExit) as caught:
            parser().parse_args(["--help"])
        self.assertEqual(caught.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
