from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.pippi_work_units import (build_work_selection,
                                  validate_acceptance_case)


class PippiWorkSelectionNormalizationTests(unittest.TestCase):
    def test_normalized_records_conform_and_preimages_are_preserved(self):
        receipt = json.loads((ROOT / "program/pippi-work-selection-normalization-r019/NORMALIZATION.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(receipt["mapping_count"], 16)
        self.assertFalse(receipt["implementation_effect_authorized"])
        self.assertEqual(len(receipt["preimage_members"]), 55)
        count = 0
        for directory in (ROOT / "program/pippi-interface-r016",
                          ROOT / "program/pippi-adaptive-r017",
                          ROOT / "program/pippi-adaptive-r018"):
            for case_path in directory.glob("*ACCEPTANCE-CASE.json"):
                case = validate_acceptance_case(json.loads(case_path.read_text(encoding="utf-8")))
                selection_path = case_path.with_name(
                    case_path.name.replace("ACCEPTANCE-CASE", "WORK-SELECTION"))
                selection = json.loads(selection_path.read_text(encoding="utf-8"))
                self.assertEqual(selection, build_work_selection(
                    acceptance_case=case, work_class="DIRECT_ACCEPTANCE_CLOSURE",
                    direct_closure_check_id=case["verification_surface"],
                    infrastructure_block=None))
                count += 1
        self.assertEqual(count, 16)

    def test_normalization_builder_check_is_read_only_and_exact(self):
        spec = importlib.util.spec_from_file_location(
            "normalize_pippi_history", ROOT / "tools/normalize_pippi_work_selection_history.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        programs, receipt = module.expected()
        self.assertEqual(set(programs), {
            "pippi-interface-r016", "pippi-adaptive-r017", "pippi-adaptive-r018"})
        self.assertEqual(receipt["mapping_count"], 16)


if __name__ == "__main__":
    unittest.main()
