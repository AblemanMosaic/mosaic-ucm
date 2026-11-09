"""Sovereign SQLite storage for shared, replay-resistant browser sessions."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .canonical import canonical_bytes, commitment
from .model import UIRefusal


SCHEMA = "mosaic.ui.sqlite-browser-session-store.v0.1"
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class StoredBrowserSession:
    session_id: str
    token: str
    owner_id: str | None
    snapshot: dict[str, Any]
    next_sequence: int
    created_epoch: float
    expires_epoch: float
    last_access_epoch: float


class SQLiteBrowserSessionStore:
    """Coordinate session custody across workers with SQLite write transactions."""

    def __init__(self, path: Path, binding_root: str, *, timeout_seconds: float = 5.0) -> None:
        self.path = path.resolve()
        if not binding_root or len(binding_root) != 64 or any(c not in "0123456789abcdef" for c in binding_root):
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "BINDING_ROOT")
        if timeout_seconds <= 0 or timeout_seconds > 60:
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "TIMEOUT")
        self.binding_root = binding_root
        self.timeout_seconds = float(timeout_seconds)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _snapshot_bytes(snapshot: dict[str, Any]) -> bytes:
        raw = canonical_bytes(snapshot)
        if len(raw) > MAX_SNAPSHOT_BYTES:
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "SNAPSHOT_SIZE")
        return raw

    @staticmethod
    def _validate_access(session_id: str, token: str | None, owner_id: str | None) -> None:
        if not isinstance(session_id, str) or not 16 <= len(session_id) <= 128:
            raise UIRefusal("BROWSER_SESSION_REFUSED", "SESSION_ID")
        if token is not None and (not isinstance(token, str) or not 24 <= len(token) <= 256):
            raise UIRefusal("BROWSER_SESSION_REFUSED", "TOKEN")
        if owner_id is not None and (not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256):
            raise UIRefusal("BROWSER_SESSION_REFUSED", "OWNER")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path, timeout=self.timeout_seconds, isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        try:
            connection = self._connect()
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        token_digest TEXT NOT NULL,
                        owner_id TEXT,
                        snapshot_json BLOB NOT NULL,
                        snapshot_commitment TEXT NOT NULL,
                        next_sequence INTEGER NOT NULL CHECK(next_sequence >= 1),
                        created_epoch REAL NOT NULL,
                        expires_epoch REAL NOT NULL,
                        last_access_epoch REAL NOT NULL
                    )
                """)
                existing = dict(connection.execute("SELECT key, value FROM metadata"))
                wanted = {"schema": SCHEMA, "binding_root": self.binding_root}
                if existing and existing != wanted:
                    raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "DATABASE_BINDING_MISMATCH")
                for key, value in wanted.items():
                    connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", (key, value))
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        except sqlite3.Error as exc:
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", type(exc).__name__) from exc

    @staticmethod
    def _prune(connection: sqlite3.Connection, now: float) -> int:
        return connection.execute("DELETE FROM sessions WHERE expires_epoch <= ?", (now,)).rowcount

    def _decode(self, row: sqlite3.Row, token: str) -> StoredBrowserSession:
        try:
            raw = bytes(row["snapshot_json"])
            snapshot = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "SNAPSHOT_ENCODING") from exc
        if not isinstance(snapshot, dict) \
                or commitment("MOSAIC.UI.SQLITE_SESSION_SNAPSHOT.v0.1", snapshot) != row["snapshot_commitment"]:
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "SNAPSHOT_COMMITMENT")
        return StoredBrowserSession(
            str(row["session_id"]), token, row["owner_id"], snapshot, int(row["next_sequence"]),
            float(row["created_epoch"]), float(row["expires_epoch"]), float(row["last_access_epoch"]),
        )

    @staticmethod
    def _owner_matches(row: sqlite3.Row, owner_id: str | None) -> bool:
        return row["owner_id"] == owner_id

    def create(
        self, owner_id: str | None, snapshot: dict[str, Any], *, ttl_seconds: int, max_sessions: int,
    ) -> StoredBrowserSession:
        if owner_id is not None and (not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256):
            raise UIRefusal("BROWSER_SESSION_REFUSED", "OWNER")
        now = time.time()
        session_id, token = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
        raw = self._snapshot_bytes(snapshot)
        snapshot_root = commitment("MOSAIC.UI.SQLITE_SESSION_SNAPSHOT.v0.1", snapshot)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._prune(connection, now)
            count = int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
            if count >= max_sessions:
                connection.execute(
                    "DELETE FROM sessions WHERE session_id IN (SELECT session_id FROM sessions ORDER BY last_access_epoch, session_id LIMIT ?)",
                    (count - max_sessions + 1,),
                )
            connection.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (session_id, self._token_digest(token), owner_id, raw, snapshot_root, 1,
                 now, now + ttl_seconds, now),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            return self._decode(row, token)
        except sqlite3.Error as exc:
            connection.rollback()
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", type(exc).__name__) from exc
        finally:
            connection.close()

    def load(
        self, session_id: str, token: str | None, owner_id: str | None, *, ttl_seconds: int,
    ) -> StoredBrowserSession:
        self._validate_access(session_id, token, owner_id)
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._prune(connection, now)
            row = connection.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            if row is None:
                raise UIRefusal("BROWSER_SESSION_REFUSED", "ABSENT_OR_EXPIRED")
            if not self._owner_matches(row, owner_id):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "OWNER_MISMATCH")
            current_token = token
            if token is None:
                current_token = secrets.token_urlsafe(32)
                connection.execute(
                    "UPDATE sessions SET token_digest=? WHERE session_id=?",
                    (self._token_digest(current_token), session_id),
                )
            elif not hmac.compare_digest(str(row["token_digest"]), self._token_digest(token)):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "TOKEN_MISMATCH")
            connection.execute(
                "UPDATE sessions SET last_access_epoch=?, expires_epoch=? WHERE session_id=?",
                (now, now + ttl_seconds, session_id),
            )
            connection.commit()
            updated = connection.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            return self._decode(updated, str(current_token))
        except UIRefusal:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", type(exc).__name__) from exc
        finally:
            connection.close()

    def mutate(
        self, session_id: str, token: str, owner_id: str | None, sequence: int,
        mutator: Callable[[dict[str, Any]], tuple[dict[str, Any], Any]], *, ttl_seconds: int,
    ) -> tuple[StoredBrowserSession, Any]:
        self._validate_access(session_id, token, owner_id)
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise UIRefusal("BROWSER_EVENT_SEQUENCE_REFUSED", str(sequence))
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._prune(connection, now)
            row = connection.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            if row is None:
                raise UIRefusal("BROWSER_SESSION_REFUSED", "ABSENT_OR_EXPIRED")
            if not self._owner_matches(row, owner_id):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "OWNER_MISMATCH")
            if not hmac.compare_digest(str(row["token_digest"]), self._token_digest(token)):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "TOKEN_MISMATCH")
            if int(row["next_sequence"]) != sequence:
                raise UIRefusal("BROWSER_EVENT_SEQUENCE_REFUSED", f"{sequence}!={row['next_sequence']}")
            stored = self._decode(row, token)
            snapshot, result = mutator(stored.snapshot)
            raw = self._snapshot_bytes(snapshot)
            snapshot_root = commitment("MOSAIC.UI.SQLITE_SESSION_SNAPSHOT.v0.1", snapshot)
            connection.execute(
                "UPDATE sessions SET snapshot_json=?,snapshot_commitment=?,next_sequence=?,last_access_epoch=?,expires_epoch=? WHERE session_id=?",
                (raw, snapshot_root, sequence + 1, now, now + ttl_seconds, session_id),
            )
            connection.commit()
            updated = connection.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            return self._decode(updated, token), result
        except UIRefusal:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", type(exc).__name__) from exc
        finally:
            connection.close()

    def evidence(self) -> dict[str, Any]:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._prune(connection, now)
            count = int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
            mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).upper()
            connection.commit()
        finally:
            connection.close()
        value = {
            "schema": "mosaic.ui.browser-session-store-evidence.v0.1",
            "backend": "SQLITE_WAL", "active_session_count": count,
            "journal_mode": mode, "token_storage": "SHA256_DIGEST",
            "transaction_mode": "BEGIN_IMMEDIATE", "binding_root": self.binding_root,
            "max_snapshot_bytes": MAX_SNAPSHOT_BYTES,
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_STORE_EVIDENCE.v0.1", value)
        return value

    def readiness(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            integrity = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            ready = integrity == ["ok"] and metadata == {"schema": SCHEMA, "binding_root": self.binding_root}
        except sqlite3.Error as exc:
            raise UIRefusal("BROWSER_SESSION_STORE_NOT_READY", type(exc).__name__) from exc
        finally:
            connection.close()
        if not ready:
            raise UIRefusal("BROWSER_SESSION_STORE_NOT_READY", "INTEGRITY_OR_BINDING")
        value = {
            "schema": "mosaic.ui.browser-session-store-readiness.v0.1",
            "backend": "SQLITE_WAL", "integrity_check": "ok",
            "binding_root": self.binding_root, "disposition": "PASS_LOCAL_CANDIDATE",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_STORE_READINESS.v0.1", value)
        return value

    def close(self) -> None:
        return None


__all__ = ["MAX_SNAPSHOT_BYTES", "SQLiteBrowserSessionStore", "StoredBrowserSession"]
