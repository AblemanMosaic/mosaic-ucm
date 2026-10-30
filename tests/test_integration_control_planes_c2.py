from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal, root
from ucm.control_planes import verify_control_plane_disposition
from _integration_c2_helpers import control


class ControlPlaneTests(unittest.TestCase):
    def test_valid_native_control_plane_is_retained(self):
        self.assertEqual(verify_control_plane_disposition(control())["effect_executor"],
                         "APP.NATIVE")

    def test_semantic_and_effect_collisions_refuse(self):
        value = control()
        value["native_control_planes"].append({
            "id": "APP.SECOND", "role": "SECOND", "disposition": "ADAPT",
            "semantic_authority": True,
            "effect_classes": ["LOCAL_ARTIFACT_PREPARATION"],
            "equivalence_evidence_root": None})
        value["root"] = root({key: raw for key, raw in value.items() if key != "root"})
        with self.assertRaises(Refusal):
            verify_control_plane_disposition(value)

    def test_replace_requires_equivalence_evidence(self):
        value = control()
        value["native_control_planes"][0]["disposition"] = "REPLACE_AFTER_EQUIVALENCE"
        value["root"] = root({key: raw for key, raw in value.items() if key != "root"})
        with self.assertRaises(Refusal):
            verify_control_plane_disposition(value)


if __name__ == "__main__":
    unittest.main()
