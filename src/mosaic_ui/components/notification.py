from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    owner.window.notification(key, display(item), rect, tone=str(item.get("props", {}).get("tone", "info")))


def sync(owner, item, key, value):
    text = str(value) if value is not None and value != "" else display(item)
    owner.window.set_notification(key, text, str(item.get("props", {}).get("tone", "info")))


HANDLER = ComponentHandler("NOTIFICATION", draw_fill="surface_raised", build=build, sync=sync)
