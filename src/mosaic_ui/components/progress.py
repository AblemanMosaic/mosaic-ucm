from .base import ComponentHandler


def build(owner, _item, key, rect, value):
    owner.window.progress(key, rect)
    owner.window.set_progress(key, float(value or 0))


def sync(owner, _item, key, value):
    owner.window.set_progress(key, float(value or 0))


HANDLER = ComponentHandler("PROGRESS", draw_fill="field", build=build, sync=sync)
