from __future__ import annotations

import html
import json
from typing import Any

from .canonical import canonical_bytes, root
from .errors import require
from .evidence import verify_ledger


def derive_flow(
    workflow: dict[str, Any],
    ledger: list[dict[str, Any]],
    key_hex: str,
    *,
    expected_count: int,
    expected_anchor: str,
) -> dict[str, Any]:
    require(workflow.get("root") == root(workflow.get("body")), "FLOW_WORKFLOW_ROOT_MISMATCH")
    stages = workflow["body"]["stages"]
    require(len({item["id"] for item in stages}) == len(stages), "FLOW_STAGE_IDS_INVALID")
    verification = verify_ledger(ledger, workflow_root=workflow["root"], key_hex=key_hex, expected_count=expected_count, expected_anchor=expected_anchor)
    by_id = {entry["body"]["stage_id"]: entry for entry in ledger}
    nodes = []
    terminal_seen = False
    for stage in stages:
        entry = by_id.get(stage["id"])
        if entry is None:
            status = "PENDING"
            output_root = None
        elif entry["body"]["event"] == "STAGE_REFUSED":
            status = "REFUSED"
            output_root = entry["body"]["output_root"]
            terminal_seen = True
        else:
            require(not terminal_seen, "FLOW_COMPLETION_AFTER_REFUSAL")
            status = "COMPLETE"
            output_root = entry["body"]["output_root"]
        nodes.append({"id": stage["id"], "stage": stage["stage"], "horizon": stage["horizon"], "status": status, "output_root": output_root})
    body = {
        "schema": "ucl.selfhost.executable_flow.v1",
        "workflow_root": workflow["root"],
        "receipt_anchor": verification["anchor"],
        "nodes": nodes,
        "complete": all(item["status"] == "COMPLETE" for item in nodes),
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body)}


def build_flow_html(flow: dict[str, Any]) -> bytes:
    require(flow.get("root") == root(flow.get("body")), "FLOW_ROOT_MISMATCH")
    cards = []
    for node in flow["body"]["nodes"]:
        cards.append(
            '<article class="stage {status}"><div class="top"><span>{id}</span><b>{horizon}</b></div>'
            '<strong>{stage}</strong><em>{status_upper}</em><code>{output}</code></article>'.format(
                status=node["status"].lower(),
                id=html.escape(node["id"]),
                horizon=html.escape(node["horizon"]),
                stage=html.escape(node["stage"]),
                status_upper=html.escape(node["status"]),
                output=html.escape((node["output_root"] or "pending")[:16]),
            )
        )
    payload = canonical_bytes(flow).decode("utf-8")
    document = """<!doctype html><html><head><meta charset="utf-8"><title>UCL/UCM self-hosting flow</title>
<style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui;background:#090d18;color:#eff4ff}body{max-width:1280px;margin:0 auto;padding:36px}h1{font-size:clamp(28px,4vw,52px);margin:0}.lede{color:#9facbf;max-width:780px;line-height:1.55}.status{display:inline-block;margin:16px 0 24px;padding:8px 12px;border:1px solid #35556c;border-radius:999px;color:#8ee3bc;background:#10221e}.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.stage{min-height:125px;padding:16px;border-radius:14px;border:1px solid #263751;background:linear-gradient(145deg,#141c2c,#101624);box-shadow:0 12px 32px #0005}.stage.complete{border-color:#277d65}.stage.refused{border-color:#aa4b59}.stage.pending{border-color:#4d596d}.top{display:flex;justify-content:space-between;color:#8091aa;font-size:12px}.stage b{color:#d9b86c}.stage strong,.stage em,.stage code{display:block}.stage strong{margin:20px 0 10px}.stage em{font-size:12px;color:#79d7ae;font-style:normal}.stage code{margin-top:8px;color:#74849c}footer{margin-top:28px;color:#708097;font-size:13px}
</style></head><body><h1>Universal constitutional computation</h1><p class="lede">A receipt-derived view of the full self-hosting and H2–H5 information-only vertical. Every green stage is backed by a verified output root. The graph grants no standing or effect.</p><div class="status">EXPERIMENTAL · INFORMATION_ONLY · effect NONE</div><main class="flow">""" + "".join(cards) + """</main><footer>Derived from the signed fixture ledger. Real A5 held. G0 closed.</footer><script type="application/json" id="ucl-flow">""" + html.escape(payload) + """</script></body></html>"""
    return document.encode("utf-8")

