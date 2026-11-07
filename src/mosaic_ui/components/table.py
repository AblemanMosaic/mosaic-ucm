from .base import ComponentHandler


def _rows(value, props):
    source = value if isinstance(value, list) else props.get("rows", [])
    return [tuple(str(cell) for cell in row) for row in source]


def build(owner, item, key, rect, value):
    props = item.get("props", {})
    columns = props.get("columns", ["Name", "State", "Evidence"])
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        owner._component_refusal("NATIVE_TABLE_COLUMNS_REFUSED", str(item["node_id"]))
    owner.window.table(key, columns, rect)
    owner.window.set_rows(key, _rows(value, props))


def sync(owner, item, key, value):
    if isinstance(value, list):
        owner.window.set_rows(key, _rows(value, item.get("props", {})))


def accessible(value, props):
    return f"{len(_rows(value, props))} rows"


HANDLER = ComponentHandler("TABLE", build=build, sync=sync, accessible_value=accessible)
