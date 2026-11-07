from .base import ComponentHandler, apply_toggle, display


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    owner.window.checkbox(key, display(item), rect, checked=bool(value),
                          command=lambda selected: owner._apply({"intent": "TOGGLE", "node_id": node_id, "value": selected}))


def sync(owner, _item, key, value):
    owner.window.set_checked(key, bool(value))


HANDLER = ComponentHandler("CHECKBOX", default_action="Toggle", interaction_intent="TOGGLE",
                           build=build, sync=sync, interact=apply_toggle)
