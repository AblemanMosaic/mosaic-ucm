from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from uclop.canonical import root


ROOT = Path(__file__).resolve().parents[1]


def contract(*, effect: bool = False, identities: bool = False):
    value = json.loads((ROOT / "examples" / "amcas" /
                        "portable-agent.integration.json").read_text(encoding="utf-8"))
    value = deepcopy(value)
    if effect:
        value["capabilities"][0]["effect_class"] = "LOCAL_ARTIFACT_PREPARATION"
        value["effects"] = [{"id": "WRITE_OUTPUT", "capability_id": "ORIENT",
                             "effect_class": "LOCAL_ARTIFACT_PREPARATION",
                             "operation": "WRITE_OUTPUT", "ceiling": "NONE"}]
    if identities:
        value["identities"].update({"user_required": True, "agent_required": True,
                                    "possession_required": True})
    body = {key: item for key, item in value.items() if key != "contract_root"}
    value["contract_root"] = root(body)
    return value


def operation():
    return {"operation_id": "OP-1", "kind": "INTEGRATION_WORK",
            "capability_id": "ORIENT", "effect_ids": ["WRITE_OUTPUT"],
            "intent": "Create one bounded integration output.",
            "inputs": [{"path": "input.json", "sha256": "3" * 64}],
            "expected_outputs": [{"path": "output.json", "sha256": "4" * 64}],
            "resource_budget": {"max_seconds": 30, "max_bytes": 4096, "max_invocations": 1},
            "rollback": {"required": True, "plan_root": "5" * 64}}
