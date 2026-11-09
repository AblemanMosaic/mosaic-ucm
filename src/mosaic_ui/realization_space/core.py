"""Validation, selection, and composition for Realization Space Contracts.

The kernel is deliberately independent of Panda3D, Pygame, Win32, and Mosaic
UI. Domain owners keep their own authority and supply application adapters.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import random
import re
from typing import Any, Iterable, Mapping


CONTRACT_SCHEMA = "mosaic.realization-space-contract.v0.1"
COMPOSITE_SCHEMA = "mosaic.realization-space-composite.v0.1"
CONFIGURATION_SCHEMA = "mosaic.realization-space-configuration.v0.1"

STATE_EFFECTS = frozenset({
    "PRESENTATION",
    "INPUT_POLICY",
    "SIMULATION_RULE",
    "WORLD_GENERATION",
    "PERSISTENCE_SCHEMA",
    "OBSERVATION_POLICY",
    "EVALUATION_ONLY",
    "DERIVED",
})
APPLY_MODES = frozenset({
    "IMMEDIATE",
    "FRAME_BOUNDARY",
    "PREPARE_AND_SWAP",
    "TICK_BOUNDARY",
    "WORLD_REVISION",
    "SAVE_MIGRATION",
    "RESTART_REQUIRED",
    "OFFLINE_ONLY",
})
OWNERSHIP = frozenset({"AUTHORIAL", "USER", "ADAPTIVE", "RUNTIME", "DERIVED", "EVIDENCE_ONLY"})
MUTABILITY = frozenset({"FROZEN", "INSTANCE", "SESSION", "FRAME", "EDIT", "DERIVED"})
CONTINUITY = frozenset({
    "DISCRETE", "CONTINUOUS_LINEAR", "CONTINUOUS_ANGULAR",
    "CONTINUOUS_COLOR", "PIECEWISE", "NOT_INTERPOLABLE",
})
VALUE_TYPES = frozenset({"BOOLEAN", "INTEGER", "NUMBER", "ENUM", "VECTOR", "COLOR", "CURVE", "SEED", "REFERENCE"})
CAPABILITIES = frozenset({
    "ENUMERATE", "VALIDATE", "NORMALIZE", "SAMPLE", "INTERPOLATE",
    "ESTIMATE_COST", "SELECT", "LOWER", "REALIZE", "COMPARE",
    "ADAPT", "EXPLAIN", "RECEIPT",
})
_ID = re.compile(r"^[A-Z][A-Z0-9_.:-]*$")
_CONTRACT_REQUIRED_FIELDS = frozenset({
    "schema", "contract_id", "contract_version", "subject", "possibility",
    "axes", "constraints", "capabilities", "selection", "lowering",
    "evidence", "authority",
})
_CONTRACT_ALLOWED_FIELDS = _CONTRACT_REQUIRED_FIELDS | frozenset({
    "description", "objectives", "preferred_regions", "adaptation", "revision",
})
_AXIS_ALLOWED_FIELDS = frozenset({
    "id", "label", "description", "value_type", "domain", "default", "unit",
    "precision", "ownership", "mutability", "continuity", "state_effect",
    "effect_owner", "apply_mode", "persistence_effect", "replay_effect",
    "dependencies", "cost_metrics", "ui_hint", "authority_effect",
})


class RealizationSpaceError(ValueError):
    """Stable typed refusal from the RSC kernel."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def canonical_root(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise RealizationSpaceError(code, detail)


