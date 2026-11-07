from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from mosaic_ui.canonical import commitment


Build = Callable[[Any, dict[str, Any], str, tuple[int, int, int, int], Any], None]
Sync = Callable[[Any, dict[str, Any], str, Any], None]
Interact = Callable[[Any, dict[str, Any], dict[str, Any]], None]
AccessibleValue = Callable[[Any, dict[str, Any]], str]
ProjectionText = Callable[[Any, dict[str, Any]], str]


def display(item: dict[str, Any]) -> str:
    return str(item.get("props", {}).get("display_text") or item["semantics"]["name"])


def option_pairs(owner: Any, item: dict[str, Any], *names: str) -> list[tuple[str, str]]:
    props = item.get("props", {})
    value = next((props.get(name) for name in names if props.get(name) is not None), None)
    if not isinstance(value, list) or not value:
        owner._component_refusal("NATIVE_OPTIONS_REFUSED", str(item["node_id"]))
    pairs = []
    for option in value:
        if isinstance(option, str):
            pair = (option, option)
        elif isinstance(option, dict):
            stable = option.get("value", option.get("label", option.get("name")))
            label = option.get("label", option.get("name", stable))
            pair = (stable, label)
        else:
            pair = (None, None)
        if not all(isinstance(part, str) and part for part in pair):
            owner._component_refusal("NATIVE_OPTIONS_REFUSED", str(item["node_id"]))
        pairs.append(pair)
    if len({pair[0] for pair in pairs}) != len(pairs) or len({pair[1] for pair in pairs}) != len(pairs):
        owner._component_refusal("NATIVE_OPTIONS_REFUSED", f'{item["node_id"]}:DUPLICATE')
    return pairs


def options(owner: Any, item: dict[str, Any], *names: str) -> list[str]:
    return [pair[0] for pair in option_pairs(owner, item, *names)]


def option_labels(owner: Any, item: dict[str, Any], *names: str) -> list[str]:
    return [pair[1] for pair in option_pairs(owner, item, *names)]


def option_label(owner: Any, item: dict[str, Any], value: Any, *names: str) -> str:
    pairs = option_pairs(owner, item, *names)
    return next((label for stable, label in pairs if stable == value), str(value or ""))


def option_value(owner: Any, item: dict[str, Any], label: Any, *names: str) -> str:
    pairs = option_pairs(owner, item, *names)
    selected = next((stable for stable, visible in pairs if visible == label), None)
    if selected is None:
        owner._component_refusal("NATIVE_OPTIONS_REFUSED", f'{item["node_id"]}:SELECTION')
    return selected


def default_accessible_value(value: Any, _props: dict[str, Any]) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "checked" if value else "not checked"
    return str(value)


def apply_select(runtime: Any, item: dict[str, Any], event: dict[str, Any]) -> None:
    value = event.get("value")
    props = item.get("props", {})
    choices = props.get("options") or props.get("tabs") or props.get("items")
    current = runtime.state["values"].get(props.get("realization_key"))
    if item.get("kind") == "DATA_GRID" and isinstance(current, dict):
        rows = current.get("rows", [])
        choices = [row[0] for row in rows if isinstance(row, (list, tuple)) and row]
    if item.get("kind") == "DATA_GRID" and not choices:
        rows = props.get("rows", [])
        choices = [row[0] for row in rows if isinstance(row, (list, tuple)) and row]
    if isinstance(choices, list):
        choices = [
            choice.get("value", choice.get("label", choice.get("name"))) if isinstance(choice, dict) else choice
            for choice in choices
        ]
    if not isinstance(choices, list) or value not in choices:
        runtime._component_refusal("INVALID_SELECTION", f'{item["node_id"]}:{value}')
    if item.get("kind") == "DATA_GRID" and isinstance(current, dict):
        runtime.state["values"][item["props"]["realization_key"]] = {**current, "selected": value}
    else:
        runtime.state["values"][item["props"]["realization_key"]] = value
    runtime.state["emitted_intents"].append({
        "intent": "REQUEST_SELECTION_CHANGE", "node_id": item["node_id"],
        "value": value, "authority_effect": "NONE",
    })


