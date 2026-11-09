"""Engine-neutral Mosaic Play 2D schema, headless runner, and experiments."""
from __future__ import annotations

import copy
from typing import Any

from .canonical import commitment
from .domain_protocol import (
    DOMAIN_PROTOCOL_SCHEMA, DomainRealizerDescriptor, DomainRefusal, negotiate_domain_protocol,
    require_exact_mapping, require_identifier, require_int_vector, require_sha256,
    semantic_state_root,
)


PLAY_SCENE_SCHEMA = "mosaic.play.scene.v0.1"
PLAY_EVENT_SCHEMA = "mosaic.play.event.v0.1"
PLAY_ACTION_TYPES = {"MOVE", "SELECT", "TOGGLE_VISIBILITY", "PAUSE", "SAVE"}


def _validate_assets(assets: Any, maximum: int, byte_budget: int) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(assets, list) or len(assets) > maximum:
        raise DomainRefusal("PLAY_ASSET_BUDGET_REFUSED", str(len(assets) if isinstance(assets, list) else assets))
    seen: set[str] = set()
    total = 0
    for asset in assets:
        require_exact_mapping(asset, {"asset_id", "media_kind", "sha256", "bytes"}, "PLAY_ASSET_SCHEMA_REFUSED")
        asset_id = require_identifier(asset["asset_id"], "PLAY_ASSET_ID_REFUSED")
        if asset_id in seen or asset["media_kind"] not in {"SPRITE", "TILEMAP", "AUDIO"}:
            raise DomainRefusal("PLAY_ASSET_REFUSED", asset_id)
        require_sha256(asset["sha256"], "PLAY_ASSET_HASH_REFUSED")
        if not isinstance(asset["bytes"], int) or isinstance(asset["bytes"], bool) or asset["bytes"] < 0:
            raise DomainRefusal("PLAY_ASSET_BYTES_REFUSED", asset_id)
        total += asset["bytes"]
        seen.add(asset_id)
    if total > byte_budget:
        raise DomainRefusal("PLAY_ASSET_BYTE_BUDGET_REFUSED", str(total))
    return copy.deepcopy(assets), seen


