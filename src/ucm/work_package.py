"""One stable composition of architecture, project intelligence, and planning."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from uclop import autonomous_project_manager as apm
from uclop import project_intelligence as pi
from uclop.canonical import require, root

from .architecture import check_architecture_change
from .system import BOUNDARY


def prepare_work_package(*, project: Any, changed_ids: list[str],
                         changed_paths: list[str], objective: str,
                         workspace: str, architecture_contract: Any,
                         architecture_candidate: Any) -> dict[str, Any]:
    require(type(workspace) is str and workspace, "UCM_WORKSPACE_INVALID")
    pi.validate_project(project)
    require(project["baseline"]["source_root"] == architecture_contract.get("subject_root")
            and project["baseline"]["source_root"] == architecture_candidate.get("subject_root"),
            "UCM_WORK_PACKAGE_SUBJECT_MISMATCH")
    require(sorted(changed_paths) == sorted(architecture_candidate.get("changed_paths", [])),
            "UCM_WORK_PACKAGE_CHANGE_INVENTORY_MISMATCH")
    architecture = check_architecture_change(architecture_contract,
                                             architecture_candidate)
    impact = pi.impact_analysis(project, changed_ids, changed_paths)
    require(not impact["unknown_changed_ids"] and not impact["unknown_changed_paths"],
            "UCM_WORK_PACKAGE_UNKNOWN_CHANGE")
    order = pi.work_order(project, impact, Path(workspace))
    plan = apm.make_plan(project, changed_ids, changed_paths, objective=objective)
    status = ("READY_FOR_REVIEW" if architecture["status"] == "PASS_ARCHITECTURE_FIDELITY"
              else "HOLD_ARCHITECTURE_DRIFT")
    body = {"schema": "mosaic.ucm.governed-work-package.v0.1",
            "project_snapshot_root": project["snapshot_root"],
            "architecture_check_root": architecture["check_root"],
            "impact": deepcopy(impact), "work_order": deepcopy(order),
            "simulation_plan": deepcopy(plan), "status": status,
            "non_claims": ["NOT_EXECUTION", "NOT_TEST_EVIDENCE", "NOT_RELEASE_AUTHORITY"],
            **BOUNDARY}
    return {**body, "work_package_root": root(body)}
