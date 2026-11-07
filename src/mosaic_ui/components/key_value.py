from .base import ComponentHandler, display


def _rows(value, props):
    if value is not None:
        return [["Value", value, False]]
    return props.get("rows", [])


def build(owner, item, key, rect, value):
    props = item.get("props", {})
    owner.window.key_value(key, str(props.get("title", display(item))), rect, columns=int(props.get("columns", 1)))
    owner.window.set_key_value(key, _rows(value, props))


def sync(owner, item, key, value):
    if value is not None:
        owner.window.set_key_value(key, _rows(value, item.get("props", {})))


HANDLER = ComponentHandler("KEY_VALUE", build=build, sync=sync)
