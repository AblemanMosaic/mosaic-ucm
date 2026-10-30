"""Bounded execution of a host-accepted coding plan through the real facade.

The controller cannot define tasks, replace accepted payloads, seat a signer,
or discharge project, proof, or review obligations from worker task success.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .maturity_semantics import BOUNDARY, seal
from .maturity_workbench import MaturityWorkbench, capability_registry
from .project_intelligence import validate_project
from .workbench_manager import _head
from .workbench_workers import snapshot_source


ACCEPTANCE_SCHEMA = "ucl.ucm.maturity.coding_acceptance.v1"
MAX_TASKS = 32
_ACCEPTANCE_FIELDS = {"schema", "source_root", "project_root", "plan_root", "orientation_root", "registry_root",
    "worker_root", "trusted_test_policy_root", "task_ids", "task_contracts_root", "initial_head", "dispatcher_id",
    "execution_scope", "sandbox", "standing", "authority_effect", "real_a5", "g0", "root"}


def _dispatcher(value):
    require(type(value) is str and 0 < len(value) <= 128
            and value == value.strip() and not any(ord(c) < 32 for c in value), "CONTROLLER_DISPATCHER_INVALID")
    return value


def _tasks(workbench, task_ids):
    require(type(task_ids) is list and 0 < len(task_ids) <= MAX_TASKS
            and all(type(name) is str and name for name in task_ids)
            and len(task_ids) == len(set(task_ids)), "CONTROLLER_TASK_SCOPE_INVALID")
    manager = workbench.legacy.manager
    require(set(task_ids) == set(manager.tasks), "CONTROLLER_FULL_PLAN_REQUIRED")
    tasks = {task["id"]: task for task in manager.plan["tasks"]}
    require(set(tasks) == set(task_ids), "CONTROLLER_TASK_SCOPE_INVALID")
    seen, rows = set(), []
    for identifier in task_ids:
        task = tasks[identifier]
        require(task["operation"] in {"INSPECT_ARTIFACTS", "PREPARE_CANDIDATE", "RUN_TESTS"}
                and set(task["depends_on"]) <= seen, "CONTROLLER_TASK_ORDER_INVALID")
        require(canonical_bytes(task) == canonical_bytes(manager.tasks[identifier]), "CONTROLLER_TASK_CONTRACT_CHANGED")
        rows.append(deepcopy(task))
        seen.add(identifier)
    return rows


def make_acceptance(workbench: MaturityWorkbench, *, expected_source_root: str,
                    expected_project_root: str, expected_plan_root: str,
                    expected_head: dict, task_ids: list[str], dispatcher_id: str) -> dict:
    """Prepare a proposal for the host to retain and accept by its exact root.

    Calling this helper supplies no authorization. A controller always requires
    the host-held root separately, including again on every action and report.
    """
    require(type(workbench) is MaturityWorkbench, "CONTROLLER_REAL_MATURITY_WORKBENCH_REQUIRED")
    _dispatcher(dispatcher_id)
    legacy, manager = workbench.legacy, workbench.legacy.manager
    source, project, plan = map(require_root, (expected_source_root, expected_project_root, expected_plan_root))
    require(source == legacy.orientation["source_root"] == legacy.worker.manifest["source_root"]
            and project == manager.project["snapshot_root"] and plan == manager.plan["plan_root"], "CONTROLLER_HOST_PINS_MISMATCH")
    head = _head(expected_head)
    require(head == manager.current_head, "CONTROLLER_HEAD_STALE")
    rows = _tasks(workbench, task_ids)
    return seal({"schema": ACCEPTANCE_SCHEMA, "source_root": source, "project_root": project, "plan_root": plan,
        "orientation_root": legacy.orientation["root"], "registry_root": workbench.registry_root,
        "worker_root": legacy.worker.worker_root, "trusted_test_policy_root": root(legacy.worker.policy["trusted_tests"]),
        "task_ids": deepcopy(task_ids), "task_contracts_root": root(rows), "initial_head": head,
        "dispatcher_id": dispatcher_id, "execution_scope": "TRUSTED_PINNED_CODE_ONLY", "sandbox": "UNBOUND_EXTERNAL", **BOUNDARY})


class BoundedCodingController:
    def __init__(self, workbench: MaturityWorkbench, acceptance: Any, *,
                 expected_acceptance_root: str, expected_head: dict, now: int):
        require(type(workbench) is MaturityWorkbench, "CONTROLLER_REAL_MATURITY_WORKBENCH_REQUIRED")
        self.workbench = workbench
        self.acceptance = deepcopy(exact_keys(acceptance, _ACCEPTANCE_FIELDS))
        self.acceptance_root = require_root(expected_acceptance_root)
        self._check(expected_acceptance_root=expected_acceptance_root, expected_head=expected_head)
        self._call("WORKBENCH.STATUS", {}, expected_head=expected_head, now=now)

    def _check(self, *, expected_acceptance_root, expected_head):
        accepted = self.acceptance
        require(accepted["schema"] == ACCEPTANCE_SCHEMA and accepted["root"] == self.acceptance_root
                == require_root(expected_acceptance_root)
                == root({key: value for key, value in accepted.items() if key != "root"}), "CONTROLLER_ACCEPTANCE_PIN_MISMATCH")
        require(all(type(accepted.get(key)) is type(value) and accepted[key] == value for key, value in BOUNDARY.items())
                and accepted["execution_scope"] == "TRUSTED_PINNED_CODE_ONLY" and accepted["sandbox"] == "UNBOUND_EXTERNAL", "CONTROLLER_BOUNDARY_INVALID")
        _head(accepted["initial_head"])
        _dispatcher(accepted["dispatcher_id"])
        legacy, manager = self.workbench.legacy, self.workbench.legacy.manager
        require(_head(expected_head) == manager.current_head, "CONTROLLER_HEAD_STALE")
        require(accepted["source_root"] == legacy.orientation["source_root"] == legacy.worker.manifest["source_root"]
                and accepted["project_root"] == manager.project["snapshot_root"]
                and accepted["plan_root"] == manager.plan["plan_root"]
                == root({key: value for key, value in manager.plan.items() if key != "plan_root"})
                and accepted["orientation_root"] == legacy.orientation["root"]
                and accepted["registry_root"] == self.workbench.registry_root == capability_registry()["root"], "CONTROLLER_CONTEXT_CHANGED")
        validate_project(manager.project, expected_source_root=accepted["source_root"])
        require(root(_tasks(self.workbench, accepted["task_ids"])) == accepted["task_contracts_root"], "CONTROLLER_TASK_CONTRACT_CHANGED")
        worker = legacy.worker
        require(accepted["worker_root"] == manager.worker_root == worker.worker_root == root(worker.policy)
                and accepted["trusted_test_policy_root"] == root(worker.policy["trusted_tests"])
                and canonical_bytes(worker.trusted_tests) == canonical_bytes(worker.policy["trusted_tests"]), "CONTROLLER_WORKER_POLICY_CHANGED")
        require(canonical_bytes(snapshot_source(worker.source)) == canonical_bytes(worker.manifest), "CONTROLLER_SOURCE_CHANGED")

    def _call(self, surface, payload, *, expected_head, now, task_id=None):
        request_id = "coding-" + root({"acceptance": self.acceptance_root, "surface": surface, "task_id": task_id})[:40]
        return self.workbench.dispatch({"schema": "ucl.ucm.maturity.request.v1", "surface": surface,
            "payload": payload, "context_root": self.acceptance["orientation_root"], "request_id": request_id,
            "expected_head": deepcopy(expected_head), "registry_root": self.acceptance["registry_root"]}, now=now)

    def step(self, task_id: str, *, expected_acceptance_root: str, expected_head: dict, now: int) -> dict:
        """Execute exactly the next accepted task; no new payload is accepted."""
        self._check(expected_acceptance_root=expected_acceptance_root, expected_head=expected_head)
        status = self._call("WORKBENCH.STATUS", {}, expected_head=expected_head, now=now)["result"]["result"]
        pending = [name for name in self.acceptance["task_ids"] if status["tasks"][name]["state"] != "COMPLETE"]
        require(pending and task_id == pending[0] and status["tasks"][task_id]["state"] == "PENDING"
                and status["active"] is None, "CONTROLLER_NEXT_TASK_REQUIRED")
        context = self._call("WORKBENCH.CURRENT_TASK_CONTEXT", {"task_id": task_id}, expected_head=expected_head, now=now, task_id=task_id)["result"]["result"]
        require(root(context["task_contract"]) == root(self.workbench.legacy.manager.tasks[task_id])
                and context["current_head"] == expected_head, "CONTROLLER_TASK_CONTEXT_CHANGED")
        # Preserve the domain response after local custody effects, including a
        # FAILED or UNCERTAIN result and its new head. A later report rechecks
        # readiness; it must not replace this response with a clean refusal.
        return self._call("WORKBENCH.RUN_TASK", {"task_id": task_id, "dispatcher_id": self.acceptance["dispatcher_id"]},
            expected_head=expected_head, now=now, task_id=task_id)

    def report(self, *, expected_acceptance_root: str, expected_head: dict, now: int) -> dict:
        self._check(expected_acceptance_root=expected_acceptance_root, expected_head=expected_head)
        status = self._call("WORKBENCH.STATUS", {}, expected_head=expected_head, now=now)["result"]["result"]
        context = self._call("EXPORT_MATURITY_CONTEXT", {}, expected_head=expected_head, now=now)["result"]
        complete = status["status"] == "COMPLETE_INFORMATION_ONLY"
        project = self.workbench.legacy.manager.project
        return seal({"schema": "ucl.ucm.maturity.coding_controller_report.v1", "acceptance_root": self.acceptance_root,
            "source_root": self.acceptance["source_root"], "project_root": self.acceptance["project_root"],
            "plan_root": self.acceptance["plan_root"], "current_head": deepcopy(expected_head),
            "status": "TASK_PLAN_COMPLETE_WITH_RESIDUALS" if complete else "TASK_PLAN_INCOMPLETE",
            "completion_scope": "ACCEPTED_TASK_PLAN_ONLY", "task_plan_status": status["status"],
            "tasks": deepcopy(status["tasks"]), "project_obligations_satisfied": deepcopy(status["project_obligations_satisfied"]),
            "residuals": {"project": {"status": "NOT_DISCHARGED_BY_TASK_RECEIPTS", "record_ids": sorted(row["id"] for row in project["records"])},
                "proof": {"status": "NOT_EVALUATED_BY_CONTROLLER", "configured_plan_roots": deepcopy(self.workbench.proof_pins), "discharged_obligation_ids": []},
                "review": {"status": "PENDING_INDEPENDENT_REVIEW", "independent_review_attested": False}},
            "source_unchanged": True, "context": context,
            "execution_scope": "TRUSTED_PINNED_CODE_ONLY", "sandbox": "UNBOUND_EXTERNAL", **BOUNDARY})
