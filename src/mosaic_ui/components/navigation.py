from .base import ComponentHandler, apply_select, option_label, option_labels, option_value


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    owner.window.navigation(key, option_labels(owner, item, "options", "items"), rect,
                            selected=option_label(owner, item, value, "options", "items"),
                            command=lambda selected: owner._apply(
                                {"intent": "SELECT", "node_id": node_id,
                                 "value": option_value(owner, item, selected, "options", "items")}))


def sync(owner, item, key, value):
    owner.window.set_choice(key, option_labels(owner, item, "options", "items"),
                            option_label(owner, item, value, "options", "items"))


HANDLER = ComponentHandler("NAVIGATION", draw_fill="surface", default_action="Navigate",
                           interaction_intent="SELECT", build=build, sync=sync, interact=apply_select)
