"""Explicit Governor-authorized successor custody for bounded project plans.

Old task receipts remain history. Successor tasks always begin independently.
No authenticated old snapshot supplies freshness: both externally held store
heads and the exact Governor/identity/policy pins are required.
"""
from __future__ import annotations

from copy import deepcopy
import json
from types import SimpleNamespace
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root, strict_loads
from .custody import CustodyProvider, verify_asymmetric
from .protected_state import ProtectedStateStore, STATE_DOMAIN, _anchor_record
from .workbench_manager import (CAPSULE_DOMAIN, STATE_SCHEMA, WorkbenchManager,
                                _exclusive, _head, _pins, validate_plan)
from .workbench_orientation import verify_orientation

MIGRATION_DOMAIN = "UCL_UCM_WORKBENCH_MIGRATION_AUTHORIZATION_V1"
TERMINAL_SCHEMA = "ucl.ucm.workbench.migration_terminal.v1"
MAX_GENERATIONS = 6


def store_namespace(*, project_id: str, plan_root: str, state_key_root: str,
                    generation: int) -> str:
    require(type(project_id) is str and project_id and type(generation) is int
            and 1 <= generation <= MAX_GENERATIONS, "WORKBENCH_MIGRATION_GENERATION_INVALID")
    return root({"schema": "ucl.ucm.workbench.store_namespace.v1", "project_id": project_id,
                 "plan_root": require_root(plan_root), "state_key_root": require_root(state_key_root),
                 "generation": generation})


def _state_record(record: Any, identity: dict[str, Any]) -> dict[str, Any]:
    # Reuse the protected store's exact signed-state validator without a signer
    # or filesystem. No record is accepted merely for having its own root.
    verifier = ProtectedStateStore.__new__(ProtectedStateStore)
    verifier.identity = identity
    return verifier._verify_state(record)


