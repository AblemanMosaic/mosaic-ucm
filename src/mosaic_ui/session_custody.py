"""Consistent backup and verification for sovereign browser-session custody."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .browser_session_store import MAX_SNAPSHOT_BYTES, SCHEMA
from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal


SESSION_COLUMNS = (
    "session_id", "token_digest", "owner_id", "snapshot_json", "snapshot_commitment",
    "next_sequence", "created_epoch", "expires_epoch", "last_access_epoch",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _connect(path: Path, *, readonly: bool) -> sqlite3.Connection:
    try:
        if readonly:
            connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5.0)
        else:
            connection = sqlite3.connect(path.resolve(), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
    except sqlite3.Error as exc:
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", type(exc).__name__) from exc


def _validate_connection(connection: sqlite3.Connection) -> dict[str, Any]:
    try:
        integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "INTEGRITY_CHECK")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        binding_root = metadata.get("binding_root", "")
        if set(metadata) != {"schema", "binding_root"} or metadata.get("schema") != SCHEMA \
                or len(binding_root) != 64 or any(c not in "0123456789abcdef" for c in binding_root):
            raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "METADATA")
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(sessions)"))
        if columns != SESSION_COLUMNS:
            raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SESSION_SCHEMA")
        rows = list(connection.execute("SELECT * FROM sessions ORDER BY session_id"))
        for row in rows:
            session_id, token_digest = str(row["session_id"]), str(row["token_digest"])
            owner_id = row["owner_id"]
            raw = bytes(row["snapshot_json"])
            if not 16 <= len(session_id) <= 128 \
                    or len(token_digest) != 64 or any(c not in "0123456789abcdef" for c in token_digest) \
                    or (owner_id is not None and (not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256)) \
                    or len(raw) > MAX_SNAPSHOT_BYTES:
                raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SESSION_ROW")
            try:
                snapshot = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SNAPSHOT_ENCODING") from exc
            if not isinstance(snapshot, dict) or commitment(
                "MOSAIC.UI.SQLITE_SESSION_SNAPSHOT.v0.1", snapshot,
            ) != row["snapshot_commitment"]:
                raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SNAPSHOT_COMMITMENT")
            sequence = row["next_sequence"]
            times = tuple(float(row[name]) for name in ("created_epoch", "last_access_epoch", "expires_epoch"))
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 \
                    or not all(math.isfinite(value) for value in times) \
                    or not times[0] <= times[1] <= times[2]:
                raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SESSION_TIMELINE")
        return {"binding_root": binding_root, "session_count": len(rows), "integrity_check": "ok"}
    except sqlite3.Error as exc:
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", type(exc).__name__) from exc


def verify_session_backup(path: Path) -> dict[str, Any]:
    database = path.resolve()
    if not database.is_file() or database.stat().st_size <= 0:
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "DATABASE_ABSENT")
    connection = _connect(database, readonly=True)
    try:
        validation = _validate_connection(connection)
    finally:
        connection.close()
    value = {
        "schema": "mosaic.ui.browser-session-backup-verification.v0.1",
        "database": {"name": database.name, "bytes": database.stat().st_size, "sha256": _sha256(database)},
        **validation,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "STANDALONE_SQLITE_BACKUP_INTEGRITY_DOES_NOT ESTABLISH RESTORE_OPERATIONS_OR_MULTI_HOST_DURABILITY",
    }
    value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_BACKUP_VERIFICATION.v0.1", value)
    return value


def backup_session_database(source: Path, destination: Path) -> dict[str, Any]:
    source, destination = source.resolve(), destination.resolve()
    if source == destination:
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SOURCE_EQUALS_DESTINATION")
    if not source.is_file():
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "SOURCE_ABSENT")
    if destination.exists():
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "DESTINATION_EXISTS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{secrets.token_hex(8)}.tmp")
    source_connection = _connect(source, readonly=True)
    try:
        source_validation = _validate_connection(source_connection)
        target = _connect(temporary, readonly=False)
        try:
            source_connection.backup(target)
            target.commit()
        finally:
            target.close()
        verification = verify_session_backup(temporary)
        if verification["binding_root"] != source_validation["binding_root"]:
            raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", "BINDING_ROOT_CHANGED")
        os.replace(temporary, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
    except (sqlite3.Error, OSError) as exc:
        raise UIRefusal("BROWSER_SESSION_BACKUP_REFUSED", type(exc).__name__) from exc
    finally:
        source_connection.close()
        if temporary.exists():
            temporary.unlink()
    verified = verify_session_backup(destination)
    value = {
        "schema": "mosaic.ui.browser-session-backup.v0.1",
        "backup": verified["database"],
        "binding_root": verified["binding_root"],
        "session_count": verified["session_count"],
        "verification_commitment": verified["commitment"],
        "copy_semantics": "SQLITE_ONLINE_BACKUP_TO_ATOMIC_DESTINATION",
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "ONE_BACKUP_OPERATION_DOES_NOT ESTABLISH SCHEDULED_RETENTION_OFF_HOST_REPLICATION_OR_DISASTER_RECOVERY",
    }
    value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_BACKUP.v0.1", value)
    return value


def session_custody_witness(*, output: Path | None = None) -> dict[str, Any]:
    from .browser_realizer import BrowserSessionManager
    from .sufficiency import build_sufficiency_payload

    with tempfile.TemporaryDirectory(prefix="mosaic-ui-session-custody-") as raw:
        root = Path(raw)
        source, backup = root / "sessions.db", root / "sessions.backup.db"
        manager = BrowserSessionManager(build_sufficiency_payload(), session_database=source)
        try:
            session = manager.create_session("custody-witness")
            state, next_sequence = manager.apply_session(
                session.session_id, session.token, 1,
                {"intent": "SELECT", "node_id": "suff.menu", "value": "View"}, "custody-witness",
            )
            readiness = manager.readiness()
            backup_receipt = backup_session_database(source, backup)
        finally:
            manager.close()
        verification = verify_session_backup(backup)
        restored = BrowserSessionManager(build_sufficiency_payload(), session_database=backup)
        try:
            recovered = restored.get_session(session.session_id, session.token, "custody-witness")
            recovery = {
                "selected_value": recovered.realizer.snapshot()["values"]["suff.menu"],
                "next_sequence": recovered.next_sequence,
                "token_digest_only": session.token not in backup.read_bytes().decode("latin1"),
            }
        finally:
            restored.close()
    checks = {
        "SOURCE_READY": readiness["disposition"] == "PASS_LOCAL_CANDIDATE",
        "BACKUP_VERIFIED": verification["disposition"] == "PASS_LOCAL_CANDIDATE",
        "BINDING_PRESERVED": backup_receipt["binding_root"] == verification["binding_root"],
        "STATE_RECOVERED": state["values"]["suff.menu"] == recovery["selected_value"] == "View",
        "SEQUENCE_RECOVERED": next_sequence == recovery["next_sequence"] == 2,
        "PLAINTEXT_TOKEN_ABSENT": recovery["token_digest_only"],
    }
    value = {
        "schema": "mosaic.ui.browser-session-custody-evidence.v0.1",
        "checks": checks,
        "backup_commitment": backup_receipt["commitment"],
        "verification_commitment": verification["commitment"],
        "session_count": verification["session_count"],
        "recovery": recovery,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "LOCAL_BACKUP_AND_RESTORE_WITNESS_DOES_NOT ESTABLISH SCHEDULED_OFF_HOST_BACKUP_RPO_RTO_OR_MULTI_HOST_DURABILITY",
    }
    value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_CUSTODY_EVIDENCE.v0.1", value)
    if output is not None:
        atomic_write(output.resolve(), canonical_bytes(value) + b"\n")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("source", type=Path)
    backup.add_argument("destination", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("database", type=Path)
    args = parser.parse_args(argv)
    try:
        result = backup_session_database(args.source, args.destination) if args.command == "backup" \
            else verify_session_backup(args.database)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    except (UIRefusal, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({
            "schema": "mosaic.ui.browser-session-custody-refusal.v0.1", "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "BROWSER_SESSION_BACKUP_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE",
        }, indent=2))
        return 32


__all__ = ["backup_session_database", "session_custody_witness", "verify_session_backup"]


if __name__ == "__main__":
    raise SystemExit(main())
