"""Bounded, hash-chained receipt retention for governed UI runtimes."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal


class ReceiptLedgerRefusal(UIRefusal):
    pass


@dataclass(frozen=True)
class ReceiptRetentionPolicy:
    max_in_memory: int = 1024
    checkpoint_interval: int = 256
    max_checkpoints: int = 64

    def __post_init__(self) -> None:
        for name, value in (
            ("max_in_memory", self.max_in_memory),
            ("checkpoint_interval", self.checkpoint_interval),
            ("max_checkpoints", self.max_checkpoints),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ReceiptLedgerRefusal("RECEIPT_RETENTION_POLICY_REFUSED", name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "mosaic.ui.receipt-retention-policy.v0.1",
            "max_in_memory": self.max_in_memory,
            "checkpoint_interval": self.checkpoint_interval,
            "max_checkpoints": self.max_checkpoints,
            "authority_effect": "NONE",
        }


class ReceiptLedger:
    """Retain a bounded tail while preserving chain and compaction commitments."""

    def __init__(
        self,
        policy: ReceiptRetentionPolicy | None = None,
        *,
        stream_path: Path | None = None,
    ) -> None:
        self.policy = policy or ReceiptRetentionPolicy()
        self.stream_path = stream_path.resolve() if stream_path is not None else None
        if self.stream_path is not None and self.stream_path.exists():
            raise ReceiptLedgerRefusal("RECEIPT_STREAM_EXISTS", str(self.stream_path))
        self._receipts: list[dict[str, Any]] = []
        self._checkpoints: list[dict[str, Any]] = []
        self._total_count = 0
        self._compacted_count = 0
        self._head: str | None = None
        self._compaction_root: str | None = None

    @property
    def receipts(self) -> list[dict[str, Any]]:
        return self._receipts

    @property
    def head(self) -> str | None:
        return self._head

    @property
    def total_count(self) -> int:
        return self._total_count

    def next_sequence(self, pending_count: int = 0) -> int:
        return self._total_count + pending_count + 1

    def append(self, receipt: dict[str, Any]) -> None:
        sequence = receipt.get("sequence")
        expected = self._total_count + 1
        if sequence != expected:
            raise ReceiptLedgerRefusal("RECEIPT_SEQUENCE_REFUSED", f"{sequence}!={expected}")
        if receipt.get("previous_receipt") != self._head:
            raise ReceiptLedgerRefusal("RECEIPT_CHAIN_REFUSED", str(sequence))
        observed = receipt.get("receipt_commitment")
        body = dict(receipt)
        body.pop("receipt_commitment", None)
        if observed != commitment("MOSAIC.UI.RUNTIME_RECEIPT.v0.1", body):
            raise ReceiptLedgerRefusal("RECEIPT_COMMITMENT_REFUSED", str(sequence))
        stored = copy.deepcopy(receipt)
        if self.stream_path is not None:
            self.stream_path.parent.mkdir(parents=True, exist_ok=True)
            with self.stream_path.open("ab") as stream:
                stream.write(canonical_bytes(stored) + b"\n")
                stream.flush()
        self._receipts.append(stored)
        self._total_count = expected
        self._head = str(observed)
        self.compact(self.policy.max_in_memory)
        if self._total_count % self.policy.checkpoint_interval == 0:
            self.checkpoint()

    def compact(self, retain: int | None = None) -> dict[str, Any]:
        retain = self.policy.max_in_memory if retain is None else retain
        if isinstance(retain, bool) or not isinstance(retain, int) or retain < 0:
            raise ReceiptLedgerRefusal("RECEIPT_COMPACTION_REFUSED", str(retain))
        while len(self._receipts) > retain:
            removed = self._receipts.pop(0)
            record = {
                "sequence": removed["sequence"],
                "receipt_commitment": removed["receipt_commitment"],
                "previous_compaction_root": self._compaction_root,
            }
            self._compaction_root = commitment("MOSAIC.UI.RECEIPT_COMPACTION.v0.1", record)
            self._compacted_count += 1
        return self.summary()

    def checkpoint(self) -> dict[str, Any]:
        body = {
            "schema": "mosaic.ui.receipt-checkpoint.v0.1",
            "sequence": self._total_count,
            "ledger_head": self._head,
            "compacted_count": self._compacted_count,
            "compaction_root": self._compaction_root,
            "previous_checkpoint": self._checkpoints[-1]["commitment"] if self._checkpoints else None,
            "authority_effect": "NONE",
        }
        body["commitment"] = commitment("MOSAIC.UI.RECEIPT_CHECKPOINT.v0.1", body)
        self._checkpoints.append(body)
        if len(self._checkpoints) > self.policy.max_checkpoints:
            self._checkpoints.pop(0)
        return copy.deepcopy(body)

    def summary(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.receipt-ledger-summary.v0.1",
            "policy": self.policy.as_dict(),
            "total_count": self._total_count,
            "retained_count": len(self._receipts),
            "first_retained_sequence": self._receipts[0]["sequence"] if self._receipts else None,
            "compacted_count": self._compacted_count,
            "compaction_root": self._compaction_root,
            "ledger_head": self._head,
            "checkpoints": copy.deepcopy(self._checkpoints),
            "streaming": "JSONL" if self.stream_path is not None else "NOT_CONFIGURED",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.RECEIPT_LEDGER_SUMMARY.v0.1", value)
        return value

    def export(self, path: Path) -> None:
        value = {
            "schema": "mosaic.ui.receipt-ledger-export.v0.1",
            "summary": self.summary(),
            "retained_receipts": copy.deepcopy(self._receipts),
            "claim_boundary": "COMPACTED_RECEIPT_BODIES_REQUIRE_A_CONFIGURED_STREAM",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.RECEIPT_LEDGER_EXPORT.v0.1", value)
        atomic_write(path, canonical_bytes(value) + b"\n")

    def export_stream(self, path: Path) -> None:
        if self.stream_path is None:
            data = b"".join(canonical_bytes(receipt) + b"\n" for receipt in self._receipts)
        else:
            data = self.stream_path.read_bytes() if self.stream_path.exists() else b""
        atomic_write(path, data)


__all__ = ["ReceiptLedger", "ReceiptLedgerRefusal", "ReceiptRetentionPolicy"]
