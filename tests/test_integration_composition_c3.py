from __future__ import annotations

from copy import deepcopy
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import root
from ucm.composition import build_preflight, declaration_template

from _integration_c2_helpers import stage1_bundle


class CompositionC3Tests(unittest.TestCase):
    def test_preflight_refuses_to_infer_relations(self):
        with tempfile.TemporaryDirectory() as folder:
            raw, _ = stage1_bundle(pathlib.Path(folder))
            bundle = pathlib.Path(folder) / "app.zip"
            bundle.write_bytes(raw)
            result = build_preflight([bundle])
        self.assertEqual(result["status"], "DECLARATIONS_REQUIRED")
        self.assertEqual(result["missing_declarations"], ["EXAMPLE.PORTABLE_AGENT"])
        self.assertFalse(result["composition_authorized"])

    def test_explicit_matching_relation_is_ready_for_court(self):
        with tempfile.TemporaryDirectory() as folder:
            raw, _ = stage1_bundle(pathlib.Path(folder))
            declaration = declaration_template(raw)
            declaration["exports"] = [{
                "capability_id": declaration["available_capabilities"][0]["id"],
                "interface_id": "TEST.INTERFACE",
                "schema_root": "1" * 64,
                "semantic_owner": declaration["semantic_authority"],
                "effect_executor": declaration["native_effect_executor"],
                "consumers": [declaration["application_id"]],
            }]
            declaration["imports"] = [{
                "provider_application_id": declaration["application_id"],
                "interface_id": "TEST.INTERFACE",
                "schema_root": "1" * 64,
                "required": True,
                "purpose": "self-test only",
            }]
            declaration["declared_relations_status"] = "DECLARED_INFORMATION_ONLY"
            declaration["declaration_root"] = root({k: deepcopy(v) for k, v in declaration.items()
                                                    if k != "declaration_root"})
            bundle = pathlib.Path(folder) / "app.zip"
            bundle.write_bytes(raw)
            result = build_preflight([bundle], [declaration])
        self.assertEqual(result["status"], "READY_FOR_CORRESPONDENCE_COURT")
        self.assertEqual(result["edges"][0]["status"], "MATCHED")
        self.assertFalse(result["composition_authorized"])

    def test_provider_cannot_speak_for_consumer(self):
        with tempfile.TemporaryDirectory() as folder:
            raw, _ = stage1_bundle(pathlib.Path(folder))
            declaration = declaration_template(raw)
            declaration["exports"] = [{
                "capability_id": declaration["available_capabilities"][0]["id"],
                "interface_id": "TEST.INTERFACE",
                "schema_root": "1" * 64,
                "semantic_owner": declaration["semantic_authority"],
                "effect_executor": declaration["native_effect_executor"],
                "consumers": [declaration["application_id"]],
            }]
            declaration["declared_relations_status"] = "DECLARED_INFORMATION_ONLY"
            declaration["declaration_root"] = root({k: deepcopy(v) for k, v in declaration.items()
                                                    if k != "declaration_root"})
            bundle = pathlib.Path(folder) / "app.zip"; bundle.write_bytes(raw)
            result = build_preflight([bundle], [declaration])
        self.assertEqual(result["status"], "DECLARATIONS_REQUIRED")
        self.assertEqual(result["issues"][0]["kind"], "CONSUMER_DECLARATION_MISSING")


if __name__ == "__main__":
    unittest.main()
