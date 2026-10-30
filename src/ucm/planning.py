"""Evidence-derived campaign planning over the AMCAS IR and impact graph."""
from __future__ import annotations

from typing import Any

from uclop.canonical import require, root
from .content_graph import impact_plan


def prepare_plan(campaign, *, changed_paths: list[str], objective: str) -> dict[str, Any]:
    require(type(objective) is str and bool(objective.strip()), "CAMPAIGN_OBJECTIVE_INVALID")
    status = campaign.status()
    impact = impact_plan(changed_paths)
    tasks = []
    for obligation in status["obligations"]:
        if obligation["status"] != "PASS":
            tasks.append({"task_id": f"RESOLVE:{obligation['id']}",
                          "kind": "OBLIGATION", "subject": obligation["id"],
                          "requires": [], "acceptance": "EVIDENCE_BOUND_DISPOSITION"})
    for group in impact["selected_groups"]:
        tasks.append({"task_id": f"TEST:{group}", "kind": "COURT", "subject": group,
                      "requires": [task["task_id"] for task in tasks if task["kind"] == "OBLIGATION"],
                      "acceptance": "EXACT_TEST_IDENTITIES_AND_RESULTS"})
    if impact["lane"] == "QUALIFICATION":
        tasks.append({"task_id": "QUALIFY:FULL", "kind": "QUALIFICATION",
                      "subject": "CACHE_FREE_SOURCE_REBUILD",
                      "requires": [task["task_id"] for task in tasks],
                      "acceptance": "ONE_COMPLETE_CACHE_FREE_RUN"})
    body = {"schema": "mosaic.ucm.integration-plan.v0.1", "objective": objective.strip(),
            "contract_root": status["contract_root"], "journal_head": status["journal_head"]["head"],
            "impact": impact, "tasks": tasks, "execution_authorized": False,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}