def _axis_map(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    axes = contract.get("axes")
    _require(isinstance(axes, list) and bool(axes), "RSC_AXES_REQUIRED")
    result: dict[str, dict[str, Any]] = {}
    for raw in axes:
        _require(isinstance(raw, dict), "RSC_AXIS_SHAPE_REFUSED")
        axis_id = raw.get("id")
        _require(isinstance(axis_id, str) and _ID.fullmatch(axis_id) is not None,
                 "RSC_AXIS_ID_REFUSED", str(axis_id))
        _require(axis_id not in result, "RSC_AXIS_DUPLICATE", axis_id)
        result[axis_id] = raw
    return result


def _in_domain(axis: Mapping[str, Any], value: Any) -> bool:
    kind = axis["value_type"]
    domain = axis["domain"]
    if kind == "BOOLEAN":
        return isinstance(value, bool)
    if kind in {"INTEGER", "SEED"}:
        if not isinstance(value, int) or isinstance(value, bool):
            return False
    elif kind == "NUMBER":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            return False
    elif kind == "ENUM":
        return value in domain.get("values", [])
    elif kind in {"VECTOR", "COLOR"}:
        length = domain.get("length")
        return (isinstance(value, list) and (length is None or len(value) == length)
                and all(isinstance(item, (int, float)) and not isinstance(item, bool)
                        and math.isfinite(float(item)) for item in value))
    elif kind == "REFERENCE":
        return isinstance(value, str) and bool(value)
    elif kind == "CURVE":
        return (isinstance(value, list) and bool(value)
                and all(isinstance(point, list) and len(point) == 2
                        and all(isinstance(item, (int, float)) and not isinstance(item, bool)
                                and math.isfinite(float(item)) for item in point)
                        for point in value))
    else:
        return False
    minimum, maximum = domain.get("minimum"), domain.get("maximum")
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    step = domain.get("step")
    if step is not None:
        origin = minimum or 0
        quotient = (value - origin) / step
        if not math.isclose(quotient, round(quotient), abs_tol=1e-8):
            return False
    return True


def validate_axis(axis: Mapping[str, Any]) -> None:
    required = {
        "id", "label", "value_type", "domain", "default", "ownership",
        "mutability", "continuity", "state_effect", "effect_owner",
        "apply_mode", "persistence_effect", "replay_effect", "authority_effect",
    }
    _require(required <= set(axis), "RSC_AXIS_FIELDS_REFUSED", str(axis.get("id")))
    unexpected = set(axis) - _AXIS_ALLOWED_FIELDS
    _require(not unexpected, "RSC_AXIS_FIELDS_REFUSED", str(sorted(unexpected)))
    _require(axis["value_type"] in VALUE_TYPES, "RSC_AXIS_TYPE_REFUSED", axis["id"])
    _require(isinstance(axis["domain"], dict), "RSC_AXIS_DOMAIN_REFUSED", axis["id"])
    _require(axis["ownership"] in OWNERSHIP, "RSC_AXIS_OWNERSHIP_REFUSED", axis["id"])
    _require(axis["mutability"] in MUTABILITY, "RSC_AXIS_MUTABILITY_REFUSED", axis["id"])
    _require(axis["continuity"] in CONTINUITY, "RSC_AXIS_CONTINUITY_REFUSED", axis["id"])
    _require(axis["state_effect"] in STATE_EFFECTS, "RSC_AXIS_STATE_EFFECT_REFUSED", axis["id"])
    _require(isinstance(axis["effect_owner"], str) and bool(axis["effect_owner"]),
             "RSC_AXIS_EFFECT_OWNER_REFUSED", axis["id"])
    _require(axis["apply_mode"] in APPLY_MODES, "RSC_AXIS_APPLY_MODE_REFUSED", axis["id"])
    _require(axis["persistence_effect"] in {
        "NONE", "SESSION", "PROFILE", "SAVE_COMPATIBILITY", "NEW_WORLD",
        "SAVE_MIGRATION_REQUIRED",
    },
             "RSC_AXIS_PERSISTENCE_EFFECT_REFUSED", axis["id"])
    _require(axis["replay_effect"] in {"NONE", "PRESENTATION_ONLY", "INPUT_TRACE", "SIMULATION_RULES", "WORLD_IDENTITY"},
             "RSC_AXIS_REPLAY_EFFECT_REFUSED", axis["id"])
    _require(axis["authority_effect"] == "NONE", "RSC_AXIS_AUTHORITY_EFFECT_REFUSED", axis["id"])
    _require(_in_domain(axis, axis["default"]), "RSC_AXIS_DEFAULT_REFUSED", axis["id"])
    if axis["state_effect"] in {"SIMULATION_RULE", "WORLD_GENERATION", "PERSISTENCE_SCHEMA"}:
        _require(axis["apply_mode"] in {"TICK_BOUNDARY", "WORLD_REVISION", "SAVE_MIGRATION", "RESTART_REQUIRED"},
                 "RSC_AXIS_EFFECT_APPLICATION_REFUSED", axis["id"])
    if axis["ownership"] in {"DERIVED", "EVIDENCE_ONLY"}:
        _require(axis["mutability"] == "DERIVED", "RSC_AXIS_DERIVED_MUTABILITY_REFUSED", axis["id"])


def _segment_count(value: Any) -> int:
    return {"NONE": 0, "NORMAL_ONLY": 0, "ONE_SEGMENT_BEVEL": 1,
            "TWO_SEGMENT_BEVEL": 2}.get(str(value), 0)


def _safe_expression(expression: str, values: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    replacements: dict[str, Any] = {**context, **values}
    rewritten = expression
    names: dict[str, Any] = {}
    for index, key in enumerate(sorted(replacements, key=len, reverse=True)):
        token = f"_v{index}"
        rewritten = rewritten.replace(key, token)
        names[token] = replacements[key]
    try:
        tree = ast.parse(rewritten, mode="eval")
    except SyntaxError as exc:
        raise RealizationSpaceError("RSC_CONSTRAINT_SYNTAX_REFUSED", expression) from exc
    allowed = (
        ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
        ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.In, ast.NotIn, ast.Name, ast.Constant, ast.List, ast.Tuple,
        ast.Call, ast.Load,
    )
    for node in ast.walk(tree):
        _require(isinstance(node, allowed), "RSC_CONSTRAINT_NODE_REFUSED", type(node).__name__)
        if isinstance(node, ast.Name):
            _require(node.id in names or node.id in {"segments"},
                     "RSC_CONSTRAINT_NAME_REFUSED", node.id)
        if isinstance(node, ast.Call):
            _require(isinstance(node.func, ast.Name) and node.func.id == "segments"
                     and len(node.args) == 1 and not node.keywords,
                     "RSC_CONSTRAINT_CALL_REFUSED")
    return bool(eval(compile(tree, "<rsc-constraint>", "eval"),
                     {"__builtins__": {}, "segments": _segment_count}, names))


def validate_configuration(contract: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
    axes = _axis_map(contract)
    _require(set(values) == set(axes), "RSC_CONFIGURATION_KEYS_REFUSED",
             str(sorted(set(values) ^ set(axes))))
    normalized = copy.deepcopy(dict(values))
    for axis_id, axis in axes.items():
        _require(_in_domain(axis, normalized[axis_id]), "RSC_AXIS_DOMAIN_REFUSED", axis_id)
    context = {"authority_effect": contract.get("authority", {}).get("authority_effect")}
    for constraint in contract.get("constraints", []):
        if constraint.get("severity") != "HARD":
            continue
        _require(_safe_expression(constraint["expression"], normalized, context),
                 constraint.get("refusal_code", "RSC_CONSTRAINT_REFUSED"),
                 constraint.get("id", ""))
    return normalized


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(contract, dict) and contract.get("schema") == CONTRACT_SCHEMA,
             "RSC_SCHEMA_REFUSED")
    fields = set(contract)
    missing = _CONTRACT_REQUIRED_FIELDS - fields
    unexpected = fields - _CONTRACT_ALLOWED_FIELDS
    _require(not missing, "RSC_CONTRACT_FIELDS_REFUSED", f"missing={sorted(missing)}")
    _require(not unexpected, "RSC_CONTRACT_FIELDS_REFUSED",
             f"unexpected={sorted(unexpected)}")
    _require(isinstance(contract.get("contract_id"), str)
             and _ID.fullmatch(contract["contract_id"]) is not None,
             "RSC_CONTRACT_ID_REFUSED")
    authority = contract.get("authority")
    _require(isinstance(authority, dict) and authority.get("authority_effect") == "NONE"
             and authority.get("self_admission") is False
             and authority.get("release_gate") is False
             and authority.get("track_a_dependency") == "NONE",
             "RSC_AUTHORITY_REFUSED")
    axes = _axis_map(contract)
    for axis in axes.values():
        validate_axis(axis)
    capabilities = contract.get("capabilities")
    _require(isinstance(capabilities, list) and set(capabilities) <= CAPABILITIES,
             "RSC_CAPABILITIES_REFUSED")
    defaults = {axis_id: copy.deepcopy(axis["default"]) for axis_id, axis in axes.items()}
    validate_configuration(contract, defaults)
    seen_regions: set[str] = set()
    for region in contract.get("preferred_regions", []):
        _require(isinstance(region, dict) and isinstance(region.get("id"), str)
                 and region["id"] not in seen_regions, "RSC_REGION_REFUSED")
        seen_regions.add(region["id"])
        profile = {**defaults, **copy.deepcopy(region.get("profile_defaults", {}))}
        validate_configuration(contract, profile)
        _require(_safe_expression(region["predicate"], profile,
                                  {"authority_effect": "NONE"}),
                 "RSC_REGION_DEFAULTS_REFUSED", region["id"])
    result = copy.deepcopy(dict(contract))
    result["contract_root"] = canonical_root(contract)
    result["axis_count"] = len(axes)
    return result


def select_configuration(
    contract: Mapping[str, Any], *, requested: Mapping[str, Any] | None = None,
    region_id: str | None = None, locks: Iterable[str] = (), seed: int | None = None,
) -> dict[str, Any]:
    checked = validate_contract(contract)
    axes = _axis_map(contract)
    values = {axis_id: copy.deepcopy(axis["default"]) for axis_id, axis in axes.items()}
    selected_region = None
    if region_id is not None:
        regions = {region["id"]: region for region in contract.get("preferred_regions", [])}
        _require(region_id in regions, "RSC_PROFILE_UNKNOWN", region_id)
        selected_region = regions[region_id]
        values.update(copy.deepcopy(selected_region.get("profile_defaults", {})))
    requested = dict(requested or {})
    unknown = set(requested) - set(axes)
    _require(not unknown, "RSC_AXIS_UNKNOWN", str(sorted(unknown)))
    locked = set(locks)
    _require(locked <= set(axes), "RSC_LOCK_AXIS_UNKNOWN", str(sorted(locked - set(axes))))
    values.update(copy.deepcopy(requested))
    values = validate_configuration(contract, values)
    if selected_region is not None:
        _require(_safe_expression(selected_region["predicate"], values,
                                  {"authority_effect": "NONE"}),
                 "RSC_REGION_SELECTION_REFUSED", region_id or "")
    body = {
        "schema": CONFIGURATION_SCHEMA,
        "contract_id": contract["contract_id"],
        "contract_root": checked["contract_root"],
        "region_id": region_id,
        "values": values,
        "locks": sorted(locked),
        "seed": seed,
        "state_effects": sorted({axis["state_effect"] for axis in axes.values()}),
        "apply_modes": sorted({axis["apply_mode"] for axis in axes.values()}),
        "authority_effect": "NONE",
    }
    body["configuration_root"] = canonical_root(body)
    return body


def sample_configuration(contract: Mapping[str, Any], *, seed: int,
                         region_id: str | None = None,
                         locks: Mapping[str, Any] | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    axes = _axis_map(contract)
    values: dict[str, Any] = {}
    locked_values = dict(locks or {})
    for axis_id, axis in axes.items():
        if axis_id in locked_values:
            values[axis_id] = locked_values[axis_id]
            continue
        domain = axis["domain"]
        kind = axis["value_type"]
        if kind == "ENUM":
            values[axis_id] = rng.choice(list(domain["values"]))
        elif kind == "BOOLEAN":
            values[axis_id] = bool(rng.getrandbits(1))
        elif kind in {"INTEGER", "SEED"}:
            step = int(domain.get("step", 1))
            values[axis_id] = rng.randrange(int(domain["minimum"]), int(domain["maximum"]) + 1, step)
        elif kind == "NUMBER":
            step = domain.get("step")
            if step:
                count = round((domain["maximum"] - domain["minimum"]) / step)
                values[axis_id] = domain["minimum"] + rng.randint(0, count) * step
            else:
                values[axis_id] = rng.uniform(domain["minimum"], domain["maximum"])
        else:
            values[axis_id] = copy.deepcopy(axis["default"])
    return select_configuration(contract, requested=values, region_id=region_id,
                                locks=locked_values, seed=seed)


def compose_contracts(contracts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [validate_contract(contract) for contract in contracts]
    _require(bool(rows), "RSC_COMPOSITION_EMPTY")
    ids = [row["contract_id"] for row in rows]
    _require(len(ids) == len(set(ids)), "RSC_COMPOSITION_CONTRACT_DUPLICATE")
    axis_owner: dict[str, str] = {}
    for row in rows:
        for axis in row["axes"]:
            _require(axis["id"] not in axis_owner, "RSC_COMPOSITION_AXIS_COLLISION", axis["id"])
            axis_owner[axis["id"]] = row["contract_id"]
    body = {
        "schema": COMPOSITE_SCHEMA,
        "contracts": [{"contract_id": row["contract_id"], "contract_root": row["contract_root"],
                       "axis_count": row["axis_count"]} for row in rows],
        "axis_owner": dict(sorted(axis_owner.items())),
        "authority_effect": "NONE",
        "track_a_dependency": "NONE",
    }
    body["composite_root"] = canonical_root(body)
    return body
