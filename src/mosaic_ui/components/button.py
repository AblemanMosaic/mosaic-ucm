from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    node_id = str(item["node_id"])
    owner.window.button(key, display(item), rect, lambda: owner._apply({"intent": "ACTIVATE", "node_id": node_id}))
    props = item.get("props", {})
    owner.window.style_button(key, primary=bool(props.get("primary")), selected=bool(props.get("selected")))


HANDLER = ComponentHandler("BUTTON", draw_fill="surface_raised", corner_radius="md", default_action="Press", build=build)
