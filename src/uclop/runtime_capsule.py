from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .protected_state import ProtectedStateStore


RUNTIME_SCHEMA = "ucl.ucm.anchored_constitutional_runtime.v1"
RUNTIME_SLOTS = {"controller", "federation", "retirement_ledger"}


def _component(value: Any) -> dict[str, Any]:
    require(type(value) in {dict, list}, "RUNTIME_COMPONENT_TYPE_INVALID")
    return {"state": deepcopy(value), "state_root": root(value)}


def _append_only_prefix(old: list[Any], new: list[Any], code: str) -> None:
    require(type(old) is list and type(new) is list, code)
    require(len(new) >= len(old) and new[:len(old)] == old, code)


def _controller_successor(old: Any, new: Any) -> None:
    """Require controller state to extend the anchored event history.

    Replaying the controller snapshot is still the component's responsibility;
    this boundary prevents a fresh controller from overwriting an existing
    refusal or accepted stage after the aggregate runtime is reopened.
    """
    require(type(old) is dict and type(new) is dict, "RUNTIME_CONTROLLER_SUCCESSOR_INVALID")
    _append_only_prefix(old.get("events"), new.get("events"), "RUNTIME_CONTROLLER_HISTORY_REPLACED")
    require(len(new["events"]) > len(old["events"]), "RUNTIME_CONTROLLER_NO_SUCCESSOR_EVENT")


def _ledger_successor(old: Any, new: Any) -> None:
    require(type(old) is dict and type(new) is dict, "RUNTIME_RETIREMENT_SUCCESSOR_INVALID")
    _append_only_prefix(old.get("events"), new.get("events"), "RUNTIME_RETIREMENT_HISTORY_REPLACED")
    require(len(new["events"]) > len(old["events"]), "RUNTIME_RETIREMENT_NO_SUCCESSOR_EVENT")
    old_used, new_used = old.get("ever_used"), new.get("ever_used")
    require(type(old_used) is dict and type(new_used) is dict, "RUNTIME_RETIREMENT_HISTORY_INVALID")
    require(all(new_used.get(key) == value for key, value in old_used.items()), "RUNTIME_RETIREMENT_HISTORY_REPLACED")


def _federation_successor(old: Any, new: Any) -> None:
    require(type(old) is dict and type(new) is dict and set(old) == set(new), "RUNTIME_FEDERATION_NODE_SET_CHANGED")
    changed = 0
    for node_id in sorted(old):
        prior, successor = old[node_id], new[node_id]
        if successor == prior:
            continue
        changed += 1
        require(type(prior) is dict and type(successor) is dict, "RUNTIME_FEDERATION_SUCCESSOR_INVALID", node_id)
        prior_body, successor_body = prior.get("body"), successor.get("body")
        require(type(prior_body) is dict and type(successor_body) is dict, "RUNTIME_FEDERATION_SUCCESSOR_INVALID", node_id)
        require(successor_body.get("state_predecessor") == prior.get("state_root"), "RUNTIME_FEDERATION_PREDECESSOR_MISMATCH", node_id)
        require(successor_body.get("state_sequence") == prior_body.get("state_sequence", -1) + 1, "RUNTIME_FEDERATION_SEQUENCE_MISMATCH", node_id)
    require(changed == 1, "RUNTIME_FEDERATION_UPDATE_CARDINALITY_INVALID")


def _require_successor(name: str, old: Any, new: Any) -> None:
    if name == "controller":
        _controller_successor(old, new)
    elif name == "retirement_ledger":
        _ledger_successor(old, new)
    elif name == "federation":
        _federation_successor(old, new)
    else:
        require(False, "RUNTIME_COMPONENT_UNKNOWN")


