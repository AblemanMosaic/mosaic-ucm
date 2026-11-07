from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import root, require_root
from .errors import require
from .evidence import PAIR_DOMAIN, key_root, signed, verify_signed

LIFECYCLE_DOMAIN = "UCL_SH_AUTHORITY_LIFECYCLE_V3"
GENESIS_DOMAIN = "UCL_SH_AUTHORITY_GENESIS_V3"
STATE_DOMAIN = "UCL_SH_AUTHORITY_STATE_V2"
RECOVERY_DOMAIN = "UCL_SH_AUTHORITY_RECOVERY_V2"
STATUS_DOMAIN = "UCL_SH_AUTHORITY_STATUS_V2"
EMERGENCY_DOMAIN = "UCL_SH_AUTHORITY_EMERGENCY_V1"
PAIR_DECISION_DOMAIN = "UCL_SH_PAIR_COMPATIBILITY_DECISION_V1"
ROLE_KEYS = {"H_M": "hm", "H_J": "hj"}


def make_authority_genesis(hm_key: str, hj_key: str, recovery_key: str, governor_key: str, decision_root: str, generation: str) -> dict[str, Any]:
    require(type(generation) is str and bool(generation), "AUTHORITY_GENERATION_INVALID")
    roots = [key_root(value) for value in (hm_key, hj_key, recovery_key, governor_key)]
    require(len(set(roots)) == 4, "AUTHORITY_KEYS_NOT_INDEPENDENT")
    body = {
        "schema": "ucl.selfhost.authority_genesis.v3", "generation": generation,
        "decision_root": require_root(decision_root, "$.decision_root"),
        "hm_key_root": roots[0], "hj_key_root": roots[1], "authority_key_root": roots[2], "governor_key_root": roots[3],
        "sequence": 0, "effect": "NONE", "standing": "INFORMATION_ONLY",
    }
    recovery_record = signed(GENESIS_DOMAIN, body, recovery_key)
    governor_attestation = signed(GENESIS_DOMAIN + ":GOVERNOR", body, governor_key)
    record = {**recovery_record, "governor_attestation": governor_attestation}
    return {**record, "genesis_root": root(record)}


def verify_pair_attestation(pair: dict[str, Any], *, hm_key: str, hj_key: str, decision_root: str, hm_epoch: int, hj_epoch: int, approved_pair_roots: set[str]) -> dict[str, Any]:
    require(type(pair) is dict and set(pair) == {"body", "body_root", "hm_signature", "hj_signature", "pair_root"}, "PAIR_SHAPE_INVALID")
    body = pair["body"]
    require(pair["body_root"] == root(body), "PAIR_BODY_ROOT_MISMATCH")
    require(pair["pair_root"] == root({key: pair[key] for key in ("body", "body_root", "hm_signature", "hj_signature")}), "PAIR_ROOT_MISMATCH")
    require(pair["pair_root"] in approved_pair_roots, "PAIR_NOT_LISTED")
    require(body["decision_root"] == require_root(decision_root), "PAIR_DECISION_MISMATCH")
    require(type(body["hm_epoch"]) is int and type(body["hm_epoch"]) is not bool and body["hm_epoch"] == hm_epoch, "PAIR_HM_EPOCH_MISMATCH")
    require(type(body["hj_epoch"]) is int and type(body["hj_epoch"]) is not bool and body["hj_epoch"] == hj_epoch, "PAIR_HJ_EPOCH_MISMATCH")
    require(body["hm_key_root"] == key_root(hm_key) and body["hj_key_root"] == key_root(hj_key), "PAIR_KEY_MISMATCH")
    verify_signed({"body": body, "body_root": pair["body_root"], "signature": pair["hm_signature"]}, PAIR_DOMAIN + ":H_M", hm_key)
    verify_signed({"body": body, "body_root": pair["body_root"], "signature": pair["hj_signature"]}, PAIR_DOMAIN + ":H_J", hj_key)
    return {"status": "VERIFIED_INFORMATION_ONLY", "pair_root": pair["pair_root"], "standing": "INFORMATION_ONLY"}


