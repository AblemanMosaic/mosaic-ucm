from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import Refusal
from uclop.operational_canonical import OperationalCanonicalWorkbench, make_system_manifest
from uclop.operational_explanation import make_semantic_inventory_contract
from uclop.operational_realization import make_space_contract


class CompatibilityScopeTests(unittest.TestCase):
    def setUp(self):
        self.realization = make_space_contract(
            contract_id="scope-test",
            subject_root="1" * 64,
            axes=[{
                "id": "FLAG", "kind": "BOOLEAN", "domain": [False, True],
                "default": False, "description": "bounded fixture",
            }],
            hard_constraints=[],
            objectives=[],
            identity_axes=[],
        )
        self.inventory = make_semantic_inventory_contract(
            contract_id="semantic-scope",
            predecessor_root="2" * 64,
            successor_root="3" * 64,
            predecessor_claims=[{"id": "C1", "statement": "preserved"}],
            successor_claims=[{"id": "C1", "statement": "preserved"}],
        )
        self.manifest = make_system_manifest(
            source_root="4" * 64,
            maturity_registry_root="5" * 64,
            realization_contract_roots={"R": self.realization["root"]},
            semantic_inventory_roots={"S": self.inventory["root"]},
        )
        self.workbench = OperationalCanonicalWorkbench(
            self.manifest,
            {"R": self.realization},
            expected_manifest_root=self.manifest["root"],
            expected_maturity_registry_root="5" * 64,
            semantic_inventories={"S": self.inventory},
        )

    def _request(self, payload):
        return {
            "schema": "ucl.ucm.operational_request.v1",
            "surface": "MAKE_SEMANTIC_CHANGE_PLAN",
            "payload": payload,
            "request_id": "scope-test",
            "manifest_root": self.manifest["root"],
        }

    def test_semantic_plan_uses_manifest_pinned_inventory(self):
        response = self.workbench.dispatch(self._request({
            "inventory_id": "S",
            "evidence_checks": {},
            "expected_evidence_roots": {},
            "method": "test",
        }))
        self.assertEqual(response["result"]["inventory_contract_root"], self.inventory["root"])

    def test_request_cannot_supply_its_own_inventory_scope(self):
        with self.assertRaises(Refusal):
            self.workbench.dispatch(self._request({
                "inventory_contract": self.inventory,
                "expected_inventory_contract_root": self.inventory["root"],
                "evidence_checks": {},
                "expected_evidence_roots": {},
                "method": "test",
            }))


if __name__ == "__main__":
    unittest.main()
