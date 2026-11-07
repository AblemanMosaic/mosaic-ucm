from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path
from typing import Any, Iterable

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .headless import HeadlessRefusal, HeadlessUI, replay
from .model import STATES, UIRefusal, walk


DOCKET_SCHEMA = "mosaic.ui.probe-docket.v0.1"
LAYOUT_SCHEMA = "mosaic.ui.probe-layouts.v0.1"
CLAIM_BOUNDARY = "HEADLESS_EVIDENCE_DOES_NOT_ESTABLISH_HOST_DESKTOP_BEHAVIOR_OR_AUTHORITY"


class ProbeRefusal(UIRefusal):
    pass


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ProbeRefusal(code, detail)


def _write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_bytes(value) + b"\n")


def _generated_assignments(source: str) -> tuple[str, dict[str, Any]]:
    """Read the fixed Foundry module shape without executing generated Python."""
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        raise ProbeRefusal("GENERATED_MODULE_SYNTAX_REFUSED", str(exc)) from exc

    generated_root: str | None = None
    payload: dict[str, Any] | None = None
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if isinstance(node, ast.Import) and [alias.name for alias in node.names] == ["json"]:
            continue
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise ProbeRefusal("GENERATED_MODULE_SHAPE_REFUSED", type(node).__name__)
        name = node.targets[0].id
        if name == "GENERATED_ROOT":
            value = ast.literal_eval(node.value)
            _require(isinstance(value, str), "GENERATED_ROOT_INVALID")
            generated_root = value
            continue
        if name == "PAYLOAD":
            call = node.value
            valid_call = (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "json"
                and call.func.attr == "loads"
                and len(call.args) == 1
                and not call.keywords
            )
            _require(valid_call, "GENERATED_PAYLOAD_SHAPE_REFUSED")
            encoded = ast.literal_eval(call.args[0])
            _require(isinstance(encoded, str), "GENERATED_PAYLOAD_ENCODING_REFUSED")
            decoded = json.loads(encoded)
            _require(isinstance(decoded, dict), "GENERATED_PAYLOAD_INVALID")
            payload = decoded
            continue
        raise ProbeRefusal("GENERATED_MODULE_ASSIGNMENT_REFUSED", name)

    _require(generated_root is not None, "GENERATED_ROOT_ABSENT")
    _require(payload is not None, "GENERATED_PAYLOAD_ABSENT")
    return generated_root, payload


