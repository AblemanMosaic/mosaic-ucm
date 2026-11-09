from .base import ComponentHandler, apply_select, option_label, option_labels, option_value


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    owner.window.segmented(key, option_labels(owner, item, "options", "segments"), rect,
                           selected=option_label(owner, item, value, "options", "segments"),
                           command=lambda selected: owner._apply({"intent": "SELECT", "node_id": node_id,
                                                                   "value": option_value(owner, item, selected, "options", "segments")}))


def sync(owner, item, key, value):
    owner.window.set_segmented(key, option_labels(owner, item, "options", "segments"),
                               option_label(owner, item, value, "options", "segments"))


HANDLER = ComponentHandler("SEGMENTED", default_action="Select", interaction_intent="SELECT",
                           build=build, sync=sync, interact=apply_select)