def apply_text_commit(runtime: Any, item: dict[str, Any], event: dict[str, Any]) -> None:
    props = item.get("props", {})
    if props.get("readonly"):
        runtime._component_refusal("TEXT_COMMIT_REFUSED", str(item["node_id"]))
    value = str(event.get("value") or "")
    if "\x00" in value:
        runtime._component_refusal("TEXT_VALUE_REFUSED", f'{item["node_id"]}:NUL')
    minimum = int(props.get("min_length", 0))
    maximum = props.get("max_length")
    if props.get("required") and not value.strip():
        runtime._component_refusal("TEXT_VALUE_REQUIRED", str(item["node_id"]))
    if len(value) < minimum:
        runtime._component_refusal("TEXT_VALUE_TOO_SHORT", f'{item["node_id"]}:{len(value)}<{minimum}')
    if maximum is not None and len(value) > int(maximum):
        runtime._component_refusal("TEXT_VALUE_TOO_LONG", f'{item["node_id"]}:{len(value)}>{maximum}')
    runtime.state["values"][props["realization_key"]] = value
    runtime.state["emitted_intents"].append({
        "intent": "REQUEST_TEXT_COMMIT", "node_id": item["node_id"],
        "value_commitment": commitment("MOSAIC.UI.TEXT.v0.1", value), "authority_effect": "NONE",
    })


def apply_toggle(runtime: Any, item: dict[str, Any], event: dict[str, Any]) -> None:
    value = event.get("value")
    if value is not None and not isinstance(value, bool):
        runtime._component_refusal("INVALID_TOGGLE_VALUE", f'{item["node_id"]}:{value}')
    key = item["props"]["realization_key"]
    selected = not bool(runtime.state["values"].get(key, False)) if value is None else value
    runtime.state["values"][key] = selected
    runtime.state["emitted_intents"].append({
        "intent": "REQUEST_SELECTION_CHANGE", "node_id": item["node_id"], "value": selected,
        "interaction": "TOGGLE", "authority_effect": "NONE",
    })


def apply_step(runtime: Any, item: dict[str, Any], event: dict[str, Any]) -> None:
    props = item.get("props", {})
    steps = props.get("steps")
    if not isinstance(steps, list) or not steps:
        runtime._component_refusal("STEPPER_STEPS_ABSENT", str(item["node_id"]))
    step_values = [
        step.get("value", step.get("label", step.get("name"))) if isinstance(step, dict) else step
        for step in steps
    ]
    key = props["realization_key"]
    current = runtime.state["values"].get(key, props.get("default", 0))
    try:
        current_index = step_values.index(current) if current in step_values else int(current)
        target_index = int(event["index"]) if "index" in event else current_index + int(event.get("delta", 1))
    except (TypeError, ValueError):
        runtime._component_refusal("INVALID_STEP", str(item["node_id"]))
    if target_index < 0 or target_index >= len(steps):
        runtime._component_refusal("STEP_OUT_OF_RANGE", f'{item["node_id"]}:{target_index}')
    selected = step_values[target_index]
    runtime.state["values"][key] = selected
    runtime.state["emitted_intents"].append({
        "intent": "REQUEST_SELECTION_CHANGE", "node_id": item["node_id"], "value": selected,
        "index": target_index, "interaction": "STEP", "authority_effect": "NONE",
    })


def apply_dialog(runtime: Any, item: dict[str, Any], event: dict[str, Any]) -> None:
    value = event.get("value")
    decisions = item.get("props", {}).get("decisions")
    if isinstance(decisions, list):
        decisions = [
            decision.get("value", decision.get("label", decision.get("name")))
            if isinstance(decision, dict) else decision for decision in decisions
        ]
    if not isinstance(decisions, list) or value not in decisions:
        runtime._component_refusal("INVALID_DIALOG_DECISION", f'{item["node_id"]}:{value}')
    runtime.state["values"][item["props"]["realization_key"]] = value
    runtime.state["emitted_intents"].append({
        "intent": "REQUEST_DIALOG_DECISION", "node_id": item["node_id"],
        "value": value, "authority_effect": "NONE",
    })


@dataclass(frozen=True)
class ComponentHandler:
    kind: str
    draw_fill: str = "canvas"
    corner_radius: str | None = None
    default_action: str = ""
    interaction_intent: str | None = None
    build: Build | None = None
    sync: Sync | None = None
    interact: Interact | None = None
    accessible_value: AccessibleValue = default_accessible_value
    projection_text: ProjectionText = default_accessible_value
