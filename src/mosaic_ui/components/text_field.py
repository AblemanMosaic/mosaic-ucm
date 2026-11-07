from .base import ComponentHandler, apply_text_commit


def _text(value, props):
    text = str(value or "")
    return text.replace("\r\n", "\n").replace("\n", "\r\n") if props.get("multiline") else text


def build(owner, item, key, rect, value):
    node_id, props = str(item["node_id"]), item.get("props", {})
    owner.window.edit(key, _text(value, props), rect, multiline=bool(props.get("multiline")),
                      readonly=bool(props.get("readonly")),
                      command=lambda selected: owner._apply({"intent": "TEXT_COMMIT", "node_id": node_id, "value": selected}))


def sync(owner, item, key, value):
    owner.window.set_text(key, _text(value, item.get("props", {})))


HANDLER = ComponentHandler("TEXT_FIELD", draw_fill="field", default_action="Edit", interaction_intent="TEXT_COMMIT",
                           build=build, sync=sync, interact=apply_text_commit)
