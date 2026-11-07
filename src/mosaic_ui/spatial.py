"""Engine-neutral Mosaic Spatial 3D schema, runner, and realization experiments."""
from __future__ import annotations

import copy
import math
from typing import Any

from .canonical import commitment
from .domain_protocol import (
    DOMAIN_PROTOCOL_SCHEMA, DomainRealizerDescriptor, DomainRefusal, negotiate_domain_protocol,
    require_exact_mapping, require_identifier, require_int_vector, require_sha256,
    semantic_state_root,
)


SPATIAL_SCENE_SCHEMA = "mosaic.spatial.scene.v0.1"
SPATIAL_EVENT_SCHEMA = "mosaic.spatial.event.v0.1"
SPATIAL_ACTION_TYPES = {"TRANSLATE", "SELECT", "NAVIGATE", "PERSIST"}


def _matrix_multiply(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [[sum(left[row][inner] * right[inner][column] for inner in range(4))
             for column in range(4)] for row in range(4)]


def _canonical_number(value: float) -> int | float:
    rounded = round(value, 9)
    if abs(rounded) < 1e-9:
        return 0
    integer = round(rounded)
    return int(integer) if abs(rounded - integer) < 1e-9 else rounded


def _local_transform(state: dict[str, Any]) -> list[list[float]]:
    x, y, z = (math.radians(value / 1000.0) for value in state["rotation_millidegrees"])
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rotation_x = [[1.0, 0.0, 0.0, 0.0], [0.0, cx, -sx, 0.0], [0.0, sx, cx, 0.0], [0.0, 0.0, 0.0, 1.0]]
    rotation_y = [[cy, 0.0, sy, 0.0], [0.0, 1.0, 0.0, 0.0], [-sy, 0.0, cy, 0.0], [0.0, 0.0, 0.0, 1.0]]
    rotation_z = [[cz, -sz, 0.0, 0.0], [sz, cz, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    scale = [[state["scale_milli"][0] / 1000.0, 0.0, 0.0, 0.0],
             [0.0, state["scale_milli"][1] / 1000.0, 0.0, 0.0],
             [0.0, 0.0, state["scale_milli"][2] / 1000.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    translation = [[1.0, 0.0, 0.0, float(state["position"][0])],
                   [0.0, 1.0, 0.0, float(state["position"][1])],
                   [0.0, 0.0, 1.0, float(state["position"][2])], [0.0, 0.0, 0.0, 1.0]]
    # Column-vector convention: local X, then Y, then Z rotation, then translation.
    return _matrix_multiply(translation, _matrix_multiply(rotation_z, _matrix_multiply(rotation_y,
                                                                                         _matrix_multiply(rotation_x, scale))))


def world_transform_closure(scene: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute deterministic hierarchical world matrices for every spatial object."""
    definitions = {item["object_id"]: item for item in scene["objects"]}
    states = snapshot["state"]["objects"]
    matrices: dict[str, list[list[float]]] = {}
    visiting: set[str] = set()

    def close(object_id: str) -> list[list[float]]:
        if object_id in matrices:
            return matrices[object_id]
        if object_id in visiting or object_id not in definitions or object_id not in states:
            raise DomainRefusal("SPATIAL_TRANSFORM_CLOSURE_REFUSED", object_id)
        visiting.add(object_id)
        local = _local_transform(states[object_id])
        parent_id = definitions[object_id]["parent_id"]
        matrices[object_id] = local if parent_id is None else _matrix_multiply(close(parent_id), local)
        visiting.remove(object_id)
        return matrices[object_id]

    result: dict[str, dict[str, Any]] = {}
    for object_id in sorted(definitions):
        matrix = close(object_id)
        canonical_matrix = [[_canonical_number(value) for value in row] for row in matrix]
        result[object_id] = {
            "matrix": canonical_matrix,
            "position": [canonical_matrix[index][3] for index in range(3)],
            "convention": "COLUMN_VECTOR_T_RZ_RY_RX_S",
        }
    return result


def validate_spatial_scene(value: Any) -> dict[str, Any]:
    keys = {"schema", "scene_id", "coordinate_system", "units", "bounds", "budgets", "assets",
            "objects", "camera", "actions", "authority_effect"}
    scene = require_exact_mapping(value, keys, "SPATIAL_SCENE_SCHEMA_REFUSED")
    if scene["schema"] != SPATIAL_SCENE_SCHEMA or scene["coordinate_system"] != "RIGHT_HANDED_Y_UP" \
            or scene["units"] != "MILLIMETER" or scene["authority_effect"] != "NONE":
        raise DomainRefusal("SPATIAL_SCENE_HEADER_REFUSED")
    require_identifier(scene["scene_id"], "SPATIAL_SCENE_ID_REFUSED")
    bounds = require_int_vector(scene["bounds"], 6, "SPATIAL_BOUNDS_REFUSED")
    if any(bounds[index] >= bounds[index + 3] for index in range(3)):
        raise DomainRefusal("SPATIAL_BOUNDS_REFUSED")
    budgets = require_exact_mapping(
        scene["budgets"], {"max_objects", "max_assets", "max_asset_bytes", "max_actions",
                           "max_triangles", "max_texture_bytes", "max_shader_units"},
        "SPATIAL_BUDGET_SCHEMA_REFUSED",
    )
    if not all(isinstance(budgets[key], int) and not isinstance(budgets[key], bool) and budgets[key] >= 0
               for key in budgets):
        raise DomainRefusal("SPATIAL_BUDGET_VALUE_REFUSED")
    if not isinstance(scene["assets"], list) or len(scene["assets"]) > budgets["max_assets"]:
        raise DomainRefusal("SPATIAL_ASSET_BUDGET_REFUSED")
    asset_ids: set[str] = set()
    total_asset_bytes = total_triangles = total_texture_bytes = total_shader_units = 0
    for asset in scene["assets"]:
        require_exact_mapping(
            asset, {"asset_id", "media_kind", "sha256", "bytes", "triangles", "texture_bytes", "shader_units"},
            "SPATIAL_ASSET_SCHEMA_REFUSED",
        )
        asset_id = require_identifier(asset["asset_id"], "SPATIAL_ASSET_ID_REFUSED")
        if asset_id in asset_ids or asset["media_kind"] not in {"MESH", "MATERIAL", "TEXTURE", "AUDIO"}:
            raise DomainRefusal("SPATIAL_ASSET_REFUSED", asset_id)
        require_sha256(asset["sha256"], "SPATIAL_ASSET_HASH_REFUSED")
        numeric = (asset["bytes"], asset["triangles"], asset["texture_bytes"], asset["shader_units"])
        if not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in numeric):
            raise DomainRefusal("SPATIAL_ASSET_COST_REFUSED", asset_id)
        total_asset_bytes += asset["bytes"]
        total_triangles += asset["triangles"]
        total_texture_bytes += asset["texture_bytes"]
        total_shader_units += asset["shader_units"]
        asset_ids.add(asset_id)
    if total_asset_bytes > budgets["max_asset_bytes"] or total_triangles > budgets["max_triangles"] \
            or total_texture_bytes > budgets["max_texture_bytes"] or total_shader_units > budgets["max_shader_units"]:
        raise DomainRefusal("SPATIAL_RESOURCE_BUDGET_REFUSED")
    if not isinstance(scene["objects"], list) or len(scene["objects"]) > budgets["max_objects"]:
        raise DomainRefusal("SPATIAL_OBJECT_BUDGET_REFUSED")
    object_ids: set[str] = set()
    parents: dict[str, str | None] = {}
    for item in scene["objects"]:
        require_exact_mapping(
            item, {"object_id", "kind", "parent_id", "asset_ref", "position", "rotation_millidegrees",
                   "scale_milli", "visible", "selectable", "persistent", "accessibility"},
            "SPATIAL_OBJECT_SCHEMA_REFUSED",
        )
        object_id = require_identifier(item["object_id"], "SPATIAL_OBJECT_ID_REFUSED")
        if object_id in object_ids or item["kind"] not in {"OBJECT", "ANCHOR", "SURFACE", "VOLUME", "PORTAL", "ZONE"}:
            raise DomainRefusal("SPATIAL_OBJECT_REFUSED", object_id)
        position = require_int_vector(item["position"], 3, "SPATIAL_POSITION_REFUSED")
        require_int_vector(item["rotation_millidegrees"], 3, "SPATIAL_ROTATION_REFUSED")
        require_int_vector(item["scale_milli"], 3, "SPATIAL_SCALE_REFUSED", positive=True)
        if any(position[index] < bounds[index] or position[index] > bounds[index + 3] for index in range(3)):
            raise DomainRefusal("SPATIAL_OBJECT_OUT_OF_BOUNDS", object_id)
        if item["asset_ref"] is not None and item["asset_ref"] not in asset_ids:
            raise DomainRefusal("SPATIAL_OBJECT_ASSET_REFUSED", object_id)
        if not all(isinstance(item[key], bool) for key in ("visible", "selectable", "persistent")):
            raise DomainRefusal("SPATIAL_OBJECT_FLAG_REFUSED", object_id)
        accessibility = require_exact_mapping(
            item["accessibility"], {"role", "name", "description"}, "SPATIAL_ACCESSIBILITY_REFUSED",
        )
        if not all(isinstance(accessibility[key], str) and accessibility[key] for key in accessibility):
            raise DomainRefusal("SPATIAL_ACCESSIBILITY_REFUSED", object_id)
        object_ids.add(object_id)
        parents[object_id] = item["parent_id"]
    for object_id, parent_id in parents.items():
        if parent_id is not None and (parent_id not in object_ids or parent_id == object_id):
            raise DomainRefusal("SPATIAL_PARENT_REFUSED", object_id)
        visited = {object_id}
        cursor = parent_id
        while cursor is not None:
            if cursor in visited:
                raise DomainRefusal("SPATIAL_PARENT_CYCLE_REFUSED", object_id)
            visited.add(cursor)
            cursor = parents[cursor]
    camera = require_exact_mapping(
        scene["camera"], {"camera_id", "position", "target", "navigation_bounds", "motion_safety"},
        "SPATIAL_CAMERA_SCHEMA_REFUSED",
    )
    require_identifier(camera["camera_id"], "SPATIAL_CAMERA_ID_REFUSED")
    camera_position = require_int_vector(camera["position"], 3, "SPATIAL_CAMERA_POSITION_REFUSED")
    camera_target = require_int_vector(camera["target"], 3, "SPATIAL_CAMERA_TARGET_REFUSED")
    navigation_bounds = require_int_vector(camera["navigation_bounds"], 6, "SPATIAL_NAVIGATION_BOUNDS_REFUSED")
    if any(navigation_bounds[index] < bounds[index] or navigation_bounds[index + 3] > bounds[index + 3]
           or navigation_bounds[index] >= navigation_bounds[index + 3] for index in range(3)):
        raise DomainRefusal("SPATIAL_NAVIGATION_BOUNDS_REFUSED")
    if any(camera_position[index] < navigation_bounds[index]
           or camera_position[index] > navigation_bounds[index + 3] for index in range(3)):
        raise DomainRefusal("SPATIAL_CAMERA_POSITION_REFUSED")
    if any(camera_target[index] < bounds[index] or camera_target[index] > bounds[index + 3]
           for index in range(3)):
        raise DomainRefusal("SPATIAL_CAMERA_TARGET_REFUSED")
    motion = require_exact_mapping(camera["motion_safety"], {"max_step_mm", "reduced_motion"}, "SPATIAL_MOTION_SAFETY_REFUSED")
    if not isinstance(motion["max_step_mm"], int) or motion["max_step_mm"] <= 0 \
            or not isinstance(motion["reduced_motion"], bool):
        raise DomainRefusal("SPATIAL_MOTION_SAFETY_REFUSED")
    if not isinstance(scene["actions"], list) or len(scene["actions"]) > budgets["max_actions"]:
        raise DomainRefusal("SPATIAL_ACTION_BUDGET_REFUSED")
    action_ids: set[str] = set()
    for action in scene["actions"]:
        require_exact_mapping(action, {"action_id", "type", "target_id", "delta", "effect"}, "SPATIAL_ACTION_SCHEMA_REFUSED")
        action_id = require_identifier(action["action_id"], "SPATIAL_ACTION_ID_REFUSED")
        if action_id in action_ids or action["type"] not in SPATIAL_ACTION_TYPES:
            raise DomainRefusal("SPATIAL_ACTION_REFUSED", action_id)
        if action["type"] in {"TRANSLATE", "SELECT", "PERSIST"} and action["target_id"] not in object_ids:
            raise DomainRefusal("SPATIAL_ACTION_TARGET_REFUSED", action_id)
        target_required = action["type"] in {"TRANSLATE", "SELECT", "PERSIST"}
        if target_required != (action["target_id"] is not None):
            raise DomainRefusal("SPATIAL_ACTION_TARGET_REFUSED", action_id)
        if action["type"] in {"TRANSLATE", "NAVIGATE"}:
            delta = require_int_vector(action["delta"], 3, "SPATIAL_ACTION_DELTA_REFUSED")
            if action["type"] == "NAVIGATE" and any(abs(item) > motion["max_step_mm"] for item in delta):
                raise DomainRefusal("SPATIAL_MOTION_SAFETY_REFUSED", action_id)
        elif action["delta"] is not None:
            raise DomainRefusal("SPATIAL_ACTION_DELTA_REFUSED", action_id)
        expected_effect = "PERSISTENCE_INTENT" if action["type"] == "PERSIST" else "NONE"
        if action["effect"] != expected_effect:
            raise DomainRefusal("SPATIAL_ACTION_EFFECT_REFUSED", action_id)
        action_ids.add(action_id)
    result = copy.deepcopy(scene)
    result["scene_commitment"] = commitment("MOSAIC.SPATIAL.SCENE.v0.1", scene)
    return result


class SpatialHeadlessRunner:
    def __init__(self, scene: dict[str, Any]) -> None:
        self.scene = validate_spatial_scene(scene)
        self._actions = {item["action_id"]: item for item in self.scene["actions"]}
        self._persistent = {item["object_id"]: item["persistent"] for item in self.scene["objects"]}
        self._state = {
            "sequence": 0, "selected_object_id": None,
            "camera_position": list(self.scene["camera"]["position"]),
            "objects": {
                item["object_id"]: {"position": list(item["position"]),
                                    "rotation_millidegrees": list(item["rotation_millidegrees"]),
                                    "scale_milli": list(item["scale_milli"]), "visible": item["visible"]}
                for item in self.scene["objects"]
            },
            "persistence_intent": None,
        }

    def snapshot(self) -> dict[str, Any]:
        state = copy.deepcopy(self._state)
        value = {
            "schema": "mosaic.spatial.headless-snapshot.v0.1", "scene_id": self.scene["scene_id"],
            "scene_commitment": self.scene["scene_commitment"], "state": state,
            "semantic_state_root": semantic_state_root("SPATIAL_3D", self.scene["scene_commitment"], state),
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.SPATIAL.HEADLESS_SNAPSHOT.v0.1", value)
        return value

    def _bounded_position(self, current: list[int], delta: list[int], bounds: list[int], code: str) -> list[int]:
        proposed = [current[index] + delta[index] for index in range(3)]
        if any(proposed[index] < bounds[index] or proposed[index] > bounds[index + 3] for index in range(3)):
            raise DomainRefusal(code)
        return proposed

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        require_exact_mapping(event, {"schema", "sequence", "action_id"}, "SPATIAL_EVENT_SCHEMA_REFUSED")
        if event["schema"] != SPATIAL_EVENT_SCHEMA or event["sequence"] != self._state["sequence"] + 1:
            raise DomainRefusal("SPATIAL_EVENT_SEQUENCE_REFUSED", str(event.get("sequence")))
        action = self._actions.get(event["action_id"])
        if action is None:
            raise DomainRefusal("SPATIAL_ACTION_NOT_DECLARED", str(event["action_id"]))
        before = self.snapshot()["semantic_state_root"]
        if action["type"] == "TRANSLATE":
            current = self._state["objects"][action["target_id"]]["position"]
            self._state["objects"][action["target_id"]]["position"] = self._bounded_position(
                current, action["delta"], self.scene["bounds"], "SPATIAL_TRANSITION_OUT_OF_BOUNDS",
            )
        elif action["type"] == "SELECT":
            subject = next(item for item in self.scene["objects"] if item["object_id"] == action["target_id"])
            if not subject["selectable"]:
                raise DomainRefusal("SPATIAL_SELECTION_REFUSED", action["target_id"])
            self._state["selected_object_id"] = action["target_id"]
        elif action["type"] == "NAVIGATE":
            self._state["camera_position"] = self._bounded_position(
                self._state["camera_position"], action["delta"], self.scene["camera"]["navigation_bounds"],
                "SPATIAL_NAVIGATION_REFUSED",
            )
        elif action["type"] == "PERSIST":
            target = action["target_id"]
            if not self._persistent[target]:
                raise DomainRefusal("SPATIAL_PERSISTENCE_REFUSED", target)
            self._state["persistence_intent"] = commitment(
                "MOSAIC.SPATIAL.PERSISTENCE_INTENT.v0.1", {target: self._state["objects"][target]},
            )
        self._state["sequence"] = event["sequence"]
        after = self.snapshot()["semantic_state_root"]
        receipt = {
            "schema": "mosaic.spatial.transition-receipt.v0.1", "event": copy.deepcopy(event),
            "before": before, "after": after, "effect": action["effect"],
            "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
        }
        receipt["commitment"] = commitment("MOSAIC.SPATIAL.TRANSITION_RECEIPT.v0.1", receipt)
        return receipt


class _SpatialAdapter:
    def __init__(self, descriptor: DomainRealizerDescriptor) -> None:
        self.descriptor = descriptor

    def negotiation(self) -> dict[str, Any]:
        return negotiate_domain_protocol(
            (DOMAIN_PROTOCOL_SCHEMA,), self.descriptor,
            required_capabilities=("SPATIAL_SCENE", "SEMANTIC_STATE", "TRANSFORM_CLOSURE"),
        )


class SpatialSceneGraphExperiment(_SpatialAdapter):
    def __init__(self) -> None:
        super().__init__(DomainRealizerDescriptor(
            "SPATIAL_SCENE_GRAPH_EXPERIMENT", "SPATIAL_3D", DOMAIN_PROTOCOL_SCHEMA,
            ("SPATIAL_SCENE", "SEMANTIC_STATE", "TRANSFORM_CLOSURE", "ASSET_REFERENCES"),
            ("SCENE_GRAPH",),
        ))

    def project(self, scene: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        definitions = {item["object_id"]: item for item in scene["objects"]}
        world = world_transform_closure(scene, snapshot)
        nodes = [
            {"id": object_id, "parent_id": definitions[object_id]["parent_id"],
             "position": state["position"], "rotation_millidegrees": state["rotation_millidegrees"],
             "scale_milli": state["scale_milli"], "world_transform": world[object_id],
             "asset_ref": definitions[object_id]["asset_ref"]}
            for object_id, state in sorted(snapshot["state"]["objects"].items()) if state["visible"]
        ]
        return _spatial_projection(self.descriptor, snapshot, "scene_graph", nodes)


class SpatialObjectIdDepthExperiment(_SpatialAdapter):
    def __init__(self) -> None:
        super().__init__(DomainRealizerDescriptor(
            "SPATIAL_OBJECT_ID_DEPTH_EXPERIMENT", "SPATIAL_3D", DOMAIN_PROTOCOL_SCHEMA,
            ("SPATIAL_SCENE", "SEMANTIC_STATE", "TRANSFORM_CLOSURE", "OBJECT_ID_DEPTH"),
            ("OBJECT_ID_DEPTH",),
        ))

    def project(self, scene: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        camera = snapshot["state"]["camera_position"]
        world = world_transform_closure(scene, snapshot)
        records = [
            {"object_id": object_id, "depth_mm": _canonical_number(world[object_id]["position"][2] - camera[2]),
             "selected": snapshot["state"]["selected_object_id"] == object_id,
             "visible": state["visible"]}
            for object_id, state in snapshot["state"]["objects"].items()
        ]
        records.sort(key=lambda item: (item["depth_mm"], item["object_id"]))
        return _spatial_projection(self.descriptor, snapshot, "object_id_depth", records)


def _spatial_projection(descriptor: DomainRealizerDescriptor, snapshot: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    result = {
        "schema": "mosaic.spatial.experimental-projection.v0.1", "descriptor": descriptor.as_dict(),
        "semantic_state_root": snapshot["semantic_state_root"], key: value,
        "exact_pixel_equality_required": False, "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "EXPERIMENTAL_PROJECTION_IS_NOT_RENDERER_PHYSICS_XR_OR_HOST_CERTIFICATION",
    }
    result["commitment"] = commitment("MOSAIC.SPATIAL.EXPERIMENTAL_PROJECTION.v0.1", result)
    return result


def reference_spatial_scene() -> dict[str, Any]:
    return {
        "schema": SPATIAL_SCENE_SCHEMA, "scene_id": "spatial.reference.one",
        "coordinate_system": "RIGHT_HANDED_Y_UP", "units": "MILLIMETER",
        "bounds": [-10000, -1000, -10000, 10000, 10000, 10000],
        "budgets": {"max_objects": 4, "max_assets": 2, "max_asset_bytes": 8192, "max_actions": 8,
                    "max_triangles": 1000, "max_texture_bytes": 4096, "max_shader_units": 4},
        "assets": [{"asset_id": "mesh.cube", "media_kind": "MESH", "sha256": "b" * 64,
                    "bytes": 2048, "triangles": 12, "texture_bytes": 0, "shader_units": 1}],
        "objects": [
            {"object_id": "anchor.origin", "kind": "ANCHOR", "parent_id": None, "asset_ref": None,
             "position": [0, 0, 0], "rotation_millidegrees": [0, 0, 0], "scale_milli": [1000, 1000, 1000],
             "visible": True, "selectable": False, "persistent": False,
             "accessibility": {"role": "anchor", "name": "Origin", "description": "Scene origin"}},
            {"object_id": "object.cube", "kind": "OBJECT", "parent_id": "anchor.origin", "asset_ref": "mesh.cube",
             "position": [0, 1000, 2000], "rotation_millidegrees": [0, 0, 0], "scale_milli": [1000, 1000, 1000],
             "visible": True, "selectable": True, "persistent": True,
             "accessibility": {"role": "object", "name": "Reference cube", "description": "Selectable cube"}},
        ],
        "camera": {"camera_id": "camera.main", "position": [0, 1500, -5000], "target": [0, 1000, 0],
                   "navigation_bounds": [-8000, 0, -8000, 8000, 8000, 8000],
                   "motion_safety": {"max_step_mm": 500, "reduced_motion": True}},
        "actions": [
            {"action_id": "translate.cube", "type": "TRANSLATE", "target_id": "object.cube", "delta": [250, 0, 0], "effect": "NONE"},
            {"action_id": "select.cube", "type": "SELECT", "target_id": "object.cube", "delta": None, "effect": "NONE"},
            {"action_id": "navigate.forward", "type": "NAVIGATE", "target_id": None, "delta": [0, 0, 500], "effect": "NONE"},
            {"action_id": "persist.cube", "type": "PERSIST", "target_id": "object.cube", "delta": None, "effect": "PERSISTENCE_INTENT"},
        ],
        "authority_effect": "NONE",
    }


def spatial_evidence_witness() -> dict[str, Any]:
    scene = reference_spatial_scene()
    events = [
        {"schema": SPATIAL_EVENT_SCHEMA, "sequence": 1, "action_id": "translate.cube"},
        {"schema": SPATIAL_EVENT_SCHEMA, "sequence": 2, "action_id": "select.cube"},
        {"schema": SPATIAL_EVENT_SCHEMA, "sequence": 3, "action_id": "navigate.forward"},
        {"schema": SPATIAL_EVENT_SCHEMA, "sequence": 4, "action_id": "persist.cube"},
    ]
    first, second = SpatialHeadlessRunner(scene), SpatialHeadlessRunner(scene)
    first_receipts = [first.apply(event) for event in events]
    second_receipts = [second.apply(event) for event in events]
    first_snapshot, second_snapshot = first.snapshot(), second.snapshot()
    adapters = (SpatialSceneGraphExperiment(), SpatialObjectIdDepthExperiment())
    projections = [adapter.project(first.scene, first_snapshot) for adapter in adapters]
    probe_scene = reference_spatial_scene()
    probe_scene["objects"][0]["position"] = [100, 200, 300]
    probe_scene["objects"][0]["rotation_millidegrees"] = [0, 90000, 0]
    probe_scene["objects"][0]["scale_milli"] = [2000, 1000, 1000]
    probe_scene["objects"][1]["position"] = [1000, 0, 0]
    probe_runner = SpatialHeadlessRunner(probe_scene)
    transform_probe = world_transform_closure(probe_runner.scene, probe_runner.snapshot())
    checks = {
        "SCHEMA_VALID": True,
        "DETERMINISTIC_REPLAY": first_snapshot == second_snapshot and first_receipts == second_receipts,
        "TWO_INDEPENDENT_EXPERIMENTS": len({item["descriptor"]["realizer_id"] for item in projections}) == 2,
        "SEMANTIC_STATE_EQUIVALENT": len({item["semantic_state_root"] for item in projections}) == 1,
        "TRANSFORM_CLOSURE": transform_probe["object.cube"]["position"] == [100, 200, -1700]
        and all("world_transform" in node for node in projections[0]["scene_graph"]),
        "PIXEL_EQUALITY_NOT_REQUIRED": all(item["exact_pixel_equality_required"] is False for item in projections),
        "ENGINE_BINDING_ABSENT": all(item["descriptor"]["engine_binding"] == "NONE_EXPERIMENTAL" for item in projections),
    }
    value = {
        "schema": "mosaic.spatial.evidence-witness.v0.1", "scene_commitment": first.scene["scene_commitment"],
        "events": events, "transition_receipts": first_receipts, "snapshot": first_snapshot,
        "negotiations": [adapter.negotiation() for adapter in adapters], "projections": projections,
        "transform_closure_probe": transform_probe,
        "checks": checks, "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "NO_3D_ENGINE_RENDERER_PHYSICS_XR_RUNTIME_OR_BROAD_HOST_BEHAVIOR_IS_AUTHORIZED_OR_CERTIFIED",
    }
    value["commitment"] = commitment("MOSAIC.SPATIAL.EVIDENCE_WITNESS.v0.1", value)
    return value


__all__ = [
    "SPATIAL_ACTION_TYPES", "SPATIAL_EVENT_SCHEMA", "SPATIAL_SCENE_SCHEMA",
    "SpatialHeadlessRunner", "SpatialObjectIdDepthExperiment", "SpatialSceneGraphExperiment",
    "reference_spatial_scene", "spatial_evidence_witness", "validate_spatial_scene", "world_transform_closure",
]
