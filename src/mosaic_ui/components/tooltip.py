from .base import ComponentHandler, display


def build(owner, item, key, rect, _value):
    owner.window.tooltip(key, display(item), rect)


HANDLER = ComponentHandler("TOOLTIP", build=build)