def _journal_row(row: Any, identity: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(row, {"body", "body_root", "signature", "key_root", "signature_algorithm", "journal_root"})
    signed = {key: item[key] for key in item if key != "journal_root"}
    body = verify_asymmetric(signed, STATE_DOMAIN + ":JOURNAL",
                             expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"])
    exact_keys(body, {"schema", "sequence", "predecessor", "state_root", "state_sequence", "standing", "authority_effect"})
    require(body["schema"] == "ucl.ucm.protected_state_journal.v2"
            and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE"
            and item["journal_root"] == root(signed), "WORKBENCH_MIGRATION_JOURNAL_INVALID")
    return body


def _capsule(capsule: Any, identity: dict[str, Any], expected_head: dict[str, Any]) -> dict[str, Any]:
    body = verify_asymmetric(capsule, CAPSULE_DOMAIN, expected_key_root=identity["key_root"],
                             public_key_hex=identity["public_key_hex"])
    exact_keys(body, {"schema", "current_head", "anchor", "state_record", "journal", "pins", "status", "standing", "authority_effect"})
    require(body["schema"] == "ucl.ucm.workbench.portable_capsule.v1"
            and body["current_head"] == _head(expected_head)
            and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE",
            "WORKBENCH_MIGRATION_CAPSULE_INVALID")
    record = _state_record(body["state_record"], identity)
    require(record["state_root"] == expected_head["head"] and record["body"]["sequence"] == expected_head["sequence"],
            "WORKBENCH_MIGRATION_CAPSULE_INVALID")
    rows = body["journal"]
    require(type(rows) is list and len(rows) == expected_head["sequence"] > 0,
            "WORKBENCH_MIGRATION_JOURNAL_INVALID")
    previous = "GENESIS"
    for number, row in enumerate(rows, 1):
        checked = _journal_row(row, identity)
        require(type(checked["sequence"]) is int and checked["sequence"] == checked["state_sequence"] == number
                and checked["predecessor"] == previous, "WORKBENCH_MIGRATION_JOURNAL_INVALID")
        previous = row["journal_root"]
    require(rows[-1]["body"]["state_root"] == expected_head["head"], "WORKBENCH_MIGRATION_JOURNAL_INVALID")
    require(body["anchor"] == _anchor_record(len(rows), expected_head["head"], len(rows), previous),
            "WORKBENCH_MIGRATION_ANCHOR_INVALID")
    return body


def _inventory(folded: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    accepted = []
    for operation_id, operation in sorted(folded["operations"].items()):
        if operation["status"] == "COMPLETE":
            request = operation["ticket"]["request"]
            accepted.append({"operation_id": operation_id, "task_id": request["task_id"],
                             "request_root": request["request_root"],
                             "receipt_root": root(operation["result"]["receipt"])})
    pending = [{"task_id": tid, **state} for tid, state in sorted(folded["tasks"].items())
               if state["state"] != "COMPLETE"]
    obligations = [{"id": row["id"], "record_root": root(row), "state": row["state"]}
                   for row in project["records"] if row["kind"] == "VERIFICATION_OBLIGATION"]
    return {"accepted_receipts": accepted, "pending_tasks": pending, "pending_obligations": obligations}


def _historical_manager(payload: dict[str, Any], *, project: dict[str, Any],
                        orientation: dict[str, Any], orientation_pins: dict[str, Any],
                        identity: dict[str, Any]) -> WorkbenchManager:
    exact_keys(payload, {"schema", "project_root", "plan", "pins", "worker_identity", "worker_root", "generation", "predecessor", "events"})
    require(payload["schema"] == STATE_SCHEMA and payload["project_root"] == project["snapshot_root"],
            "WORKBENCH_MIGRATION_SOURCE_INVALID")
    manager = WorkbenchManager.__new__(WorkbenchManager)
    manager.store = SimpleNamespace(identity=identity)
    manager.project, manager.plan, manager.pins = project, payload["plan"], _pins(payload["pins"])
    manager.orientation, manager.orientation_pins = orientation, orientation_pins
    manager.worker_identity, manager.worker_root = payload["worker_identity"], payload["worker_root"]
    manager.tasks = validate_plan(manager.plan, project, pins=manager.pins)
    require(type(payload["generation"]) is int and 1 <= payload["generation"] <= MAX_GENERATIONS,
            "WORKBENCH_MIGRATION_GENERATION_INVALID")
    manager._verify_predecessor(payload)
    return manager


def prepare_migration(manager: WorkbenchManager, *, expected_head: dict[str, Any], now: int,
                      target_project: dict[str, Any], target_plan: dict[str, Any],
                      target_orientation: dict[str, Any], target_orientation_pins: dict[str, Any],
                      target_state_identity: dict[str, Any], target_worker_identity: dict[str, Any],
                      target_worker_root: str) -> dict[str, Any]:
    """Return exact unsigned material for a separately held Governor signer."""
    manager._authorize(now)
    WorkbenchManager.preflight_configuration(project=target_project, plan=target_plan,
        orientation=target_orientation, orientation_pins=target_orientation_pins,
        worker_identity=target_worker_identity, worker_root=target_worker_root, now=now)
    verify_orientation(target_orientation, external_pins=target_orientation_pins, now=now,
                       expected_head=target_orientation["current_head"])
    validate_plan(target_plan, target_project, pins=target_plan["pins"])
    require(target_project["project_id"] == manager.project["project_id"], "WORKBENCH_MIGRATION_PROJECT_MISMATCH")
    require(target_orientation["tenant_id"] == manager.orientation["tenant_id"], "WORKBENCH_MIGRATION_TENANT_MISMATCH")
    require(target_orientation_pins["issuer_key_root"] == manager.orientation_pins["issuer_key_root"],
            "WORKBENCH_MIGRATION_GOVERNOR_ROTATION_UNBOUND")
    capsule = manager.export_capsule(expected_head=expected_head, now=now)
    payload = capsule["body"]["state_record"]["body"]["payload"]
    folded = manager._fold(payload)
    require(folded["active"] is None, "WORKBENCH_MIGRATION_IN_FLIGHT")
    generation = payload["generation"] + 1
    namespace = store_namespace(project_id=target_project["project_id"], plan_root=target_plan["plan_root"],
                                state_key_root=target_state_identity["key_root"], generation=generation)
    source = {"generation": payload["generation"], "head": dict(expected_head),
              "plan_root": manager.plan["plan_root"], "pins": manager.pins,
              "state_identity": manager.store.identity, "worker_identity": manager.worker_identity,
              "worker_root": manager.worker_root, "capsule_root": root(capsule), **_inventory(folded, manager.project)}
    target = {"generation": generation, "plan_root": target_plan["plan_root"], "pins": target_plan["pins"],
              "state_identity": deepcopy(target_state_identity), "worker_identity": deepcopy(target_worker_identity),
              "worker_root": require_root(target_worker_root), "store_namespace_root": namespace}
    body = {"schema": "ucl.ucm.workbench.migration_authorization.v1", "project_id": manager.project["project_id"],
            "tenant_id": manager.orientation["tenant_id"], "issued_at": now, "source": source, "target": target,
            "completion_transfer": "HISTORY_ONLY_NEW_TASKS_PENDING", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {"body": body, "source_capsule": capsule, "source_project": deepcopy(manager.project),
            "source_orientation": deepcopy(manager.orientation), "source_orientation_pins": deepcopy(manager.orientation_pins)}


def authorize_migration(prepared: dict[str, Any], *, provider: CustodyProvider, signing_handle: str,
                        expected_governor: dict[str, Any]) -> dict[str, Any]:
    exact_keys(prepared, {"body", "source_capsule", "source_project", "source_orientation", "source_orientation_pins"})
    require(provider.identity(signing_handle) == expected_governor and expected_governor["role"] == "GOVERNOR",
            "WORKBENCH_MIGRATION_GOVERNOR_INVALID")
    require(prepared["source_orientation_pins"]["issuer_key_root"] == expected_governor["key_root"],
            "WORKBENCH_MIGRATION_GOVERNOR_INVALID")
    return provider.sign(signing_handle, MIGRATION_DOMAIN, deepcopy(prepared["body"]))


def _authorization(authorization: Any, external_pins: dict[str, Any]) -> dict[str, Any]:
    body = verify_asymmetric(authorization, MIGRATION_DOMAIN,
                             expected_key_root=external_pins["issuer_key_root"],
                             public_key_hex=external_pins["issuer_public_key_hex"])
    exact_keys(body, {"schema", "project_id", "tenant_id", "issued_at", "source", "target", "completion_transfer", "standing", "authority_effect"})
    require(body["schema"] == "ucl.ucm.workbench.migration_authorization.v1"
            and type(body["issued_at"]) is int and body["issued_at"] >= 0
            and body["completion_transfer"] == "HISTORY_ONLY_NEW_TASKS_PENDING"
            and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE",
            "WORKBENCH_MIGRATION_AUTHORIZATION_INVALID")
    source = exact_keys(body["source"], {"generation", "head", "plan_root", "pins", "state_identity", "worker_identity", "worker_root", "capsule_root", "accepted_receipts", "pending_tasks", "pending_obligations"})
    target = exact_keys(body["target"], {"generation", "plan_root", "pins", "state_identity", "worker_identity", "worker_root", "store_namespace_root"})
    require(type(source["generation"]) is int and type(target["generation"]) is int
            and 1 <= source["generation"] < MAX_GENERATIONS
            and target["generation"] == source["generation"] + 1,
            "WORKBENCH_MIGRATION_GENERATION_INVALID")
    _head(source["head"]); _pins(source["pins"]); _pins(target["pins"])
    return body


def verify_predecessor(bundle: Any, *, target_project: dict[str, Any], target_plan: dict[str, Any],
                       target_orientation: dict[str, Any], target_orientation_pins: dict[str, Any],
                       target_state_identity: dict[str, Any], target_worker_identity: dict[str, Any],
                       target_worker_root: str, target_generation: int) -> dict[str, Any]:
    item = exact_keys(bundle, {"schema", "authorization", "source_capsule", "source_project", "source_orientation", "source_orientation_pins", "terminal_record", "terminal_journal_row"})
    require(item["schema"] == "ucl.ucm.workbench.predecessor_custody.v1", "WORKBENCH_MIGRATION_PREDECESSOR_INVALID")
    body = _authorization(item["authorization"], target_orientation_pins)
    source, target = body["source"], body["target"]
    require(body["project_id"] == item["source_project"]["project_id"] == target_project["project_id"],
            "WORKBENCH_MIGRATION_PROJECT_MISMATCH")
    require(body["tenant_id"] == item["source_orientation"]["tenant_id"] == target_orientation["tenant_id"],
            "WORKBENCH_MIGRATION_TENANT_MISMATCH")
    require(item["source_orientation_pins"]["issuer_key_root"] == target_orientation_pins["issuer_key_root"],
            "WORKBENCH_MIGRATION_GOVERNOR_ROTATION_UNBOUND")
    verify_orientation(item["source_orientation"], external_pins=item["source_orientation_pins"],
                       now=body["issued_at"], expected_head=item["source_orientation"]["current_head"])
    capsule = _capsule(item["source_capsule"], source["state_identity"], source["head"])
    require(root(item["source_capsule"]) == source["capsule_root"], "WORKBENCH_MIGRATION_CAPSULE_MISMATCH")
    payload = capsule["state_record"]["body"]["payload"]
    old = _historical_manager(payload, project=item["source_project"], orientation=item["source_orientation"],
                              orientation_pins=item["source_orientation_pins"], identity=source["state_identity"])
    old._authorize(body["issued_at"])
    folded = old._fold(payload)
    require(folded["active"] is None, "WORKBENCH_MIGRATION_IN_FLIGHT")
    require(source["generation"] == payload["generation"] and source["plan_root"] == old.plan["plan_root"]
            and source["pins"] == old.pins and source["worker_identity"] == old.worker_identity
            and source["worker_root"] == old.worker_root and capsule["pins"] == old.pins
            and capsule["status"] == folded["status"], "WORKBENCH_MIGRATION_SOURCE_INVALID")
    inventory = _inventory(folded, item["source_project"])
    require(all(source[key] == value for key, value in inventory.items()), "WORKBENCH_MIGRATION_HISTORY_MISMATCH")
    expected_namespace = store_namespace(project_id=target_project["project_id"], plan_root=target_plan["plan_root"],
                                        state_key_root=target_state_identity["key_root"], generation=target_generation)
    require(target == {"generation": target_generation, "plan_root": target_plan["plan_root"],
                       "pins": target_plan["pins"], "state_identity": target_state_identity,
                       "worker_identity": target_worker_identity, "worker_root": target_worker_root,
                       "store_namespace_root": expected_namespace}, "WORKBENCH_MIGRATION_TARGET_MISMATCH")
    terminal = _state_record(item["terminal_record"], source["state_identity"])
    expected_terminal = {"schema": TERMINAL_SCHEMA, "authorization": item["authorization"],
                         "source_capsule_root": source["capsule_root"], "source_head": source["head"],
                         "target_namespace_root": expected_namespace, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    require(terminal["body"]["payload"] == expected_terminal
            and terminal["body"]["sequence"] == source["head"]["sequence"] + 1
            and terminal["body"]["predecessor"] == source["head"]["head"], "WORKBENCH_MIGRATION_TERMINAL_INVALID")
    row = _journal_row(item["terminal_journal_row"], source["state_identity"])
    require(row["sequence"] == row["state_sequence"] == terminal["body"]["sequence"]
            and row["state_root"] == terminal["state_root"]
            and row["predecessor"] == capsule["anchor"]["journal_head"], "WORKBENCH_MIGRATION_TERMINAL_INVALID")
    return body


def migrate(manager: WorkbenchManager, new_store: ProtectedStateStore, *, prepared: dict[str, Any],
            authorization: dict[str, Any], expected_old_head: dict[str, Any],
            expected_new_head: dict[str, Any], now: int, **target_args: Any) -> WorkbenchManager:
    """Consume the old head once, seal its terminal state, then initialize child.

    The durable intent allows `resume_migration` after an interrupted child
    initialization. Retrying this operation blindly against the old pin refuses.
    """
    body = _authorization(authorization, target_args["orientation_pins"])
    require(body == prepared["body"], "WORKBENCH_MIGRATION_AUTHORIZATION_MISMATCH")
    issued_at = body["issued_at"]
    require(type(now) is int and now >= issued_at,
            "WORKBENCH_MIGRATION_AUTHORIZATION_TIME_INVALID")
    # Authorization remains the exact signed preparation made at issued_at.
    # Execution freshness is checked independently at the actual migration
    # time, so a fresh timestamp can no longer make an otherwise identical
    # signed preparation compare unequal.
    manager._authorize(now)
    WorkbenchManager.preflight_configuration(project=target_args["project"], plan=target_args["plan"],
        orientation=target_args["orientation"], orientation_pins=target_args["orientation_pins"],
        worker_identity=target_args["worker_identity"], worker_root=target_args["worker_root"], now=now)
    current = prepare_migration(manager, expected_head=expected_old_head, now=issued_at,
        target_project=target_args["project"], target_plan=target_args["plan"],
        target_orientation=target_args["orientation"], target_orientation_pins=target_args["orientation_pins"],
        target_state_identity=new_store.identity, target_worker_identity=target_args["worker_identity"],
        target_worker_root=target_args["worker_root"])
    require(prepared == current, "WORKBENCH_MIGRATION_PREPARATION_STALE")
    require(_head(expected_new_head) == {"sequence": 0, "head": "GENESIS"}
            and tuple(new_store.anchor.observe()) == (0, "GENESIS"), "WORKBENCH_MIGRATION_DESTINATION_NOT_EMPTY")
    require(not new_store.path.exists() and not new_store.journal_path.exists()
            and not new_store.transaction_path.exists(), "WORKBENCH_MIGRATION_DESTINATION_NOT_EMPTY")
    intent = {"schema": "ucl.ucm.workbench.migration_intent.v1", "prepared": prepared, "authorization": authorization}
    intent_path = new_store.directory / "workbench-migration-intent.json"
    require(not intent_path.is_symlink(), "WORKBENCH_MIGRATION_DESTINATION_ALIAS")
    raw = (json.dumps(intent, sort_keys=True, indent=2) + "\n").encode()
    require(not intent_path.exists() or intent_path.read_bytes() == raw, "WORKBENCH_MIGRATION_DESTINATION_CONFLICT")
    new_store._write_atomic(intent_path, raw)
    with _exclusive(manager.store.directory):
        manager._load(expected_old_head)
        terminal = {"schema": TERMINAL_SCHEMA, "authorization": authorization,
                    "source_capsule_root": body["source"]["capsule_root"], "source_head": body["source"]["head"],
                    "target_namespace_root": body["target"]["store_namespace_root"],
                    "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        record = manager.store.commit(terminal, expected_sequence=expected_old_head["sequence"],
                                      expected_head=expected_old_head["head"])
        terminal_head = {"sequence": record["body"]["sequence"], "head": record["state_root"]}
    return resume_migration(manager.store, new_store, expected_old_head=terminal_head,
                            expected_new_head=expected_new_head, now=now, **target_args)


def resume_migration(old_store: ProtectedStateStore, new_store: ProtectedStateStore, *,
                     expected_old_head: dict[str, Any], expected_new_head: dict[str, Any],
                     now: int, **target_args: Any) -> WorkbenchManager:
    """Reconcile only the recorded migration; never synthesize a new genesis."""
    old_pin, new_pin = _head(expected_old_head), _head(expected_new_head)
    verify_orientation(target_args["orientation"], external_pins=target_args["orientation_pins"], now=now,
                       expected_head=target_args["orientation"]["current_head"])
    WorkbenchManager.preflight_configuration(now=now, **target_args)
    intent_path = new_store.directory / "workbench-migration-intent.json"
    require(intent_path.is_file() and not intent_path.is_symlink(), "WORKBENCH_MIGRATION_INTENT_MISSING")
    intent = exact_keys(strict_loads(intent_path.read_bytes()), {"schema", "prepared", "authorization"})
    require(intent["schema"] == "ucl.ucm.workbench.migration_intent.v1", "WORKBENCH_MIGRATION_INTENT_INVALID")
    prepared = exact_keys(intent["prepared"], {"body", "source_capsule", "source_project", "source_orientation", "source_orientation_pins"})
    authorization = intent["authorization"]
    with _exclusive(old_store.directory):
        require(tuple(old_store.anchor.observe()) == (old_pin["sequence"], old_pin["head"]), "WORKBENCH_STALE_EXTERNAL_HEAD")
        if old_store.transaction_path.exists():
            pending = strict_loads(old_store.transaction_path.read_bytes())
            require(type(pending) is dict and type(pending.get("state_record")) is dict
                    and type(pending["state_record"].get("body")) is dict,
                    "WORKBENCH_MIGRATION_SOURCE_NOT_TERMINAL")
            pending_payload = pending["state_record"]["body"].get("payload", {})
            require(type(pending_payload) is dict and pending_payload.get("schema") == TERMINAL_SCHEMA
                    and pending_payload.get("authorization") == authorization,
                    "WORKBENCH_MIGRATION_SOURCE_NOT_TERMINAL")
            old_store.recover_interrupted_commit()
        record = old_store.load()
        require(record["body"]["payload"].get("schema") == TERMINAL_SCHEMA,
                "WORKBENCH_MIGRATION_SOURCE_NOT_TERMINAL")
        require(record["body"]["payload"]["authorization"] == authorization, "WORKBENCH_MIGRATION_AUTHORIZATION_MISMATCH")
        journal = old_store.verify_journal()
        bundle = {"schema": "ucl.ucm.workbench.predecessor_custody.v1", "authorization": authorization,
                  **{key: prepared[key] for key in ("source_capsule", "source_project", "source_orientation", "source_orientation_pins")},
                  "terminal_record": record, "terminal_journal_row": journal[-1]}
        body = _authorization(authorization, target_args["orientation_pins"])
        verify_predecessor(bundle, target_project=target_args["project"], target_plan=target_args["plan"],
            target_orientation=target_args["orientation"], target_orientation_pins=target_args["orientation_pins"],
            target_state_identity=new_store.identity, target_worker_identity=target_args["worker_identity"],
            target_worker_root=target_args["worker_root"], target_generation=body["target"]["generation"])
        with _exclusive(new_store.directory):
            require(tuple(new_store.anchor.observe()) == (new_pin["sequence"], new_pin["head"]), "WORKBENCH_STALE_EXTERNAL_HEAD")
            if new_store.transaction_path.exists():
                new_store.recover_interrupted_commit()
            if new_store.path.exists():
                existing = new_store.load()["body"]["payload"]
                require(existing.get("predecessor") == bundle, "WORKBENCH_MIGRATION_DESTINATION_CONFLICT")
            else:
                require(new_pin == {"sequence": 0, "head": "GENESIS"}, "WORKBENCH_MIGRATION_DESTINATION_NOT_EMPTY")
                payload = {"schema": STATE_SCHEMA, "project_root": target_args["project"]["snapshot_root"],
                           "plan": deepcopy(target_args["plan"]), "pins": _pins(target_args["plan"]["pins"]),
                           "worker_identity": deepcopy(target_args["worker_identity"]),
                           "worker_root": target_args["worker_root"], "generation": body["target"]["generation"],
                           "predecessor": bundle, "events": []}
                new_store.commit(payload, expected_sequence=0, expected_head="GENESIS")
            sequence, head = new_store.anchor.observe()
    return WorkbenchManager(new_store, expected_head={"sequence": sequence, "head": head}, now=now, **target_args)
