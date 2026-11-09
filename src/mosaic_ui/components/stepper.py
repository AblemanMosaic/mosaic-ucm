from .base import ComponentHandler, apply_step, option_labels, options


def build(owner, item, key, rect, value):
    node_id, props = str(item["node_id"]), item.get("props", {})
    steps, labels = options(owner, item, "steps"), option_labels(owner, item, "steps")
    index = steps.index(value) if value in steps else int(value or 0)
    owner.window.stepper(key, labels, rect, selected=index,
                         command=lambda selected: owner._apply({"intent": "STEP", "node_id": node_id, "index": labels.index(selected)}))
    owner.window.set_steps(key, labels, index, str(props.get("tone", "accent")))


HANDLER = ComponentHandler("STEPPER", default_action="Select step", interaction_intent="STEP",
                           build=build, interact=apply_step)
