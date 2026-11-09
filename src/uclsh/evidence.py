from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import root, require_root, sha256_bytes
from .errors import require
from .kernel import Kernel


RECEIPT_DOMAIN = "UCL_SH_STAGE_RECEIPT_V1"
CAPSULE_DOMAIN = "UCL_SH_CONTINUITY_CAPSULE_V1"
DOSSIER_DOMAIN = "UCL_SH_FEDERATION_DOSSIER_V1"
FEDERATION_GENESIS_DOMAIN = "UCL_SH_FEDERATION_GENESIS_V2"
FEDERATION_STATE_DOMAIN = "UCL_SH_FEDERATION_STATE_V2"
PAIR_DOMAIN = "UCL_SH_EXACT_PAIR_ATTESTATION_V1"


def key_root(key_hex: str) -> str:
    require(type(key_hex) is str and len(key_hex) == 64 and all(ch in "0123456789abcdef" for ch in key_hex), "FIXTURE_KEY_INVALID")
    return sha256_bytes(bytes.fromhex(key_hex))


def signed(domain: str, body: dict[str, Any], key_hex: str, kernel: Kernel | None = None) -> dict[str, Any]:
    active = kernel or Kernel()
    return {
        "body": deepcopy(body),
        "body_root": root(body),
        "signature": active.invoke("HMAC_SIGN_DOMAIN", [domain, body, key_hex]),
    }


def verify_signed(record: dict[str, Any], domain: str, key_hex: str, kernel: Kernel | None = None) -> dict[str, Any]:
    active = kernel or Kernel()
    require(type(record) is dict and set(record) == {"body", "body_root", "signature"}, "SIGNED_RECORD_SHAPE_INVALID")
    require(record["body_root"] == root(record["body"]), "SIGNED_RECORD_ROOT_MISMATCH")
    active.invoke("HMAC_VERIFY_DOMAIN", [domain, record["body"], key_hex, record["signature"]])
    return record["body"]


