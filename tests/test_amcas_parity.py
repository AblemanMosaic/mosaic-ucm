from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from uclop.canonical import root, strict_loads
from ucm.amcas_parity import (
    build_amcas_registry,
    build_profile_baseline_migration,
    build_portfolio_observatory,
    build_ucm_coverage_registry,
    compile_amcas_baseline,
    compile_stage_i3_profile_set,
    run_amcas_ucm_parity,
    semantic_diff_amcas,
)
from ucm.system import capability_registry

ROOT = Path(__file__).resolve().parents[1]


class AmcasParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = build_amcas_registry()
        cls.coverage = build_ucm_coverage_registry(cls.registry)
        cls.parity = run_amcas_ucm_parity(cls.registry, cls.coverage)
        cls.contract = strict_loads((ROOT / "examples/amcas/portable-agent.integration.json").read_bytes())

    def test_registry_is_fixed_and_self_rooted(self):
        self.assertEqual(26, len(self.registry["elements"]))
        self.assertEqual(self.registry["registry_root"], root({k: v for k, v in self.registry.items() if k != "registry_root"}))
        ids = [row["element_id"] for row in self.registry["elements"]]
        self.assertEqual(ids, sorted(set(ids)))

    def test_every_active_surface_is_accounted_once(self):
        active = {row["name"] for row in capability_registry()["surfaces"]}
        self.assertEqual(active, set(self.coverage["active_surface_assignments"]))
        self.assertEqual(len(active), self.coverage["active_surface_count"])
        self.assertEqual([], self.coverage["unaccounted_surface_names"])

    def test_baseline_compilation_preserves_contract_and_declares_gaps(self):
        program = compile_amcas_baseline(self.contract, amcas_registry_value=self.registry,
                                         coverage_value=self.coverage)
        self.assertEqual(self.contract["contract_root"], program["contract_root"])
        self.assertEqual(4, len(program["profile_bindings"]))
        self.assertEqual(26, len(program["element_requirements"]))
        self.assertEqual("READY_WITH_MIGRATION_OBLIGATIONS", program["status"])
        self.assertTrue(program["migration_obligations"])

    def test_semantic_diff_is_exact_and_authority_adjacent(self):
        changed = deepcopy(self.contract)
        changed["cm1"]["requirements"][0]["statement"] += " Exact bytes are mandatory."
        changed["integration_boundary"]["identity_binding_status"] = "PROPOSED"
        changed["contract_root"] = root({k: v for k, v in changed.items() if k != "contract_root"})
        result = semantic_diff_amcas(self.contract, changed)
        self.assertEqual(2, result["change_count"])
        self.assertEqual(2, result["authority_adjacent_change_count"])
        self.assertTrue(result["migration_required"])

    def test_parity_court_uses_fixed_registry_plus_surface_denominator(self):
        expected = len(self.registry["elements"]) + self.coverage["active_surface_count"]
        self.assertEqual(expected, self.parity["fixed_denominator"])
        self.assertEqual(expected, self.parity["completed_denominator"])
        self.assertEqual(0, self.parity["failed"])
        self.assertEqual("PASS_WITH_DECLARED_GAPS", self.parity["status"])

    def test_all_frozen_stage_i3_plans_receive_four_non_authorizing_profiles(self):
        plans = sorted((ROOT / "integration/stage-i3/authoring/plans").glob("*.json"))
        profiles = [compile_stage_i3_profile_set(strict_loads(path.read_bytes()),
                    self.registry, self.coverage) for path in plans]
        self.assertEqual(7, len(profiles))
        for result in profiles:
            self.assertEqual(["AUTHORING", "COMPATIBILITY", "OPERATIONAL", "VERIFY_ONLY"],
                             [row["profile_id"] for row in result["profiles"]])
            self.assertTrue(result["native_authority_preserved"])
            self.assertEqual("NONE", result["authority_effect"])
        observatory = build_portfolio_observatory(profile_sets=profiles,
            parity_result=self.parity)
        self.assertEqual(7, observatory["application_count"])
        self.assertEqual("PASS_OBSERVATION_ONLY", observatory["status"])
        self.assertIn("MOSAIC.UI", observatory["stage_i1_intake_required"])

    def test_profile_baseline_migration_preserves_fixed_application_denominator(self):
        migration = build_profile_baseline_migration()
        self.assertEqual(7, migration["row_count"])
        self.assertTrue(all(row["predecessor_profile_set_root"] !=
                            row["successor_profile_set_root"] for row in migration["rows"]))
        self.assertTrue(all(row["native_authority_preserved"] for row in migration["rows"]))


if __name__ == "__main__":
    unittest.main()


