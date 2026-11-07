"""Host-mediated, one-use navigation admission for Mosaic Reader.

This module never opens a URL. It validates a reference already present in a
canonical document, records a host decision, and releases the target once to the
same host actor. The external navigation effect remains owned by that host.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import secrets
from typing import Callable
from urllib.parse import urlparse

from .canonical import commitment
from .document_model import DocumentIR, DocumentReference


NAVIGATION_POLICIES = frozenset({"PROMPT", "ALLOWLIST_ONLY", "DISABLED"})
HOST_DECISIONS = frozenset({"ALLOW", "REFUSE"})


class NavigationRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


@dataclass(frozen=True)
class NavigationRequest:
    request_root: str
    document_root: str
    reference_id: str
    role: str
    label: str
    target: str
    scheme: str
    policy: str
    allowlist_key: str
    disposition: str = "PENDING_HOST_ADMISSION"
    authority_effect: str = "NONE"
    external_effect_executed: bool = False


@dataclass(frozen=True)
class NavigationAdmission:
    request_root: str
    decision: str
    host_actor: str
    capability: str | None
    receipt: dict


def _find_reference(document: DocumentIR, reference_id: str) -> DocumentReference | None:
    return next((
        reference
        for block in document.blocks
        for reference in block.references
        if reference.reference_id == reference_id
    ), None)


def _allowlist_key(target: str) -> str:
    parsed = urlparse(target)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"}:
        return (parsed.hostname or "").lower()
    return scheme


class NavigationGate:
    """Stateful admission gate with one-use, actor-bound release capabilities."""

    def __init__(self, *, token_factory: Callable[[], str] | None = None) -> None:
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._pending: dict[str, NavigationRequest] = {}
        self._capabilities: dict[str, dict[str, str]] = {}
        self._receipts: list[dict] = []
        self._previous_receipt_root = "GENESIS"

    @property
    def receipts(self) -> tuple[dict, ...]:
        return tuple(dict(item) for item in self._receipts)

    def _record(self, event: str, detail: dict) -> dict:
        value = {
            "schema": "mosaic.reader.navigation-receipt.v0.1",
            "sequence": len(self._receipts) + 1,
            "event": event,
            "detail": detail,
            "previous_receipt_root": self._previous_receipt_root,
            "authority_effect": "NONE",
            "external_effect_executed": False,
        }
        value["receipt_root"] = commitment("MOSAIC.READER.NAVIGATION_RECEIPT.v0.1", value)
        self._previous_receipt_root = value["receipt_root"]
        self._receipts.append(value)
        return dict(value)

    def _refuse(self, code: str, detail: str, *, request_root: str = "") -> None:
        self._record("REFUSED", {
            "code": code,
            "detail": detail,
            "request_root": request_root,
        })
        raise NavigationRefusal(code, detail)

    def request(
        self,
        document: DocumentIR,
        reference_id: str,
        *,
        policy: str = "PROMPT",
        allowlist: tuple[str, ...] | list[str] = (),
    ) -> NavigationRequest:
        if policy not in NAVIGATION_POLICIES:
            self._refuse("NAVIGATION_POLICY_REFUSED", str(policy))
        reference = _find_reference(document, reference_id)
        if reference is None:
            self._refuse("NAVIGATION_REFERENCE_REFUSED", str(reference_id))
        if reference.role != "LINK":
            self._refuse("NAVIGATION_ROLE_REFUSED", reference.role)
        if reference.disposition != "HOST_ADMISSION_REQUIRED":
            self._refuse("NAVIGATION_TARGET_REFUSED", reference.disposition)
        if policy == "DISABLED":
            self._refuse("NAVIGATION_DISABLED", reference.reference_id)
        key = _allowlist_key(reference.target)
        normalized_allowlist = {str(item).strip().lower() for item in allowlist}
        if policy == "ALLOWLIST_ONLY" and key not in normalized_allowlist:
            self._refuse("NAVIGATION_ALLOWLIST_REFUSED", key)
        body = {
            "document_root": document.document_root,
            "reference_id": reference.reference_id,
            "role": reference.role,
            "label": reference.label,
            "target": reference.target,
            "scheme": urlparse(reference.target).scheme.lower(),
            "policy": policy,
            "allowlist_key": key,
            "disposition": "PENDING_HOST_ADMISSION",
            "authority_effect": "NONE",
            "external_effect_executed": False,
        }
        request_root = commitment("MOSAIC.READER.NAVIGATION_REQUEST.v0.1", body)
        request = NavigationRequest(request_root=request_root, **body)
        self._pending[request_root] = request
        self._record("REQUESTED", {
            "request_root": request_root,
            "document_root": document.document_root,
            "reference_id": reference.reference_id,
            "policy": policy,
            "allowlist_key": key,
        })
        return request

    def decide(
        self,
        request_root: str,
        decision: str,
        *,
        host_actor: str,
    ) -> NavigationAdmission:
        if decision not in HOST_DECISIONS:
            self._refuse("NAVIGATION_DECISION_REFUSED", str(decision), request_root=request_root)
        actor = str(host_actor).strip()
        if not actor:
            self._refuse("NAVIGATION_HOST_ACTOR_REFUSED", "EMPTY", request_root=request_root)
        request = self._pending.pop(request_root, None)
        if request is None:
            self._refuse("NAVIGATION_REQUEST_STATE_REFUSED", request_root, request_root=request_root)
        capability = None
        capability_root = None
        if decision == "ALLOW":
            capability = self._token_factory()
            if not isinstance(capability, str) or len(capability) < 16:
                self._refuse("NAVIGATION_CAPABILITY_REFUSED", "TOKEN_FACTORY", request_root=request_root)
            capability_root = sha256(capability.encode("utf-8")).hexdigest()
            if capability_root in self._capabilities:
                self._refuse("NAVIGATION_CAPABILITY_REFUSED", "COLLISION", request_root=request_root)
            self._capabilities[capability_root] = {
                "request_root": request_root,
                "host_actor": actor,
                "target": request.target,
            }
        receipt = self._record("DECIDED", {
            "request_root": request_root,
            "decision": decision,
            "host_actor": actor,
            "capability_root": capability_root,
        })
        return NavigationAdmission(request_root, decision, actor, capability, receipt)

    def claim(self, capability: str, *, host_actor: str) -> tuple[str, dict]:
        capability_root = sha256(str(capability).encode("utf-8")).hexdigest()
        record = self._capabilities.get(capability_root)
        if record is None:
            self._refuse("NAVIGATION_CAPABILITY_STATE_REFUSED", capability_root)
        actor = str(host_actor).strip()
        if actor != record["host_actor"]:
            self._refuse(
                "NAVIGATION_HOST_ACTOR_MISMATCH",
                actor,
                request_root=record["request_root"],
            )
        self._capabilities.pop(capability_root)
        receipt = self._record("RELEASED_TO_HOST", {
            "request_root": record["request_root"],
            "host_actor": actor,
            "capability_root": capability_root,
            "target_root": sha256(record["target"].encode("utf-8")).hexdigest(),
        })
        return record["target"], receipt


__all__ = [
    "HOST_DECISIONS", "NAVIGATION_POLICIES", "NavigationAdmission", "NavigationGate",
    "NavigationRefusal", "NavigationRequest",
]
