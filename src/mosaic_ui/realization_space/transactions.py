"""Reversible transaction lifecycle for applying selected configurations."""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable, Mapping
from typing import Any

from .core import RealizationSpaceError, canonical_root
from .registry import RealizationSpaceRegistry


ApplyHandler = Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]]


class RealizationTransactionManager:
    """Owns requested/prepared/effective state without owning domain semantics."""

    def __init__(self, registry: RealizationSpaceRegistry) -> None:
        self.registry = registry
        self._handlers: dict[str, ApplyHandler] = {}
        self._effective: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._sequence = 0
        self._lock = threading.RLock()

    def bind(self, contract_id: str, handler: ApplyHandler) -> None:
        self.registry.contract(contract_id)
        if contract_id in self._handlers:
            raise RealizationSpaceError("RSC_HANDLER_DUPLICATE", contract_id)
        self._handlers[contract_id] = handler

    def prime(self, contract_id: str, configuration: Mapping[str, Any]) -> None:
        """Record an inspected runtime baseline without applying it."""
        with self._lock:
            self._effective[contract_id] = self.registry.select(
                contract_id, requested=configuration,
            )

    def effective(self, contract_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if contract_id is None:
                return copy.deepcopy(self._effective)
            return copy.deepcopy(self._effective.get(contract_id, {}))

    def apply(self, contract_id: str, *, requested: Mapping[str, Any] | None = None,
              region_id: str | None = None, locks: tuple[str, ...] = (),
              seed: int | None = None, expected_sequence: int | None = None) -> dict[str, Any]:
        with self._lock:
            if expected_sequence is not None and expected_sequence != self._sequence:
                raise RealizationSpaceError("RSC_TRANSACTION_STALE", str(expected_sequence))
            if contract_id not in self._handlers:
                raise RealizationSpaceError("RSC_HANDLER_MISSING", contract_id)
            selection = self.registry.select(
                contract_id, requested=requested, region_id=region_id, locks=locks, seed=seed,
            )
            before = copy.deepcopy(self._effective.get(contract_id))
            if before is not None:
                changed_locks = [axis_id for axis_id in locks
                                 if selection["values"][axis_id] != before["values"][axis_id]]
                if changed_locks:
                    raise RealizationSpaceError("RSC_LOCKED_AXIS_CHANGE_REFUSED", ",".join(changed_locks))
            self._sequence += 1
            intent = {
                "schema": "mosaic.realization-transaction-intent.v0.1",
                "sequence": self._sequence,
                "contract_id": contract_id,
                "configuration_root": selection["configuration_root"],
                "before_root": before.get("configuration_root") if before else None,
                "authority_effect": "NONE",
            }
            intent["intent_root"] = canonical_root(intent)
            try:
                application = self._handlers[contract_id](copy.deepcopy(selection), before)
            except BaseException as exc:
                receipt = {
                    "schema": "mosaic.realization-transaction-receipt.v0.1",
                    "sequence": self._sequence,
                    "intent_root": intent["intent_root"],
                    "status": "REFUSED",
                    "error": f"{type(exc).__name__}:{exc}",
                    "effective_configuration_root": before.get("configuration_root") if before else None,
                    "authority_effect": "NONE",
                }
                receipt["receipt_root"] = canonical_root(receipt)
                self._history.append({"contract_id": contract_id, "before": before,
                                      "after": before, "receipt": receipt})
                raise
            if not isinstance(application, dict) or application.get("accepted") is not True:
                receipt = {
                    "schema": "mosaic.realization-transaction-receipt.v0.1",
                    "sequence": self._sequence, "intent_root": intent["intent_root"],
                    "status": "REFUSED", "error": "RSC_APPLICATION_REFUSED",
                    "effective_configuration_root": before.get("configuration_root") if before else None,
                    "authority_effect": "NONE",
                }
                receipt["receipt_root"] = canonical_root(receipt)
                self._history.append({"contract_id": contract_id, "before": before,
                                      "after": before, "receipt": receipt})
                raise RealizationSpaceError("RSC_APPLICATION_REFUSED", contract_id)
            self._effective[contract_id] = copy.deepcopy(selection)
            receipt = {
                "schema": "mosaic.realization-transaction-receipt.v0.1",
                "sequence": self._sequence,
                "intent_root": intent["intent_root"],
                "status": "EFFECTIVE",
                "application": copy.deepcopy(application),
                "effective_configuration_root": selection["configuration_root"],
                "authority_effect": "NONE",
            }
            receipt["receipt_root"] = canonical_root(receipt)
            self._history.append({"contract_id": contract_id, "before": before,
                                  "after": copy.deepcopy(selection), "receipt": receipt})
            self._redo.clear()
            return receipt

    def undo(self, contract_id: str) -> dict[str, Any]:
        with self._lock:
            index = next((i for i in range(len(self._history) - 1, -1, -1)
                          if self._history[i]["receipt"].get("status") == "EFFECTIVE"
                          and self._history[i]["contract_id"] == contract_id), None)
            if index is None:
                raise RealizationSpaceError("RSC_UNDO_EMPTY", contract_id)
            row = self._history[index]
            if row["before"] is None:
                raise RealizationSpaceError("RSC_UNDO_BASELINE_MISSING", contract_id)
            application = self._handlers[contract_id](copy.deepcopy(row["before"]), row["after"])
            if not isinstance(application, dict) or application.get("accepted") is not True:
                raise RealizationSpaceError("RSC_UNDO_APPLICATION_REFUSED", contract_id)
            self._history.pop(index)
            self._redo.append(row)
            self._effective[contract_id] = copy.deepcopy(row["before"])
            self._sequence += 1
            receipt = {
                "schema": "mosaic.realization-undo-receipt.v0.1",
                "sequence": self._sequence,
                "contract_id": contract_id,
                "application": copy.deepcopy(application),
                "restored_configuration_root": (
                    row["before"].get("configuration_root") if row["before"] else None
                ),
                "authority_effect": "NONE",
            }
            receipt["receipt_root"] = canonical_root(receipt)
            return receipt

    def receipt(self) -> dict[str, Any]:
        with self._lock:
            value = {
                "schema": "mosaic.realization-transaction-ledger.v0.1",
                "sequence": self._sequence,
                "effective": {key: row["configuration_root"]
                              for key, row in sorted(self._effective.items())},
                "history_receipts": [row["receipt"]["receipt_root"] for row in self._history],
                "redo_depth": len(self._redo),
                "authority_effect": "NONE",
            }
            value["ledger_root"] = canonical_root(value)
            return value
