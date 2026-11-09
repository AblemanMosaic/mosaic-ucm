"""Committed pre-1.0 architecture-readiness witness."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from mosaic_ui_std.catalog import load_runtime_catalog, validate_catalog

from .accessibility import accessibility_witness
from .browser_host import BrowserHostPolicy
from .browser_realizer import BrowserSessionManager
from .canonical import atomic_write, canonical_bytes, commitment
from .components import load_handlers
from .framework_bindings import binding_manifest
from .localization import localization_evidence
from .model import UIRefusal
from .pilot import build_payload
from .realizer import PROTOCOL_SCHEMA, RealizerRefusal, negotiate_protocol
from .runtime import GovernedRuntime, ReceiptRetentionPolicy
from .session_custody import session_custody_witness
from .sufficiency import build_sufficiency_payload
from .web_distribution import web_manifest


NATIVE_CONTROL_KINDS = {
    "COMBOBOX", "DATA_GRID", "LIST", "MENU", "NAVIGATION", "NOTIFICATION", "RADIO_GROUP", "TREE",
}


def architecture_witness(performance_evidence_commitment: str, *, output=None) -> dict[str, Any]:
    if len(performance_evidence_commitment) != 64 \
            or any(character not in "0123456789abcdef" for character in performance_evidence_commitment):
        raise UIRefusal("ARCHITECTURE_PERFORMANCE_ROOT_REFUSED", performance_evidence_commitment)

    catalog = load_runtime_catalog()
    catalog_validation = validate_catalog(catalog)
    handlers = load_handlers(catalog)
    win32_kinds = sorted(
        component["kind"] for component in catalog["components"] if "WIN32" in component["realized_by"]
    )
    win32_handler_parity = (
        len(win32_kinds) == 25
        and all(kind in handlers for kind in win32_kinds)
        and all(handlers[kind].build is not None for kind in NATIVE_CONTROL_KINDS)
    )
    host_policy = BrowserHostPolicy(
        "https://ui.example.test", ("ui.example.test",), ("https://app.example.test",),
    ).as_dict()
    shared_host_policy = BrowserHostPolicy(
        "https://ui.example.test", ("ui.example.test",), ("https://app.example.test",),
        session_storage="SQLITE_WAL_SHARED",
    ).as_dict()
    bindings = binding_manifest()
    web = web_manifest()
    accessibility = accessibility_witness()
    localization = localization_evidence(build_sufficiency_payload())
    custody = session_custody_witness()
    negotiation = negotiate_protocol((PROTOCOL_SCHEMA,))
    try:
        negotiate_protocol(("mosaic.ui.realizer-protocol.v9.9",))
        unsupported_protocol = {"status": "FAIL_OPEN"}
    except RealizerRefusal as exc:
        unsupported_protocol = {"status": "REFUSE", "refusal_code": exc.code}

    runtime = GovernedRuntime(
        build_payload(), (), catalog=catalog,
        receipt_policy=ReceiptRetentionPolicy(max_in_memory=2, checkpoint_interval=2, max_checkpoints=2),
    )
    for _ in range(4):
        runtime.dispatch({"intent": "ACTIVATE", "node_id": "release.show"})
    ledger = runtime.ledger.summary()
    receipt_bounded = (
        ledger["total_count"] == 4 and ledger["retained_count"] == 2
        and ledger["compacted_count"] == 2 and len(ledger["checkpoints"]) == 2
    )

    manager = BrowserSessionManager(build_sufficiency_payload(), catalog=catalog, max_sessions=2)
    try:
        first = manager.create_session()
        second = manager.create_session()
        second_before = second.realizer.snapshot()["commitment"]
        manager.apply_session(
            first.session_id, first.token, 1,
            {"intent": "SELECT", "node_id": "suff.menu", "value": "View"},
        )
        isolated = second.realizer.snapshot()["commitment"] == second_before \
            and first.realizer.snapshot()["values"]["suff.menu"] == "View"
        try:
            manager.apply_session(first.session_id, first.token, 1, {
                "intent": "SELECT", "node_id": "suff.menu", "value": "File",
            })
            replay = {"status": "FAIL_OPEN"}
        except UIRefusal as exc:
            replay = {"status": "REFUSE", "refusal_code": exc.code}
        try:
            manager.get_session(first.session_id, "invalid-token")
            token_check = {"status": "FAIL_OPEN"}
        except UIRefusal as exc:
            token_check = {"status": "REFUSE", "refusal_code": exc.code}
        manager.create_session()
        session_evidence = manager.evidence()
    finally:
        manager.close()

    with tempfile.TemporaryDirectory(prefix="mosaic-ui-shared-session-") as raw:
        database = Path(raw) / "sessions.db"
        first_manager = BrowserSessionManager(build_sufficiency_payload(), catalog=catalog, session_database=database)
        second_manager = BrowserSessionManager(build_sufficiency_payload(), catalog=catalog, session_database=database)
        try:
            shared_session = first_manager.create_session("architecture")
            shared_state, shared_next = second_manager.apply_session(
                shared_session.session_id, shared_session.token, 1,
                {"intent": "SELECT", "node_id": "suff.menu", "value": "View"}, "architecture",
            )
            shared_continuity = shared_state["values"]["suff.menu"] == "View" \
                and first_manager.get_session(
                    shared_session.session_id, shared_session.token, "architecture",
                ).realizer.snapshot()["values"]["suff.menu"] == "View"
            try:
                first_manager.apply_session(
                    shared_session.session_id, shared_session.token, 1,
                    {"intent": "SELECT", "node_id": "suff.menu", "value": "File"}, "architecture",
                )
                shared_replay = {"status": "FAIL_OPEN"}
            except UIRefusal as exc:
                shared_replay = {"status": "REFUSE", "refusal_code": exc.code}
            shared_store_evidence = first_manager.session_store.evidence()
        finally:
            first_manager.close()
            second_manager.close()
        restarted_manager = BrowserSessionManager(
            build_sufficiency_payload(), catalog=catalog, session_database=database,
        )
        try:
            rotated = restarted_manager.get_session(shared_session.session_id, owner_id="architecture")
            restart_continuity = rotated.realizer.snapshot()["values"]["suff.menu"] == "View" \
                and rotated.next_sequence == shared_next and rotated.token != shared_session.token
        finally:
            restarted_manager.close()

    checks = {
        "EXPLICIT_CATALOG": catalog_validation["disposition"],
        "PROTOCOL_NEGOTIATION": negotiation["disposition"],
        "UNSUPPORTED_PROTOCOL": "PASS" if unsupported_protocol["status"] == "REFUSE" else "FAIL",
        "BOUNDED_RECEIPTS": "PASS" if receipt_bounded else "FAIL",
        "SESSION_ISOLATION": "PASS" if isolated else "FAIL",
        "SESSION_REPLAY_REFUSAL": "PASS" if replay["status"] == "REFUSE" else "FAIL",
        "SESSION_TOKEN_REFUSAL": "PASS" if token_check["status"] == "REFUSE" else "FAIL",
        "SESSION_COUNT_BOUND": "PASS" if session_evidence["active_session_count"] == 2 else "FAIL",
        "SHARED_SESSION_STORAGE": "PASS" if shared_store_evidence["backend"] == "SQLITE_WAL" else "FAIL",
        "CROSS_WORKER_SESSION_CONTINUITY": "PASS" if shared_continuity else "FAIL",
        "SHARED_SESSION_REPLAY_REFUSAL": "PASS" if shared_replay["status"] == "REFUSE" else "FAIL",
        "SESSION_RESTART_CONTINUITY": "PASS" if restart_continuity else "FAIL",
        "SESSION_STORAGE_READINESS": "PASS" if custody["checks"]["SOURCE_READY"] else "FAIL",
        "SESSION_BACKUP_VERIFICATION": "PASS" if custody["checks"]["BACKUP_VERIFIED"] else "FAIL",
        "SESSION_BACKUP_RESTORE_CONTINUITY": "PASS" if custody["checks"]["STATE_RECOVERED"] else "FAIL",
        "PERFORMANCE_EVIDENCE_BOUND": "PASS",
        "WIN32_25_KIND_HANDLER_PARITY": "PASS" if win32_handler_parity else "FAIL",
        "DEPLOYABLE_BROWSER_HOST_POLICY": "PASS" if host_policy["secure_cookies"] else "FAIL",
        "SOVEREIGN_WEB_DISTRIBUTION": "PASS" if not web["runtime_dependencies"] and not web["framework_dependencies"] else "FAIL",
        "OPTIONAL_FRAMEWORK_ADAPTER_BOUNDARY": "PASS" if bindings["canonical_runtime"] is False else "FAIL",
        "ACCESSIBILITY_CONTRACT": "PASS" if accessibility["disposition"] == "PASS_LOCAL_CANDIDATE" else "FAIL",
        "LOCALIZATION_RTL_CONTRACT": "PASS" if localization["disposition"] == "PASS_LOCAL_CANDIDATE" else "FAIL",
    }
    passed = all(value in {"PASS", "PASS_LOCAL_CANDIDATE"} for value in checks.values())
    value = {
        "schema": "mosaic.ui.architecture-readiness-evidence.v0.1",
        "checks": checks,
        "catalog_validation": catalog_validation,
        "protocol_negotiation": negotiation,
        "unsupported_protocol": unsupported_protocol,
        "receipt_ledger": ledger,
        "browser_sessions": session_evidence,
        "shared_session_store": shared_store_evidence,
        "shared_session_replay": shared_replay,
        "session_custody_evidence_commitment": custody["commitment"],
        "replay_refusal": replay,
        "token_refusal": token_check,
        "performance_evidence_commitment": performance_evidence_commitment,
        "win32_realized_kinds": win32_kinds,
        "browser_host_policy": host_policy,
        "shared_browser_host_policy": shared_host_policy,
        "web_distribution": web,
        "compatibility_adapters": bindings,
        "accessibility_evidence_commitment": accessibility["commitment"],
        "localization_evidence_commitment": localization["commitment"],
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "LOCALIZATION_AND_SQLITE EVIDENCE DO NOT ESTABLISH HUMAN_TRANSLATION QUALITY MULTI_HOST DISTRIBUTED SCALE EXTERNAL ACCEPTANCE OR ADMISSION",
    }
    value["commitment"] = commitment("MOSAIC.UI.ARCHITECTURE_READINESS_EVIDENCE.v0.1", value)
    if output is not None:
        atomic_write(output.resolve(), canonical_bytes(value) + b"\n")
    return value


__all__ = ["architecture_witness"]
