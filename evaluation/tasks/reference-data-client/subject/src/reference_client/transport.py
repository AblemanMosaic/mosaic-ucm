from __future__ import annotations

from typing import Protocol

from .domain import ReferenceRecord


class ReferenceTransport(Protocol):
    def fetch(self, key: str) -> ReferenceRecord: ...
