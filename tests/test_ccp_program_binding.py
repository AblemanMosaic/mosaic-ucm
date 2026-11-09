from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/build_ccp_native_program.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_ccp_native_program", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("CCP_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CcpProgramBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.outputs = {
            path: path.read_bytes()
            for path in sorted((ROOT / "program/ccp-admissibility-r014").glob("*.json"))
        }
        cls.records = {
            path.name: json.loads(data.decode("utf-8"))
            for path, data in cls.outputs.items()
        }

    def test_exact_source_and_generated_records_are_current(self):
        self.assertEqual(
            "9a38419d655b9306c7216554081a6c869e12c0dcab1e08b961b8d645115e985e",
            self.records["SOURCE-INVENTORY.json"]["source_archive_sha256"],
        )
        self.assertEqual(45, self.records["SOURCE-INVENTORY.json"]["member_count"])
        checked = self.builder.check_frozen_program_directory(
            source_root=ROOT,
            registry=json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text()),
            directory="program/ccp-admissibility-r014")
        self.assertEqual("PASS_FROZEN_CUSTODY", checked["status"])

    def test_complete_source_obligation_denominator_is_preserved(self):
        program = self.records["NATIVE-PROGRAM.json"]
        self.assertEqual(
            {
                "batches": 6,
                "stages": 13,
                "requirements": 32,
                "product_acceptance_cases": 116,
                "product_cases_executed": 0,
            },
            program["denominators"],
        )
        self.assertEqual(13, len(program["source_stages"]))
        self.assertEqual(32, len(program["source_requirements"]))
        self.assertEqual(116, len(program["source_acceptance_cases"]))
        reconciliation = self.records["SOURCE-RECONCILIATION.json"]
        self.assertEqual("PASS_SOURCE_DENOMINATOR_PRESERVED", reconciliation["status"])
        for field, value in reconciliation["denominator_comparison"].items():
            if field.startswith("missing_") or field.startswith("extra_"):
                self.assertEqual([], value, field)

    def test_chc_thr_correspondence_is_explicitly_non_equating(self):
        record = self.records["CHC-THR-CORRESPONDENCE.json"]
        self.assertEqual(
            "EXPLICIT_NON_EQUIVALENCE_PENDING_NORMATIVE_PROFILE",
            record["mapping_status"],
        )
        self.assertEqual("NONE", record["interoperability_claim"])
        self.assertTrue(record["role_correspondences"])
        self.assertTrue(
            all(not row["identity_equivalence"] for row in record["role_correspondences"])
        )
        self.assertIn("CHC_Hm_IS_NOT_UCM_THR_H_m", record["rules"])

    def test_work_is_bound_to_one_unmet_direct_acceptance_case(self):
        case = self.records["ACCEPTANCE-CASE.json"]
        selection = self.records["WORK-SELECTION.json"]
        state = self.records["WORK-UNIT-STATE.json"]
        self.assertEqual("CCP-ADMISSIBILITY-01", case["acceptance_case_id"])
        self.assertEqual("UNMET", case["current_status"])
        self.assertEqual("DIRECT_ACCEPTANCE_CLOSURE", selection["work_class"])
        self.assertEqual(case["acceptance_case_root"], selection["acceptance_case_root"])
        self.assertEqual(selection["work_selection_root"], state["work_selection_root"])
        self.assertFalse(selection["implementation_effect_authorized"])
        self.assertEqual("NONE", state["authority_effect"])
        self.assertFalse(state["real_a5"])
        self.assertEqual("CLOSED", state["g0"])

    def test_native_point_of_use_subsystem_is_bound_without_product_admission(self):
        implementation = self.records["POINT-OF-USE-IMPLEMENTATION.json"]
        binding = self.records["NATIVE-BINDING.json"]
        self.assertEqual(
            "IMPLEMENTED_INFORMATION_ONLY_PENDING_QUALIFICATION",
            implementation["status"],
        )
        self.assertEqual(8, len(implementation["implemented_surfaces"]))
        self.assertFalse(implementation["product_program_admitted"])
        self.assertEqual(0, implementation["product_acceptance_cases_executed"])
        self.assertEqual(
            implementation["point_of_use_implementation_root"],
            binding["point_of_use_implementation_root"],
        )
        self.assertFalse(binding["program_admitted"])


if __name__ == "__main__":
    unittest.main()
