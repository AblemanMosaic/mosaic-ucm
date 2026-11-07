from .base import ComponentHandler, apply_select, option_label, option_labels, option_value, options


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    values, labels = options(owner, item, "options"), option_labels(owner, item, "options")
    selected = values.index(value) if value in values else 0
    owner.window.combo(key, labels, rect, selected=selected,
                       command=lambda selected: owner._apply({"intent": "SELECT", "node_id": node_id,
                                                               "value": option_value(owner, item, selected, "options")}))


def sync(owner, item, key, value):
    if value is not None:
        owner.window.set_combo_value(key, option_label(owner, item, value, "options"))


HANDLER = ComponentHandler("SELECT", draw_fill="field", default_action="Select", interaction_intent="SELECT",
                           build=build, sync=sync, interact=apply_select)
