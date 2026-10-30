"""Anchored, bounded work coordination over the original PI/APM contracts.

This manager completes a *work plan*, not a constitutional obligation or review.
The original PI graph and simulated APM remain unchanged.  Their exact coverage
and dependency checker is reused; a proposal never supplies execution authority.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from . import autonomous_project_manager as apm
from . import project_intelligence as pi
from .canonical import Refusal, canonical_bytes, exact_keys, require, require_root, root
from .custody import CustodyProvider, public_key_root, verify_asymmetric
from .protected_state import ProtectedStateStore
from .maturity_semantics import BOUNDARY

PLAN_SCHEMA = "ucl.ucm.workbench.plan.v1"
STATE_SCHEMA = "ucl.ucm.workbench.manager_state.v1"
CAPSULE_DOMAIN = "UCL_UCM_WORKBENCH_PORTABLE_CAPSULE_V1"
RECONCILIATION_DOMAIN = "UCL_UCM_WORKBENCH_NO_EXECUTION_V1"
RECOVERY_DOMAIN = "UCL_UCM_WORKBENCH_RECOVERY_AUTHORIZATION_V1"
RECOVERY_ACTIONS = {"OPEN_RECOVERY", "STATUS", "COMPLETE_DISPATCH",
                    "MARK_UNCERTAIN", "RECONCILE_NOT_EXECUTED", "EXPORT_CAPSULE"}
MAX_RECOVERY_WINDOW = 3600
PIN_FIELDS = {"project_root", "source_root", "registry_root", "policy_root",
              "charter_root", "grant_root", "jurisdiction_root"}
OPERATIONS = {"INSPECT_ARTIFACTS", "RUN_TESTS", "PREPARE_CANDIDATE"}
CAPABILITIES = {"INSPECT_ARTIFACTS": "INSPECT_ARTIFACTS", "RUN_TESTS": "RUN_TESTS",
                "PREPARE_CANDIDATE": "PREPARE_CANDIDATE"}
MAX_EVENTS = 4096
STORAGE_RECOVERY_SCHEMA = "ucl.ucm.workbench.storage_recovery_authorization.v1"


class StorageRecoveryPending(Refusal):
    def __init__(self, receipt: dict[str, Any], cause: Exception) -> None:
        super().__init__("WORKBENCH_STORAGE_RECOVERY_PENDING", detail=type(cause).__name__)
        self.receipt = receipt


def _text(value: Any, code: str = "WORKBENCH_IDENTIFIER_INVALID") -> str:
    require(type(value) is str and bool(value) and value == value.strip()
            and len(value) <= 200 and not any(ord(c) < 32 for c in value), code)
    return value


def _head(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"sequence", "head"}, "$.external_head")
    require(type(item["sequence"]) is int and item["sequence"] >= 0,
            "WORKBENCH_EXTERNAL_HEAD_INVALID")
    if item["sequence"] == 0:
        require(item["head"] == "GENESIS", "WORKBENCH_EXTERNAL_HEAD_INVALID")
    else:
        require_root(item["head"])
    return dict(item)


def _pins(value: Any) -> dict[str, str]:
    item = exact_keys(value, PIN_FIELDS, "$.pins")
    return {name: require_root(item[name]) for name in sorted(PIN_FIELDS)}


def authorize_recovery(prepared: dict[str, Any], *, provider: CustodyProvider,
                       signing_handle: str, expected_governor: dict[str, Any]) -> dict[str, Any]:
    """Sign exact recovery material with the already pinned Governor identity."""
    require(type(prepared) is dict and prepared.get("schema") in {"ucl.ucm.workbench.recovery_authorization.v1", STORAGE_RECOVERY_SCHEMA},
            "WORKBENCH_RECOVERY_AUTHORIZATION_INVALID")
    require(provider.identity(signing_handle) == expected_governor
            and expected_governor.get("role") == "GOVERNOR",
            "WORKBENCH_RECOVERY_GOVERNOR_INVALID")
    return provider.sign(signing_handle, RECOVERY_DOMAIN, deepcopy(prepared))


def create_plan(project: dict[str, Any], *, pins: dict[str, str],
                task_actions: dict[str, dict[str, Any]],
                selected_change_ids: list[str] | None = None,
                budget_limit_units: int | None = None) -> dict[str, Any]:
    """Adapt the unchanged APM's exact PI dependency/coverage proposal.

    Action keys are source record IDs, not free-form task names.  Every affected
    record requires exactly one action. Unknown impacts cannot narrow any court.
    """
    nodes = pi.validate_project(project)
    checked = _pins(pins)
    require(checked["project_root"] == project["snapshot_root"]
            and checked["source_root"] == project["baseline"]["source_root"],
            "WORKBENCH_PROJECT_PIN_MISMATCH")
    changes = sorted(nodes) if selected_change_ids is None else selected_change_ids
    proposal = apm.make_plan(project, changes)
    impacted = {task["source_record_ids"][0] for task in proposal["tasks"]}
    require(type(task_actions) is dict and set(task_actions) == impacted,
            "WORKBENCH_TASK_COVERAGE_INVALID")
    tasks = []
    for reference in proposal["tasks"]:
        source = reference["source_record_ids"][0]
        action = exact_keys(task_actions[source], {"operation", "payload"}, "$.task_action")
        require(type(action["operation"]) is str and action["operation"] in OPERATIONS, "WORKBENCH_OPERATION_REFUSED")
        require(type(action["payload"]) is dict, "WORKBENCH_PAYLOAD_INVALID")
        from .workbench_contracts import reject_raw_secrets
        reject_raw_secrets(action["payload"])
        # Canonical serialization validates bounded deterministic value types.
        root(action["payload"])
        tasks.append({"id": reference["id"], "source_record_id": source,
                      "depends_on": reference["depends_on"],
                      "operation": action["operation"], "payload": deepcopy(action["payload"]),
                      "cost_units": reference["budget_units"]})
    by_id = {task["id"]: task for task in tasks}
    for task in tasks:
        payload = task["payload"]
        if task["operation"] == "RUN_TESTS" and type(payload) is dict and "candidate_task_id" in payload:
            require(set(payload) == {"modules", "candidate_task_id"}
                    and type(payload["candidate_task_id"]) is str
                    and payload["candidate_task_id"] in by_id
                    and payload["candidate_task_id"] in task["depends_on"]
                    and by_id[payload["candidate_task_id"]]["operation"] == "PREPARE_CANDIDATE",
                    "WORKBENCH_CANDIDATE_TEST_CONTRACT_INVALID")
    limit = len(tasks) if budget_limit_units is None else budget_limit_units
    require(type(limit) is int and 1 <= limit <= apm.MAX_BUDGET,
            "WORKBENCH_BUDGET_INVALID")
    body = {"schema": PLAN_SCHEMA, "project_id": project["project_id"],
            "pins": checked, "reference_proposal": proposal, "tasks": tasks,
            "budget_limit_units": limit, "required_lane": "QUALIFICATION",
            "impact_completeness": "PI_GRAPH_PARTIAL_NO_REUSE_OR_DOWNGRADE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}


def validate_plan(plan: Any, project: dict[str, Any], *, pins: dict[str, str]) -> dict[str, Any]:
    item = exact_keys(plan, {"schema", "project_id", "pins", "reference_proposal", "tasks",
                            "budget_limit_units", "required_lane", "impact_completeness",
                            "standing", "authority_effect", "plan_root"}, "$.plan")
    require(item["schema"] == PLAN_SCHEMA, "WORKBENCH_PLAN_SCHEMA_INVALID")
    require(item["pins"] == _pins(pins), "WORKBENCH_PLAN_PIN_MISMATCH")
    apm.validate_plan(item["reference_proposal"], project)
    require(type(item["tasks"]) is list, "WORKBENCH_TASK_SET_INVALID")
    actions: dict[str, Any] = {}
    for task in item["tasks"]:
        entry = exact_keys(task, {"id", "source_record_id", "depends_on", "operation", "payload", "cost_units"})
        require(entry["source_record_id"] not in actions, "WORKBENCH_TASK_DUPLICATE")
        actions[entry["source_record_id"]] = {"operation": entry["operation"], "payload": entry["payload"]}
    expected = create_plan(project, pins=pins, task_actions=actions,
                           selected_change_ids=item["reference_proposal"]["selected_change_ids"],
                           budget_limit_units=item["budget_limit_units"])
    require(item == expected, "WORKBENCH_PLAN_CONTRACT_MISMATCH")
    return {row["id"]: row for row in item["tasks"]}


@contextmanager
def _exclusive(directory: Path):
    """One local dispatcher mutation at a time; OS releases the lock on death.

    This is process synchronization on the selected workspace, not a host
    security boundary. External custody/anchor providers supply that boundary.
    """
    path = directory / ".workbench-dispatch.lock"
    require(not path.is_symlink(), "WORKBENCH_LOCK_ALIAS_REFUSED")
    stream = path.open("a+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            if stream.seek(0, os.SEEK_END) == 0:
                stream.write(b"0"); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError as exc:
                raise Refusal("WORKBENCH_DISPATCHER_BUSY") from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError as exc:
                raise Refusal("WORKBENCH_DISPATCHER_BUSY") from exc
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


class WorkbenchManager:
    """A signed event fold, serialized by an external-head CAS and local lock.

    `expected_head` is always caller-supplied custody. The manager never silently
    selects its own freshness pin. A valid historical signature is not freshness.
    """
    def __init__(self, store: ProtectedStateStore, *, project: dict[str, Any],
                 plan: dict[str, Any], orientation: dict[str, Any],
                 orientation_pins: dict[str, Any], worker_identity: dict[str, Any],
                 expected_head: dict[str, Any], now: int,
                 worker_root: str | None = None,
                 recovery_authorization: dict[str, Any] | None = None) -> None:
        self.store = store
        self._configure(project=project, plan=plan, orientation=orientation,
                        orientation_pins=orientation_pins, worker_identity=worker_identity,
                        worker_root=worker_root, now=now,
                        recovery_authorization=recovery_authorization,
                        recovery_expected_head=expected_head)
        with _exclusive(store.directory):
            self._expect(expected_head)
            if expected_head["sequence"] == 0:
                require(not store.path.exists() and not store.journal_path.exists(),
                        "WORKBENCH_GENESIS_REUSE_REFUSED")
                payload = {"schema": STATE_SCHEMA, "project_root": project["snapshot_root"],
                           "plan": deepcopy(plan), "pins": self.pins,
                           "worker_identity": self.worker_identity, "worker_root": self.worker_root,
                           "generation": 1, "predecessor": None, "events": []}
                self.current_head = self._commit(payload, expected_head)
            else:
                _, folded = self._load(expected_head)
                if recovery_authorization is not None:
                    require(folded["active"] is not None
                            and folded["active"]["ticket_root"] == self._recovery_body["ticket_root"],
                            "WORKBENCH_RECOVERY_TICKET_MISMATCH")
                self.current_head = dict(expected_head)

    def _configure(self, *, project: dict[str, Any], plan: dict[str, Any],
                   orientation: dict[str, Any], orientation_pins: dict[str, Any],
                   worker_identity: dict[str, Any], worker_root: str | None, now: int,
                   recovery_authorization: dict[str, Any] | None = None,
                   recovery_expected_head: dict[str, Any] | None = None) -> None:
        self.project, self.plan = deepcopy(project), deepcopy(plan)
        self.orientation, self.orientation_pins = deepcopy(orientation), deepcopy(orientation_pins)
        self.worker_identity, self.worker_root = deepcopy(worker_identity), require_root(worker_root)
        identity = exact_keys(self.worker_identity, {"schema", "role", "key_root", "public_key_hex", "generation"})
        require(identity["schema"] == "ucl.ucm.asymmetric_public_identity.v1"
                and identity["role"] in {"WITNESS", "NODE"}
                and type(identity["generation"]) is int and identity["generation"] > 0
                and identity["key_root"] == public_key_root(identity["public_key_hex"]),
                "WORKBENCH_WORKER_IDENTITY_INVALID")
        require(type(plan) is dict and "pins" in plan, "WORKBENCH_PLAN_SCHEMA_INVALID")
        self.pins = _pins(plan["pins"])
        self.tasks = validate_plan(plan, project, pins=self.pins)
        self.recovery_authorization = deepcopy(recovery_authorization)
        self._recovery_body = None
        if recovery_authorization is None:
            self._authorize(now)
        else:
            require(recovery_expected_head is not None, "WORKBENCH_RECOVERY_HEAD_REQUIRED")
            self._recovery_body = self._authorize_recovery(
                recovery_authorization, action="OPEN_RECOVERY",
                expected_head=recovery_expected_head, ticket=None, now=now)
        require(len(self.tasks) <= self.orientation["budgets"]["max_actions"]
                and self.plan["budget_limit_units"] <= self.orientation["budgets"]["max_actions"],
                "WORKBENCH_GRANT_BUDGET_EXCEEDED")

    @classmethod
    def preflight_configuration(cls, **kwargs: Any) -> dict[str, Any]:
        """Validate a proposed manager configuration without creating custody."""
        proposed = cls.__new__(cls)
        proposed._configure(**kwargs)
        body = {"schema": "ucl.ucm.workbench.manager_preflight.v1", "plan_root": proposed.plan["plan_root"],
                "orientation_root": proposed.orientation["root"], "worker_root": proposed.worker_root,
                "pins": proposed.pins, "status": "CONFIGURATION_VALIDATED", "authority_effect": "NONE"}
        return {**body, "root": root(body)}

    def _authorize(self, now: int, operation: str | None = None) -> None:
        from .workbench_orientation import verify_orientation
        verify_orientation(self.orientation, external_pins=self.orientation_pins,
                           now=now, expected_head=self.orientation["current_head"])
        for name in ("project_root", "source_root", "registry_root", "policy_root"):
            require(self.orientation[name] == self.pins[name], "WORKBENCH_ORIENTATION_PIN_MISMATCH")
        for name in ("charter_root", "grant_root"):
            require(self.orientation_pins[name] == self.pins[name], "WORKBENCH_ORIENTATION_PIN_MISMATCH")
        require(self.orientation["jurisdiction_root"] == self.pins["jurisdiction_root"],
                "WORKBENCH_JURISDICTION_MISMATCH")
        if operation is not None:
            require(CAPABILITIES[operation] in self.orientation["capabilities"],
                    "WORKBENCH_CAPABILITY_NOT_GRANTED")

    def prepare_recovery_authorization(self, ticket: dict[str, Any], *,
                                       expected_head: dict[str, Any], actions: list[str],
                                       issued_at: int, expires_at: int) -> dict[str, Any]:
        """Prepare a one-head, one-ticket settlement grant for an external signer.

        This intentionally performs no ordinary grant-freshness check: it is the
        recovery request used when that grant has expired.  It does verify the
        externally held state head and exact active ticket before producing any
        material for the Governor signer.
        """
        with _exclusive(self.store.directory):
            _, folded = self._load(expected_head)
            require(folded["active"] == ticket, "WORKBENCH_ACTIVE_TICKET_MISMATCH")
        return self._prepared_recovery_body(ticket=ticket, expected_head=expected_head,
                                            actions=actions, issued_at=issued_at,
                                            expires_at=expires_at)

    def _prepared_recovery_body(self, *, ticket: dict[str, Any], expected_head: dict[str, Any],
                                actions: list[str], issued_at: int, expires_at: int) -> dict[str, Any]:
        require(type(actions) is list and actions == sorted(set(actions))
                and "OPEN_RECOVERY" in actions and set(actions).issubset(RECOVERY_ACTIONS)
                and not {"COMPLETE_DISPATCH", "MARK_UNCERTAIN", "RECONCILE_NOT_EXECUTED"}.isdisjoint(actions),
                "WORKBENCH_RECOVERY_ACTIONS_INVALID")
        require(type(issued_at) is int and type(expires_at) is int
                and 0 <= issued_at < expires_at <= issued_at + MAX_RECOVERY_WINDOW,
                "WORKBENCH_RECOVERY_WINDOW_INVALID")
        return {"schema": "ucl.ucm.workbench.recovery_authorization.v1",
                "plan_root": self.plan["plan_root"], "project_root": self.pins["project_root"],
                "source_root": self.pins["source_root"], "grant_root": self.pins["grant_root"],
                "orientation_root": self.orientation["root"],
                "worker_root": self.worker_root, "state_key_root": self.store.identity["key_root"],
                "expected_head": _head(expected_head), "ticket_root": ticket["ticket_root"],
                "actions": actions, "issued_at": issued_at, "expires_at": expires_at,
                "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}

    @classmethod
    def prepare_recovery_authorization_offline(cls, store: ProtectedStateStore, *,
                                               project: dict[str, Any], plan: dict[str, Any],
                                               orientation: dict[str, Any], orientation_pins: dict[str, Any],
                                               worker_identity: dict[str, Any], worker_root: str,
                                               ticket: dict[str, Any], expected_head: dict[str, Any],
                                               actions: list[str], issued_at: int,
                                               expires_at: int) -> dict[str, Any]:
        """Prepare unsigned recovery material before a live manager exists.

        The expired orientation is verified at its signed possession time, then
        the exact externally pinned store head and active ticket are folded
        read-only. No state, journal or anchor byte is changed.
        """
        require(type(orientation) is dict and type(orientation.get("material")) is dict,
                "WORKBENCH_ORIENTATION_INVALID")
        possession = orientation["material"].get("possession")
        require(type(possession) is dict and type(possession.get("body")) is dict
                and type(possession["body"].get("issued_at")) is int,
                "WORKBENCH_ORIENTATION_INVALID")
        historical_now = possession["body"]["issued_at"]
        proposed = cls.__new__(cls)
        proposed.store = store
        proposed._configure(project=project, plan=plan, orientation=orientation,
                            orientation_pins=orientation_pins, worker_identity=worker_identity,
                            worker_root=worker_root, now=historical_now)
        with _exclusive(store.directory):
            _, folded = proposed._load(expected_head)
            require(folded["active"] == ticket, "WORKBENCH_ACTIVE_TICKET_MISMATCH")
        return proposed._prepared_recovery_body(ticket=ticket, expected_head=expected_head,
                                                actions=actions, issued_at=issued_at,
                                                expires_at=expires_at)

    def _authorize_recovery(self, authorization: Any, *, action: str,
                            expected_head: dict[str, Any], ticket: dict[str, Any] | None,
                            now: int) -> dict[str, Any]:
        require(action in RECOVERY_ACTIONS, "WORKBENCH_RECOVERY_ACTION_INVALID")
        body = verify_asymmetric(authorization, RECOVERY_DOMAIN,
                                 expected_key_root=self.orientation_pins["issuer_key_root"],
                                 public_key_hex=self.orientation_pins["issuer_public_key_hex"])
        exact_keys(body, {"schema", "plan_root", "project_root", "source_root", "grant_root", "orientation_root",
                          "worker_root", "state_key_root", "expected_head", "ticket_root", "actions",
                          "issued_at", "expires_at", "standing", "authority_effect"})
        require(body["schema"] == "ucl.ucm.workbench.recovery_authorization.v1"
                and body["plan_root"] == self.plan["plan_root"]
                and body["project_root"] == self.pins["project_root"]
                and body["source_root"] == self.pins["source_root"]
                and body["grant_root"] == self.pins["grant_root"]
                and body["orientation_root"] == self.orientation["root"]
                and self.orientation["root"] == root({key: value for key, value in self.orientation.items() if key != "root"})
                and body["worker_root"] == self.worker_root
                and body["state_key_root"] == self.store.identity["key_root"]
                and body["expected_head"] == _head(expected_head)
                and type(body["actions"]) is list and body["actions"] == sorted(set(body["actions"]))
                and set(body["actions"]).issubset(RECOVERY_ACTIONS) and action in body["actions"]
                and type(body["issued_at"]) is int and type(body["expires_at"]) is int
                and 0 <= body["issued_at"] <= now <= body["expires_at"]
                and body["expires_at"] <= body["issued_at"] + MAX_RECOVERY_WINDOW
                and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE",
                "WORKBENCH_RECOVERY_AUTHORIZATION_INVALID")
        if ticket is not None:
            require(type(ticket) is dict and ticket.get("ticket_root") == body["ticket_root"],
                    "WORKBENCH_RECOVERY_TICKET_MISMATCH")
        return body

    def validate_cancellation_context(self, request: Any, *, expected_head: dict[str, Any]) -> dict[str, Any]:
        """Read-only durable gate for cancellation, including after grant expiry.

        Cancelling the exact unsettled request cannot authorize its execution.
        Historical verification preserves its original authenticated scope;
        current head, complete store/journal and active ticket remain mandatory.
        """
        issued = self.orientation["material"]["possession"]["body"]["issued_at"]
        self._authorize(issued)
        with _exclusive(self.store.directory):
            _, folded = self._load(expected_head)
            ticket = folded["active"]
            require(type(ticket) is dict and canonical_bytes(ticket["request"]) == canonical_bytes(request)
                    and ticket["orientation_root"] == self.orientation["root"],
                    "WORKBENCH_CANCELLATION_CONTEXT_MISMATCH")
        return deepcopy(ticket)

    @classmethod
    def _historical_storage_context(cls, store: ProtectedStateStore, configuration: dict[str, Any]) -> "WorkbenchManager":
        exact_keys(configuration, {"project", "plan", "orientation", "orientation_pins", "worker_identity", "worker_root"})
        orientation = configuration["orientation"]
        require(type(orientation) is dict and type(orientation.get("material")) is dict,
                "WORKBENCH_ORIENTATION_INVALID")
        possession = orientation["material"].get("possession")
        require(type(possession) is dict and type(possession.get("body")) is dict
                and type(possession["body"].get("issued_at")) is int, "WORKBENCH_ORIENTATION_INVALID")
        proposed = cls.__new__(cls)
        proposed.store = store
        proposed._configure(**configuration, now=possession["body"]["issued_at"])
        return proposed

    def _storage_recovery_body(self, *, expected_head: dict[str, Any], expected_transaction_root: str,
                               issued_at: int, expires_at: int) -> dict[str, Any]:
        require(type(issued_at) is int and type(expires_at) is int
                and 0 <= issued_at < expires_at <= issued_at + MAX_RECOVERY_WINDOW,
                "WORKBENCH_RECOVERY_WINDOW_INVALID")
        pin = self._expect(expected_head)
        transaction = self.store.inspect_interrupted_commit()
        require(transaction["transaction_root"] == require_root(expected_transaction_root),
                "WORKBENCH_STORAGE_TRANSACTION_PIN_MISMATCH")
        self._record_context(transaction["state_record"])
        successor = transaction["successor_anchor"]
        return {"schema": STORAGE_RECOVERY_SCHEMA, "plan_root": self.plan["plan_root"],
            "project_root": self.pins["project_root"], "source_root": self.pins["source_root"],
            "grant_root": self.pins["grant_root"], "orientation_root": self.orientation["root"],
            "worker_root": self.worker_root, "state_key_root": self.store.identity["key_root"],
            "expected_head": pin, "transaction_root": transaction["transaction_root"],
            "successor_head": {"sequence": successor["sequence"], "head": successor["head"]},
            "actions": ["RECOVER_SIGNED_STORE_ONLY"], "issued_at": issued_at, "expires_at": expires_at,
            "task_execution_authorized": False, **BOUNDARY}

    @classmethod
    def prepare_storage_recovery_authorization_offline(cls, store: ProtectedStateStore, *,
            expected_head: dict[str, Any], expected_transaction_root: str,
            issued_at: int, expires_at: int, **configuration: Any) -> dict[str, Any]:
        """Prepare exact storage-only material for the existing Governor signer.

        This only inspects a pending signed transaction; it never repairs it or
        permits task dispatch. The signed ordinary context may have expired.
        """
        proposed = cls._historical_storage_context(store, configuration)
        with _exclusive(store.directory):
            return proposed._storage_recovery_body(expected_head=expected_head,
                expected_transaction_root=expected_transaction_root, issued_at=issued_at, expires_at=expires_at)

    @classmethod
    def recover_storage_only(cls, store: ProtectedStateStore, *, authorization: Any,
            expected_head: dict[str, Any], expected_transaction_root: str,
            now: int, **configuration: Any) -> dict[str, Any]:
        """Reconcile exactly one Governor-authorized signed commit, without a worker.

        The native recovery signature/domain is reused with a distinct exact
        storage-only schema. It cannot serve as a task-settlement authorization.
        """
        require(type(now) is int, "WORKBENCH_TIME_INVALID")
        proposed = cls._historical_storage_context(store, configuration)
        body = verify_asymmetric(authorization, RECOVERY_DOMAIN,
            expected_key_root=proposed.orientation_pins["issuer_key_root"],
            public_key_hex=proposed.orientation_pins["issuer_public_key_hex"])
        require(type(body) is dict and type(body.get("issued_at")) is int and type(body.get("expires_at")) is int
                and body["issued_at"] <= now <= body["expires_at"], "WORKBENCH_STORAGE_RECOVERY_AUTHORIZATION_INVALID")
        mutation_attempted = False
        preflight_refusal = None
        phase, verified_state = "PREFLIGHT", "NO_STORAGE_MUTATION_ATTEMPTED"
        try:
            with _exclusive(store.directory):
                try:
                    expected = proposed._storage_recovery_body(expected_head=expected_head,
                        expected_transaction_root=expected_transaction_root,
                        issued_at=body["issued_at"], expires_at=body["expires_at"])
                    require(canonical_bytes(body) == canonical_bytes(expected), "WORKBENCH_STORAGE_RECOVERY_AUTHORIZATION_INVALID")
                except Refusal as error:
                    # A lock-release failure must not mask an earlier exact
                    # authority/head/transaction refusal before any store write.
                    preflight_refusal = error
                    raise
                receipt = {"schema": "ucl.ucm.workbench.storage_recovery_result.v1",
                    "authorization_root": root(authorization), "transaction_root": expected_transaction_root,
                    "prior_head": expected["expected_head"], "successor_head": expected["successor_head"],
                    "worker_invocations": 0, "task_execution_authorized": False,
                    "effect_scope": "LOCAL_CUSTODY", **BOUNDARY}
                phase = "RECONCILE_SIGNED_STORE"
                mutation_attempted = True
                record = store.recover_interrupted_commit(expected_transaction_root=expected_transaction_root)
                require(record["state_root"] == expected["successor_head"]["head"], "WORKBENCH_STORAGE_SUCCESSOR_MISMATCH")
                proposed._record_context(record)
                verified_state = "SIGNED_STORE_RECONCILED"
                done = {**receipt, "status": "STORAGE_RECOVERED_ONLY", "recovery_required": False,
                    "current_head": expected["successor_head"], "effects_status": "SIGNED_STORE_RECONCILED"}
                result = {**done, "root": root(done)}
                phase = "RELEASE_STORAGE_LOCK"
            return result
        except Exception as error:
            if not mutation_attempted:
                if preflight_refusal is not None and error is not preflight_refusal:
                    raise preflight_refusal from error
                raise
            pending = {**receipt, "status": "STORAGE_RECOVERY_REQUIRED", "recovery_required": True,
                "pending_phase": phase, "last_verified_state": verified_state,
                "effects_status": "MAY_HAVE_OCCURRED_OBSERVE_BEFORE_RETRY"}
            raise StorageRecoveryPending({**pending, "root": root(pending)}, error) from error

    def _authorize_action(self, now: int, *, operation: str | None = None,
                          recovery_action: str | None = None,
                          expected_head: dict[str, Any] | None = None,
                          ticket: dict[str, Any] | None = None) -> None:
        try:
            self._authorize(now, operation)
        except Refusal:
            if self.recovery_authorization is None or recovery_action is None or expected_head is None:
                raise
            self._authorize_recovery(self.recovery_authorization, action=recovery_action,
                                     expected_head=expected_head, ticket=ticket, now=now)

    def _expect(self, expected_head: dict[str, Any]) -> dict[str, Any]:
        pin = _head(expected_head)
        require(tuple(self.store.anchor.observe()) == (pin["sequence"], pin["head"]),
                "WORKBENCH_STALE_EXTERNAL_HEAD")
        return pin

    def _load(self, expected_head: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        self._expect(expected_head)
        record = self.store.load()
        return self._record_context(record)

    def _record_context(self, record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        raw_payload = record["body"]["payload"]
        require(type(raw_payload) is dict and raw_payload.get("schema") != "ucl.ucm.workbench.migration_terminal.v1",
                "WORKBENCH_SUCCESSOR_ALREADY_BOUND")
        payload = exact_keys(raw_payload, {"schema", "project_root", "plan", "pins",
                             "worker_identity", "worker_root", "generation", "predecessor", "events"})
        require(payload["schema"] == STATE_SCHEMA and payload["project_root"] == self.project["snapshot_root"]
                and payload["pins"] == self.pins and payload["plan"] == self.plan,
                "WORKBENCH_STORED_CONTEXT_MISMATCH")
        require(payload["worker_identity"] == self.worker_identity and payload["worker_root"] == self.worker_root,
                "WORKBENCH_WORKER_PIN_MISMATCH")
        require(type(payload["generation"]) is int and payload["generation"] >= 1,
                "WORKBENCH_GENERATION_INVALID")
        self._verify_predecessor(payload)
        return deepcopy(payload), self._fold(payload)

    def _verify_predecessor(self, payload: dict[str, Any]) -> None:
        if payload["generation"] == 1:
            require(payload["predecessor"] is None, "WORKBENCH_GENESIS_PREDECESSOR_INVALID")
        else:
            from .workbench_migration import verify_predecessor
            verify_predecessor(payload["predecessor"], target_project=self.project,
                               target_plan=self.plan, target_orientation=self.orientation,
                               target_orientation_pins=self.orientation_pins,
                               target_state_identity=self.store.identity,
                               target_worker_identity=self.worker_identity,
                               target_worker_root=self.worker_root,
                               target_generation=payload["generation"])

    def _commit(self, payload: dict[str, Any], expected_head: dict[str, Any]) -> dict[str, Any]:
        self._fold(payload)
        record = self.store.commit(payload, expected_sequence=expected_head["sequence"], expected_head=expected_head["head"])
        self.current_head = {"sequence": record["body"]["sequence"], "head": record["state_root"]}
        return dict(self.current_head)

    def _verify_result(self, result: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        from .workbench_workers import verify_worker_result
        body = verify_worker_result(result, expected_request=request,
                                    expected_issuer=self.worker_identity,
                                    expected_worker_root=self.worker_root)
        self._check_worker_policy(result["evidence"]["policy"])
        return body

    def _check_worker_policy(self, policy: Any) -> None:
        require(type(policy) is dict and root(policy) == self.worker_root,
                "WORKBENCH_WORKER_PIN_MISMATCH")
        maximum = policy.get("maximum_artifact_bytes")
        require(type(maximum) is int and 1 <= maximum <= self.orientation["budgets"]["max_artifact_bytes"],
                "WORKBENCH_ARTIFACT_BUDGET_EXCEEDED")

    def _verify_worker_preflight(self, preflight: Any, request: dict[str, Any]) -> dict[str, Any]:
        item = exact_keys(preflight, {"schema", "request_root", "worker_root", "source_root",
                                      "status", "authority_effect", "preflight_root"})
        body = {key: item[key] for key in item if key != "preflight_root"}
        require(item["schema"] == "ucl.ucm.workbench_worker_preflight.v1"
                and item["request_root"] == request["request_root"]
                and item["worker_root"] == self.worker_root
                and item["source_root"] == self.pins["source_root"]
                and item["status"] in {"READY", "ALREADY_COMPLETE"}
                and item["authority_effect"] == "NONE"
                and item["preflight_root"] == root(body),
                "WORKBENCH_WORKER_PREFLIGHT_INVALID")
        return dict(item)

    def _runtime_task_payload(self, task: dict[str, Any], tasks: dict[str, Any],
                              operations: dict[str, Any]) -> dict[str, Any]:
        planned = task["payload"]
        if task["operation"] != "RUN_TESTS" or "candidate_task_id" not in planned:
            return deepcopy(planned)
        candidate_task_id = planned["candidate_task_id"]
        require(candidate_task_id in task["depends_on"]
                and tasks[candidate_task_id]["state"] == "COMPLETE",
                "WORKBENCH_CANDIDATE_NOT_READY")
        matches = [row for row in operations.values()
                   if row["ticket"]["request"]["task_id"] == candidate_task_id
                   and row["ticket"]["request"]["operation"] == "PREPARE_CANDIDATE"
                   and row["status"] == "COMPLETE"]
        require(len(matches) == 1 and type(matches[0].get("result")) is dict,
                "WORKBENCH_CANDIDATE_PROVENANCE_INVALID")
        prepared = matches[0]
        manifest = prepared["result"]["evidence"]["result"]["candidate_manifest"]
        require(type(manifest) is dict and type(manifest.get("source_root")) is str,
                "WORKBENCH_CANDIDATE_PROVENANCE_INVALID")
        return {"modules": deepcopy(planned["modules"]),
                "candidate_operation_id": prepared["ticket"]["request"]["operation_id"],
                "candidate_source_root": require_root(manifest["source_root"]),
                "candidate_receipt_root": root(prepared["result"]["receipt"])}

    def _fold(self, payload: dict[str, Any]) -> dict[str, Any]:
        events = payload["events"]
        require(type(events) is list and len(events) <= MAX_EVENTS, "WORKBENCH_EVENT_BUDGET_EXCEEDED")
        tasks = {name: {"state": "PENDING", "attempts": 0, "receipt_root": None} for name in self.tasks}
        operations: dict[str, Any] = {}
        active = None
        spent = 0
        for event in events:
            item = exact_keys(event, {"kind", "ticket", "material"})
            ticket = item["ticket"]
            exact_keys(ticket, {"request", "dispatcher_id", "session_id", "orientation_root", "ticket_root"})
            require(ticket["ticket_root"] == root({key: value for key, value in ticket.items() if key != "ticket_root"}),
                    "WORKBENCH_TICKET_ROOT_INVALID")
            request = ticket["request"]
            from .workbench_workers import verify_worker_request
            verify_worker_request(request)
            tid, oid = request["task_id"], request["operation_id"]
            require(tid in self.tasks, "WORKBENCH_TASK_UNKNOWN")
            task, state = self.tasks[tid], tasks[tid]
            if item["kind"] == "DISPATCH_STARTED":
                require(active is None and oid not in operations and state["state"] == "PENDING",
                        "WORKBENCH_DISPATCH_CONFLICT")
                require(all(tasks[name]["state"] == "COMPLETE" for name in task["depends_on"]),
                        "WORKBENCH_DEPENDENCY_NOT_COMPLETE")
                expected_runtime_payload = self._runtime_task_payload(task, tasks, operations)
                require(request["generation"] == payload["generation"]
                        and request["operation"] == task["operation"] and request["payload"] == expected_runtime_payload,
                        "WORKBENCH_REQUEST_CONTRACT_MISMATCH")
                for name in PIN_FIELDS:
                    require(request[name] == self.pins[name], "WORKBENCH_REQUEST_PIN_MISMATCH")
                require(request["tenant_id"] == self.orientation["tenant_id"], "WORKBENCH_TENANT_MISMATCH")
                require(state["attempts"] < self.orientation["budgets"]["max_attempts"],
                        "WORKBENCH_ATTEMPT_BUDGET_EXCEEDED")
                require(request["attempt_id"] == tid + ":" + str(state["attempts"] + 1), "WORKBENCH_ATTEMPT_INVALID")
                require(item["material"] == {"cost_units": task["cost_units"]}, "WORKBENCH_COST_INVALID")
                spent += task["cost_units"]
                require(spent <= self.plan["budget_limit_units"], "WORKBENCH_BUDGET_EXCEEDED")
                state.update(state="IN_FLIGHT", attempts=state["attempts"] + 1)
                active = ticket
                operations[oid] = {"ticket": ticket, "result": None, "status": "IN_FLIGHT"}
            elif item["kind"] == "DISPATCH_UNCERTAIN":
                require(active == ticket and state["state"] == "IN_FLIGHT", "WORKBENCH_ACTIVE_TICKET_MISMATCH")
                exact_keys(item["material"], {"diagnostic"})
                _text(item["material"]["diagnostic"])
                state["state"] = operations[oid]["status"] = "UNCERTAIN"
            elif item["kind"] == "DISPATCH_COMPLETED":
                require(active == ticket and state["state"] in {"IN_FLIGHT", "UNCERTAIN"},
                        "WORKBENCH_ACTIVE_TICKET_MISMATCH")
                body = self._verify_result(item["material"], request)
                status = "COMPLETE" if body["status"] == "PASS" else "FAILED"
                state.update(state=status, receipt_root=root(item["material"]["receipt"]))
                operations[oid].update(result=item["material"], status=status)
                active = None
            elif item["kind"] == "DISPATCH_NOT_EXECUTED":
                require(active == ticket and state["state"] in {"IN_FLIGHT", "UNCERTAIN"},
                        "WORKBENCH_ACTIVE_TICKET_MISMATCH")
                body = verify_asymmetric(item["material"], RECONCILIATION_DOMAIN,
                                         expected_key_root=self.worker_identity["key_root"],
                                         public_key_hex=self.worker_identity["public_key_hex"])
                require(body == {"schema": "ucl.ucm.workbench.no_execution.v1", "request_root": request["request_root"],
                                 "status": "NOT_EXECUTED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"},
                        "WORKBENCH_RECONCILIATION_INVALID")
                # A new operation ID may attempt this task only after the
                # worker authenticates that this attempt did not execute.
                # Its consumed budget and prior operation remain recorded.
                state.update(state="PENDING", receipt_root=None)
                operations[oid].update(result=item["material"], status="CANCELLED")
                active = None
            else:
                raise Refusal("WORKBENCH_EVENT_KIND_INVALID")
        return {"tasks": tasks, "operations": operations, "active": active, "budget_spent_units": spent,
                "status": "COMPLETE_INFORMATION_ONLY" if all(s["state"] == "COMPLETE" for s in tasks.values())
                else ("RECOVERY_REQUIRED" if active is not None else "WORK_PENDING"),
                "project_obligations_satisfied": [], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}

    def status(self, *, expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        self._authorize_action(now, recovery_action="STATUS", expected_head=expected_head)
        with _exclusive(self.store.directory):
            _, folded = self._load(expected_head)
            return {**folded, "current_head": dict(expected_head), "plan_root": self.plan["plan_root"]}

    def current_task_context(self, task_id: str, *, expected_head: dict[str, Any],
                             now: int) -> dict[str, Any]:
        """One deterministic agent projection of task, custody and evidence state."""
        _text(task_id)
        require(task_id in self.tasks, "WORKBENCH_TASK_UNKNOWN")
        self._authorize_action(now, recovery_action="STATUS", expected_head=expected_head)
        with _exclusive(self.store.directory):
            _, folded = self._load(expected_head)
        task = self.tasks[task_id]
        state = folded["tasks"][task_id]
        active = folded["active"] if (folded["active"] or {}).get("request", {}).get("task_id") == task_id else None
        completed = [row for row in folded["operations"].values()
                     if row["ticket"]["request"]["task_id"] == task_id
                     and row["status"] in {"COMPLETE", "FAILED"}]
        evidence_roots = sorted({root(row["result"]["receipt"]) for row in completed
                                 if type(row.get("result")) is dict and type(row["result"].get("receipt")) is dict})
        remaining = self.plan["budget_limit_units"] - folded["budget_spent_units"]
        body = {"schema": "ucl.ucm.workbench.current_task_context.v1",
                "task_id": task_id, "task_contract": deepcopy(task), "task_state": deepcopy(state),
                "project_root": self.pins["project_root"], "source_root": self.pins["source_root"],
                "plan_root": self.plan["plan_root"], "current_head": _head(expected_head),
                "active_ticket_root": None if active is None else active["ticket_root"],
                "allowed_operation": task["operation"], "dependency_states": [
                    {"task_id": name, "state": folded["tasks"][name]["state"]}
                    for name in task["depends_on"]],
                "budget": {"spent_units": folded["budget_spent_units"],
                           "remaining_units": remaining,
                           "plan_limit_units": self.plan["budget_limit_units"]},
                "evidence_receipt_roots": evidence_roots,
                "completion_claim": "INFORMATION_ONLY_TASK_COMPLETE" if state["state"] == "COMPLETE" else None,
                "unresolved_effects": ["ACTIVE_WORKER_RESULT_UNSETTLED"] if active is not None else [],
                "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        return {**body, "context_root": root(body)}

    def begin_dispatch(self, task_id: str, operation_id: str, dispatcher_id: str, *,
                       expected_head: dict[str, Any], now: int, worker: Any | None = None) -> dict[str, Any]:
        _text(task_id); _text(operation_id); _text(dispatcher_id)
        require(task_id in self.tasks, "WORKBENCH_TASK_UNKNOWN")
        task = self.tasks[task_id]
        self._authorize(now, task["operation"])
        with _exclusive(self.store.directory):
            payload, folded = self._load(expected_head)
            from .workbench_workers import make_worker_request
            runtime_payload = self._runtime_task_payload(task, folded["tasks"], folded["operations"])
            request = make_worker_request(operation=task["operation"], operation_id=operation_id,
                         task_id=task_id, attempt_id=task_id + ":" + str(folded["tasks"][task_id]["attempts"] + 1), generation=payload["generation"],
                         tenant_id=self.orientation["tenant_id"], payload=runtime_payload, **self.pins)
            old = folded["operations"].get(operation_id)
            if old is not None:
                # Bind the operation to its original exact request including
                # original attempt; do not reconstruct it as a fresh retry.
                compared = dict(request, attempt_id=old["ticket"]["request"]["attempt_id"])
                compared = make_worker_request(**{key: value for key, value in compared.items() if key not in {"schema", "request_root"}})
                require(old["ticket"]["request"] == compared, "WORKBENCH_IDEMPOTENCY_CONFLICT")
                require(old["status"] in {"COMPLETE", "FAILED", "CANCELLED"}, "WORKBENCH_RECONCILIATION_REQUIRED")
                return {"ticket": old["ticket"], "current_head": dict(expected_head), "idempotent": True,
                        "status": old["status"], "result": old["result"]}
            require(folded["active"] is None, "WORKBENCH_DISPATCHER_BUSY")
            require(folded["tasks"][task_id]["state"] == "PENDING", "WORKBENCH_TASK_ALREADY_ATTEMPTED")
            if worker is not None:
                require(getattr(worker, "worker_root", None) == self.worker_root,
                        "WORKBENCH_WORKER_PIN_MISMATCH")
                self._check_worker_policy(getattr(worker, "policy", None))
                self._verify_worker_preflight(worker.preflight(request), request)
            body = {"request": request, "dispatcher_id": dispatcher_id,
                    "session_id": self.orientation["session_id"], "orientation_root": self.orientation["root"]}
            ticket = {**body, "ticket_root": root(body)}
            payload["events"].append({"kind": "DISPATCH_STARTED", "ticket": ticket,
                                       "material": {"cost_units": task["cost_units"]}})
            head = self._commit(payload, expected_head)
            return {"ticket": ticket, "current_head": head, "idempotent": False, "status": "IN_FLIGHT"}

    def complete_dispatch(self, ticket: dict[str, Any], result: dict[str, Any], *,
                          expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        require(type(ticket) is dict and type(ticket.get("request")) is dict
                and type(ticket["request"].get("operation")) is str
                and ticket["request"].get("operation") in OPERATIONS,
                "WORKBENCH_TICKET_INVALID")
        self._authorize_action(now, operation=ticket["request"]["operation"],
                               recovery_action="COMPLETE_DISPATCH",
                               expected_head=expected_head, ticket=ticket)
        with _exclusive(self.store.directory):
            payload, folded = self._load(expected_head)
            require(folded["active"] == ticket, "WORKBENCH_ACTIVE_TICKET_MISMATCH")
            self._verify_result(result, ticket["request"])
            payload["events"].append({"kind": "DISPATCH_COMPLETED", "ticket": deepcopy(ticket), "material": deepcopy(result)})
            head = self._commit(payload, expected_head)
            return {**self._fold(payload), "current_head": head}

    def mark_uncertain(self, ticket: dict[str, Any], *, diagnostic: str,
                       expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        self._authorize_action(now, recovery_action="MARK_UNCERTAIN",
                               expected_head=expected_head, ticket=ticket)
        with _exclusive(self.store.directory):
            payload, folded = self._load(expected_head)
            require(folded["active"] == ticket, "WORKBENCH_ACTIVE_TICKET_MISMATCH")
            payload["events"].append({"kind": "DISPATCH_UNCERTAIN", "ticket": deepcopy(ticket),
                                       "material": {"diagnostic": _text(diagnostic)}})
            head = self._commit(payload, expected_head)
            return {**self._fold(payload), "current_head": head}

    def reconcile_not_executed(self, ticket: dict[str, Any], attestation: dict[str, Any], *,
                               expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        self._authorize_action(now, recovery_action="RECONCILE_NOT_EXECUTED",
                               expected_head=expected_head, ticket=ticket)
        with _exclusive(self.store.directory):
            payload, folded = self._load(expected_head)
            require(folded["active"] == ticket, "WORKBENCH_ACTIVE_TICKET_MISMATCH")
            payload["events"].append({"kind": "DISPATCH_NOT_EXECUTED", "ticket": deepcopy(ticket), "material": deepcopy(attestation)})
            head = self._commit(payload, expected_head)
            return {**self._fold(payload), "current_head": head}

    def execute(self, task_id: str, operation_id: str, dispatcher_id: str, worker: Any, *,
                expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        self._authorize(now)
        require(getattr(worker, "worker_root", None) == self.worker_root,
                "WORKBENCH_WORKER_PIN_MISMATCH")
        self._check_worker_policy(getattr(worker, "policy", None))
        begun = self.begin_dispatch(task_id, operation_id, dispatcher_id,
                                    expected_head=expected_head, now=now, worker=worker)
        if begun["idempotent"]:
            return begun
        try:
            result = worker.execute(begun["ticket"]["request"])
        except Exception as exc:
            pending = self.mark_uncertain(begun["ticket"], diagnostic=type(exc).__name__,
                                          expected_head=begun["current_head"], now=now)
            return {**pending, "ticket": begun["ticket"], "worker_result": None}
        try:
            return self.complete_dispatch(begun["ticket"], result, expected_head=begun["current_head"], now=now)
        except Refusal:
            # Invalid results never permit a second attempt. Preserve the exact
            # IN_FLIGHT event for authenticated reconciliation.
            raise

    def recover_store(self, *, expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        """Complete only the signed interrupted storage transaction, no worker retry."""
        self._authorize(now)
        with _exclusive(self.store.directory):
            self._expect(expected_head)
            self.store.recover_interrupted_commit()
            sequence, head = self.store.anchor.observe()
            pin = {"sequence": sequence, "head": head}
            _, folded = self._load(pin)
            return {**folded, "current_head": pin}

    @classmethod
    def reopen_recovering_store(cls, store: ProtectedStateStore, *, expected_head: dict[str, Any],
                               **kwargs: Any) -> "WorkbenchManager":
        """Storage-only restart reconciliation, requiring the current external pin.

        The store verifies the signed transaction and journal. The recovered
        plan is then folded normally. This never invokes a worker, including
        when the recovered event says IN_FLIGHT.
        """
        pin = _head(expected_head)
        from .workbench_orientation import verify_orientation
        verify_orientation(kwargs["orientation"], external_pins=kwargs["orientation_pins"],
                           now=kwargs["now"], expected_head=kwargs["orientation"]["current_head"])
        validate_plan(kwargs["plan"], kwargs["project"], pins=kwargs["plan"]["pins"])
        with _exclusive(store.directory):
            require(tuple(store.anchor.observe()) == (pin["sequence"], pin["head"]),
                    "WORKBENCH_STALE_EXTERNAL_HEAD")
            store.recover_interrupted_commit()
            sequence, head = store.anchor.observe()
        return cls(store, expected_head={"sequence": sequence, "head": head}, **kwargs)

    def export_capsule(self, *, expected_head: dict[str, Any], now: int) -> dict[str, Any]:
        self._authorize_action(now, recovery_action="EXPORT_CAPSULE", expected_head=expected_head)
        with _exclusive(self.store.directory):
            _, folded = self._load(expected_head)
            body = {"schema": "ucl.ucm.workbench.portable_capsule.v1", "current_head": dict(expected_head),
                    "anchor": self.store.anchor.observe_record(), "state_record": self.store.load(),
                    "journal": self.store.verify_journal(), "pins": self.pins,
                    "status": folded["status"], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
            return self.store.keys.sign(self.store.signing_handle, CAPSULE_DOMAIN, body)

    @classmethod
    def import_capsule(cls, store: ProtectedStateStore, capsule: dict[str, Any], *,
                       expected_head: dict[str, Any], **kwargs: Any) -> "WorkbenchManager":
        """Move exact custody under the *same externally held head*.

        Import never advances or rewrites the anchor. A valid older capsule is
        refused. Existing destination files may only equal the imported bytes,
        permitting recovery after interruption between the two file copies.
        """
        pin = _head(expected_head)
        body = verify_asymmetric(capsule, CAPSULE_DOMAIN,
                                 expected_key_root=store.identity["key_root"],
                                 public_key_hex=store.identity["public_key_hex"])
        exact_keys(body, {"schema", "current_head", "anchor", "state_record", "journal", "pins", "status", "standing", "authority_effect"})
        require(body["schema"] == "ucl.ucm.workbench.portable_capsule.v1"
                and body["current_head"] == pin
                and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE",
                "WORKBENCH_CAPSULE_CONTRACT_MISMATCH")
        require(body["anchor"] == store.anchor.observe_record(), "WORKBENCH_CAPSULE_STALE")
        require((body["anchor"]["sequence"], body["anchor"]["head"]) == (pin["sequence"], pin["head"]),
                "WORKBENCH_CAPSULE_STALE")
        require(type(body["journal"]) is list, "WORKBENCH_CAPSULE_JOURNAL_INVALID")
        state_bytes = (json.dumps(body["state_record"], indent=2, sort_keys=True) + "\n").encode()
        journal_bytes = b"".join((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode() for row in body["journal"])
        with _exclusive(store.directory):
            require(not store.transaction_path.exists(), "PROTECTED_COMMIT_RECOVERY_REQUIRED")
            require(body["anchor"] == store.anchor.observe_record(), "WORKBENCH_CAPSULE_STALE")
            with tempfile.TemporaryDirectory(prefix="workbench-import-", dir=store.directory) as staging:
                checked = ProtectedStateStore(Path(staging), anchor=store.anchor, keys=store.keys, signing_handle=store.signing_handle)
                checked.path.write_bytes(state_bytes); checked.journal_path.write_bytes(journal_bytes)
                checked.load()
                # Also validate every event/receipt before materializing it.
                staged_manager = cls(checked, expected_head=pin, **kwargs)
                require(staged_manager.pins == body["pins"]
                        and staged_manager.status(expected_head=pin, now=kwargs["now"])["status"] == body["status"],
                        "WORKBENCH_CAPSULE_PROJECTION_MISMATCH")
            for path, blob in ((store.path, state_bytes), (store.journal_path, journal_bytes)):
                require(not path.is_symlink(), "WORKBENCH_CAPSULE_DESTINATION_ALIAS")
                require(not path.exists() or path.read_bytes() == blob, "WORKBENCH_CAPSULE_DESTINATION_CONFLICT")
            store._write_atomic(store.path, state_bytes)
            store._write_atomic(store.journal_path, journal_bytes)
        return cls(store, expected_head=pin, **kwargs)
