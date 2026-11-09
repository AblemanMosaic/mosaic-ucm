from .base import ComponentHandler, apply_select


def _rows(item, value=None):
    rows = value.get("rows", []) if isinstance(value, dict) else item.get("props", {}).get("rows", [])
    return [tuple(str(cell) for cell in row) for row in rows]


def _selected(value):
    return value.get("selected", "") if isinstance(value, dict) else value


def build(owner, item, key, rect, value):
    node_id, props = str(item["node_id"]), item.get("props", {})
    columns = props.get("columns", [])
    if not isinstance(columns, list) or not columns or not all(isinstance(column, str) for column in columns):
        owner._component_refusal("NATIVE_DATA_GRID_COLUMNS_REFUSED", node_id)
    owner.window.table(
        key, columns, rect, kind="data_grid",
        command=lambda selected: owner._apply({"intent": "SELECT", "node_id": node_id, "value": selected}),
    )
    owner.window.set_rows(key, _rows(item, value))
    owner.window.set_table_selection(key, str(_selected(value) or ""))


def sync(owner, item, key, value):
    owner.window.set_rows(key, _rows(item, value))
    owner.window.set_table_selection(key, str(_selected(value) or ""))


def accessible(value, props):
    rows = value.get("rows", []) if isinstance(value, dict) else props.get("rows", [])
    return f"{_selected(value) or ''}; {len(rows)} rows"


HANDLER = ComponentHandler("DATA_GRID", draw_fill="surface", default_action="Select row",
                           interaction_intent="SELECT", build=build, sync=sync, interact=apply_select,
                           accessible_value=accessible)
