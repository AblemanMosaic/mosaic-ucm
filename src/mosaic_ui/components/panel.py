from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    owner.window.panel(key, display(item), rect)


HANDLER = ComponentHandler("PANEL", build=build)