class AuthorityState:
    """Fixture-key mechanics only. It cannot grant standing or authority."""

    def __init__(self, hm_key: str, hj_key: str, recovery_key: str, governor_key: str, decision_root: str, *, genesis: dict[str, Any] | None = None, expected_genesis_root: str | None = None, expected_sequence: int | None = None) -> None:
        require(genesis is not None and expected_genesis_root is not None, "AUTHORITY_GENESIS_REQUIRED")
        require(type(expected_sequence) is int and type(expected_sequence) is not bool and expected_sequence == 0, "AUTHORITY_GENESIS_SEQUENCE_REQUIRED")
        roots = [key_root(value) for value in (hm_key, hj_key, recovery_key, governor_key)]
        require(len(set(roots)) == 4, "AUTHORITY_KEYS_NOT_INDEPENDENT")
        require(type(genesis) is dict and set(genesis) == {"body", "body_root", "signature", "governor_attestation", "genesis_root"}, "AUTHORITY_GENESIS_SHAPE_INVALID")
        record = {key: genesis[key] for key in ("body", "body_root", "signature")}
        body = verify_signed(record, GENESIS_DOMAIN, recovery_key)
        require(verify_signed(genesis["governor_attestation"], GENESIS_DOMAIN + ":GOVERNOR", governor_key) == body, "GOVERNOR_GENESIS_ATTESTATION_INVALID")
        complete_record = {**record, "governor_attestation": genesis["governor_attestation"]}
        require(genesis["genesis_root"] == root(complete_record) == require_root(expected_genesis_root), "AUTHORITY_GENESIS_ROOT_MISMATCH")
        require(type(body) is dict and set(body) == {"schema", "generation", "decision_root", "hm_key_root", "hj_key_root", "authority_key_root", "governor_key_root", "sequence", "effect", "standing"}, "AUTHORITY_GENESIS_BODY_INVALID")
        require(type(body["generation"]) is str and bool(body["generation"]), "AUTHORITY_GENERATION_INVALID")
        require(body["schema"] == "ucl.selfhost.authority_genesis.v3" and body["decision_root"] == require_root(decision_root), "AUTHORITY_GENESIS_BINDING_MISMATCH")
        require([body["hm_key_root"], body["hj_key_root"], body["authority_key_root"], body["governor_key_root"]] == roots, "AUTHORITY_GENESIS_BINDING_MISMATCH")
        require(body["sequence"] == 0 and body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "AUTHORITY_GENESIS_EFFECT_FORBIDDEN")
        self.keys = {"H_M": hm_key, "H_J": hj_key, "RECOVERY": recovery_key, "GOVERNOR": governor_key}
        self.key_roots = {role: key_root(value) for role, value in self.keys.items()}
        self.epochs = {"H_M": 1, "H_J": 1}
        self.status = {"H_M": "ACTIVE", "H_J": "ACTIVE"}
        self.history = {"H_M": [self.key_roots["H_M"]], "H_J": [self.key_roots["H_J"]]}
        self.decision_root = require_root(decision_root, "$.decision_root")
        self.genesis, self.genesis_root = deepcopy(genesis), genesis["genesis_root"]
        self.lifecycle: list[dict[str, Any]] = []

    @property
    def sequence(self) -> int:
        return len(self.lifecycle)

    @property
    def anchor(self) -> str:
        return "GENESIS" if not self.lifecycle else self.lifecycle[-1]["event_root"]

    def _state_body(self) -> dict[str, Any]:
        return {
            "schema": "ucl.selfhost.authority_state.v2", "genesis_root": self.genesis_root,
            "sequence": self.sequence, "anchor": self.anchor, "decision_root": self.decision_root,
            "authority_key_root": self.key_roots["RECOVERY"], "governor_key_root": self.key_roots["GOVERNOR"],
            "key_roots": {role: self.key_roots[role] for role in ROLE_KEYS}, "epochs": deepcopy(self.epochs),
            "status": deepcopy(self.status), "history": deepcopy(self.history), "effect": "NONE", "standing": "INFORMATION_ONLY",
        }

    def snapshot(self) -> dict[str, Any]:
        record = signed(STATE_DOMAIN, self._state_body(), self.keys["RECOVERY"])
        return {**record, "state_root": root(record)}

    @classmethod
    def from_lifecycle(cls, initial_hm_key: str, initial_hj_key: str, recovery_key: str, governor_key: str, decision_root: str, *, genesis: dict[str, Any], expected_genesis_root: str, lifecycle: list[dict[str, Any]], state_pin: dict[str, Any], expected_state_root: str, expected_sequence: int, key_material_by_root: dict[str, str] | None = None) -> "AuthorityState":
        require(type(expected_sequence) is int and type(expected_sequence) is not bool and expected_sequence > 0, "AUTHORITY_CURRENT_SEQUENCE_REQUIRED")
        state = cls(initial_hm_key, initial_hj_key, recovery_key, governor_key, decision_root, genesis=genesis, expected_genesis_root=expected_genesis_root, expected_sequence=0)
        material = {key_root(initial_hm_key): initial_hm_key, key_root(initial_hj_key): initial_hj_key, **(key_material_by_root or {})}
        require(type(lifecycle) is list and len(lifecycle) == expected_sequence, "LIFECYCLE_LENGTH_MISMATCH")
        predecessor = "GENESIS"
        for index, event in enumerate(lifecycle):
            require(type(event) is dict and set(event) == {"body", "body_root", "signature", "event_root"}, "LIFECYCLE_EVENT_SHAPE_INVALID")
            record = {key: event[key] for key in ("body", "body_root", "signature")}
            body = verify_signed(record, LIFECYCLE_DOMAIN, recovery_key)
            require(event["event_root"] == root(record), "LIFECYCLE_EVENT_ROOT_MISMATCH")
            require(type(body) is dict and set(body) == {"schema", "sequence", "predecessor", "action", "role", "details", "approvals", "decision_root", "authority_key_root", "effect", "standing"}, "LIFECYCLE_BODY_SHAPE_INVALID")
            require(body["schema"] == "ucl.selfhost.authority_lifecycle.v3" and body["sequence"] == index + 1 and body["predecessor"] == predecessor, "LIFECYCLE_CHAIN_INVALID")
            require(body["decision_root"] == state.decision_root and body["authority_key_root"] == state.key_roots["RECOVERY"], "LIFECYCLE_BINDING_MISMATCH")
            require(body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "LIFECYCLE_EFFECT_FORBIDDEN")
            role, action, details, approvals = body["role"], body["action"], body["details"], body["approvals"]
            require(role in ROLE_KEYS and type(approvals) is dict, "AUTHORITY_ROLE_INVALID")
            if action == "SUSPEND":
                require(set(approvals) == {"authority"}, "LIFECYCLE_APPROVAL_SET_INVALID")
                request = state.status_request_body("SUSPEND", role)
                require(verify_signed(approvals["authority"], STATUS_DOMAIN + ":AUTHORITY", recovery_key) == request, "STATUS_APPROVAL_BODY_MISMATCH")
                state._apply_suspend(role, details)
            elif action == "REVOKE":
                require(set(approvals) == {"custodian", "authority"}, "LIFECYCLE_APPROVAL_SET_INVALID")
                request = state.status_request_body("REVOKE", role)
                require(verify_signed(approvals["custodian"], STATUS_DOMAIN + ":CUSTODIAN", state.keys[role]) == request, "STATUS_CUSTODIAN_BODY_MISMATCH")
                require(verify_signed(approvals["authority"], STATUS_DOMAIN + ":AUTHORITY", recovery_key) == request, "STATUS_APPROVAL_BODY_MISMATCH")
                state._apply_revoke(role, details)
            else:
                require(action == "RECOVER" and set(approvals) == {"authority", "cosigner", "possession"}, "LIFECYCLE_APPROVAL_SET_INVALID")
                new_root = require_root(details.get("new_key_root"), "$.lifecycle.details.new_key_root")
                require(new_root in material and key_root(material[new_root]) == new_root, "RECOVERY_KEY_MATERIAL_REQUIRED")
                request = state.recovery_request_body(role, material[new_root])
                other = "H_J" if role == "H_M" else "H_M"
                require(verify_signed(approvals["authority"], RECOVERY_DOMAIN + ":AUTHORITY", recovery_key) == request, "RECOVERY_APPROVAL_BODY_MISMATCH")
                require(verify_signed(approvals["cosigner"], RECOVERY_DOMAIN + ":COSIGNER", state.keys[other]) == request, "RECOVERY_COSIGN_BODY_MISMATCH")
                require(verify_signed(approvals["possession"], RECOVERY_DOMAIN + ":POSSESSION", material[new_root]) == request, "RECOVERY_POSSESSION_BODY_MISMATCH")
                state._apply_recovery(role, material[new_root], details)
            state.lifecycle.append(deepcopy(event))
            predecessor = event["event_root"]
        require(type(state_pin) is dict and set(state_pin) == {"body", "body_root", "signature", "state_root"}, "AUTHORITY_STATE_SHAPE_INVALID")
        pin_record = {key: state_pin[key] for key in ("body", "body_root", "signature")}
        pin_body = verify_signed(pin_record, STATE_DOMAIN, recovery_key)
        require(state_pin["state_root"] == root(pin_record) == require_root(expected_state_root), "AUTHORITY_STATE_ROOT_MISMATCH")
        require(pin_body.get("sequence") == expected_sequence, "AUTHORITY_STATE_SEQUENCE_MISMATCH")
        require(pin_body == state._state_body(), "AUTHORITY_STATE_BINDING_MISMATCH")
        return state

    def _append_lifecycle(self, action: str, role: str, details: dict[str, Any], approvals: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schema": "ucl.selfhost.authority_lifecycle.v3", "sequence": self.sequence + 1, "predecessor": self.anchor,
            "action": action, "role": role, "details": deepcopy(details), "approvals": deepcopy(approvals),
            "decision_root": self.decision_root, "authority_key_root": self.key_roots["RECOVERY"], "effect": "NONE", "standing": "INFORMATION_ONLY",
        }
        record = signed(LIFECYCLE_DOMAIN, body, self.keys["RECOVERY"])
        event = {**record, "event_root": root(record)}
        self.lifecycle.append(event)
        return event

    def status_request_body(self, action: str, role: str) -> dict[str, Any]:
        require(action in {"SUSPEND", "REVOKE"} and role in ROLE_KEYS, "AUTHORITY_ACTION_INVALID")
        return {
            "schema": "ucl.selfhost.authority_status_request.v2", "action": action, "role": role,
            "prior_status": self.status[role], "epoch": self.epochs[role], "key_root": self.key_roots[role],
            "genesis_root": self.genesis_root, "sequence": self.sequence + 1, "predecessor": self.anchor,
            "prior_state_root": self.snapshot()["state_root"], "decision_root": self.decision_root,
            "effect": "NONE", "standing": "INFORMATION_ONLY",
        }

    def _apply_suspend(self, role: str, details: dict[str, Any]) -> None:
        require(self.status[role] == "ACTIVE", "AUTHORITY_NOT_ACTIVE")
        other = "H_J" if role == "H_M" else "H_M"
        require(self.status[other] == "ACTIVE", "LAST_ACTIVE_CUSTODIAN_REQUIRED")
        require(details == {"epoch": self.epochs[role], "key_root": self.key_roots[role]}, "LIFECYCLE_DETAILS_INVALID")
        self.status[role] = "SUSPENDED"

    def suspend(self, role: str, authority_approval: dict[str, Any]) -> dict[str, Any]:
        body = self.status_request_body("SUSPEND", role)
        require(verify_signed(authority_approval, STATUS_DOMAIN + ":AUTHORITY", self.keys["RECOVERY"]) == body, "STATUS_APPROVAL_BODY_MISMATCH")
        details = {"epoch": self.epochs[role], "key_root": self.key_roots[role]}
        self._apply_suspend(role, details)
        return self._append_lifecycle("SUSPEND", role, details, {"authority": authority_approval})

    def _apply_revoke(self, role: str, details: dict[str, Any]) -> None:
        require(self.status[role] in {"ACTIVE", "SUSPENDED"}, "AUTHORITY_ALREADY_REVOKED")
        other = "H_J" if role == "H_M" else "H_M"
        require(self.status[other] == "ACTIVE", "EMERGENCY_REVOCATION_POLICY_UNRATIFIED")
        require(details == {"epoch": self.epochs[role], "key_root": self.key_roots[role]}, "LIFECYCLE_DETAILS_INVALID")
        self.status[role] = "REVOKED"

    def revoke(self, role: str, custodian_approval: dict[str, Any], authority_approval: dict[str, Any], governor_emergency_approval: dict[str, Any] | None = None) -> dict[str, Any]:
        body = self.status_request_body("REVOKE", role)
        require(verify_signed(custodian_approval, STATUS_DOMAIN + ":CUSTODIAN", self.keys[role]) == body, "STATUS_CUSTODIAN_BODY_MISMATCH")
        require(verify_signed(authority_approval, STATUS_DOMAIN + ":AUTHORITY", self.keys["RECOVERY"]) == body, "STATUS_APPROVAL_BODY_MISMATCH")
        other = "H_J" if role == "H_M" else "H_M"
        require(self.status[other] == "ACTIVE", "EMERGENCY_REVOCATION_POLICY_UNRATIFIED")
        require(governor_emergency_approval is None, "EMERGENCY_REVOCATION_POLICY_UNRATIFIED")
        details = {"epoch": self.epochs[role], "key_root": self.key_roots[role]}
        self._apply_revoke(role, details)
        approvals = {"custodian": custodian_approval, "authority": authority_approval}
        return self._append_lifecycle("REVOKE", role, details, approvals)

    def recovery_request_body(self, role: str, new_key: str) -> dict[str, Any]:
        require(role in ROLE_KEYS, "AUTHORITY_ROLE_INVALID")
        return {
            "schema": "ucl.selfhost.recovery_request.v2", "role": role,
            "old_key_root": self.key_roots[role], "new_key_root": key_root(new_key),
            "old_epoch": self.epochs[role], "new_epoch": self.epochs[role] + 1,
            "genesis_root": self.genesis_root, "sequence": self.sequence + 1, "predecessor": self.anchor,
            "prior_state_root": self.snapshot()["state_root"], "decision_root": self.decision_root,
            "effect": "NONE", "standing": "INFORMATION_ONLY",
        }

    def _apply_recovery(self, role: str, new_key: str, details: dict[str, Any]) -> None:
        require(self.status[role] == "SUSPENDED", "RECOVERY_ROLE_NOT_SUSPENDED")
        other = "H_J" if role == "H_M" else "H_M"
        require(self.status[other] == "ACTIVE", "RECOVERY_COSIGNER_NOT_ACTIVE")
        new_root = key_root(new_key)
        forbidden = {self.key_roots["RECOVERY"], self.key_roots["GOVERNOR"], *self.history["H_M"], *self.history["H_J"]}
        require(new_root not in forbidden, "RECOVERY_KEY_NOT_INDEPENDENT")
        require(details == {"old_key_root": self.key_roots[role], "new_key_root": new_root, "epoch": self.epochs[role] + 1}, "LIFECYCLE_DETAILS_INVALID")
        self.keys[role], self.key_roots[role] = new_key, new_root
        self.epochs[role] += 1
        self.status[role] = "ACTIVE"
        self.history[role].append(new_root)

    def recover(self, role: str, new_key: str, authority_approval: dict[str, Any], cosigner_approval: dict[str, Any], possession_proof: dict[str, Any]) -> dict[str, Any]:
        body = self.recovery_request_body(role, new_key)
        other = "H_J" if role == "H_M" else "H_M"
        require(verify_signed(authority_approval, RECOVERY_DOMAIN + ":AUTHORITY", self.keys["RECOVERY"]) == body, "RECOVERY_APPROVAL_BODY_MISMATCH")
        require(verify_signed(cosigner_approval, RECOVERY_DOMAIN + ":COSIGNER", self.keys[other]) == body, "RECOVERY_COSIGN_BODY_MISMATCH")
        require(verify_signed(possession_proof, RECOVERY_DOMAIN + ":POSSESSION", new_key) == body, "RECOVERY_POSSESSION_BODY_MISMATCH")
        details = {"old_key_root": self.key_roots[role], "new_key_root": key_root(new_key), "epoch": self.epochs[role] + 1}
        self._apply_recovery(role, new_key, details)
        return self._append_lifecycle("RECOVER", role, details, {"authority": authority_approval, "cosigner": cosigner_approval, "possession": possession_proof})

    def attest_pair(self, hm_commitment_root: str, hj_commitment_root: str) -> dict[str, Any]:
        require(self.status == {"H_M": "ACTIVE", "H_J": "ACTIVE"}, "PAIR_CUSTODIAN_NOT_ACTIVE")
        body = {"schema": "ucl.selfhost.exact_pair_attestation.v1", "hm_commitment_root": require_root(hm_commitment_root), "hj_commitment_root": require_root(hj_commitment_root), "hm_epoch": self.epochs["H_M"], "hj_epoch": self.epochs["H_J"], "hm_key_root": self.key_roots["H_M"], "hj_key_root": self.key_roots["H_J"], "decision_root": self.decision_root, "effect": "NONE", "standing": "INFORMATION_ONLY"}
        hm, hj = signed(PAIR_DOMAIN + ":H_M", body, self.keys["H_M"]), signed(PAIR_DOMAIN + ":H_J", body, self.keys["H_J"])
        record = {"body": body, "body_root": root(body), "hm_signature": hm["signature"], "hj_signature": hj["signature"]}
        return {**record, "pair_root": root(record)}

    def verify_pair(self, pair: dict[str, Any], approved_pair_roots: set[str]) -> dict[str, Any]:
        return verify_pair_attestation(pair, hm_key=self.keys["H_M"], hj_key=self.keys["H_J"], decision_root=self.decision_root, hm_epoch=self.epochs["H_M"], hj_epoch=self.epochs["H_J"], approved_pair_roots=approved_pair_roots)

    def verify_lifecycle(self, state_pin: dict[str, Any], expected_state_root: str, expected_sequence: int) -> dict[str, Any]:
        require(self.sequence == expected_sequence, "LIFECYCLE_LENGTH_MISMATCH")
        record = {key: state_pin[key] for key in ("body", "body_root", "signature")}
        body = verify_signed(record, STATE_DOMAIN, self.keys["RECOVERY"])
        require(state_pin["state_root"] == root(record) == require_root(expected_state_root), "AUTHORITY_STATE_ROOT_MISMATCH")
        require(body == self._state_body(), "AUTHORITY_STATE_BINDING_MISMATCH")
        return {"status": "VERIFIED", "count": expected_sequence, "anchor": self.anchor, "state_root": expected_state_root, "standing": "INFORMATION_ONLY"}
