from .base import ComponentHandler, apply_select, option_label, option_labels, option_value


def build(owner, item, key, rect, value):
    node_id = str(item["node_id"])
    owner.window.tab_bar(key, option_labels(owner, item, "options", "tabs"), rect,
                         selected=option_label(owner, item, value, "options", "tabs"),
                         command=lambda selected: owner._apply({"intent": "SELECT", "node_id": node_id,
                                                                 "value": option_value(owner, item, selected, "options", "tabs")}))


def sync(owner, item, key, value):
    owner.window.set_tabs(key, option_labels(owner, item, "options", "tabs"),
                          option_label(owner, item, value, "options", "tabs"))


HANDLER = ComponentHandler("TAB_BAR", default_action="Select", interaction_intent="SELECT",
                           build=build, sync=sync, interact=apply_select)