def validate_play_scene(value: Any) -> dict[str, Any]:
    keys = {"schema", "scene_id", "units", "bounds", "budgets", "assets", "entities",
            "actions", "persistence", "authority_effect"}
    scene = require_exact_mapping(value, keys, "PLAY_SCENE_SCHEMA_REFUSED")
    if scene["schema"] != PLAY_SCENE_SCHEMA or scene["units"] != "MILLI_PIXEL" \
            or scene["authority_effect"] != "NONE":
        raise DomainRefusal("PLAY_SCENE_HEADER_REFUSED")
    require_identifier(scene["scene_id"], "PLAY_SCENE_ID_REFUSED")
    width, height = require_int_vector(scene["bounds"], 2, "PLAY_BOUNDS_REFUSED", positive=True)
    budgets = require_exact_mapping(
        scene["budgets"], {"max_entities", "max_assets", "max_asset_bytes", "max_actions"},
        "PLAY_BUDGET_SCHEMA_REFUSED",
    )
    if not all(isinstance(budgets[key], int) and not isinstance(budgets[key], bool) and budgets[key] >= 0
               for key in budgets):
        raise DomainRefusal("PLAY_BUDGET_VALUE_REFUSED")
    _, asset_ids = _validate_assets(scene["assets"], budgets["max_assets"], budgets["max_asset_bytes"])
    if not isinstance(scene["entities"], list) or len(scene["entities"]) > budgets["max_entities"]:
        raise DomainRefusal("PLAY_ENTITY_BUDGET_REFUSED")
    entity_ids: set[str] = set()
    for entity in scene["entities"]:
        require_exact_mapping(
            entity, {"entity_id", "kind", "asset_ref", "position", "size", "visible", "interactive",
                     "accessibility"}, "PLAY_ENTITY_SCHEMA_REFUSED",
        )
        entity_id = require_identifier(entity["entity_id"], "PLAY_ENTITY_ID_REFUSED")
        if entity_id in entity_ids or entity["kind"] not in {"SPRITE", "TILE", "HUD", "ZONE"}:
            raise DomainRefusal("PLAY_ENTITY_REFUSED", entity_id)
        position = require_int_vector(entity["position"], 2, "PLAY_ENTITY_POSITION_REFUSED")
        size = require_int_vector(entity["size"], 2, "PLAY_ENTITY_SIZE_REFUSED", positive=True)
        if position[0] < 0 or position[1] < 0 or position[0] + size[0] > width or position[1] + size[1] > height:
            raise DomainRefusal("PLAY_ENTITY_OUT_OF_BOUNDS", entity_id)
        if entity["asset_ref"] is not None and entity["asset_ref"] not in asset_ids:
            raise DomainRefusal("PLAY_ENTITY_ASSET_REFUSED", entity_id)
        if not isinstance(entity["visible"], bool) or not isinstance(entity["interactive"], bool):
            raise DomainRefusal("PLAY_ENTITY_FLAG_REFUSED", entity_id)
        accessibility = require_exact_mapping(entity["accessibility"], {"role", "name"}, "PLAY_ACCESSIBILITY_REFUSED")
        if not all(isinstance(accessibility[key], str) and accessibility[key] for key in accessibility):
            raise DomainRefusal("PLAY_ACCESSIBILITY_REFUSED", entity_id)
        entity_ids.add(entity_id)
    if not isinstance(scene["actions"], list) or len(scene["actions"]) > budgets["max_actions"]:
        raise DomainRefusal("PLAY_ACTION_BUDGET_REFUSED")
    action_ids: set[str] = set()
    for action in scene["actions"]:
        require_exact_mapping(action, {"action_id", "type", "target_id", "delta", "effect"}, "PLAY_ACTION_SCHEMA_REFUSED")
        action_id = require_identifier(action["action_id"], "PLAY_ACTION_ID_REFUSED")
        if action_id in action_ids or action["type"] not in PLAY_ACTION_TYPES:
            raise DomainRefusal("PLAY_ACTION_REFUSED", action_id)
        if action["target_id"] is not None and action["target_id"] not in entity_ids:
            raise DomainRefusal("PLAY_ACTION_TARGET_REFUSED", action_id)
        target_required = action["type"] in {"MOVE", "SELECT", "TOGGLE_VISIBILITY"}
        if target_required != (action["target_id"] is not None):
            raise DomainRefusal("PLAY_ACTION_TARGET_REFUSED", action_id)
        if action["type"] == "MOVE":
            require_int_vector(action["delta"], 2, "PLAY_ACTION_DELTA_REFUSED")
        elif action["delta"] is not None:
            raise DomainRefusal("PLAY_ACTION_DELTA_REFUSED", action_id)
        expected_effect = "PERSISTENCE_INTENT" if action["type"] == "SAVE" else "NONE"
        if action["effect"] != expected_effect:
            raise DomainRefusal("PLAY_ACTION_EFFECT_REFUSED", action_id)
        action_ids.add(action_id)
    persistence = require_exact_mapping(scene["persistence"], {"keys", "maximum_bytes"}, "PLAY_PERSISTENCE_REFUSED")
    if not isinstance(persistence["keys"], list) or persistence["keys"] != sorted(set(persistence["keys"])) \
            or not all(isinstance(item, str) and item for item in persistence["keys"]) \
            or not set(persistence["keys"]) <= {"entities", "paused", "selected_entity_id"} \
            or not isinstance(persistence["maximum_bytes"], int) or persistence["maximum_bytes"] < 0:
        raise DomainRefusal("PLAY_PERSISTENCE_REFUSED")
    result = copy.deepcopy(scene)
    result["scene_commitment"] = commitment("MOSAIC.PLAY.SCENE.v0.1", scene)
    return result


