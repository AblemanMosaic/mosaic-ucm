from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucm.identity import (Refusal, canonical, consume_durable_proof, create_challenge, create_passport,
                          create_proof, issue_durable_challenge)
from ucm.integration import IntegrationCampaign
from ucm.journal import CampaignJournal
from _amcas_helpers import contract


class IdentityTests(unittest.TestCase):
    def test_user_and_agent_identity_collision_refuses_before_workspace(self):
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(serialization.Encoding.Raw,
                                                   serialization.PublicFormat.Raw).hex()
        passport = create_passport(public)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / "passport.json"; path.write_bytes(canonical(passport))
            workspace = root / "campaign"
            with self.assertRaises(ValueError):
                IntegrationCampaign.create(workspace, contract(identities=True),
                    user_passport=path, expected_user_id=passport["mosaic_id"],
                    agent_passport=path, expected_agent_id=passport["mosaic_id"])
            self.assertFalse(workspace.exists())

    def test_challenge_is_consumed_once_across_restart(self):
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(serialization.Encoding.Raw,
                                                   serialization.PublicFormat.Raw).hex()
        passport = create_passport(public)
        with tempfile.TemporaryDirectory() as temp:
            journal = CampaignJournal(Path(temp) / "journal"); journal.initialize()
            now = int(time.time())
            issued = issue_durable_challenge(journal, passport,
                expected_mosaic_id=passport["mosaic_id"], session_mosaic_id="f" * 64,
                audience="TEST", context_sha256="e" * 64, issued_at=now,
                expires_at=now + 300, nonce="d" * 64, event_id="issue")
            proof = create_proof(passport, issued["challenge"], private.sign)
            checked = consume_durable_proof(journal, passport, proof,
                expected_challenge=issued["challenge"], expected_mosaic_id=passport["mosaic_id"],
                now=now + 1, event_id="consume")
            self.assertTrue(checked["session_authenticated"])
            restarted = CampaignJournal(Path(temp) / "journal")
            with self.assertRaises(Refusal):
                consume_durable_proof(restarted, passport, proof,
                    expected_challenge=issued["challenge"], expected_mosaic_id=passport["mosaic_id"],
                    now=now + 2, event_id="consume-again")


if __name__ == "__main__":
    unittest.main()
