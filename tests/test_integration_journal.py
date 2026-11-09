import json
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucm.journal import CampaignJournal, JournalRefusal


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = CampaignJournal(Path(self.temp.name) / "journal")
        self.journal.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_append_restart_and_head_recovery(self):
        event = self.journal.append(event_id="A", event_type="CAMPAIGN_CREATED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"value": 1})
        self.journal.head_path.write_text("{}", encoding="utf-8")
        reopened = CampaignJournal(self.journal.directory)
        self.assertEqual(reopened.head()["head"], event["event_root"])

    def test_idempotency_conflict_refuses(self):
        kwargs = dict(event_id="A", event_type="CAMPAIGN_CREATED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None})
        self.journal.append(**kwargs, payload={"value": 1})
        with self.assertRaises(JournalRefusal):
            self.journal.append(**kwargs, payload={"value": 2})

    def test_truncation_refuses(self):
        self.journal.append(event_id="A", event_type="CAMPAIGN_CREATED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None}, payload={})
        raw = self.journal.events_path.read_bytes()
        self.journal.events_path.write_bytes(raw[:-1])
        with self.assertRaises(JournalRefusal):
            self.journal.verify()


if __name__ == "__main__":
    unittest.main()
