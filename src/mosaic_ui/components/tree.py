from .base import ComponentHandler, apply_select, option_label, option_labels, option_value, options


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    choices = options(owner, item, "items", "options")
    labels = option_labels(owner, item, "items", "options")
    selected = choices.index(value) if value in choices else 0
    owner.window.listbox(
        key, labels, rect, selected=selected, kind="tree",
        command=lambda selected: owner._apply({"intent": "SELECT", "node_id": node_id,
                                                "value": option_value(owner, item, selected, "items", "options")}),
    )


def sync(owner, item, key, value):
    owner.window.set_list_value(key, option_label(owner, item, value, "items", "options"))


HANDLER = ComponentHandler("TREE", draw_fill="surface", default_action="Select tree item",
                           interaction_intent="SELECT", build=build, sync=sync, interact=apply_select)
