"""UCM Autonomous Project Manager c1: bounded *simulated* execution prototype.

Adds durable, replay-checked management to project_intelligence snapshots.
This module deliberately has NO network, subprocess, shell, repository write,
production worker, or constitutional authority adapter. Project work is not
performed: simulated task receipts are never evidence of a real repair/test.

Trust: standard-library SQLite under a trusted local filesystem. The hash chain
is an integrity *consistency* check, not an external signature or tamper-proof
log against someone able to rewrite the DB and all of its hashes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from typing import Any

from uclop import project_intelligence as pi

SCHEMA = "ucl.ucm.autonomous_project_manager.plan.v1"
JOURNAL_SCHEMA = "ucl.ucm.autonomous_project_manager.journal.v1"
STATUS_SCHEMA = "ucl.ucm.autonomous_project_manager.status.v1"
PLAN_DOMAIN = b"ucl.ucm.autonomous_project_manager.plan.v1\0"
EVENT_DOMAIN = b"ucl.ucm.autonomous_project_manager.event.v1\0"
RECEIPT_DOMAIN = b"ucl.ucm.autonomous_project_manager.simulated_receipt.v1\0"
ZERO_HASH = "0" * 64
STANDING = "INFORMATION_ONLY"
AUTHORITY_EFFECT = "NONE"
MODE = "SIMULATION_ONLY"
ACTIONS = {
    "REQUIREMENT": "SIMULATE_ANALYZE",
    "DESIGN_DECISION": "SIMULATE_ANALYZE",
    "IMPLEMENTATION_ARTIFACT": "SIMULATE_DRAFT",
    "VERIFICATION_OBLIGATION": "SIMULATE_CHECK",
    "AUTHORIZATION_DECISION": "SIMULATE_REVIEW_PACKET",
}
MAX_TASKS = 64
MAX_EVENTS = 4096
MAX_PLAN_BYTES = 2 * 1024 * 1024
MAX_BUDGET = 500
TASK_ID_RE = re.compile(r"^TASK-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class ManagerError(ValueError):
    """Refusal or incomplete recovery, with no constitutional authority effect."""


def fail(code: str, detail: str = "") -> None:
    raise ManagerError(code + (": " + detail if detail else ""))


def exact(obj: Any, names: set[str], where: str) -> None:
    if type(obj) is not dict or set(obj) != names:
        fail("APM_SCHEMA_INVALID", where)


def text(value: Any, where: str, limit: int = 500) -> None:
    if (type(value) is not str or not value or value.strip() != value or len(value) > limit
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        fail("APM_TEXT_INVALID", where)


def digest(value: Any, where: str) -> None:
    if type(value) is not str or not HEX_RE.fullmatch(value):
        fail("APM_DIGEST_INVALID", where)


def sorted_unique(value: Any, where: str) -> None:
    if type(value) is not list or any(type(item) is not str for item in value) or value != sorted(set(value)):
        fail("APM_ORDER_INVALID", where)


def canonical(obj: Any) -> bytes:
    return pi.canonical(obj)


def rooted(domain: bytes, body: Any) -> str:
    return hashlib.sha256(domain + canonical(body)).hexdigest()


def root_plan(plan_without_root: dict[str, Any]) -> str:
    return rooted(PLAN_DOMAIN, plan_without_root)


def _task_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {task["id"]: task for task in plan["tasks"]}


def make_plan(project: dict[str, Any], changed_ids: list[str], changed_paths: list[str] | None = None,
              *, objective: str = "Review and plan the affected project obligations") -> dict[str, Any]:
    pi.validate_project(project)
    text(objective, "objective", 500)
    impact = pi.impact_analysis(project, changed_ids, changed_paths)
    if impact["unknown_changed_ids"] or impact["unknown_changed_paths"] or not impact["selected_changed_ids"]:
        fail("APM_CHANGE_UNKNOWN_OR_EMPTY")
    impacted = {row["id"] for row in impact["impacted"]}
    if len(impacted) > MAX_TASKS:
        fail("APM_TOO_MANY_TASKS")
    nodes = {row["id"]: row for row in project["records"]}
    tasks = []
    for rid in sorted(impacted):
        rec = nodes[rid]
        tasks.append({
            "id": "TASK-" + rid,
            "title": "Simulated assessment: " + rec["title"],
            "source_record_ids": [rid],
            "depends_on": ["TASK-" + dep for dep in rec["depends_on"] if dep in impacted],
            "action": ACTIONS[rec["kind"]],
            "budget_units": 1,
            "max_attempts": 2,
            "review_required": True,
        })
    body = {
        "schema": SCHEMA,
        "project_id": project["project_id"],
        "project_snapshot_root": project["snapshot_root"],
        "baseline_source_root": project["baseline"]["source_root"],
        "selected_change_ids": impact["selected_changed_ids"],
        "objective": objective,
        "execution_mode": MODE,
        "standing": STANDING,
        "authority_effect": AUTHORITY_EFFECT,
        "budget_limit_units": max(1, min(MAX_BUDGET, len(tasks) * 2)),
        "tasks": tasks,
    }
    result = dict(body, plan_root=root_plan(body))
    validate_plan(result, project)
    return result


def validate_plan(plan: Any, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pi.validate_project(project)
    exact(plan, {"schema", "project_id", "project_snapshot_root", "baseline_source_root",
                 "selected_change_ids", "objective", "execution_mode", "standing",
                 "authority_effect", "budget_limit_units", "tasks", "plan_root"}, "plan")
    if (plan["schema"] != SCHEMA or plan["execution_mode"] != MODE
            or plan["standing"] != STANDING or plan["authority_effect"] != AUTHORITY_EFFECT):
        fail("APM_BOUNDARY_INVALID")
    if (plan["project_id"] != project["project_id"]
            or plan["project_snapshot_root"] != project["snapshot_root"]
            or plan["baseline_source_root"] != project["baseline"]["source_root"]):
        fail("APM_PROJECT_PIN_MISMATCH")
    text(plan["objective"], "objective", 500)
    if type(plan["budget_limit_units"]) is not int or not 1 <= plan["budget_limit_units"] <= MAX_BUDGET:
        fail("APM_BUDGET_INVALID")
    sorted_unique(plan["selected_change_ids"], "selected_change_ids")
    if not plan["selected_change_ids"]:
        fail("APM_NO_CHANGE")
    impact = pi.impact_analysis(project, plan["selected_change_ids"])
    if impact["unknown_changed_ids"]:
        fail("APM_UNKNOWN_CHANGE")
    impacted = {row["id"] for row in impact["impacted"]}
    nodes = {row["id"]: row for row in project["records"]}
    tasks = plan["tasks"]
    if type(tasks) is not list or not tasks or len(tasks) > MAX_TASKS:
        fail("APM_TASK_COUNT_INVALID")
    task_ids = [t.get("id") if type(t) is dict else None for t in tasks]
    if task_ids != sorted("TASK-" + rid for rid in impacted):
        fail("APM_TASK_COVERAGE_INVALID")
    for row in tasks:
        exact(row, {"id", "title", "source_record_ids", "depends_on", "action",
                    "budget_units", "max_attempts", "review_required"}, "task")
        if not TASK_ID_RE.fullmatch(row["id"]):
            fail("APM_TASK_ID_INVALID")
        text(row["title"], row["id"] + "/title", 500)
        rid = row["id"][5:]
        if row["source_record_ids"] != [rid]:
            fail("APM_TASK_SOURCE_INVALID", row["id"])
        expected_deps = sorted("TASK-" + dep for dep in nodes[rid]["depends_on"] if dep in impacted)
        if row["depends_on"] != expected_deps:
            fail("APM_TASK_DEPENDENCIES_INVALID", row["id"])
        if row["action"] != ACTIONS[nodes[rid]["kind"]]:
            fail("APM_ACTION_REFUSED", row["id"])
        if type(row["budget_units"]) is not int or not 1 <= row["budget_units"] <= 10:
            fail("APM_TASK_BUDGET_INVALID", row["id"])
        if type(row["max_attempts"]) is not int or not 1 <= row["max_attempts"] <= 3:
            fail("APM_RETRIES_INVALID", row["id"])
        if row["review_required"] is not True:
            fail("APM_REVIEW_REQUIRED", row["id"])
    digest(plan["plan_root"], "plan_root")
    body = {key: val for key, val in plan.items() if key != "plan_root"}
    if root_plan(body) != plan["plan_root"]:
        fail("APM_PLAN_ROOT_MISMATCH")
    return _task_map(plan)


def authorization_decision(operation: str, *, execution_mode: str = MODE) -> dict[str, Any]:
    """This is an advisory guard for this simulation, NOT a real authorization broker."""
    allowed = execution_mode == MODE and operation in set(ACTIONS.values())
    return {"operation": operation, "simulation_permitted": allowed,
            "real_operation_authorized": False, "standing": STANDING,
            "authority_effect": AUTHORITY_EFFECT,
            "decision": "SIMULATION_ONLY" if allowed else "DENIED"}


def simulated_receipt(plan: dict[str, Any], project: dict[str, Any], task: dict[str, Any],
                      dependency_results: list[dict[str, str]]) -> dict[str, Any]:
    """Pure deterministic sample output. A receipt never attests real execution."""
    record = next(row for row in project["records"] if row["id"] == task["source_record_ids"][0])
    kind = record["kind"]
    claim = {
        "REQUIREMENT": {"requirement_satisfied": False, "next_step": "INDEPENDENT_REVIEW"},
        "DESIGN_DECISION": {"design_accepted": False, "next_step": "INDEPENDENT_REVIEW"},
        "IMPLEMENTATION_ARTIFACT": {"candidate_patch_written": False, "next_step": "HUMAN_OR_GOVERNED_WORKER"},
        "VERIFICATION_OBLIGATION": {"real_tests_executed": False, "obligation_verified": False},
        "AUTHORIZATION_DECISION": {"authorization_granted": False, "standing_changed": False},
    }[kind]
    body = {
        "schema": "ucl.ucm.autonomous_project_manager.simulated_receipt.v1",
        "plan_root": plan["plan_root"], "project_snapshot_root": project["snapshot_root"],
        "task_id": task["id"], "source_record_id": record["id"], "source_record_kind": kind,
        "operation": task["action"], "dependency_results": dependency_results,
        "simulated_claim": claim, "actual_work_performed": False,
        "project_obligations_satisfied": [], "release_authorized": False,
        "standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
    }
    return dict(body, receipt_root=rooted(RECEIPT_DOMAIN, body))


def _event_hash(seq: int, kind: str, task_id: str | None, payload: dict[str, Any], prev: str) -> str:
    return rooted(EVENT_DOMAIN, {"seq": seq, "kind": kind, "task_id": task_id,
                                 "payload": payload, "prev_hash": prev})


def _new_states(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {t["id"]: {"state": "PENDING", "attempts": 0, "result_root": None} for t in plan["tasks"]}


def _fold(plan: dict[str, Any], project: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = _task_map(plan)
    states = _new_states(plan)
    spent = 0
    if not events:
        fail("APM_GENESIS_MISSING")
    for n, event in enumerate(events):
        kind, tid, payload = event["kind"], event["task_id"], event["payload"]
        if n == 0:
            if kind != "GENESIS" or tid is not None or payload != {
                "plan_root": plan["plan_root"], "project_snapshot_root": project["snapshot_root"],
                "baseline_source_root": project["baseline"]["source_root"], "execution_mode": MODE,
            }:
                fail("APM_GENESIS_INVALID")
            continue
        if tid not in tasks:
            fail("APM_EVENT_TASK_INVALID")
        entry = states[tid]
        task = tasks[tid]
        if kind == "ATTEMPT_STARTED":
            exact(payload, {"attempt", "budget_units"}, "started")
            if (entry["state"] != "PENDING" or type(payload["attempt"]) is not int
                    or payload["attempt"] != entry["attempts"] + 1
                    or payload["attempt"] > task["max_attempts"]
                    or type(payload["budget_units"]) is not int
                    or payload["budget_units"] != task["budget_units"]):
                fail("APM_INVALID_START", tid)
            if any(s["state"] == "RUNNING" for s in states.values()):
                fail("APM_PARALLEL_START_INVALID")
            if any(states[d]["state"] != "SIMULATED_DONE" for d in task["depends_on"]):
                fail("APM_UNMET_DEPENDENCIES", tid)
            spent += task["budget_units"]
            if spent > plan["budget_limit_units"]:
                fail("APM_BUDGET_EXCEEDED")
            entry["attempts"] += 1
            entry["state"] = "RUNNING"
        elif kind == "ATTEMPT_COMPLETED":
            exact(payload, {"receipt"}, "completed")
            if entry["state"] != "RUNNING":
                fail("APM_COMPLETION_WITHOUT_START", tid)
            roots = [{"task_id": d, "result_root": states[d]["result_root"]} for d in task["depends_on"]]
            if payload["receipt"] != simulated_receipt(plan, project, task, roots):
                fail("APM_RECEIPT_SEMANTICS_INVALID", tid)
            entry["state"] = "SIMULATED_DONE"
            entry["result_root"] = payload["receipt"]["receipt_root"]
        elif kind == "ATTEMPT_RECONCILED":
            if (entry["state"] != "RUNNING"
                    or payload != {"outcome": "NO_EXTERNAL_EFFECTS_SIMULATION_ONLY"}):
                fail("APM_RECONCILIATION_INVALID", tid)
            entry["state"] = "PENDING" if entry["attempts"] < task["max_attempts"] else "BLOCKED_RETRY_LIMIT"
        else:
            fail("APM_EVENT_KIND_INVALID", kind)
    return {"tasks": states, "spent_units": spent}


def _check_state_path(path: Path, *, must_exist: bool) -> Path:
    """Refuse links and directories at the DB path (trusted parent required)."""
    path = Path(path).absolute()
    if path.name in ("", ".", ".."):
        fail("APM_STATE_PATH_INVALID")
    try:
        base = path.parent.resolve(strict=True)
        if not base.is_dir():
            fail("APM_STATE_PARENT_INVALID")
        # Detect a symlink somewhere below the filesystem root, not just DB leaf.
        current = Path(path.anchor)
        for piece in path.parts[1:-1]:
            current = current / piece
            if stat.S_ISLNK(current.lstat().st_mode):
                fail("APM_STATE_PARENT_LINK_REFUSED")
        if must_exist:
            st = path.lstat()
            if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
                fail("APM_STATE_NOT_REGULAR")
        elif path.exists() or path.is_symlink():
            fail("APM_STATE_ALREADY_EXISTS")
    except ManagerError:
        raise
    except (OSError, ValueError) as exc:
        fail("APM_STATE_PATH_UNAVAILABLE", type(exc).__name__)
    return base / path.name


def _connect(path: Path, *, create: bool = False) -> sqlite3.Connection:
    p = _check_state_path(path, must_exist=not create)
    if create:
        try:
            fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        except OSError as exc:
            fail("APM_STATE_CREATE_REFUSED", type(exc).__name__)
    try:
        cx = sqlite3.connect(str(p), isolation_level=None, timeout=10)
        cx.execute("PRAGMA synchronous=FULL")
        cx.execute("PRAGMA journal_mode=DELETE")
        cx.execute("PRAGMA trusted_schema=OFF")
        return cx
    except sqlite3.Error as exc:
        fail("APM_DB_UNAVAILABLE", type(exc).__name__)


def _append(cx: sqlite3.Connection, kind: str, task_id: str | None, payload: dict[str, Any]) -> str:
    tail = cx.execute("SELECT seq, event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
    seq = 1 if tail is None else tail[0] + 1
    previous = ZERO_HASH if tail is None else tail[1]
    root = _event_hash(seq, kind, task_id, payload, previous)
    cx.execute("INSERT INTO events(seq,kind,task_id,payload,prev_hash,event_hash) VALUES(?,?,?,?,?,?)",
               (seq, kind, task_id, canonical(payload).decode("utf-8"), previous, root))
    return root


def init_state(path: Path, plan: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    validate_plan(plan, project)
    cx = _connect(path, create=True)
    try:
        cx.execute("BEGIN IMMEDIATE")
        cx.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        cx.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, task_id TEXT, "
                   "payload TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL)")
        for key, val in (("journal_schema", JOURNAL_SCHEMA),
                         ("plan", canonical(plan).decode("utf-8")),
                         ("project", canonical(project).decode("utf-8"))):
            cx.execute("INSERT INTO meta(key,value) VALUES(?,?)", (key, val))
        _append(cx, "GENESIS", None, {
            "plan_root": plan["plan_root"], "project_snapshot_root": project["snapshot_root"],
            "baseline_source_root": project["baseline"]["source_root"], "execution_mode": MODE,
        })
        cx.execute("COMMIT")
    except (sqlite3.Error, ManagerError):
        if cx.in_transaction:
            cx.execute("ROLLBACK")
        cx.close()
        # A failed creation is an exceptional local filesystem operation; do
        # not promise atomic absence of the new DB if process exits mid-init.
        raise
    finally:
        try:
            cx.close()
        except sqlite3.Error:
            pass
    return audit_state(path)


def _load(cx: sqlite3.Connection, *, expect_head: str | None = None) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    try:
        rows = cx.execute("SELECT key,value FROM meta ORDER BY key").fetchall()
        if [r[0] for r in rows] != ["journal_schema", "plan", "project"]:
            fail("APM_META_INVALID")
        meta = dict(rows)
        if any(type(v) is not str for v in meta.values()):
            fail("APM_META_INVALID")
        if meta["journal_schema"] != JOURNAL_SCHEMA:
            fail("APM_JOURNAL_SCHEMA_INVALID")
        if len(meta["plan"].encode("utf-8")) > MAX_PLAN_BYTES:
            fail("APM_PLAN_TOO_LARGE")
        plan = pi.strict_load(meta["plan"].encode("utf-8"))
        project = pi.strict_load(meta["project"].encode("utf-8"))
        validate_plan(plan, project)
        raw_rows = cx.execute("SELECT seq,kind,task_id,payload,prev_hash,event_hash FROM events ORDER BY seq LIMIT ?", (MAX_EVENTS + 1,)).fetchall()
        if len(raw_rows) > MAX_EVENTS:
            fail("APM_EVENT_LIMIT_EXCEEDED")
        events = []
        prev = ZERO_HASH
        for expected_seq, (seq, kind, tid, payload_json, prev_hash, event_hash) in enumerate(raw_rows, 1):
            if (type(seq) is not int or seq != expected_seq or type(kind) is not str
                    or (tid is not None and type(tid) is not str)
                    or type(payload_json) is not str or len(payload_json) > 65536
                    or type(prev_hash) is not str or type(event_hash) is not str):
                fail("APM_EVENT_SEQUENCE_INVALID")
            payload = pi.strict_load(payload_json.encode("utf-8"))
            if type(payload) is not dict or prev_hash != prev or event_hash != _event_hash(seq, kind, tid, payload, prev):
                fail("APM_EVENT_CHAIN_INVALID", str(seq))
            events.append({"seq": seq, "kind": kind, "task_id": tid, "payload": payload, "event_hash": event_hash})
            prev = event_hash
        if expect_head is not None and prev != expect_head:
            fail("APM_EXPECTED_HEAD_MISMATCH")
        state = _fold(plan, project, events)
        return plan, project, events, state
    except sqlite3.Error as exc:
        fail("APM_DB_INVALID", type(exc).__name__)


def _report(plan: dict[str, Any], events: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    states = state["tasks"]
    ready = sorted(t["id"] for t in plan["tasks"] if states[t["id"]]["state"] == "PENDING" and
                   all(states[d]["state"] == "SIMULATED_DONE" for d in t["depends_on"]))
    running = sorted(k for k, v in states.items() if v["state"] == "RUNNING")
    blocked = sorted(k for k, v in states.items() if v["state"] == "BLOCKED_RETRY_LIMIT")
    all_done = all(v["state"] == "SIMULATED_DONE" for v in states.values())
    status = ("RECOVERY_REQUIRED" if running else "SIMULATION_COMPLETE_REVIEW_REQUIRED" if all_done
              else "BLOCKED" if not ready else "SIMULATION_IN_PROGRESS")
    return {"schema": STATUS_SCHEMA, "project_id": plan["project_id"], "plan_root": plan["plan_root"],
            "project_snapshot_root": plan["project_snapshot_root"],
            "journal_head": events[-1]["event_hash"], "event_count": len(events),
            "state": status, "tasks": {k: states[k] for k in sorted(states)},
            "ready_tasks": ready, "running_tasks": running, "blocked_tasks": blocked,
            "spent_units": state["spent_units"], "budget_limit_units": plan["budget_limit_units"],
            "simulated_tasks_completed": sum(v["state"] == "SIMULATED_DONE" for v in states.values()),
            "total_tasks": len(states), "real_actions_executed": 0,
            "real_project_obligations_verified": 0, "release_authorized": False,
            "constitutional_standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
            "review_disposition": "REVIEW_REQUIRED", "execution_mode": MODE}


def audit_state(path: Path, *, expect_head: str | None = None) -> dict[str, Any]:
    if expect_head is not None:
        digest(expect_head, "expect_head")
    cx = _connect(path)
    try:
        plan, project, events, state = _load(cx, expect_head=expect_head)
        return _report(plan, events, state)
    finally:
        cx.close()


def step(path: Path, *, interrupt_after_start: bool = False) -> dict[str, Any]:
    """At most one simulated step, journaled before and after its pure worker.

    interrupt_after_start is a test-only failure injection; it leaves a durable
    RUNNING entry and requires explicit reconciliation before future dispatch.
    """
    cx = _connect(path)
    try:
        cx.execute("BEGIN IMMEDIATE")
        plan, project, events, folded = _load(cx)
        report = _report(plan, events, folded)
        if report["running_tasks"]:
            fail("APM_RECOVERY_REQUIRED")
        if not report["ready_tasks"]:
            cx.execute("COMMIT")
            return report
        tid = report["ready_tasks"][0]
        task = _task_map(plan)[tid]
        if folded["spent_units"] + task["budget_units"] > plan["budget_limit_units"]:
            fail("APM_BUDGET_EXHAUSTED")
        if len(events) + 2 > MAX_EVENTS:
            fail("APM_EVENT_LIMIT_EXCEEDED")
        decision = authorization_decision(task["action"])
        if not decision["simulation_permitted"] or decision["real_operation_authorized"]:
            fail("APM_POLICY_DENIED")
        _append(cx, "ATTEMPT_STARTED", tid, {"attempt": folded["tasks"][tid]["attempts"] + 1,
                                                   "budget_units": task["budget_units"]})
        cx.execute("COMMIT")
        if interrupt_after_start:
            return audit_state(path)
        # NO host execution. This receipt is derived entirely from static bytes.
        roots = [{"task_id": d, "result_root": folded["tasks"][d]["result_root"]} for d in task["depends_on"]]
        receipt = simulated_receipt(plan, project, task, roots)
        cx.execute("BEGIN IMMEDIATE")
        _, _, verify_events, verify_state = _load(cx)
        if verify_state["tasks"][tid]["state"] != "RUNNING":
            fail("APM_EXECUTION_STATE_CHANGED")
        _append(cx, "ATTEMPT_COMPLETED", tid, {"receipt": receipt})
        cx.execute("COMMIT")
        return audit_state(path)
    except (ManagerError, sqlite3.Error) as exc:
        if cx.in_transaction:
            cx.execute("ROLLBACK")
        if isinstance(exc, sqlite3.Error):
            fail("APM_DB_WRITE_FAILED", type(exc).__name__)
        raise
    finally:
        cx.close()


def reconcile_simulation(path: Path) -> dict[str, Any]:
    """Explicitly ack a test-only interrupted simulated worker: no real effect."""
    cx = _connect(path)
    try:
        cx.execute("BEGIN IMMEDIATE")
        _, _, events, state = _load(cx)
        running = sorted(tid for tid, row in state["tasks"].items() if row["state"] == "RUNNING")
        if len(running) != 1:
            fail("APM_NO_SINGLE_RUNNING_TASK")
        if len(events) + 1 > MAX_EVENTS:
            fail("APM_EVENT_LIMIT_EXCEEDED")
        _append(cx, "ATTEMPT_RECONCILED", running[0], {"outcome": "NO_EXTERNAL_EFFECTS_SIMULATION_ONLY"})
        cx.execute("COMMIT")
        return audit_state(path)
    except (ManagerError, sqlite3.Error) as exc:
        if cx.in_transaction:
            cx.execute("ROLLBACK")
        if isinstance(exc, sqlite3.Error):
            fail("APM_DB_WRITE_FAILED", type(exc).__name__)
        raise
    finally:
        cx.close()


def run(path: Path, *, max_steps: int = 64) -> dict[str, Any]:
    if type(max_steps) is not int or not 1 <= max_steps <= 256:
        fail("APM_MAX_STEPS_INVALID")
    for _ in range(max_steps):
        before = audit_state(path)
        if before["state"] == "RECOVERY_REQUIRED":
            fail("APM_RECOVERY_REQUIRED")
        if not before["ready_tasks"]:
            return before
        after = step(path)
        if after["state"] == "SIMULATION_COMPLETE_REVIEW_REQUIRED":
            return after
    return audit_state(path)


def write_new(path: Path, contents: bytes) -> None:
    """Explicitly requested *new file* output; never overwrite an existing file."""
    if len(contents) > MAX_PLAN_BYTES:
        fail("APM_OUTPUT_TOO_LARGE")
    dest = Path(path).absolute()
    parent = dest.parent
    if not parent.is_dir() or parent.is_symlink():
        fail("APM_OUTPUT_PARENT_INVALID")
    try:
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        fail("APM_OUTPUT_EXISTS_OR_UNAVAILABLE", type(exc).__name__)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        fail("APM_OUTPUT_WRITE_FAILED", type(exc).__name__)


def load_plan(path: Path) -> dict[str, Any]:
    try:
        data = Path(path).read_bytes()
        if len(data) > MAX_PLAN_BYTES:
            fail("APM_PLAN_TOO_LARGE")
        return pi.strict_load(data)
    except OSError as exc:
        fail("APM_PLAN_UNAVAILABLE", type(exc).__name__)


def review_packet(path: Path, *, expect_head: str | None = None) -> dict[str, Any]:
    """Documentary handoff; simulation receipts cannot close real obligations."""
    if expect_head is not None:
        digest(expect_head, "expect_head")
    cx = _connect(path)
    try:
        plan, project, events, state = _load(cx, expect_head=expect_head)
        report = _report(plan, events, state)
    finally:
        cx.close()
    impact = pi.impact_analysis(project, plan["selected_change_ids"])
    nodes = {row["id"]: row for row in project["records"]}
    tasks = [
        {"id": task["id"], "source_record_id": task["source_record_ids"][0],
         "action": task["action"], "simulation_state": state["tasks"][task["id"]]["state"],
         "simulated_receipt_root": state["tasks"][task["id"]]["result_root"]}
        for task in plan["tasks"]
    ]
    impacted_ver = sorted(row["id"] for row in impact["impacted"]
                          if row["kind"] == "VERIFICATION_OBLIGATION")
    return {
        "schema": "ucl.ucm.autonomous_project_manager.review_packet.v1",
        "project_id": plan["project_id"], "objective": plan["objective"],
        "project_snapshot_root": plan["project_snapshot_root"],
        "frozen_source_baseline": plan["baseline_source_root"],
        "plan_root": plan["plan_root"], "journal_head": report["journal_head"],
        "simulation_state": report["state"], "task_receipts": tasks,
        "affected_required_verification_ids": impacted_ver,
        "real_verification_obligations_closed_by_this_run": [],
        "affected_authorization_record_ids": sorted(row["id"] for row in impact["impacted"]
                                                     if row["kind"] == "AUTHORIZATION_DECISION"),
        "release_authorized": False, "project_implementation_modified": False,
        "real_external_actions_executed": 0,
        "required_real_next_steps": [
            "INDEPENDENTLY_REVIEW_PROPOSED_WORK_ORDER",
            "IMPLEMENT_REPAIR_USING_SEPARATELY_GOVERNED_WORKER",
            "EXECUTE_TRUSTED_QUALIFICATION_AND_SEMANTIC_COURTS",
            "OBTAIN_INDEPENDENT_REVIEW_AND_AUTHORIZATION",
        ],
        "impact_completeness": "UNKNOWN_OUTSIDE_DECLARED_GRAPH",
        "recommendation": "REVIEW_REQUIRED_NOT_A_RELEASE_OR_VERIFICATION",
        "standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
    }
