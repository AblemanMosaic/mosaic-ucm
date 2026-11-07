from .base import ComponentHandler, apply_dialog, display, option_label, option_labels, option_value


def build(owner, item, key, rect, value):
    node_id, props = str(item["node_id"]), item.get("props", {})
    decisions = option_labels(owner, item, "decisions")
    owner.window.dialog(key, display(item), str(props.get("message", item["semantics"].get("description", ""))),
                        decisions, rect, selected=option_label(owner, item, value, "decisions"),
                        command=lambda selected: owner._apply({"intent": "DIALOG_DECISION", "node_id": node_id,
                                                                "value": option_value(owner, item, selected, "decisions")}))


def accessible(value, props):
    return str(value or props.get("decisions", [""])[0])


HANDLER = ComponentHandler("DIALOG", default_action="Choose decision", interaction_intent="DIALOG_DECISION",
                           build=build, interact=apply_dialog, accessible_value=accessible)