class AnchoredConstitutionalRuntime:
    """One externally anchored history for all security-relevant runtime state.

    Opening an existing history requires its current protected-state head.  A
    missing or older caller pin cannot silently create or select a history.
    """

    def __init__(
        self, store: ProtectedStateStore, *, required_head: str,
        deployment_contract_root: str, governor_seating_root: str,
    ) -> None:
        self.store = store
        self.deployment_contract_root = require_root(deployment_contract_root)
        self.governor_seating_root = require_root(governor_seating_root)
        anchor = store.anchor.observe_record()
        if anchor["sequence"] == 0:
            require(required_head == "GENESIS", "RUNTIME_GENESIS_PIN_REQUIRED")
            require(not store.path.exists() and not store.journal_path.exists(), "RUNTIME_UNANCHORED_EXISTING_STATE")
            self.record: dict[str, Any] | None = None
            self.payload: dict[str, Any] | None = None
        else:
            require(required_head != "GENESIS", "RUNTIME_CURRENT_HEAD_PIN_REQUIRED")
            require(require_root(required_head) == anchor["head"], "RUNTIME_HEAD_PIN_MISMATCH")
            self.record = store.load()
            self.payload = self._validate_payload(self.record["body"]["payload"])

    def _validate_payload(self, value: Any) -> dict[str, Any]:
        item = exact_keys(value, {
            "schema", "deployment_contract_root", "governor_seating_root",
            "components", "standing", "authority_effect", "runtime_root",
        }, "$.runtime")
        body = {key: item[key] for key in item if key != "runtime_root"}
        require(item["schema"] == RUNTIME_SCHEMA and item["runtime_root"] == root(body), "RUNTIME_ROOT_INVALID")
        require(item["deployment_contract_root"] == self.deployment_contract_root, "RUNTIME_CONTRACT_MISMATCH")
        require(item["governor_seating_root"] == self.governor_seating_root, "RUNTIME_GOVERNOR_SEATING_MISMATCH")
        require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "RUNTIME_EFFECT_INVALID")
        components = item["components"]
        require(type(components) is dict and set(components) == RUNTIME_SLOTS, "RUNTIME_COMPONENT_SET_INVALID")
        for name, component in components.items():
            checked = exact_keys(component, {"state", "state_root"}, f"$.runtime.components.{name}")
            require(checked["state_root"] == root(checked["state"]), "RUNTIME_COMPONENT_ROOT_INVALID", name)
        return deepcopy(item)

    def initialize(self, *, controller: dict[str, Any], federation: dict[str, Any], retirement_ledger: dict[str, Any]) -> dict[str, Any]:
        require(self.record is None and self.payload is None, "RUNTIME_ALREADY_INITIALIZED")
        payload = self._make_payload({
            "controller": _component(controller),
            "federation": _component(federation),
            "retirement_ledger": _component(retirement_ledger),
        })
        self.record = self.store.commit(payload, expected_sequence=0, expected_head="GENESIS")
        self.payload = payload
        return deepcopy(self.record)

    def _make_payload(self, components: dict[str, dict[str, Any]]) -> dict[str, Any]:
        body = {
            "schema": RUNTIME_SCHEMA,
            "deployment_contract_root": self.deployment_contract_root,
            "governor_seating_root": self.governor_seating_root,
            "components": deepcopy(components),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "runtime_root": root(body)}

    @property
    def head(self) -> str:
        require(self.record is not None, "RUNTIME_NOT_INITIALIZED")
        return self.record["state_root"]

    def component(self, name: str) -> Any:
        require(name in RUNTIME_SLOTS and self.payload is not None, "RUNTIME_COMPONENT_UNKNOWN")
        return deepcopy(self.payload["components"][name]["state"])

    def update(self, name: str, state: Any) -> dict[str, Any]:
        require(name in RUNTIME_SLOTS and self.record is not None and self.payload is not None, "RUNTIME_NOT_INITIALIZED")
        components = deepcopy(self.payload["components"])
        _require_successor(name, components[name]["state"], state)
        components[name] = _component(state)
        payload = self._make_payload(components)
        sequence = self.record["body"]["sequence"]
        self.record = self.store.commit(payload, expected_sequence=sequence, expected_head=self.record["state_root"])
        self.payload = payload
        return deepcopy(self.record)

    def callback(self, name: str):
        require(name in RUNTIME_SLOTS, "RUNTIME_COMPONENT_UNKNOWN")

        def persist(state: Any) -> None:
            self.update(name, state)

        return persist