def append_receipt(
    ledger: list[dict[str, Any]],
    *,
    workflow_root: str,
    stage_id: str,
    stage: str,
    event: str,
    input_roots: list[str],
    output: Any,
    key_hex: str,
    kernel: Kernel | None = None,
) -> dict[str, Any]:
    require(event in {"STAGE_COMPLETE", "STAGE_REFUSED"}, "RECEIPT_EVENT_INVALID")
    require(type(input_roots) is list and all(require_root(item, "$.input_roots") for item in input_roots), "RECEIPT_INPUT_ROOTS_INVALID")
    body = {
        "schema": "ucl.selfhost.stage_receipt.v1",
        "sequence": len(ledger) + 1,
        "predecessor": "GENESIS" if not ledger else ledger[-1]["entry_root"],
        "workflow_root": require_root(workflow_root, "$.workflow_root"),
        "stage_id": stage_id,
        "stage": stage,
        "event": event,
        "input_roots": input_roots,
        "output_root": root(output),
        "signer_key_root": key_root(key_hex),
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    record = signed(RECEIPT_DOMAIN, body, key_hex, kernel)
    entry = {**record, "entry_root": root(record)}
    ledger.append(entry)
    return entry


def verify_ledger(
    ledger: list[dict[str, Any]],
    *,
    workflow_root: str,
    key_hex: str,
    expected_count: int,
    expected_anchor: str,
    kernel: Kernel | None = None,
) -> dict[str, Any]:
    require(type(ledger) is list and len(ledger) == expected_count, "LEDGER_LENGTH_MISMATCH")
    predecessor = "GENESIS"
    completed: list[str] = []
    for index, entry in enumerate(ledger):
        require(type(entry) is dict and set(entry) == {"body", "body_root", "signature", "entry_root"}, "LEDGER_ENTRY_SHAPE_INVALID", f"$.ledger[{index}]")
        record = {key: entry[key] for key in ("body", "body_root", "signature")}
        body = verify_signed(record, RECEIPT_DOMAIN, key_hex, kernel)
        require(entry["entry_root"] == root(record), "LEDGER_ENTRY_ROOT_MISMATCH", f"$.ledger[{index}]")
        require(body["sequence"] == index + 1, "LEDGER_SEQUENCE_INVALID", f"$.ledger[{index}]")
        require(body["predecessor"] == predecessor, "LEDGER_PREDECESSOR_INVALID", f"$.ledger[{index}]")
        require(body["workflow_root"] == workflow_root, "LEDGER_WORKFLOW_MISMATCH", f"$.ledger[{index}]")
        require(body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "LEDGER_EFFECT_OR_STANDING_FORBIDDEN")
        predecessor = entry["entry_root"]
        if body["event"] == "STAGE_COMPLETE":
            completed.append(body["stage_id"])
    require(predecessor == expected_anchor, "LEDGER_ANCHOR_MISMATCH")
    return {
        "schema": "ucl.selfhost.ledger_verification.v1",
        "workflow_root": workflow_root,
        "count": len(ledger),
        "anchor": predecessor,
        "completed": completed,
        "complete": len(completed) == expected_count,
        "standing": "INFORMATION_ONLY",
    }


def make_capsule(
    *,
    program_root: str,
    workflow_root: str,
    sequence: int,
    phase: str,
    completed: list[str],
    pending: list[str],
    receipt_anchor: str,
    predecessor_capsule_root: str,
    key_hex: str,
) -> dict[str, Any]:
    require(type(sequence) is int and type(sequence) is not bool and sequence > 0, "CAPSULE_SEQUENCE_INVALID")
    require(type(completed) is list and len(completed) == len(set(completed)), "CAPSULE_COMPLETED_INVALID")
    require(type(pending) is list and len(pending) == len(set(pending)), "CAPSULE_PENDING_INVALID")
    require(not set(completed).intersection(pending), "CAPSULE_PHASE_OVERLAP")
    body = {
        "schema": "ucl.selfhost.continuity_capsule.v1",
        "program_root": require_root(program_root),
        "workflow_root": require_root(workflow_root),
        "sequence": sequence,
        "phase": phase,
        "completed": completed,
        "pending": pending,
        "receipt_anchor": require_root(receipt_anchor),
        "predecessor_capsule_root": predecessor_capsule_root,
        "key_root": key_root(key_hex),
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    record = signed(CAPSULE_DOMAIN, body, key_hex)
    return {**record, "capsule_root": root(record)}


def verify_capsule(
    capsule: dict[str, Any],
    *,
    key_hex: str,
    expected_program_root: str,
    expected_workflow_root: str,
    expected_sequence: int,
    expected_predecessor: str,
    expected_receipt_anchor: str,
) -> dict[str, Any]:
    require(type(capsule) is dict and set(capsule) == {"body", "body_root", "signature", "capsule_root"}, "CAPSULE_SHAPE_INVALID")
    record = {key: capsule[key] for key in ("body", "body_root", "signature")}
    body = verify_signed(record, CAPSULE_DOMAIN, key_hex)
    require(capsule["capsule_root"] == root(record), "CAPSULE_ROOT_MISMATCH")
    require(body["program_root"] == expected_program_root, "CAPSULE_PROGRAM_MISMATCH")
    require(body["workflow_root"] == expected_workflow_root, "CAPSULE_WORKFLOW_MISMATCH")
    require(body["sequence"] == expected_sequence, "CAPSULE_STALE_OR_FUTURE")
    require(body["predecessor_capsule_root"] == expected_predecessor, "CAPSULE_LINEAGE_MISMATCH")
    require(body["receipt_anchor"] == expected_receipt_anchor, "CAPSULE_RECEIPT_ANCHOR_MISMATCH")
    return {"status": "CURRENT", "capsule_root": capsule["capsule_root"], "sequence": expected_sequence, "standing": "INFORMATION_ONLY"}


def make_federation_genesis(dossier_key_hex: str, state_key_hex: str, scope_root: str, generation: str) -> dict[str, Any]:
    require(type(generation) is str and bool(generation), "FEDERATION_GENERATION_INVALID")
    require(key_root(dossier_key_hex) != key_root(state_key_hex), "FEDERATION_KEYS_NOT_INDEPENDENT")
    body = {
        "schema": "ucl.selfhost.federation_genesis.v2",
        "scope_root": require_root(scope_root, "$.scope_root"),
        "generation": generation,
        "dossier_key_root": key_root(dossier_key_hex),
        "state_key_root": key_root(state_key_hex),
        "sequence": 0,
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    record = signed(FEDERATION_GENESIS_DOMAIN, body, state_key_hex)
    return {**record, "genesis_root": root(record)}


class FederationExporter:
    """Dossier-only sender; it never receives the receiver state key.

    The exact genesis root is supplied by an external pin. Signature validation
    and durable freshness remain receiver responsibilities.
    """

    def __init__(self, dossier_key_hex: str, *, genesis: dict[str, Any], expected_genesis_root: str) -> None:
        require(type(genesis) is dict and set(genesis) == {"body", "body_root", "signature", "genesis_root"}, "FEDERATION_GENESIS_SHAPE_INVALID")
        body = genesis["body"]
        require(genesis["body_root"] == root(body), "FEDERATION_GENESIS_BODY_ROOT_MISMATCH")
        require(genesis["genesis_root"] == root({key: genesis[key] for key in ("body", "body_root", "signature")}) == require_root(expected_genesis_root), "FEDERATION_GENESIS_ROOT_MISMATCH")
        require(type(body) is dict and set(body) == {"schema", "scope_root", "generation", "dossier_key_root", "state_key_root", "sequence", "effect", "standing"}, "FEDERATION_GENESIS_BODY_INVALID")
        require(body["schema"] == "ucl.selfhost.federation_genesis.v2" and body["dossier_key_root"] == key_root(dossier_key_hex), "FEDERATION_GENESIS_BINDING_MISMATCH")
        require(body["sequence"] == 0 and body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "FEDERATION_GENESIS_BINDING_MISMATCH")
        self.dossier_key_hex = dossier_key_hex
        self.genesis_root = genesis["genesis_root"]
        self.head = "GENESIS"
        self.sequence = 0

    def export(self, payload: dict[str, Any], nonce: str) -> dict[str, Any]:
        require(type(nonce) is str and bool(nonce), "DOSSIER_NONCE_INVALID")
        body = {
            "schema": "ucl.selfhost.federation_dossier.v1", "genesis_root": self.genesis_root,
            "nonce": nonce, "predecessor": self.head, "payload": deepcopy(payload),
            "payload_root": root(payload), "transfers_standing": False,
            "effect": "NONE", "standing": "INFORMATION_ONLY",
        }
        record = signed(DOSSIER_DOMAIN, body, self.dossier_key_hex)
        dossier = {**record, "dossier_root": root(record)}
        self.head = dossier["dossier_root"]
        self.sequence += 1
        return dossier


class FederationInbox:
    def __init__(
        self,
        dossier_key_hex: str,
        state_key_hex: str,
        *,
        genesis: dict[str, Any] | None = None,
        expected_genesis_root: str | None = None,
        state_pin: dict[str, Any] | None = None,
        expected_state_root: str | None = None,
        expected_sequence: int | None = None,
    ) -> None:
        require(key_root(dossier_key_hex) != key_root(state_key_hex), "FEDERATION_KEYS_NOT_INDEPENDENT")
        self.dossier_key_hex = dossier_key_hex
        self.state_key_hex = state_key_hex
        require((genesis is None) != (state_pin is None), "FEDERATION_START_MODE_REQUIRED")
        if genesis is not None:
            require(expected_genesis_root is not None and expected_state_root is None, "FEDERATION_GENESIS_PIN_REQUIRED")
            require(type(expected_sequence) is int and type(expected_sequence) is not bool and expected_sequence == 0, "FEDERATION_GENESIS_SEQUENCE_REQUIRED")
            require(set(genesis) == {"body", "body_root", "signature", "genesis_root"}, "FEDERATION_GENESIS_SHAPE_INVALID")
            record = {key: genesis[key] for key in ("body", "body_root", "signature")}
            body = verify_signed(record, FEDERATION_GENESIS_DOMAIN, state_key_hex)
            require(genesis["genesis_root"] == root(record) == require_root(expected_genesis_root), "FEDERATION_GENESIS_ROOT_MISMATCH")
            require(type(body) is dict and set(body) == {"schema", "scope_root", "generation", "dossier_key_root", "state_key_root", "sequence", "effect", "standing"}, "FEDERATION_GENESIS_BODY_INVALID")
            require(body["schema"] == "ucl.selfhost.federation_genesis.v2" and body["dossier_key_root"] == key_root(dossier_key_hex) and body["state_key_root"] == key_root(state_key_hex), "FEDERATION_GENESIS_BINDING_MISMATCH")
            require(body["sequence"] == 0 and body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "FEDERATION_GENESIS_BINDING_MISMATCH")
            self.genesis_root = genesis["genesis_root"]
            self.nonces = set()
            self.head = "GENESIS"
            self.sequence = 0
        else:
            require(expected_state_root is not None and expected_genesis_root is None, "FEDERATION_STATE_PIN_REQUIRED")
            require(type(expected_sequence) is int and type(expected_sequence) is not bool and expected_sequence > 0, "FEDERATION_CURRENT_SEQUENCE_REQUIRED")
            require(type(state_pin) is dict and set(state_pin) == {"body", "body_root", "signature", "state_root"}, "FEDERATION_STATE_SHAPE_INVALID")
            record = {key: state_pin[key] for key in ("body", "body_root", "signature")}
            body = verify_signed(record, FEDERATION_STATE_DOMAIN, state_key_hex)
            require(state_pin["state_root"] == root(record) == require_root(expected_state_root), "FEDERATION_STATE_ROOT_MISMATCH")
            require(type(body) is dict and set(body) == {"schema", "genesis_root", "sequence", "head", "seen_nonces", "dossier_key_root", "state_key_root", "effect", "standing"}, "FEDERATION_STATE_BODY_INVALID")
            require(body["schema"] == "ucl.selfhost.federation_state.v2" and body["sequence"] == expected_sequence, "FEDERATION_STATE_SEQUENCE_MISMATCH")
            require(body["dossier_key_root"] == key_root(dossier_key_hex) and body["state_key_root"] == key_root(state_key_hex), "FEDERATION_STATE_BINDING_MISMATCH")
            require(body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "FEDERATION_STATE_BINDING_MISMATCH")
            self.genesis_root = require_root(body["genesis_root"], "$.genesis_root")
            self.nonces = set(body["seen_nonces"])
            require(len(self.nonces) == len(body["seen_nonces"]) and all(type(item) is str and item for item in self.nonces), "FEDERATION_STATE_NONCES_INVALID")
            self.head = body["head"]
            require(self.head == "GENESIS" or require_root(self.head), "FEDERATION_STATE_HEAD_INVALID")
            self.sequence = expected_sequence

    def snapshot(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.selfhost.federation_state.v2",
            "genesis_root": self.genesis_root,
            "sequence": self.sequence,
            "head": self.head,
            "seen_nonces": sorted(self.nonces),
            "dossier_key_root": key_root(self.dossier_key_hex),
            "state_key_root": key_root(self.state_key_hex),
            "effect": "NONE",
            "standing": "INFORMATION_ONLY",
        }
        record = signed(FEDERATION_STATE_DOMAIN, body, self.state_key_hex)
        return {**record, "state_root": root(record)}

    def import_dossier(self, dossier: dict[str, Any]) -> dict[str, Any]:
        require(type(dossier) is dict and set(dossier) == {"body", "body_root", "signature", "dossier_root"}, "DOSSIER_SHAPE_INVALID")
        record = {key: dossier[key] for key in ("body", "body_root", "signature")}
        body = verify_signed(record, DOSSIER_DOMAIN, self.dossier_key_hex)
        require(dossier["dossier_root"] == root(record), "DOSSIER_ROOT_MISMATCH")
        require(body["genesis_root"] == self.genesis_root, "DOSSIER_GENESIS_MISMATCH")
        require(body["nonce"] not in self.nonces, "DOSSIER_REPLAY")
        require(body["predecessor"] == self.head, "DOSSIER_PREDECESSOR_MISMATCH")
        require(body["payload_root"] == root(body["payload"]), "DOSSIER_PAYLOAD_ROOT_MISMATCH")
        require(body["transfers_standing"] is False and body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "DOSSIER_EFFECT_OR_STANDING_FORBIDDEN")
        self.nonces.add(body["nonce"])
        self.head = dossier["dossier_root"]
        self.sequence += 1
        return {"status": "OBSERVED_INFORMATION_ONLY", "dossier_root": self.head, "standing": "INFORMATION_ONLY"}