def load_subject(generated_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    module_path = generated_dir / "library.py"
    receipt_path = generated_dir / "receipt.json"
    _require(module_path.is_file(), "GENERATED_MODULE_ABSENT", str(module_path))
    _require(receipt_path.is_file(), "FOUNDRY_RECEIPT_ABSENT", str(receipt_path))

    source = module_path.read_text(encoding="utf-8")
    receipt = read_json(receipt_path)
    _require(isinstance(receipt, dict), "FOUNDRY_RECEIPT_INVALID")
    _require(receipt.get("schema") == "mosaic.ui.foundry-receipt.v0.1", "FOUNDRY_RECEIPT_SCHEMA_REFUSED")
    generated_root, payload = _generated_assignments(source)

    module_commitment = commitment("MOSAIC.UI.GENERATED_MODULE.v0.1", source)
    payload_commitment = commitment("MOSAIC.UI.GENERATED_LIBRARY.v0.1", payload)
    checks = {
        "module_commitment": receipt.get("module_sha256") == module_commitment,
        "generated_root": generated_root == receipt.get("generated_root") == payload_commitment,
        "input_root": receipt.get("input_root") == payload.get("input_root"),
        "component_count": receipt.get("component_count") == payload.get("library_validation", {}).get("component_count"),
        "node_count": receipt.get("node_count") == payload.get("tree_validation", {}).get("node_count"),
        "authority_effect": receipt.get("authority_effect") == "NONE" and payload.get("authority_effect") == "NONE",
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    _require(not failures, "SUBJECT_INTEGRITY_REFUSED", ",".join(failures))
    subject = {
        "schema": "mosaic.ui.probe-subject.v0.1",
        "generated_root": generated_root,
        "input_root": payload["input_root"],
        "module_commitment": module_commitment,
        "receipt_commitment": commitment("MOSAIC.UI.FOUNDRY_RECEIPT.v0.1", receipt),
        "component_count": receipt["component_count"],
        "node_count": receipt["node_count"],
        "integrity_checks": checks,
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    subject["commitment"] = commitment("MOSAIC.UI.PROBE_SUBJECT.v0.1", subject)
    return payload, subject


def _validate_docket(value: Any) -> dict[str, Any]:
    _require(isinstance(value, dict), "PROBE_DOCKET_INVALID")
    _require(value.get("schema") == DOCKET_SCHEMA, "PROBE_DOCKET_SCHEMA_REFUSED")
    _require(isinstance(value.get("docket_id"), str) and bool(value["docket_id"]), "PROBE_DOCKET_ID_INVALID")
    scenarios = value.get("scenarios")
    _require(isinstance(scenarios, list) and bool(scenarios), "PROBE_SCENARIOS_EMPTY")
    seen: set[str] = set()
    for scenario in scenarios:
        _require(isinstance(scenario, dict), "PROBE_SCENARIO_INVALID")
        scenario_id = scenario.get("id")
        _require(isinstance(scenario_id, str) and scenario_id and scenario_id not in seen,
                 "PROBE_SCENARIO_ID_INVALID", str(scenario_id))
        seen.add(scenario_id)
        _require(isinstance(scenario.get("events"), list), "PROBE_EVENTS_INVALID", scenario_id)
        _require(isinstance(scenario.get("viewports"), list) and bool(scenario["viewports"]),
                 "PROBE_VIEWPORTS_EMPTY", scenario_id)
        for viewport in scenario["viewports"]:
            valid = (
                isinstance(viewport, dict)
                and isinstance(viewport.get("width"), int)
                and isinstance(viewport.get("height"), int)
                and viewport["width"] > 0
                and viewport["height"] > 0
            )
            _require(valid, "PROBE_VIEWPORT_INVALID", scenario_id)
        expected = scenario.get("expected_refusals", [])
        _require(isinstance(expected, list) and all(isinstance(item, str) for item in expected),
                 "PROBE_EXPECTED_REFUSALS_INVALID", scenario_id)
        matrices = scenario.get("state_matrix", [])
        _require(isinstance(matrices, list), "PROBE_STATE_MATRIX_INVALID", scenario_id)
        for matrix in matrices:
            valid_matrix = (
                isinstance(matrix, dict)
                and set(matrix) == {"node_id", "states"}
                and isinstance(matrix.get("node_id"), str)
                and isinstance(matrix.get("states"), list)
                and bool(matrix["states"])
                and all(state in STATES for state in matrix["states"])
                and len(matrix["states"]) == len(set(matrix["states"]))
            )
            _require(valid_matrix, "PROBE_STATE_MATRIX_INVALID", scenario_id)
    return copy.deepcopy(value)


def _load_layouts(path: Path) -> tuple[dict[tuple[int, int], dict[str, tuple[int, int, int, int]]], dict[str, Any]]:
    value = read_json(path)
    _require(isinstance(value, dict) and value.get("schema") == LAYOUT_SCHEMA, "PROBE_LAYOUT_SCHEMA_REFUSED")
    plans = value.get("plans")
    _require(isinstance(plans, list) and bool(plans), "PROBE_LAYOUTS_EMPTY")
    index: dict[tuple[int, int], dict[str, tuple[int, int, int, int]]] = {}
    for plan in plans:
        _require(isinstance(plan, dict), "PROBE_LAYOUT_INVALID")
        width, height, rects = plan.get("width"), plan.get("height"), plan.get("rects")
        _require(isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0,
                 "PROBE_LAYOUT_VIEWPORT_INVALID")
        _require((width, height) not in index, "PROBE_LAYOUT_DUPLICATE", f"{width}x{height}")
        _require(isinstance(rects, dict), "PROBE_LAYOUT_RECTS_INVALID", f"{width}x{height}")
        normalized: dict[str, tuple[int, int, int, int]] = {}
        for key, rect in rects.items():
            valid = isinstance(key, str) and isinstance(rect, list) and len(rect) == 4 and all(isinstance(v, int) for v in rect)
            _require(valid, "PROBE_LAYOUT_RECT_INVALID", str(key))
            normalized[key] = tuple(rect)  # type: ignore[assignment]
        index[(width, height)] = normalized
    descriptor = {
        "schema": LAYOUT_SCHEMA,
        "viewport_count": len(index),
        "viewports": [{"width": width, "height": height} for width, height in sorted(index)],
        "commitment": commitment("MOSAIC.UI.PROBE_LAYOUTS.v0.1", value),
        "authority_effect": "NONE",
    }
    return index, descriptor


def _run_scenario(
    payload: dict[str, Any],
    scenario: dict[str, Any],
    layouts: dict[tuple[int, int], dict[str, tuple[int, int, int, int]]],
) -> dict[str, Any]:
    def layout_provider(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
        try:
            return copy.deepcopy(layouts[(width, height)])
        except KeyError as exc:
            raise ProbeRefusal("PROBE_LAYOUT_MISSING", f"{width}x{height}") from exc

    events = copy.deepcopy(scenario["events"])
    first_replay = replay(payload, layout_provider, events)
    second_replay = replay(payload, layout_provider, copy.deepcopy(events))
    deterministic = first_replay["commitment"] == second_replay["commitment"]

    runtime = HeadlessUI(payload, layout_provider)
    frames: list[dict[str, Any]] = []
    refusals: list[dict[str, Any]] = []

    def capture(sequence: int) -> None:
        projections = []
        for viewport in scenario["viewports"]:
            width, height = viewport["width"], viewport["height"]
            projection = runtime.project(width, height).as_dict()
            projections.append({"width": width, "height": height, **projection})
        frame = {"sequence": sequence, "state": runtime.snapshot(), "projections": projections}
        frame["commitment"] = commitment("MOSAIC.UI.PROBE_FRAME.v0.1", frame)
        frames.append(frame)

    capture(0)
    for sequence, event in enumerate(events, 1):
        try:
            runtime.apply(event)
        except HeadlessRefusal as exc:
            refusals.append({"sequence": sequence, "code": exc.code, "detail": exc.detail})
        capture(sequence)

    state_matrices = []
    for matrix in scenario.get("state_matrix", []):
        node_id = matrix["node_id"]
        probe_runtime = HeadlessUI(payload, layout_provider)
        node = probe_runtime.nodes.get(node_id)
        key = node.get("props", {}).get("realization_key") if node else None
        if not key:
            raise ProbeRefusal("PROBE_STATE_MATRIX_NODE_REFUSED", node_id)
        rows = []
        for state in matrix["states"]:
            fixture = HeadlessUI(payload, layout_provider)
            fixture.state["states"][key] = state
            fixture.state["focused_node_id"] = node_id if state == "FOCUSED" else None
            projections = []
            for viewport in scenario["viewports"]:
                width, height = viewport["width"], viewport["height"]
                projections.append({"width": width, "height": height,
                                    **fixture.project(width, height).as_dict()})
            row = {"state": state, "projections": projections, "projection_fixture_effect": "NONE"}
            row["commitment"] = commitment("MOSAIC.UI.PROBE_STATE_MATRIX_ROW.v0.1", row)
            rows.append(row)
        matrix_result = {
            "node_id": node_id, "realization_key": key, "states": rows,
            "authority_effect": "NONE",
            "claim_boundary": "STATE_MATRIX_IS_A_HEADLESS_PROJECTION_FIXTURE_NOT_A_HOST_INPUT_EVENT",
        }
        matrix_result["commitment"] = commitment("MOSAIC.UI.PROBE_STATE_MATRIX.v0.1", matrix_result)
        state_matrices.append(matrix_result)

    actual_refusals = [item["code"] for item in refusals]
    expected_refusals = scenario.get("expected_refusals", [])
    gate_failures = [
        {"sequence": frame["sequence"], "width": projection["width"], "height": projection["height"],
         "failures": projection["gates"]["failures"]}
        for frame in frames
        for projection in frame["projections"]
        if projection["gates"]["disposition"] != "PASS"
    ]
    gate_failures.extend(
        {"fixture_state": row["state"], "width": projection["width"], "height": projection["height"],
         "failures": projection["gates"]["failures"]}
        for matrix in state_matrices
        for row in matrix["states"]
        for projection in row["projections"]
        if projection["gates"]["disposition"] != "PASS"
    )
    failures: list[str] = []
    if not deterministic:
        failures.append("REPLAY_NONDETERMINISTIC")
    if actual_refusals != expected_refusals:
        failures.append("REFUSAL_EXPECTATION_MISMATCH")
    expected_replay = scenario.get("expected_replay_commitment")
    if expected_replay is not None and first_replay["commitment"] != expected_replay:
        failures.append("REPLAY_BASELINE_MISMATCH")
    if gate_failures:
        failures.append("PROJECTION_GATES_REFUSED")

    result = {
        "schema": "mosaic.ui.probe-scenario-result.v0.1",
        "scenario_id": scenario["id"],
        "event_count": len(events),
        "deterministic": deterministic,
        "replay": first_replay,
        "refusals": refusals,
        "expected_refusals": expected_refusals,
        "frames": frames,
        "state_matrices": state_matrices,
        "gate_failures": gate_failures,
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "host_effect": "NONE",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    result["commitment"] = commitment("MOSAIC.UI.PROBE_SCENARIO_RESULT.v0.1", result)
    return result


def run_probe(generated_dir: Path, docket_path: Path, layout_path: Path, output_dir: Path) -> tuple[dict[str, Any], int]:
    payload, subject = load_subject(generated_dir)
    docket = _validate_docket(read_json(docket_path))
    layouts, layout_descriptor = _load_layouts(layout_path)
    declared_keys = sorted(
        str(node["props"]["realization_key"])
        for node in walk(payload["application"]["tree"])
        if node.get("props", {}).get("realization_key")
    )
    layout_keys = sorted({key for plan in layouts.values() for key in plan})
    correspondence = {
        "declared_keys": declared_keys,
        "layout_keys": layout_keys,
        "missing_layout_keys": sorted(set(declared_keys) - set(layout_keys)),
        "undeclared_layout_keys": sorted(set(layout_keys) - set(declared_keys)),
    }
    correspondence["disposition"] = "PASS" if not correspondence["missing_layout_keys"] and not correspondence["undeclared_layout_keys"] else "REFUSE"

    results = [_run_scenario(payload, scenario, layouts) for scenario in docket["scenarios"]]
    failures = [result["scenario_id"] for result in results if result["disposition"] != "PASS_LOCAL_CANDIDATE"]
    if correspondence["disposition"] != "PASS":
        failures.insert(0, "REALIZATION_CORRESPONDENCE")
    bundle = {
        "schema": "mosaic.ui.probe-witness-bundle.v0.1",
        "docket_id": docket["docket_id"],
        "docket_commitment": commitment("MOSAIC.UI.PROBE_DOCKET.v0.1", docket),
        "subject": subject,
        "layouts": layout_descriptor,
        "realization_correspondence": correspondence,
        "scenario_count": len(results),
        "scenarios": results,
        "failed_scenarios": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "standing_effect": "NONE",
        "authority_effect": "NONE",
        "host_effect": "NONE",
        "claim_boundary": CLAIM_BOUNDARY,
        "nonclaims": [
            "HOST_DESKTOP_BEHAVIOR_NOT_ESTABLISHED",
            "PLATFORM_ACCESSIBILITY_BRIDGE_NOT_ESTABLISHED",
            "CONSTITUTIONAL_ADMISSION_NOT_CLAIMED",
            "PRODUCTION_RELEASE_NOT_CLAIMED",
        ],
    }
    bundle["witness_commitment"] = commitment("MOSAIC.UI.PROBE_WITNESS_BUNDLE.v0.1", bundle)
    receipt = {
        "schema": "mosaic.ui.probe-receipt.v0.1",
        "docket_id": docket["docket_id"],
        "generated_root": subject["generated_root"],
        "subject_commitment": subject["commitment"],
        "docket_commitment": bundle["docket_commitment"],
        "layout_commitment": layout_descriptor["commitment"],
        "witness_commitment": bundle["witness_commitment"],
        "scenario_count": len(results),
        "passed": len(results) - len([item for item in results if item["disposition"] != "PASS_LOCAL_CANDIDATE"]),
        "failed": len(failures),
        "disposition": bundle["disposition"],
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "standing_effect": "NONE",
        "authority_effect": "NONE",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.PROBE_RECEIPT.v0.1", receipt)
    _write_json(output_dir / "witness-bundle.json", bundle)
    _write_json(output_dir / "probe-receipt.json", receipt)
    return receipt, 0 if not failures else 32


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe a Mosaic UI Foundry output without host effects.")
    parser.add_argument("generated", type=Path, help="Directory containing library.py and receipt.json")
    parser.add_argument("--docket", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt, code = run_probe(args.generated.resolve(), args.docket.resolve(), args.layouts.resolve(), args.output.resolve())
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, indent=2))
        return code
    except (ProbeRefusal, UIRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        value = {
            "schema": "mosaic.ui.probe-refusal.v0.1",
            "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "PROBE_INPUT_OR_IO_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)),
            "effects_performed": [],
            "standing_effect": "NONE",
            "authority_effect": "NONE",
        }
        print(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
