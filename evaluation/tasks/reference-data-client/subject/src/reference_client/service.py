from __future__ import annotations

from .domain import ReferenceRecord
from .transport import ReferenceTransport


class ReferenceDataService:
    def __init__(self, transport: ReferenceTransport) -> None:
        self._transport = transport

    def fetch(self, key: str) -> ReferenceRecord:
        return self._transport.fetch(key)
