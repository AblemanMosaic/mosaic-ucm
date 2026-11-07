from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    owner.window.label(key, display(item), rect, style=str(item.get("props", {}).get("style", "body")))


def sync(owner, item, key, value):
    owner.window.set_text(key, str(value) if value is not None and value != "" else display(item))


HANDLER = ComponentHandler("LABEL", build=build, sync=sync)
