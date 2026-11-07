from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    owner.window.badge(key, rect)
    owner.window.set_badge(key, display(item), str(item.get("props", {}).get("tone", "info")))


def sync(owner, item, key, value):
    text = str(value) if value is not None and value != "" else display(item)
    owner.window.set_badge(key, text, str(item.get("props", {}).get("tone", "info")))


HANDLER = ComponentHandler("BADGE", build=build, sync=sync)
