"""Governed operation dispatch for semantic Mosaic UI applications."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .canonical import commitment
from .headless import HeadlessUI, LayoutProvider
from .model import UIRefusal
from .receipt_ledger import ReceiptLedger, ReceiptRetentionPolicy


EFFECT_CLASSES = ("PURE", "READ_LOCAL", "WRITE_LOCAL", "HOST_UI", "PROCESS", "NETWORK")


class RuntimeRefusal(UIRefusal):
    pass


@dataclass(frozen=True)
class RuntimePolicy:
    permitted_effects: tuple[str, ...] = ("PURE",)
    permitted_roots: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        unknown = sorted(set(self.permitted_effects) - set(EFFECT_CLASSES))
        if unknown:
            raise RuntimeRefusal("RUNTIME_POLICY_EFFECT_REFUSED", ",".join(unknown))

    def permits(self, effect: str) -> bool:
        return effect in self.permitted_effects

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.runtime-policy.v0.1",
            "permitted_effects": list(self.permitted_effects),
            "permitted_roots": sorted(str(path.resolve()) for path in self.permitted_roots),
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.RUNTIME_POLICY.v0.1", value)
        return value


@dataclass(frozen=True)
class OperationContext:
    operation_id: str
    sequence: int
    values: dict[str, Any]
    event: dict[str, Any]
    policy: RuntimePolicy

    def require_path(self, path: Path, *, write: bool = False) -> Path:
        effect = "WRITE_LOCAL" if write else "READ_LOCAL"
        if not self.policy.permits(effect):
            raise RuntimeRefusal("RUNTIME_EFFECT_REFUSED", effect)
        resolved = path.resolve()
        roots = [root.resolve() for root in self.policy.permitted_roots]
        if not roots or not any(resolved == root or root in resolved.parents for root in roots):
            raise RuntimeRefusal("RUNTIME_PATH_REFUSED", str(resolved))
        return resolved


@dataclass(frozen=True)
class OperationResult:
    message: str
    values: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)


Validator = Callable[[OperationContext], None]
Handler = Callable[[OperationContext], OperationResult]


def _accept(_: OperationContext) -> None:
    return None


@dataclass(frozen=True)
class OperationSpec:
    operation_id: str
    effect: str
    handler: Handler
    validate: Validator = _accept

    def __post_init__(self) -> None:
        if not self.operation_id or self.effect not in EFFECT_CLASSES or not callable(self.handler):
            raise RuntimeRefusal("OPERATION_SPEC_REFUSED", self.operation_id)


class GovernedRuntime:
    """Consumes closed UI intents and emits hash-chained, effect-bounded receipts."""

    def __init__(
        self,
        payload: dict[str, Any],
        operations: Iterable[OperationSpec],
        *,
        policy: RuntimePolicy | None = None,
        layout_provider: LayoutProvider | None = None,
        catalog: dict[str, Any] | None = None,
        receipt_policy: ReceiptRetentionPolicy | None = None,
        receipt_stream: Path | None = None,
    ) -> None:
        self.ui = HeadlessUI(payload, layout_provider, catalog=catalog)
        self.policy = policy or RuntimePolicy()
        specs = list(operations)
        self.operations = {spec.operation_id: spec for spec in specs}
        if len(self.operations) != len(specs):
            raise RuntimeRefusal("DUPLICATE_OPERATION_SPEC", "")
        declared = set(self.ui.application["declared_operation_ids"])
        unknown = sorted(set(self.operations) - declared)
        if unknown:
            raise RuntimeRefusal("UNDECLARED_OPERATION_SPEC", ",".join(unknown))
        self.pending: list[dict[str, Any]] = []
        self.ledger = ReceiptLedger(receipt_policy, stream_path=receipt_stream)
        self.receipts = self.ledger.receipts
        self.results: list[dict[str, Any]] = []
        self._intent_cursor = 0

    def dispatch(self, event: dict[str, Any], *, auto_run: bool = False) -> dict[str, Any]:
        before = self.ui.snapshot()["commitment"]
        state = self.ui.apply(copy.deepcopy(event))
        new_intents = self.ui.state["emitted_intents"][self._intent_cursor:]
        self._intent_cursor += len(new_intents)
        for intent in new_intents:
            operation_ref = intent.get("operation_ref")
            if operation_ref is None:
                operation_id = "INTERACTION:" + str(intent.get("node_id") or intent.get("intent") or "UNKNOWN")
                self._record_control_receipt(
                    intent, "INTERACTION", before, state["commitment"], operation_id=operation_id,
                )
                continue
            operation_id = str(operation_ref)
            operation_class = self.ui.lifecycle["operation_class"][operation_id]
            if operation_class != "LONG_RUNNING":
                self._record_control_receipt(intent, operation_class, before, state["commitment"])
                continue
            spec = self.operations.get(operation_id)
            if spec is None:
                self.ui.apply({"intent": "REFUSE", "message": "operation handler not registered"})
                raise RuntimeRefusal("OPERATION_HANDLER_MISSING", operation_id)
            request = {
                "operation_id": operation_id,
                "effect": spec.effect,
                "intent": copy.deepcopy(intent),
                "event": copy.deepcopy(event),
                "state_before": before,
                "state_requested": state["commitment"],
                "sequence": self.ledger.next_sequence(len(self.pending)),
            }
            request["request_commitment"] = commitment("MOSAIC.UI.RUNTIME_REQUEST.v0.1", request)
            self.pending.append(request)
        if auto_run:
            while self.pending:
                self.run_next()
        return self.snapshot()

    def _record_control_receipt(
        self, intent: dict[str, Any], operation_class: str, before: str, after: str,
        *, operation_id: str | None = None,
    ) -> None:
        receipt = {
            "schema": "mosaic.ui.runtime-receipt.v0.1",
            "sequence": self.ledger.next_sequence(),
            "operation_id": operation_id or intent["operation_ref"],
            "operation_class": operation_class,
            "effect": "PURE",
            "disposition": "APPLIED_CONTROL_TRANSITION",
            "request_commitment": commitment("MOSAIC.UI.RUNTIME_CONTROL_REQUEST.v0.1", intent),
            "state_before": before,
            "state_after": after,
            "result_commitment": None,
            "previous_receipt": self.ledger.head,
            "authority_effect": "NONE",
        }
        receipt["receipt_commitment"] = commitment("MOSAIC.UI.RUNTIME_RECEIPT.v0.1", receipt)
        self.ledger.append(receipt)

    def _retain_result(self, body: dict[str, Any]) -> str:
        stored = copy.deepcopy(body)
        stored["result_commitment"] = commitment("MOSAIC.UI.RUNTIME_RESULT.v0.1", stored)
        self.results.append(stored)
        if len(self.results) > self.ledger.policy.max_in_memory:
            self.results.pop(0)
        return str(stored["result_commitment"])

    def dispatch_interaction(
        self, event: dict[str, Any], operation_id: str, handler: Handler,
    ) -> dict[str, Any]:
        """Apply and reconcile one local interaction as an atomic, receipted transition."""
        if not operation_id or not callable(handler):
            raise RuntimeRefusal("INTERACTION_SPEC_REFUSED", operation_id)
        state_before = self.ui.snapshot()["commitment"]
        saved_state = copy.deepcopy(self.ui.state)
        sequence = self.ledger.next_sequence()
        request = {
            "operation_id": operation_id, "event": copy.deepcopy(event),
            "state_before": state_before, "sequence": sequence,
        }
        request_commitment = commitment("MOSAIC.UI.RUNTIME_INTERACTION_REQUEST.v0.1", request)
        disposition = "COMPLETE"
        try:
            self.ui.apply(copy.deepcopy(event))
            self._intent_cursor = len(self.ui.state["emitted_intents"])
            context = OperationContext(
                operation_id, sequence, copy.deepcopy(self.ui.state["values"]),
                copy.deepcopy(event), self.policy,
            )
            result = handler(context)
            if not isinstance(result, OperationResult):
                raise RuntimeRefusal("OPERATION_RESULT_REFUSED", operation_id)
            unknown = sorted(set(result.values) - set(self.ui.state["values"]))
            if unknown:
                raise RuntimeRefusal("OPERATION_UPDATE_KEY_REFUSED", ",".join(unknown))
            updates = copy.deepcopy(result.values)
            evidence = copy.deepcopy(result.evidence)
            message = result.message
            self.ui.state["values"].update(updates)
            self.ui.state["status"] = message
        except Exception as exc:
            disposition = "REFUSE"
            self.ui.state = saved_state
            self._intent_cursor = len(self.ui.state["emitted_intents"])
            updates = {}
            evidence = {"error_type": type(exc).__name__, "code": getattr(exc, "code", "HANDLER_EXCEPTION")}
            message = getattr(exc, "detail", str(exc)) or type(exc).__name__
            self.ui.state["status"] = message
        result_body = {
            "operation_id": operation_id, "effect": "PURE", "disposition": disposition,
            "message": message, "updates": updates, "evidence": evidence,
        }
        result_commitment = self._retain_result(result_body)
        receipt = {
            "schema": "mosaic.ui.runtime-receipt.v0.1", "sequence": sequence,
            "operation_id": operation_id, "operation_class": "INTERACTION", "effect": "PURE",
            "disposition": disposition, "request_commitment": request_commitment,
            "state_before": state_before, "state_after": self.ui.snapshot()["commitment"],
            "result_commitment": result_commitment, "previous_receipt": self.ledger.head,
            "authority_effect": "NONE",
        }
        receipt["receipt_commitment"] = commitment("MOSAIC.UI.RUNTIME_RECEIPT.v0.1", receipt)
        self.ledger.append(receipt)
        return copy.deepcopy(receipt)

    def run_next(self) -> dict[str, Any]:
        if not self.pending:
            raise RuntimeRefusal("NO_PENDING_OPERATION", "")
        request = self.pending.pop(0)
        spec = self.operations[request["operation_id"]]
        context = OperationContext(
            spec.operation_id, request["sequence"], copy.deepcopy(self.ui.state["values"]),
            copy.deepcopy(request["event"]), self.policy,
        )
        disposition = "COMPLETE"
        evidence: dict[str, Any]
        updates: dict[str, Any]
        message: str
        try:
            if not self.policy.permits(spec.effect):
                raise RuntimeRefusal("RUNTIME_EFFECT_REFUSED", spec.effect)
            spec.validate(context)
            self.ui.apply({"intent": "PROGRESS", "percent": 50, "stage": "executing", "elapsed_seconds": 0})
            result = spec.handler(context)
            if not isinstance(result, OperationResult):
                raise RuntimeRefusal("OPERATION_RESULT_REFUSED", spec.operation_id)
            unknown = sorted(set(result.values) - set(self.ui.state["values"]))
            if unknown:
                raise RuntimeRefusal("OPERATION_UPDATE_KEY_REFUSED", ",".join(unknown))
            updates, evidence, message = copy.deepcopy(result.values), copy.deepcopy(result.evidence), result.message
            self.ui.state["values"].update(updates)
            self.ui.apply({"intent": "COMPLETE", "message": message})
        except Exception as exc:
            disposition = "REFUSE"
            updates = {}
            evidence = {"error_type": type(exc).__name__, "code": getattr(exc, "code", "HANDLER_EXCEPTION")}
            message = getattr(exc, "detail", str(exc)) or type(exc).__name__
            if self.ui.state["active_operation"]:
                self.ui.apply({"intent": "REFUSE", "message": message})
        result_body = {
            "operation_id": spec.operation_id,
            "effect": spec.effect,
            "disposition": disposition,
            "message": message,
            "updates": updates,
            "evidence": evidence,
        }
        result_commitment = self._retain_result(result_body)
        receipt = {
            "schema": "mosaic.ui.runtime-receipt.v0.1",
            "sequence": request["sequence"],
            "operation_id": spec.operation_id,
            "operation_class": "LONG_RUNNING",
            "effect": spec.effect,
            "disposition": disposition,
            "request_commitment": request["request_commitment"],
            "state_before": request["state_before"],
            "state_after": self.ui.snapshot()["commitment"],
            "result_commitment": result_commitment,
            "previous_receipt": self.ledger.head,
            "authority_effect": "NONE",
        }
        receipt["receipt_commitment"] = commitment("MOSAIC.UI.RUNTIME_RECEIPT.v0.1", receipt)
        self.ledger.append(receipt)
        return copy.deepcopy(receipt)

    def snapshot(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.governed-runtime-state.v0.1",
            "ui": self.ui.snapshot(),
            "policy": self.policy.as_dict(),
            "pending": copy.deepcopy(self.pending),
            "receipts": copy.deepcopy(self.receipts),
            "results": copy.deepcopy(self.results),
            "ledger": self.ledger.summary(),
            "ledger_head": self.ledger.head,
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.GOVERNED_RUNTIME_STATE.v0.1", value)
        return value

    def export_receipts(self, path: Path) -> None:
        self.ledger.export(path)

    def export_receipt_stream(self, path: Path) -> None:
        self.ledger.export_stream(path)

    def checkpoint_receipts(self) -> dict[str, Any]:
        return self.ledger.checkpoint()

    def compact_receipts(self, retain: int | None = None) -> dict[str, Any]:
        return self.ledger.compact(retain)


__all__ = [
    "EFFECT_CLASSES", "GovernedRuntime", "OperationContext", "OperationResult", "OperationSpec",
    "RuntimePolicy", "RuntimeRefusal",
    "ReceiptRetentionPolicy",
]
