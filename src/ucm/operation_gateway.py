"""Receipt-mediated operational gateway for Stage I4 c5.

UCM does not own or select an executor.  It verifies a bounded external permit,
durably records dispatch intent before an effect, and accepts only receipts
signed by the executor pinned in that permit.  Journal state is authoritative;
progress output is never authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .identity import validate_signing_key
from .journal import CampaignJournal, JournalRefusal
from .progress import Progress


PERMIT_SCHEMA = "mosaic.ucm.external-operation-permit.v0.1"
REVOCATION_SCHEMA = "mosaic.ucm.permit-revocation-registry.v0.1"
CONTRACT_SCHEMA = "mosaic.ucm.operational-contract.v0.1"
G1_SCHEMA = "mosaic.ucm.operational-g1-receipt.v0.1"
DISPATCH_AUTH_SCHEMA = "mosaic.ucm.external-dispatch-authorization.v0.1"
DISPATCH_SCHEMA = "mosaic.ucm.external-dispatch-receipt.v0.1"
TERMINAL_SCHEMA = "mosaic.ucm.external-terminal-receipt.v0.1"
G2_SCHEMA = "mosaic.ucm.operational-g2-receipt.v0.1"
G3_SCHEMA = "mosaic.ucm.operational-g3-receipt.v0.1"
STATE_SCHEMA = "mosaic.ucm.operational-state.v0.1"

EFFECT_CLASSES = {
    "READ_STATE", "WRITE_WORKSPACE", "WRITE_EXTERNAL", "NETWORK",
    "INSTALL", "PROCESS", "DEVICE", "AUTHORITY_CHANGE",
}
TERMINAL_STATES = {"COMPLETED", "FAILED", "DIVERGED", "CANCELLED"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _integer(value: Any, code: str, *, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, code)
    return value


def _public_key(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 64, code)
    try:
        bytes.fromhex(value)
        validate_signing_key(value)
    except (ValueError, TypeError):
        require(False, code)
    return value


def _signature(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 128, code)
    try:
        bytes.fromhex(value)
    except ValueError:
        require(False, code)
    return value


def _verify_ed25519(*, public_key_hex: str, signature_hex: str,
                    message: bytes, code: str) -> None:
    _public_key(public_key_hex, code)
    _signature(signature_hex, code)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise ValueError("OPERATION_DEPENDENCY_MISSING_CRYPTOGRAPHY") from error
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), message)
    except InvalidSignature:
        require(False, code)


def _budget(value: Any) -> dict[str, int]:
    item = exact_keys(value, {"max_cases", "max_duration_ms", "max_output_bytes"})
    for name in item:
        _integer(item[name], "OPERATION_BUDGET_INVALID", minimum=1)
    return deepcopy(item)


def _effects(value: Any, code: str) -> list[str]:
    require(type(value) is list and bool(value)
            and value == sorted(set(value))
            and all(type(item) is str and item in EFFECT_CLASSES for item in value), code)
    return list(value)


def _signed_body(item: dict[str, Any], *, signature_field: str,
                 root_field: str) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in item.items()
            if key not in {signature_field, root_field}}


def validate_revocation_registry(value: Any, *, expected_root: str,
                                 expected_issuer_public_key_hex: str,
                                 expected_jurisdiction_root: str,
                                 expected_generation: int,
                                 now: int) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "issuer_public_key_hex", "jurisdiction_root", "generation",
        "sequence", "valid_at", "revoked_permit_roots", "predecessor_root",
        "standing", "authority_effect", "real_a5", "g0", "signature_hex",
        "revocation_registry_root",
    })
    require(item["schema"] == REVOCATION_SCHEMA,
            "OPERATION_REVOCATION_SCHEMA_INVALID")
    issuer = _public_key(item["issuer_public_key_hex"],
                         "OPERATION_REVOCATION_ISSUER_INVALID")
    require(issuer == _public_key(expected_issuer_public_key_hex,
                                  "OPERATION_REVOCATION_ISSUER_INVALID"),
            "OPERATION_REVOCATION_ISSUER_INVALID")
    require(item["jurisdiction_root"] == require_root(expected_jurisdiction_root),
            "OPERATION_REVOCATION_JURISDICTION_INVALID")
    require(item["generation"] == _integer(expected_generation,
            "OPERATION_REVOCATION_GENERATION_INVALID", minimum=1),
            "OPERATION_REVOCATION_GENERATION_INVALID")
    _integer(item["sequence"], "OPERATION_REVOCATION_SEQUENCE_INVALID")
    require(item["valid_at"] <= _integer(now, "OPERATION_TIME_INVALID"),
            "OPERATION_REVOCATION_FUTURE_INVALID")
    require(type(item["revoked_permit_roots"]) is list
            and item["revoked_permit_roots"] == sorted(set(item["revoked_permit_roots"])),
            "OPERATION_REVOCATION_LIST_INVALID")
    for permit_root in item["revoked_permit_roots"]:
        require_root(permit_root)
    require_root(item["predecessor_root"])
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "OPERATION_AUTHORITY_CEILING_INVALID")
    unsigned = _signed_body(item, signature_field="signature_hex",
                            root_field="revocation_registry_root")
    _verify_ed25519(public_key_hex=issuer, signature_hex=item["signature_hex"],
                    message=canonical_bytes(unsigned),
                    code="OPERATION_REVOCATION_SIGNATURE_INVALID")
    require(item["revocation_registry_root"] == root({
        **unsigned, "signature_hex": item["signature_hex"]
    }) and item["revocation_registry_root"] == require_root(expected_root),
            "OPERATION_REVOCATION_ROOT_INVALID")
    return deepcopy(item)


def validate_permit(value: Any, *, expected_issuer_public_key_hex: str,
                    expected_jurisdiction_root: str,
                    expected_revocation_registry: Any,
                    expected_revocation_registry_root: str,
                    now: int) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "permit_id", "issuer_public_key_hex", "subject_identity_root",
        "session_root", "jurisdiction_root", "application_id", "action_id",
        "request_root", "executor_public_key_hex", "allowed_effect_classes",
        "budget", "rollback_root", "generation", "nonce", "issued_at",
        "not_before", "expires_at", "revocation_registry_root", "standing",
        "authority_effect", "real_a5", "g0", "signature_hex", "permit_root",
    })
    require(item["schema"] == PERMIT_SCHEMA, "OPERATION_PERMIT_SCHEMA_INVALID")
    _identifier(item["permit_id"], "OPERATION_PERMIT_ID_INVALID")
    _identifier(item["application_id"], "OPERATION_APPLICATION_ID_INVALID")
    _identifier(item["action_id"], "OPERATION_ACTION_ID_INVALID")
    issuer = _public_key(item["issuer_public_key_hex"],
                         "OPERATION_PERMIT_ISSUER_INVALID")
    require(issuer == _public_key(expected_issuer_public_key_hex,
                                  "OPERATION_PERMIT_ISSUER_INVALID"),
            "OPERATION_PERMIT_ISSUER_INVALID")
    for name in ("subject_identity_root", "session_root", "jurisdiction_root",
                 "request_root", "rollback_root", "nonce",
                 "revocation_registry_root"):
        require_root(item[name])
    require(item["jurisdiction_root"] == require_root(expected_jurisdiction_root),
            "OPERATION_PERMIT_JURISDICTION_INVALID")
    _public_key(item["executor_public_key_hex"],
                "OPERATION_EXECUTOR_KEY_INVALID")
    _effects(item["allowed_effect_classes"], "OPERATION_EFFECTS_INVALID")
    _budget(item["budget"])
    generation = _integer(item["generation"],
                          "OPERATION_PERMIT_GENERATION_INVALID", minimum=1)
    for name in ("issued_at", "not_before", "expires_at"):
        _integer(item[name], "OPERATION_PERMIT_TIME_INVALID")
    now = _integer(now, "OPERATION_TIME_INVALID")
    require(item["issued_at"] <= item["not_before"] <= now < item["expires_at"],
            "OPERATION_PERMIT_NOT_CURRENT")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "OPERATION_AUTHORITY_CEILING_INVALID")
    registry = validate_revocation_registry(
        expected_revocation_registry,
        expected_root=expected_revocation_registry_root,
        expected_issuer_public_key_hex=issuer,
        expected_jurisdiction_root=item["jurisdiction_root"],
        expected_generation=generation, now=now)
    require(item["revocation_registry_root"] == registry["revocation_registry_root"]
            and item.get("permit_root") not in registry["revoked_permit_roots"],
            "OPERATION_PERMIT_REVOKED_OR_STALE")
    unsigned = _signed_body(item, signature_field="signature_hex",
                            root_field="permit_root")
    _verify_ed25519(public_key_hex=issuer, signature_hex=item["signature_hex"],
                    message=canonical_bytes(unsigned),
                    code="OPERATION_PERMIT_SIGNATURE_INVALID")
    require(item["permit_root"] == root({
        **unsigned, "signature_hex": item["signature_hex"]
    }), "OPERATION_PERMIT_ROOT_INVALID")
    require(item["permit_root"] not in registry["revoked_permit_roots"],
            "OPERATION_PERMIT_REVOKED_OR_STALE")
    return deepcopy(item)


def build_operation_contract(*, operation_id: str, permit: Any,
                             revocation_registry: Any,
                             expected_issuer_public_key_hex: str,
                             expected_jurisdiction_root: str,
                             expected_revocation_registry_root: str,
                             requested_effect_classes: Any,
                             idempotency_key: str,
                             expected_result_root: str | None,
                             now: int) -> dict[str, Any]:
    permit = validate_permit(
        permit, expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry=revocation_registry,
        expected_revocation_registry_root=expected_revocation_registry_root,
        now=now)
    requested = _effects(requested_effect_classes, "OPERATION_EFFECTS_INVALID")
    require(set(requested) <= set(permit["allowed_effect_classes"]),
            "OPERATION_EFFECTS_NOT_AUTHORIZED")
    _identifier(operation_id, "OPERATION_ID_INVALID")
    require_root(idempotency_key)
    if expected_result_root is not None:
        require_root(expected_result_root)
    body = {
        "schema": CONTRACT_SCHEMA, "operation_id": operation_id,
        "application_id": permit["application_id"],
        "action_id": permit["action_id"], "request_root": permit["request_root"],
        "subject_identity_root": permit["subject_identity_root"],
        "session_root": permit["session_root"],
        "jurisdiction_root": permit["jurisdiction_root"],
        "executor_public_key_hex": permit["executor_public_key_hex"],
        "requested_effect_classes": requested, "budget": deepcopy(permit["budget"]),
        "rollback_root": permit["rollback_root"], "generation": permit["generation"],
        "idempotency_key": idempotency_key,
        "expected_result_root": expected_result_root,
        "authorization_time": now, "permit": permit,
        "revocation_registry": deepcopy(revocation_registry), **BOUNDARY,
    }
    return {**body, "contract_root": root(body)}


def validate_operation_contract(value: Any, *,
                                expected_issuer_public_key_hex: str,
                                expected_jurisdiction_root: str,
                                expected_revocation_registry_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "operation_id", "application_id", "action_id", "request_root",
        "subject_identity_root", "session_root", "jurisdiction_root",
        "executor_public_key_hex", "requested_effect_classes", "budget",
        "rollback_root", "generation", "idempotency_key", "expected_result_root",
        "authorization_time", "permit", "revocation_registry", "standing",
        "authority_effect", "real_a5", "g0", "contract_root",
    })
    require(item["schema"] == CONTRACT_SCHEMA,
            "OPERATION_CONTRACT_SCHEMA_INVALID")
    expected = build_operation_contract(
        operation_id=item["operation_id"], permit=item["permit"],
        revocation_registry=item["revocation_registry"],
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root,
        requested_effect_classes=item["requested_effect_classes"],
        idempotency_key=item["idempotency_key"],
        expected_result_root=item["expected_result_root"],
        now=item["authorization_time"])
    require(item == expected, "OPERATION_CONTRACT_INVALID")
    return deepcopy(item)


def _rooted(value: Any, *, root_field: str, schema: str, code: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema, code)
    body = {key: deepcopy(raw) for key, raw in value.items() if key != root_field}
    require(value.get(root_field) == root(body), code)
    require({key: value.get(key) for key in BOUNDARY} == BOUNDARY,
            "OPERATION_AUTHORITY_CEILING_INVALID")
    return deepcopy(value)


def _signed_executor_receipt(value: Any, *, schema: str, root_field: str,
                             expected_public_key_hex: str,
                             expected_fields: set[str], code: str) -> dict[str, Any]:
    item = exact_keys(value, expected_fields | set(BOUNDARY)
                      | {"signature_hex", root_field})
    require(item["schema"] == schema, code)
    unsigned = _signed_body(item, signature_field="signature_hex",
                            root_field=root_field)
    _verify_ed25519(public_key_hex=expected_public_key_hex,
                    signature_hex=item["signature_hex"],
                    message=canonical_bytes(unsigned), code=code)
    require(item[root_field] == root({
        **unsigned, "signature_hex": item["signature_hex"]
    }), code)
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "OPERATION_AUTHORITY_CEILING_INVALID")
    return deepcopy(item)


def derive_operation_state(*, operation_id: str, events: Any) -> dict[str, Any]:
    _identifier(operation_id, "OPERATION_ID_INVALID")
    require(type(events) is list, "OPERATION_EVENTS_INVALID")
    seen_event_ids: set[str] = set()
    for row in events:
        require(type(row) is dict and row.get("event_root") == root({
            key: deepcopy(raw) for key, raw in row.items() if key != "event_root"
        }), "OPERATION_JOURNAL_EVENT_ROOT_INVALID")
        require(type(row.get("event_id")) is str and row["event_id"] not in seen_event_ids,
                "OPERATION_JOURNAL_EVENT_ID_INVALID")
        seen_event_ids.add(row["event_id"])
    relevant = [deepcopy(row) for row in events
                if row.get("payload", {}).get("operation_id") == operation_id
                and row.get("event_type", "").startswith("OPERATION_")]
    state = "EMPTY"
    contract_root = None
    roots = {"g1_root": None, "dispatch_authorization_root": None,
             "dispatch_root": None, "terminal_receipt_root": None,
             "g2_root": None, "g3_root": None}
    expected = {
        "OPERATION_AUTHORIZED": ({"EMPTY"}, "AUTHORIZED"),
        "OPERATION_G1_RECORDED": ({"AUTHORIZED"}, "SENTINEL_ALLOWED"),
        "OPERATION_DISPATCH_PREPARED": ({"SENTINEL_ALLOWED"}, "READY"),
        "OPERATION_DISPATCH_RECORDED": ({"READY"}, "DISPATCHED"),
        "OPERATION_OUTCOME_UNCERTAIN": ({"DISPATCHED"}, "UNCERTAIN"),
        "OPERATION_TERMINAL_RECORDED": ({"DISPATCHED", "UNCERTAIN"}, "WITNESSED"),
        "OPERATION_G3_RECORDED": ({"WITNESSED"}, None),
        "OPERATION_CANCELLED": ({"AUTHORIZED", "SENTINEL_ALLOWED", "READY"}, "CANCELLED"),
        "OPERATION_PROOF_RECORDED": (TERMINAL_STATES, None),
        "OPERATION_ARCHIVE_EXPORTED": (TERMINAL_STATES, None),
        "OPERATION_RECONCILED": ({"UNCERTAIN"}, "WITNESSED"),
    }
    for event in relevant:
        event_type = event["event_type"]
        require(event_type in expected and state in expected[event_type][0],
                "OPERATION_EVENT_ORDER_INVALID")
        payload = event["payload"]
        if contract_root is None:
            contract_root = payload.get("contract_root")
        require(payload.get("contract_root") == contract_root,
                "OPERATION_EVENT_CONTRACT_INVALID")
        if event_type == "OPERATION_G1_RECORDED":
            roots["g1_root"] = payload["g1"]["receipt_root"]
        elif event_type == "OPERATION_DISPATCH_PREPARED":
            roots["dispatch_authorization_root"] = payload["dispatch_authorization"]["receipt_root"]
        elif event_type == "OPERATION_DISPATCH_RECORDED":
            roots["dispatch_root"] = payload["dispatch_receipt"]["receipt_root"]
        elif event_type in {"OPERATION_TERMINAL_RECORDED", "OPERATION_RECONCILED"}:
            roots["terminal_receipt_root"] = payload["terminal_receipt"]["receipt_root"]
            roots["g2_root"] = payload["g2"]["receipt_root"]
        elif event_type == "OPERATION_G3_RECORDED":
            roots["g3_root"] = payload["g3"]["receipt_root"]
            state = payload["terminal_state"]
            require(state in TERMINAL_STATES, "OPERATION_TERMINAL_STATE_INVALID")
            continue
        following = expected[event_type][1]
        if following is not None:
            state = following
    body = {
        "schema": STATE_SCHEMA, "operation_id": operation_id,
        "contract_root": contract_root, "state": state,
        "event_roots": [row["event_root"] for row in relevant], **roots,
        "redispatch_allowed": False,
        "requires_reconciliation": state == "UNCERTAIN",
        "terminal": state in TERMINAL_STATES, **BOUNDARY,
    }
    return {**body, "state_root": root(body)}


def validate_operation_history(*, operation_id: str, events: Any,
                               expected_issuer_public_key_hex: str,
                               expected_jurisdiction_root: str,
                               expected_revocation_registry_root: str) -> dict[str, Any]:
    """Recheck every semantic record in one journaled operation."""
    state = derive_operation_state(operation_id=operation_id, events=events)
    relevant = [row for row in events
                if row.get("payload", {}).get("operation_id") == operation_id
                and row.get("event_type", "").startswith("OPERATION_")]
    require(bool(relevant) and relevant[0]["event_type"] == "OPERATION_AUTHORIZED",
            "OPERATION_HISTORY_INCOMPLETE")
    contract = validate_operation_contract(
        relevant[0]["payload"]["contract"],
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    require(relevant[0]["payload"]["contract_root"] == contract["contract_root"],
            "OPERATION_HISTORY_CONTRACT_INVALID")
    by_type = {row["event_type"]: row for row in relevant}
    if "OPERATION_G1_RECORDED" in by_type:
        g1 = _rooted(by_type["OPERATION_G1_RECORDED"]["payload"]["g1"],
                     root_field="receipt_root", schema=G1_SCHEMA,
                     code="OPERATION_G1_INVALID")
        require(g1["operation_id"] == operation_id
                and g1["contract_root"] == contract["contract_root"]
                and g1["permit_root"] == contract["permit"]["permit_root"]
                and g1["authorization_event_root"] == relevant[0]["event_root"]
                and g1["decision"] == "ALLOW"
                and g1["allowed_effect_classes"] == contract["requested_effect_classes"]
                and g1["budget"] == contract["budget"]
                and g1["rollback_root"] == contract["rollback_root"],
                "OPERATION_G1_SEMANTICS_INVALID")
    if "OPERATION_DISPATCH_PREPARED" in by_type:
        prepared = _rooted(
            by_type["OPERATION_DISPATCH_PREPARED"]["payload"]["dispatch_authorization"],
            root_field="receipt_root", schema=DISPATCH_AUTH_SCHEMA,
            code="OPERATION_DISPATCH_AUTHORIZATION_INVALID")
        require(prepared["operation_id"] == operation_id
                and prepared["contract_root"] == contract["contract_root"]
                and prepared["g1_root"] == state["g1_root"]
                and prepared["idempotency_key"] == contract["idempotency_key"]
                and prepared["status"] == "READY_FOR_EXTERNAL_DISPATCH",
                "OPERATION_DISPATCH_AUTHORIZATION_INVALID")
    if "OPERATION_DISPATCH_RECORDED" in by_type:
        dispatch = _signed_executor_receipt(
            by_type["OPERATION_DISPATCH_RECORDED"]["payload"]["dispatch_receipt"],
            schema=DISPATCH_SCHEMA, root_field="receipt_root",
            expected_public_key_hex=contract["executor_public_key_hex"],
            expected_fields={"schema", "operation_id", "contract_root", "g1_root",
                             "dispatch_authorization_root", "idempotency_key",
                             "dispatch_nonce", "started_at", "status"},
            code="OPERATION_DISPATCH_RECEIPT_INVALID")
        require(dispatch["operation_id"] == operation_id
                and dispatch["contract_root"] == contract["contract_root"]
                and dispatch["g1_root"] == state["g1_root"]
                and dispatch["dispatch_authorization_root"] == state["dispatch_authorization_root"]
                and dispatch["idempotency_key"] == contract["idempotency_key"]
                and dispatch["status"] == "DISPATCHED",
                "OPERATION_DISPATCH_BINDING_INVALID")
    terminal_rows = [row for row in relevant if row["event_type"]
                     in {"OPERATION_TERMINAL_RECORDED", "OPERATION_RECONCILED"}]
    if terminal_rows:
        require(len(terminal_rows) == 1, "OPERATION_TERMINAL_DUPLICATE")
        payload = terminal_rows[0]["payload"]
        terminal = _signed_executor_receipt(payload["terminal_receipt"],
            schema=TERMINAL_SCHEMA, root_field="receipt_root",
            expected_public_key_hex=contract["executor_public_key_hex"],
            expected_fields={"schema", "operation_id", "contract_root", "dispatch_root",
                             "terminal_status", "result_root", "output_bytes",
                             "completed_cases", "observed_effect_classes", "ended_at",
                             "receipt_nonce"}, code="OPERATION_TERMINAL_RECEIPT_INVALID")
        require(terminal["operation_id"] == operation_id
                and terminal["contract_root"] == contract["contract_root"]
                and terminal["dispatch_root"] == state["dispatch_root"]
                and set(terminal["observed_effect_classes"])
                    <= set(contract["requested_effect_classes"]),
                "OPERATION_TERMINAL_BINDING_INVALID")
        g2 = _rooted(payload["g2"], root_field="receipt_root", schema=G2_SCHEMA,
                     code="OPERATION_G2_INVALID")
        require(g2["operation_id"] == operation_id
                and g2["contract_root"] == contract["contract_root"]
                and g2["g1_root"] == state["g1_root"]
                and g2["dispatch_root"] == state["dispatch_root"]
                and g2["terminal_receipt_root"] == terminal["receipt_root"]
                and g2["result_root"] == terminal["result_root"],
                "OPERATION_G2_SEMANTICS_INVALID")
    if "OPERATION_G3_RECORDED" in by_type:
        g3 = _rooted(by_type["OPERATION_G3_RECORDED"]["payload"]["g3"],
                     root_field="receipt_root", schema=G3_SCHEMA,
                     code="OPERATION_G3_INVALID")
        require(g3["operation_id"] == operation_id
                and g3["contract_root"] == contract["contract_root"]
                and g3["g2_root"] == state["g2_root"],
                "OPERATION_G3_SEMANTICS_INVALID")
    return {"contract": contract, "state": state,
            "event_roots": [row["event_root"] for row in relevant]}


class OperationGateway:
    """Durable UCM-side operation lifecycle.  It never executes an effect."""

    def __init__(self, workspace: Path, *, progress: Progress | None = None) -> None:
        self.workspace = Path(workspace)
        self.journal = CampaignJournal(self.workspace / "journal")
        self.progress = progress or Progress()
        if not self.journal.events_path.exists() and not self.journal.head_path.exists():
            self.journal.initialize()
        require(self.journal.events_path.exists() and self.journal.head_path.exists(),
                "OPERATION_JOURNAL_PARTIAL")
        self.journal.verify()

    @staticmethod
    def _actor(contract: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"kind": "SYSTEM", "mosaic_id": None,
                "session_id": contract["session_root"] if contract else None}

    def state(self, operation_id: str) -> dict[str, Any]:
        return derive_operation_state(operation_id=operation_id,
                                      events=self.journal.verify())

    def recover_stale_lock(self, *, expected_head: str) -> dict[str, Any]:
        result = self.journal.recover_stale_lock(expected_head=expected_head)
        self.progress.emit("PHASE_PASS", phase="JOURNAL_LOCK_RECOVERED")
        return result

    def _contract_event(self, operation_id: str) -> dict[str, Any]:
        matches = [row for row in self.journal.verify()
                   if row["event_type"] == "OPERATION_AUTHORIZED"
                   and row["payload"].get("operation_id") == operation_id]
        require(len(matches) == 1, "OPERATION_NOT_AUTHORIZED")
        return matches[0]

    def contract(self, operation_id: str) -> dict[str, Any]:
        return deepcopy(self._contract_event(operation_id)["payload"]["contract"])

    def prepare(self, contract: Any, *, expected_issuer_public_key_hex: str,
                expected_jurisdiction_root: str,
                expected_revocation_registry_root: str) -> dict[str, Any]:
        contract = validate_operation_contract(
            contract, expected_issuer_public_key_hex=expected_issuer_public_key_hex,
            expected_jurisdiction_root=expected_jurisdiction_root,
            expected_revocation_registry_root=expected_revocation_registry_root)
        operation_id = contract["operation_id"]
        self.progress.emit("PHASE_START", phase="AUTHORIZE", operation_id=operation_id)
        actor = self._actor(contract)
        authorized = self.journal.append(
            event_id=f"{operation_id}:authorized", event_type="OPERATION_AUTHORIZED",
            actor=actor, payload={"operation_id": operation_id,
                                  "contract_root": contract["contract_root"],
                                  "contract": contract})
        g1_body = {
            "schema": G1_SCHEMA, "gate": "G1_SENTINEL",
            "operation_id": operation_id, "contract_root": contract["contract_root"],
            "permit_root": contract["permit"]["permit_root"],
            "authorization_event_root": authorized["event_root"],
            "decision": "ALLOW", "reason_codes": ["EXTERNAL_PERMIT_VERIFIED"],
            "allowed_effect_classes": contract["requested_effect_classes"],
            "budget": contract["budget"], "rollback_root": contract["rollback_root"],
            **BOUNDARY,
        }
        g1 = {**g1_body, "receipt_root": root(g1_body)}
        self.journal.append(event_id=f"{operation_id}:g1",
            event_type="OPERATION_G1_RECORDED", actor=actor,
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"], "g1": g1})
        dispatch_body = {
            "schema": DISPATCH_AUTH_SCHEMA, "operation_id": operation_id,
            "contract_root": contract["contract_root"], "g1_root": g1["receipt_root"],
            "idempotency_key": contract["idempotency_key"],
            "dispatch_nonce": root({"operation_id": operation_id,
                                     "idempotency_key": contract["idempotency_key"],
                                     "contract_root": contract["contract_root"]}),
            "status": "READY_FOR_EXTERNAL_DISPATCH", **BOUNDARY,
        }
        dispatch = {**dispatch_body, "receipt_root": root(dispatch_body)}
        self.journal.append(event_id=f"{operation_id}:dispatch-prepared",
            event_type="OPERATION_DISPATCH_PREPARED", actor=actor,
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "dispatch_authorization": dispatch})
        self.progress.emit("PHASE_PASS", phase="AUTHORIZE", operation_id=operation_id)
        return {"contract": contract, "g1": g1,
                "dispatch_authorization": dispatch, "state": self.state(operation_id)}

    def record_dispatch(self, operation_id: str, receipt: Any) -> dict[str, Any]:
        contract = self.contract(operation_id)
        state = self.state(operation_id)
        require(state["state"] == "READY", "OPERATION_NOT_READY_FOR_DISPATCH")
        item = _signed_executor_receipt(receipt, schema=DISPATCH_SCHEMA,
            root_field="receipt_root",
            expected_public_key_hex=contract["executor_public_key_hex"],
            expected_fields={"schema", "operation_id", "contract_root", "g1_root",
                             "dispatch_authorization_root", "idempotency_key",
                             "dispatch_nonce", "started_at", "status"},
            code="OPERATION_DISPATCH_RECEIPT_INVALID")
        require(item["operation_id"] == operation_id
                and item["contract_root"] == contract["contract_root"]
                and item["g1_root"] == state["g1_root"]
                and item["dispatch_authorization_root"] == state["dispatch_authorization_root"]
                and item["idempotency_key"] == contract["idempotency_key"]
                and item["status"] == "DISPATCHED",
                "OPERATION_DISPATCH_BINDING_INVALID")
        self.journal.append(event_id=f"{operation_id}:dispatched",
            event_type="OPERATION_DISPATCH_RECORDED", actor=self._actor(contract),
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "dispatch_receipt": item})
        self.progress.emit("PHASE_PASS", phase="DISPATCH_RECORDED",
                           operation_id=operation_id)
        return {"dispatch_receipt": item, "state": self.state(operation_id)}

    def mark_uncertain(self, operation_id: str, *, reason_code: str) -> dict[str, Any]:
        contract = self.contract(operation_id)
        require(self.state(operation_id)["state"] == "DISPATCHED",
                "OPERATION_UNCERTAIN_STATE_INVALID")
        _identifier(reason_code, "OPERATION_REASON_CODE_INVALID")
        event = self.journal.append(event_id=f"{operation_id}:uncertain",
            event_type="OPERATION_OUTCOME_UNCERTAIN", actor=self._actor(contract),
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "reason_code": reason_code})
        self.progress.emit("PHASE_FAIL", phase="OUTCOME_UNCERTAIN",
                           operation_id=operation_id, diagnostic=reason_code)
        return {"journal_event_root": event["event_root"],
                "state": self.state(operation_id)}

    def _terminal(self, operation_id: str, receipt: Any, *, reconcile: bool) -> dict[str, Any]:
        contract = self.contract(operation_id)
        state = self.state(operation_id)
        require(state["state"] == ("UNCERTAIN" if reconcile else "DISPATCHED"),
                "OPERATION_TERMINAL_STATE_INVALID")
        item = _signed_executor_receipt(receipt, schema=TERMINAL_SCHEMA,
            root_field="receipt_root",
            expected_public_key_hex=contract["executor_public_key_hex"],
            expected_fields={"schema", "operation_id", "contract_root", "dispatch_root",
                             "terminal_status", "result_root", "output_bytes",
                             "completed_cases", "observed_effect_classes", "ended_at",
                             "receipt_nonce"}, code="OPERATION_TERMINAL_RECEIPT_INVALID")
        require(item["operation_id"] == operation_id
                and item["contract_root"] == contract["contract_root"]
                and item["dispatch_root"] == state["dispatch_root"]
                and item["terminal_status"] in {"COMPLETED", "FAILED", "CANCELLED"}
                and set(_effects(item["observed_effect_classes"],
                                 "OPERATION_OBSERVED_EFFECTS_INVALID"))
                    <= set(contract["requested_effect_classes"])
                and type(item["output_bytes"]) is int
                and 0 <= item["output_bytes"] <= contract["budget"]["max_output_bytes"]
                and type(item["completed_cases"]) is int
                and 0 <= item["completed_cases"] <= contract["budget"]["max_cases"],
                "OPERATION_TERMINAL_BINDING_INVALID")
        require_root(item["result_root"]); require_root(item["receipt_nonce"])
        completion = item["terminal_status"]
        if (completion == "COMPLETED" and contract["expected_result_root"] is not None
                and item["result_root"] != contract["expected_result_root"]):
            classification = "DIVERGED"
        elif completion == "COMPLETED":
            classification = "PASS"
        else:
            classification = completion
        g2_body = {
            "schema": G2_SCHEMA, "gate": "G2_WITNESS",
            "operation_id": operation_id, "contract_root": contract["contract_root"],
            "g1_root": state["g1_root"], "dispatch_root": state["dispatch_root"],
            "terminal_receipt_root": item["receipt_root"],
            "completion_status": completion,
            "observed_effect_classes": item["observed_effect_classes"],
            "result_root": item["result_root"], "reconciled": reconcile, **BOUNDARY,
        }
        g2 = {**g2_body, "receipt_root": root(g2_body)}
        event_type = "OPERATION_RECONCILED" if reconcile else "OPERATION_TERMINAL_RECORDED"
        self.journal.append(event_id=f"{operation_id}:terminal",
            event_type=event_type, actor=self._actor(contract),
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "terminal_receipt": item, "g2": g2})
        g3_body = {
            "schema": G3_SCHEMA, "gate": "G3_DIAGNOSTIC",
            "operation_id": operation_id, "contract_root": contract["contract_root"],
            "g2_root": g2["receipt_root"], "classification": classification,
            "finding_codes": ([] if classification == "PASS"
                              else [f"OPERATION_{classification}"]),
            "next_action": ("ARCHIVE" if classification == "PASS"
                            else "REVIEW_AND_RECONCILE"), **BOUNDARY,
        }
        g3 = {**g3_body, "receipt_root": root(g3_body)}
        terminal_state = "COMPLETED" if classification == "PASS" else classification
        self.journal.append(event_id=f"{operation_id}:g3",
            event_type="OPERATION_G3_RECORDED", actor=self._actor(contract),
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "g3": g3, "terminal_state": terminal_state})
        self.progress.emit("PHASE_PASS" if classification == "PASS" else "PHASE_FAIL",
                           phase="TERMINAL", operation_id=operation_id,
                           classification=classification)
        return {"terminal_receipt": item, "g2": g2, "g3": g3,
                "state": self.state(operation_id)}

    def record_terminal(self, operation_id: str, receipt: Any) -> dict[str, Any]:
        return self._terminal(operation_id, receipt, reconcile=False)

    def reconcile(self, operation_id: str, receipt: Any) -> dict[str, Any]:
        return self._terminal(operation_id, receipt, reconcile=True)

    def cancel(self, operation_id: str, *, reason_code: str) -> dict[str, Any]:
        contract = self.contract(operation_id)
        state = self.state(operation_id)
        require(state["state"] in {"AUTHORIZED", "SENTINEL_ALLOWED", "READY"},
                "OPERATION_CANCEL_TOO_LATE")
        _identifier(reason_code, "OPERATION_REASON_CODE_INVALID")
        body = {"schema": "mosaic.ucm.operation-cancellation.v0.1",
                "operation_id": operation_id, "contract_root": contract["contract_root"],
                "prior_state_root": state["state_root"], "reason_code": reason_code,
                **BOUNDARY}
        cancellation = {**body, "receipt_root": root(body)}
        self.journal.append(event_id=f"{operation_id}:cancelled",
            event_type="OPERATION_CANCELLED", actor=self._actor(contract),
            payload={"operation_id": operation_id,
                     "contract_root": contract["contract_root"],
                     "cancellation": cancellation})
        self.progress.emit("PHASE_PASS", phase="CANCELLED", operation_id=operation_id)
        return {"cancellation": cancellation, "state": self.state(operation_id)}


def gateway_from_workspace(workspace: str | Path,
                           progress_path: str | Path | None = None) -> OperationGateway:
    return OperationGateway(Path(workspace),
        progress=Progress(Path(progress_path)) if progress_path is not None else Progress())