class PlayHeadlessRunner:
    def __init__(self, scene: dict[str, Any]) -> None:
        self.scene = validate_play_scene(scene)
        self._actions = {item["action_id"]: item for item in self.scene["actions"]}
        self._sizes = {item["entity_id"]: tuple(item["size"]) for item in self.scene["entities"]}
        self._state = {
            "sequence": 0,
            "paused": False,
            "selected_entity_id": None,
            "entities": {
                item["entity_id"]: {"position": list(item["position"]), "visible": item["visible"]}
                for item in self.scene["entities"]
            },
            "persistence_intent": None,
        }

    def snapshot(self) -> dict[str, Any]:
        state = copy.deepcopy(self._state)
        value = {
            "schema": "mosaic.play.headless-snapshot.v0.1",
            "scene_id": self.scene["scene_id"],
            "scene_commitment": self.scene["scene_commitment"],
            "state": state,
            "semantic_state_root": semantic_state_root("PLAY_2D", self.scene["scene_commitment"], state),
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.PLAY.HEADLESS_SNAPSHOT.v0.1", value)
        return value

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        require_exact_mapping(event, {"schema", "sequence", "action_id"}, "PLAY_EVENT_SCHEMA_REFUSED")
        if event["schema"] != PLAY_EVENT_SCHEMA or event["sequence"] != self._state["sequence"] + 1:
            raise DomainRefusal("PLAY_EVENT_SEQUENCE_REFUSED", str(event.get("sequence")))
        action = self._actions.get(event["action_id"])
        if action is None:
            raise DomainRefusal("PLAY_ACTION_NOT_DECLARED", str(event["action_id"]))
        before = self.snapshot()["semantic_state_root"]
        target = action["target_id"]
        if action["type"] == "MOVE":
            position = self._state["entities"][target]["position"]
            proposed = [position[index] + action["delta"][index] for index in range(2)]
            width, height = self.scene["bounds"]
            entity_width, entity_height = self._sizes[target]
            if proposed[0] < 0 or proposed[1] < 0 or proposed[0] + entity_width > width \
                    or proposed[1] + entity_height > height:
                raise DomainRefusal("PLAY_TRANSITION_OUT_OF_BOUNDS", target)
            self._state["entities"][target]["position"] = proposed
        elif action["type"] == "SELECT":
            if not next(item for item in self.scene["entities"] if item["entity_id"] == target)["interactive"]:
                raise DomainRefusal("PLAY_SELECTION_REFUSED", target)
            self._state["selected_entity_id"] = target
        elif action["type"] == "TOGGLE_VISIBILITY":
            current = self._state["entities"][target]["visible"]
            self._state["entities"][target]["visible"] = not current
        elif action["type"] == "PAUSE":
            self._state["paused"] = not self._state["paused"]
        elif action["type"] == "SAVE":
            persisted = {key: self._state.get(key) for key in self.scene["persistence"]["keys"]}
            self._state["persistence_intent"] = commitment("MOSAIC.PLAY.PERSISTENCE_INTENT.v0.1", persisted)
        self._state["sequence"] = event["sequence"]
        after = self.snapshot()["semantic_state_root"]
        receipt = {
            "schema": "mosaic.play.transition-receipt.v0.1", "event": copy.deepcopy(event),
            "before": before, "after": after, "effect": action["effect"],
            "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
        }
        receipt["commitment"] = commitment("MOSAIC.PLAY.TRANSITION_RECEIPT.v0.1", receipt)
        return receipt


class _PlayAdapter:
    def __init__(self, descriptor: DomainRealizerDescriptor) -> None:
        self.descriptor = descriptor

    def negotiation(self) -> dict[str, Any]:
        return negotiate_domain_protocol(
            (DOMAIN_PROTOCOL_SCHEMA,), self.descriptor,
            required_capabilities=("PLAY_SCENE", "SEMANTIC_STATE"),
        )


class PlayDrawCommandsExperiment(_PlayAdapter):
    def __init__(self) -> None:
        super().__init__(DomainRealizerDescriptor(
            "PLAY_DRAW_COMMANDS_EXPERIMENT", "PLAY_2D", DOMAIN_PROTOCOL_SCHEMA,
            ("PLAY_SCENE", "SEMANTIC_STATE", "ASSET_REFERENCES"), ("DRAW_COMMANDS",),
        ))

    def project(self, scene: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        entities = {item["entity_id"]: item for item in scene["entities"]}
        commands = []
        for entity_id, state in sorted(snapshot["state"]["entities"].items()):
            entity = entities[entity_id]
            if state["visible"]:
                commands.append({"op": "DRAW_ENTITY", "id": entity_id, "kind": entity["kind"],
                                 "position": state["position"], "size": entity["size"],
                                 "asset_ref": entity["asset_ref"]})
        return _play_projection(self.descriptor, snapshot, "draw_commands", commands)


class PlayEntitySnapshotExperiment(_PlayAdapter):
    def __init__(self) -> None:
        super().__init__(DomainRealizerDescriptor(
            "PLAY_ENTITY_SNAPSHOT_EXPERIMENT", "PLAY_2D", DOMAIN_PROTOCOL_SCHEMA,
            ("PLAY_SCENE", "SEMANTIC_STATE", "ACCESSIBILITY"), ("ENTITY_SNAPSHOT",),
        ))

    def project(self, scene: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        state = snapshot["state"]
        records = [
            {"id": item["entity_id"], "role": item["accessibility"]["role"],
             "name": item["accessibility"]["name"], "interactive": item["interactive"],
             "selected": state["selected_entity_id"] == item["entity_id"],
             "visible": state["entities"][item["entity_id"]]["visible"]}
            for item in sorted(scene["entities"], key=lambda value: value["entity_id"])
        ]
        return _play_projection(self.descriptor, snapshot, "entities", records)


def _play_projection(descriptor: DomainRealizerDescriptor, snapshot: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    result = {
        "schema": "mosaic.play.experimental-projection.v0.1", "descriptor": descriptor.as_dict(),
        "semantic_state_root": snapshot["semantic_state_root"], key: value,
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "EXPERIMENTAL_PROJECTION_IS_NOT_AN_ENGINE_OR_RENDERER_CERTIFICATION",
    }
    result["commitment"] = commitment("MOSAIC.PLAY.EXPERIMENTAL_PROJECTION.v0.1", result)
    return result


def reference_play_scene() -> dict[str, Any]:
    return {
        "schema": PLAY_SCENE_SCHEMA, "scene_id": "play.reference.one", "units": "MILLI_PIXEL",
        "bounds": [320000, 180000],
        "budgets": {"max_entities": 4, "max_assets": 2, "max_asset_bytes": 4096, "max_actions": 8},
        "assets": [{"asset_id": "sprite.player", "media_kind": "SPRITE", "sha256": "a" * 64, "bytes": 1024}],
        "entities": [
            {"entity_id": "player", "kind": "SPRITE", "asset_ref": "sprite.player",
             "position": [10000, 10000], "size": [16000, 16000], "visible": True, "interactive": True,
             "accessibility": {"role": "player", "name": "Player"}},
            {"entity_id": "hud.status", "kind": "HUD", "asset_ref": None,
             "position": [0, 0], "size": [100000, 12000], "visible": True, "interactive": False,
             "accessibility": {"role": "status", "name": "Scene status"}},
        ],
        "actions": [
            {"action_id": "move.right", "type": "MOVE", "target_id": "player", "delta": [1000, 0], "effect": "NONE"},
            {"action_id": "select.player", "type": "SELECT", "target_id": "player", "delta": None, "effect": "NONE"},
            {"action_id": "pause", "type": "PAUSE", "target_id": None, "delta": None, "effect": "NONE"},
            {"action_id": "save", "type": "SAVE", "target_id": None, "delta": None, "effect": "PERSISTENCE_INTENT"},
        ],
        "persistence": {"keys": ["paused", "selected_entity_id"], "maximum_bytes": 1024},
        "authority_effect": "NONE",
    }


def play_evidence_witness() -> dict[str, Any]:
    scene = reference_play_scene()
    events = [
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 1, "action_id": "move.right"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 2, "action_id": "select.player"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 3, "action_id": "save"},
    ]
    first, second = PlayHeadlessRunner(scene), PlayHeadlessRunner(scene)
    first_receipts = [first.apply(event) for event in events]
    second_receipts = [second.apply(event) for event in events]
    first_snapshot, second_snapshot = first.snapshot(), second.snapshot()
    adapters = (PlayDrawCommandsExperiment(), PlayEntitySnapshotExperiment())
    projections = [adapter.project(first.scene, first_snapshot) for adapter in adapters]
    negotiations = [adapter.negotiation() for adapter in adapters]
    checks = {
        "SCHEMA_VALID": True,
        "DETERMINISTIC_REPLAY": first_snapshot == second_snapshot and first_receipts == second_receipts,
        "TWO_INDEPENDENT_EXPERIMENTS": len({item["descriptor"]["realizer_id"] for item in projections}) == 2,
        "SEMANTIC_STATE_EQUIVALENT": len({item["semantic_state_root"] for item in projections}) == 1,
        "ENGINE_BINDING_ABSENT": all(item["descriptor"]["engine_binding"] == "NONE_EXPERIMENTAL" for item in projections),
    }
    value = {
        "schema": "mosaic.play.evidence-witness.v0.1", "scene_commitment": first.scene["scene_commitment"],
        "events": events, "transition_receipts": first_receipts, "snapshot": first_snapshot,
        "negotiations": negotiations, "projections": projections, "checks": checks,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "NO_2D_ENGINE_RENDERER_AUDIO_PHYSICS_OR_FRAME_LOOP_IS_AUTHORIZED_OR_CERTIFIED",
    }
    value["commitment"] = commitment("MOSAIC.PLAY.EVIDENCE_WITNESS.v0.1", value)
    return value


__all__ = [
    "PLAY_ACTION_TYPES", "PLAY_EVENT_SCHEMA", "PLAY_SCENE_SCHEMA", "PlayDrawCommandsExperiment",
    "PlayEntitySnapshotExperiment", "PlayHeadlessRunner", "play_evidence_witness",
    "reference_play_scene", "validate_play_scene",
]
