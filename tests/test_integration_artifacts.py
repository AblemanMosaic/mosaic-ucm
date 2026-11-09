from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucm.artifacts import build_integration_kit, deterministic_zip, verify_deterministic_zip
from ucm.integration import IntegrationCampaign
from _amcas_helpers import contract


class ArtifactTests(unittest.TestCase):
    def test_deterministic_archive_and_mutation_refusal(self):
        raw = deterministic_zip({"A.txt": b"a"}, schema="example.v1", artifact_role="EXAMPLE")
        self.assertEqual(raw, deterministic_zip({"A.txt": b"a"}, schema="example.v1", artifact_role="EXAMPLE"))
        verify_deterministic_zip(raw, expected_schema="example.v1", expected_role="EXAMPLE")
        with self.assertRaises(Exception):
            verify_deterministic_zip(raw[:-1] + bytes([raw[-1] ^ 1]),
                                     expected_schema="example.v1", expected_role="EXAMPLE")

    def test_integration_kit_is_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            campaign = IntegrationCampaign.create(Path(temp) / "campaign", contract())
            raw = build_integration_kit(campaign)
            result = verify_deterministic_zip(raw,
                expected_schema="mosaic.ucm.integration-kit.v0.1",
                expected_role="APPLICATION_INTEGRATION_KIT")
            self.assertEqual(len(result["files"]), 4)


if __name__ == "__main__":
    unittest.main()
