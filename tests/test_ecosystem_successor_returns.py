from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.artifacts import deterministic_zip
from ucm.ecosystem_successor_returns import (
    PACKAGE_ROLE, PACKAGE_SCHEMA, build_successor_return_index,
    receive_successor_return,
)


class EcosystemSuccessorReturnTests(unittest.TestCase):
    def setUp(self):
        self.dispatch = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-NEXT-WORK-DISPATCH.json").read_bytes())

    def test_successor_return_binds_prior_return_without_authority(self):
        raw = b'{"status":"ADDRESSED_PENDING_REVIEW"}'
        result = receive_successor_return(
            self.dispatch, application_id="MOSAIC.MESSENGER_CRYSTAL",
            artifact_raw=raw, artifact_filename="RETURN.json",
            claimed_status="ADDRESSED_PENDING_REVIEW")
        prior = next(row for row in self.dispatch["applications"]
                     if row["application_id"] == "MOSAIC.MESSENGER_CRYSTAL")
        self.assertEqual(result["prior_return_envelope_root"],
                         prior["return_envelope_root"])
        self.assertEqual(result["integration_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(result["hold_clearance"], "NOT_ESTABLISHED")
        self.assertEqual(result["authority_effect"], "NONE")

    def test_partial_successor_index_preserves_fixed_denominator(self):
        raw = b'{"status":"ADDRESSED_PENDING_REVIEW"}'
        envelope = receive_successor_return(
            self.dispatch, application_id="MOSAIC.MESSENGER_CRYSTAL",
            artifact_raw=raw, artifact_filename="RETURN.json",
            claimed_status="ADDRESSED_PENDING_REVIEW")
        package = deterministic_zip({
            "RETURN-ENVELOPE.json": canonical_bytes(envelope),
            "returned/RETURN.json": raw,
        }, schema=PACKAGE_SCHEMA, artifact_role=PACKAGE_ROLE)
        result = build_successor_return_index(
            self.dispatch, {"MESSENGER-RETURN.zip": package})
        self.assertEqual(result["fixed_denominator"], 7)
        self.assertEqual(result["received_count"], 1)
        self.assertEqual(result["pending_count"], 6)
        received = {row["application_id"] for row in result["applications"]
                    if row["return_status"] == "RECEIVED_UNVERIFIED"}
        self.assertEqual(received, {"MOSAIC.MESSENGER_CRYSTAL"})
        self.assertFalse(result["application_execution_authorized"])

    def test_frozen_successor_index_rebuilds_from_exact_packages(self):
        returns_dir = ROOT / "integration" / "successor-returns"
        packages = {path.name: path.read_bytes()
                    for path in sorted(returns_dir.glob("*.zip"))}
        result = build_successor_return_index(self.dispatch, packages)
        frozen = (ROOT / "integration" /
                  "ECOSYSTEM-SUCCESSOR-RETURN-INDEX.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(result["received_count"], len(packages))
        self.assertEqual(result["pending_count"], 7 - len(packages))
        received = {row["application_id"] for row in result["applications"]
                    if row["return_status"] == "RECEIVED_UNVERIFIED"}
        self.assertEqual(received, {
            "MOSAIC.2D_3D", "MOSAIC.AAC", "MOSAIC.FIELD_MODELER",
            "MOSAIC.MEDIA_CENTER", "MOSAIC.MEMORY_VAULT",
            "MOSAIC.MESSENGER_CRYSTAL", "MOSAIC.READER",
        })


if __name__ == "__main__":
    unittest.main()
