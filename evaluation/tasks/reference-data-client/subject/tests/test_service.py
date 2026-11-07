from __future__ import annotations

import unittest

from reference_client import ReferenceDataService
from reference_client.domain import ReferenceRecord


class FakeTransport:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, key: str) -> ReferenceRecord:
        self.calls += 1
        return ReferenceRecord(key, f"value:{key}")


class ServiceTests(unittest.TestCase):
    def test_fetch_uses_transport(self) -> None:
        transport = FakeTransport()
        result = ReferenceDataService(transport).fetch("alpha")
        self.assertEqual(result, ReferenceRecord("alpha", "value:alpha"))
        self.assertEqual(transport.calls, 1)


if __name__ == "__main__":
    unittest.main()
