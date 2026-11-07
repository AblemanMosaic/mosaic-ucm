from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal, root
from ucm.amcas import compile_contract, validate_contract
from _amcas_helpers import contract


class AmcasContractTests(unittest.TestCase):
    def test_contract_compiles_cm1_before_cm2(self):
        value = validate_contract(contract())
        compiled = compile_contract(value)
        self.assertEqual(compiled["cm1"]["membership_policy"], "ALL_APPLICABLE_REQUIREMENTS_PASS")
        self.assertEqual(compiled["cm2"]["selection_policy"], "CM1_THEN_CM2_LEXICOGRAPHIC")
        self.assertTrue(all(row["subject_root"] for row in compiled["obligations"]))
        self.assertEqual(compiled["realization_projection"]["schema"],
                         "mosaic.ucl-tessera.realization-projection.v0.1")
        self.assertEqual(compiled["native_proof_route"]["capability"],
                         "VERIFY_NATIVE_PROOF")

    def test_cm2_cannot_claim_cm1_override(self):
        value = contract()
        value["cm2"]["selection_policy"] = "PREFERENCES_OVERRIDE"
        value["contract_root"] = root({k: v for k, v in value.items() if k != "contract_root"})
        with self.assertRaises(Refusal):
            validate_contract(value)

    def test_effect_class_must_match_capability(self):
        value = contract(effect=True)
        value["effects"][0]["effect_class"] = "NETWORK"
        value["contract_root"] = root({k: v for k, v in value.items() if k != "contract_root"})
        with self.assertRaises(Refusal):
            validate_contract(value)

    def test_obligation_subject_change_changes_ir(self):
        first = compile_contract(contract())
        changed = contract()
        changed["cm1"]["requirements"][0]["subject_root"] = "a" * 64
        changed["contract_root"] = root({k: v for k, v in changed.items() if k != "contract_root"})
        second = compile_contract(changed)
        self.assertNotEqual(first["ir_root"], second["ir_root"])


if __name__ == "__main__":
    unittest.main()
