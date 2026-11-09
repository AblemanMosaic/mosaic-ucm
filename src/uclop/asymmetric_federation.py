from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .canonical import exact_keys, require, require_root, root
from .custody import OpaqueEd25519KeyStore, verify_asymmetric

DOSSIER_DOMAIN = "UCL_UCM_ASYMMETRIC_DOSSIER_V2"
OBSERVATION_DOMAIN = "UCL_UCM_ASYMMETRIC_OBSERVATION_V2"
STATE_DOMAIN = "UCL_UCM_ASYMMETRIC_FEDERATION_STATE_V2"


class AsymmetricFederationNode:
    """Durable, information-only two-host protocol without a transport adapter."""

    def __init__(
        self, *, node_id: str, key_store: OpaqueEd25519KeyStore, node_handle: str,
        admitted_peers: dict[str, dict[str, Any]], required_state_pin: str | None = None,
        required_state_sequence: int | None = None,
        persistence_callback: Callable[[dict[str, Any]], None] | None = None,
        fixture_only: bool = False,
    ) -> None:
        require(type(node_id) is str and node_id, "FEDERATION_NODE_ID_INVALID")
        require(fixture_only or persistence_callback is not None, "FEDERATION_PERSISTENCE_REQUIRED")
        self.node_id = node_id
        self.key_store = key_store
        self.node_handle = node_handle
        self.identity = key_store.identity(node_handle)
        self.peers = deepcopy(admitted_peers)
        require(node_id not in self.peers, "FEDERATION_SELF_PEER_FORBIDDEN")
        for peer_id, identity in self.peers.items():
            require(type(peer_id) is str and peer_id, "FEDERATION_PEER_ID_INVALID")
            exact_keys(identity, {"schema", "role", "key_root", "public_key_hex", "generation"}, "$.peer")
            require(identity["role"] == "NODE", "FEDERATION_PEER_ROLE_INVALID")
        self.peer_set_root = root({key: self.peers[key] for key in sorted(self.peers)})
        self.required_state_pin = require_root(required_state_pin) if required_state_pin is not None else None
        require(required_state_sequence is None or (type(required_state_sequence) is int and type(required_state_sequence) is not bool and required_state_sequence >= 0), "FEDERATION_REQUIRED_STATE_SEQUENCE_INVALID")
        self.required_state_sequence = required_state_sequence
        self.restore_locked = self.required_state_pin is not None
        self.outbound_sequence = 0
        self.outbound_head = "GENESIS"
        self.outbound_nonces: set[str] = set()
        self.outbound: dict[int, dict[str, Any]] = {}
        self.inbound_heads: dict[str, tuple[int, str]] = {}
        self.inbound_nonces: dict[str, set[str]] = {}
        self.observations: dict[str, dict[str, Any]] = {}
        self.state_sequence = 0
        self.state_predecessor = "GENESIS"
        self._persistence_callback = persistence_callback
        self._fixture_only = fixture_only
        self._persistence_failed = False
        self._last_persisted_state: dict[str, Any] | None = None

    def bind_persistence(self, callback: Callable[[dict[str, Any]], None], *, current_record: dict[str, Any]) -> None:
        require(self._fixture_only and self._persistence_callback is None, "FEDERATION_PERSISTENCE_ALREADY_BOUND")
        require(self.state_predecessor == current_record.get("state_root"), "FEDERATION_PERSISTED_STATE_MISMATCH")
        self._persistence_callback = callback
        self._fixture_only = False
        self._last_persisted_state = deepcopy(current_record)

    def _usable(self) -> None:
        require(not self._persistence_failed, "FEDERATION_RESTART_REQUIRED_AFTER_PERSISTENCE_FAILURE")

    def _persist(self) -> None:
        if self._fixture_only:
            return
        require(self._persistence_callback is not None, "FEDERATION_PERSISTENCE_REQUIRED")
        body = self.snapshot()
        signed = self.key_store.sign(self.node_handle, STATE_DOMAIN, body)
        record = {**signed, "state_root": root(signed)}
        old_sequence, old_predecessor = self.state_sequence, self.state_predecessor
        self.state_sequence, self.state_predecessor = body["state_sequence"], record["state_root"]
        try:
            self._persistence_callback(record)
        except Exception:
            self.state_sequence, self.state_predecessor = old_sequence, old_predecessor
            self._persistence_failed = True
            raise
        self._last_persisted_state = deepcopy(record)

    def _unlocked(self) -> None:
        self._usable()
        require(not self.restore_locked, "FEDERATION_RESTORE_REQUIRED")

    def export(self, *, recipient: str, claim: dict[str, Any], evidence_roots: list[str], nonce: str) -> dict[str, Any]:
        self._unlocked()
        require(recipient in self.peers, "FEDERATION_RECIPIENT_NOT_ADMITTED")
        require(type(claim) is dict and claim.get("standing") == "INFORMATION_ONLY" and claim.get("authority_effect") == "NONE", "FEDERATION_CLAIM_EFFECT_INVALID")
        require(type(evidence_roots) is list and all(require_root(value) for value in evidence_roots), "FEDERATION_EVIDENCE_INVALID")
        require(type(nonce) is str and nonce and nonce not in self.outbound_nonces, "FEDERATION_EXPORT_NONCE_INVALID")
        body = {
            "schema": "ucl.ucm.asymmetric_dossier.v2", "source": self.node_id,
            "recipient": recipient, "sequence": self.outbound_sequence + 1,
            "predecessor": self.outbound_head, "nonce": nonce, "claim": deepcopy(claim),
            "claim_root": root(claim), "evidence_roots": evidence_roots,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        signed = self.key_store.sign(self.node_handle, DOSSIER_DOMAIN, body)
        dossier = {**signed, "dossier_root": root(signed)}
        self.outbound_sequence += 1
        self.outbound_head = dossier["dossier_root"]
        self.outbound_nonces.add(nonce)
        self.outbound[self.outbound_sequence] = deepcopy(dossier)
        self._persist()
        return dossier

    def _verify_dossier(self, dossier: Any, *, expected_source: str | None = None) -> dict[str, Any]:
        item = exact_keys(dossier, {"body", "body_root", "signature", "key_root", "signature_algorithm", "dossier_root"}, "$.dossier")
        hint = item["body"]
        source = expected_source if expected_source is not None else hint.get("source") if type(hint) is dict else None
        require(source in self.peers or source == self.node_id, "FEDERATION_SOURCE_NOT_ADMITTED")
        identity = self.identity if source == self.node_id else self.peers[source]
        signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        body = verify_asymmetric(signed, DOSSIER_DOMAIN, expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"])
        exact_keys(body, {"schema", "source", "recipient", "sequence", "predecessor", "nonce", "claim", "claim_root", "evidence_roots", "standing", "authority_effect"}, "$.dossier.body")
        require(body["schema"] == "ucl.ucm.asymmetric_dossier.v2" and body["source"] == source, "FEDERATION_DOSSIER_BINDING_INVALID")
        require(item["dossier_root"] == root(signed), "FEDERATION_DOSSIER_ROOT_INVALID")
        require(body["claim_root"] == root(body["claim"]), "FEDERATION_CLAIM_ROOT_INVALID")
        require(body["claim"].get("standing") == "INFORMATION_ONLY" and body["claim"].get("authority_effect") == "NONE", "FEDERATION_CLAIM_EFFECT_INVALID")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "FEDERATION_DOSSIER_EFFECT_INVALID")
        return item

    def import_dossier(self, dossier: Any) -> dict[str, Any]:
        self._unlocked()
        item = self._verify_dossier(dossier)
        body = item["body"]
        require(body["recipient"] == self.node_id, "FEDERATION_DOSSIER_BINDING_INVALID")
        prior_sequence, prior_head = self.inbound_heads.get(body["source"], (0, "GENESIS"))
        require(type(body["sequence"]) is int and type(body["sequence"]) is not bool and body["sequence"] == prior_sequence + 1, "FEDERATION_SEQUENCE_INVALID")
        require(body["predecessor"] == prior_head, "FEDERATION_PREDECESSOR_INVALID")
        nonces = self.inbound_nonces.setdefault(body["source"], set())
        require(type(body["nonce"]) is str and body["nonce"] and body["nonce"] not in nonces, "FEDERATION_REPLAY")
        nonces.add(body["nonce"])
        self.inbound_heads[body["source"]] = (body["sequence"], item["dossier_root"])
        observation_body = {
            "schema": "ucl.ucm.asymmetric_delivery_observation.v2",
            "sender": body["source"], "receiver": self.node_id,
            "recipient_identity_root": self.identity["key_root"],
            "source_sequence": body["sequence"], "dossier_root": item["dossier_root"],
            "claim_root": body["claim_root"], "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.key_store.sign(self.node_handle, OBSERVATION_DOMAIN, observation_body)
        observation = {**signed, "observation_root": root(signed)}
        self._persist()
        return observation

    def accept_observation(self, observation: Any) -> dict[str, Any]:
        self._unlocked()
        item = exact_keys(observation, {"body", "body_root", "signature", "key_root", "signature_algorithm", "observation_root"}, "$.observation")
        hint = item["body"]
        require(type(hint) is dict and hint.get("receiver") in self.peers, "FEDERATION_RECEIVER_NOT_ADMITTED")
        identity = self.peers[hint["receiver"]]
        signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        body = verify_asymmetric(signed, OBSERVATION_DOMAIN, expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"])
        exact_keys(body, {"schema", "sender", "receiver", "recipient_identity_root", "source_sequence", "dossier_root", "claim_root", "standing", "authority_effect"}, "$.observation.body")
        require(item["observation_root"] == root(signed), "FEDERATION_OBSERVATION_ROOT_INVALID")
        require(body["schema"] == "ucl.ucm.asymmetric_delivery_observation.v2" and body["sender"] == self.node_id, "FEDERATION_OBSERVATION_BINDING_INVALID")
        require(body["recipient_identity_root"] == identity["key_root"], "FEDERATION_OBSERVATION_RECIPIENT_IDENTITY_MISMATCH")
        require(type(body["source_sequence"]) is int and type(body["source_sequence"]) is not bool and body["source_sequence"] in self.outbound, "FEDERATION_OBSERVATION_SEQUENCE_INVALID")
        dossier = self.outbound[body["source_sequence"]]
        require(body["receiver"] == dossier["body"]["recipient"], "FEDERATION_OBSERVATION_RECIPIENT_MISMATCH")
        require(body["dossier_root"] == dossier["dossier_root"], "FEDERATION_OBSERVATION_DOSSIER_MISMATCH")
        require(body["claim_root"] == dossier["body"]["claim_root"], "FEDERATION_OBSERVATION_CLAIM_MISMATCH")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "FEDERATION_OBSERVATION_EFFECT_INVALID")
        require(body["dossier_root"] not in self.observations, "FEDERATION_OBSERVATION_REPLAY")
        self.observations[body["dossier_root"]] = deepcopy(item)
        result = {"status": "DELIVERY_OBSERVED_INFORMATION_ONLY", "dossier_root": body["dossier_root"], "claim_root": body["claim_root"], "receiver": body["receiver"], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        self._persist()
        return result

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "ucl.ucm.asymmetric_federation_state.v2", "node_id": self.node_id,
            "identity_root": self.identity["key_root"], "peer_set_root": self.peer_set_root,
            "state_sequence": self.state_sequence + 1, "state_predecessor": self.state_predecessor,
            "outbound_sequence": self.outbound_sequence, "outbound_head": self.outbound_head,
            "outbound_nonces": sorted(self.outbound_nonces),
            "outbound": {str(key): value for key, value in sorted(self.outbound.items())},
            "inbound_heads": {key: list(value) for key, value in sorted(self.inbound_heads.items())},
            "inbound_nonces": {key: sorted(value) for key, value in sorted(self.inbound_nonces.items())},
            "observations": deepcopy(self.observations), "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }

    def export_state(self) -> dict[str, Any]:
        self._unlocked()
        if not self._fixture_only:
            require(self._last_persisted_state is not None, "FEDERATION_PERSISTED_STATE_MISSING")
            return deepcopy(self._last_persisted_state)
        body = self.snapshot()
        signed = self.key_store.sign(self.node_handle, STATE_DOMAIN, body)
        record = {**signed, "state_root": root(signed)}
        self.state_sequence = body["state_sequence"]
        self.state_predecessor = record["state_root"]
        return record

    def restore_state(self, record: Any) -> dict[str, Any]:
        require(self.restore_locked, "FEDERATION_RESTORE_NOT_REQUIRED")
        item = exact_keys(record, {"body", "body_root", "signature", "key_root", "signature_algorithm", "state_root"}, "$.federation_state")
        signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        body = verify_asymmetric(signed, STATE_DOMAIN, expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
        require(item["state_root"] == root(signed) == self.required_state_pin, "FEDERATION_STATE_PIN_MISMATCH")
        exact_keys(body, {
            "schema", "node_id", "identity_root", "peer_set_root", "state_sequence",
            "state_predecessor", "outbound_sequence", "outbound_head", "outbound_nonces",
            "outbound", "inbound_heads", "inbound_nonces", "observations",
            "standing", "authority_effect",
        }, "$.federation_state.body")
        require(body["schema"] == "ucl.ucm.asymmetric_federation_state.v2" and body["node_id"] == self.node_id, "FEDERATION_STATE_NODE_MISMATCH")
        require(body["identity_root"] == self.identity["key_root"] and body["peer_set_root"] == self.peer_set_root, "FEDERATION_STATE_IDENTITY_MISMATCH")
        require(self.required_state_sequence is None or body["state_sequence"] == self.required_state_sequence, "FEDERATION_STATE_SEQUENCE_MISMATCH")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "FEDERATION_STATE_EFFECT_INVALID")
        outbound = {int(key): value for key, value in body["outbound"].items()}
        require(sorted(outbound) == list(range(1, body["outbound_sequence"] + 1)), "FEDERATION_STATE_OUTBOUND_SEQUENCE_INVALID")
        prior = "GENESIS"
        nonces: set[str] = set()
        for sequence in sorted(outbound):
            dossier = self._verify_dossier(outbound[sequence], expected_source=self.node_id)
            dossier_body = dossier["body"]
            require(dossier_body["sequence"] == sequence and dossier_body["predecessor"] == prior, "FEDERATION_STATE_OUTBOUND_CHAIN_INVALID")
            require(dossier_body["nonce"] not in nonces, "FEDERATION_STATE_OUTBOUND_NONCE_REPLAY")
            nonces.add(dossier_body["nonce"])
            prior = dossier["dossier_root"]
        require(prior == body["outbound_head"] and nonces == set(body["outbound_nonces"]), "FEDERATION_STATE_OUTBOUND_HEAD_INVALID")
        self.outbound_sequence, self.outbound_head = body["outbound_sequence"], body["outbound_head"]
        self.outbound_nonces, self.outbound = nonces, deepcopy(outbound)
        self.inbound_heads = {key: (value[0], value[1]) for key, value in body["inbound_heads"].items()}
        self.inbound_nonces = {key: set(value) for key, value in body["inbound_nonces"].items()}
        self.observations = deepcopy(body["observations"])
        self.state_sequence, self.state_predecessor = body["state_sequence"], item["state_root"]
        self.restore_locked = False
        return {"status": "RESTORED", "state_root": item["state_root"], "state_sequence": body["state_sequence"], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
