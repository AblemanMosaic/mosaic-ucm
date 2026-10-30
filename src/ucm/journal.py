"""Durable, append-only integration campaign journal.

The JSONL history is the source of truth.  HEAD.json is a recoverable projection;
if a crash occurs after the history rename but before the head rename, opening the
journal repairs the projection from the verified history without replaying an
external effect.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root, strict_loads


GENESIS = "0" * 64
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
EVENT_TYPES = {
    "CAMPAIGN_CREATED", "BASELINE_BOUND", "CONTRACT_COMPILED", "IDENTITY_IMPORTED",
    "CHALLENGE_ISSUED", "SESSION_AUTHENTICATED", "DELEGATION_RECORDED",
    "OPERATION_PLANNED", "SENTINEL_RECEIPTED", "WITNESS_RECORDED",
    "DIAGNOSTIC_RECORDED", "REQUIREMENT_DISPOSITIONED", "TEST_RECORDED",
    "PROOF_RECORDED", "FINDING_RECORDED", "ARTIFACT_RECORDED", "CHECKPOINT_CREATED",
    "REPORT_CREATED", "ARCHIVE_EXPORTED", "INTERRUPTION_RECORDED", "RECOVERY_RECORDED",
    "OPERATION_STATE_RECORDED", "OPERATION_CANCELLED", "OUTCOME_UNCERTAIN",
    "OPERATION_AUTHORIZED", "OPERATION_G1_RECORDED",
    "OPERATION_DISPATCH_PREPARED", "OPERATION_DISPATCH_RECORDED",
    "OPERATION_TERMINAL_RECORDED", "OPERATION_G3_RECORDED",
    "OPERATION_RECONCILED", "OPERATION_PROOF_RECORDED",
    "OPERATION_ARCHIVE_EXPORTED", "OPERATION_OUTCOME_UNCERTAIN",
}


class JournalRefusal(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise JournalRefusal(code)


def _fsync_directory(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise JournalRefusal("JOURNAL_LOCKED") from error
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.fsync(descriptor)
        os.close(descriptor)
        yield
    finally:
        try:
            os.unlink(path)
            _fsync_directory(path.parent)
        except FileNotFoundError:
            pass


def _validate_payload(value: Any) -> dict[str, Any]:
    _require(type(value) is dict, "JOURNAL_PAYLOAD_INVALID")
    canonical_bytes(value)
    return deepcopy(value)


def build_event(*, sequence: int, predecessor: str, event_id: str, event_type: str,
                actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _require(type(sequence) is int and sequence >= 1, "JOURNAL_SEQUENCE_INVALID")
    require_root(predecessor)
    _require(type(event_id) is str and 0 < len(event_id) <= 256, "JOURNAL_EVENT_ID_INVALID")
    _require(event_type in EVENT_TYPES, "JOURNAL_EVENT_TYPE_INVALID")
    actor = exact_keys(actor, {"kind", "mosaic_id", "session_id"})
    _require(actor["kind"] in {"USER", "AGENT", "SYSTEM", "REVIEWER"}, "JOURNAL_ACTOR_INVALID")
    _require(actor["mosaic_id"] is None or
             (type(actor["mosaic_id"]) is str and len(actor["mosaic_id"]) == 64),
             "JOURNAL_ACTOR_ID_INVALID")
    _require(actor["session_id"] is None or
             (type(actor["session_id"]) is str and len(actor["session_id"]) == 64),
             "JOURNAL_SESSION_ID_INVALID")
    body = {
        "schema": "mosaic.ucm.integration-journal-event.v0.1",
        "sequence": sequence, "predecessor": predecessor, "event_id": event_id,
        "event_type": event_type, "actor": deepcopy(actor),
        "payload": _validate_payload(payload), **BOUNDARY,
    }
    return {**body, "event_root": root(body)}


def verify_event(value: Any, *, sequence: int, predecessor: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "sequence", "predecessor", "event_id", "event_type", "actor", "payload",
        "standing", "authority_effect", "real_a5", "g0", "event_root",
    })
    expected = build_event(sequence=sequence, predecessor=predecessor,
                           event_id=item["event_id"], event_type=item["event_type"],
                           actor=item["actor"], payload=item["payload"])
    _require(item == expected, "JOURNAL_EVENT_INVALID")
    return deepcopy(item)


class CampaignJournal:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.events_path = self.directory / "EVENTS.jsonl"
        self.head_path = self.directory / "HEAD.json"
        self.lock_path = self.directory / ".journal.lock"

    def initialize(self) -> dict[str, Any]:
        self.directory.mkdir(parents=True, exist_ok=True)
        _require(not self.events_path.exists() and not self.head_path.exists(),
                 "JOURNAL_ALREADY_EXISTS")
        _write_atomic(self.events_path, b"")
        head = self._head_record([])
        _write_atomic(self.head_path, canonical_bytes(head))
        return head

    def recover_stale_lock(self, *, expected_head: str) -> dict[str, Any]:
        """Remove a lock only after custody is intact and its recorded PID is gone."""
        require_root(expected_head)
        _require(self.lock_path.exists(), "JOURNAL_LOCK_NOT_PRESENT")
        try:
            pid = int(self.lock_path.read_text(encoding="ascii").strip())
        except (OSError, UnicodeError, ValueError) as error:
            raise JournalRefusal("JOURNAL_LOCK_RECORD_INVALID") from error
        _require(pid > 0 and not _pid_alive(pid), "JOURNAL_LOCK_OWNER_ACTIVE")
        events = self.verify()
        actual = events[-1]["event_root"] if events else GENESIS
        _require(actual == expected_head, "JOURNAL_RECOVERY_HEAD_MISMATCH")
        try:
            self.lock_path.unlink()
            _fsync_directory(self.directory)
        except OSError as error:
            raise JournalRefusal("JOURNAL_LOCK_RECOVERY_FAILED") from error
        return self._head_record(events)

    def _read_lines(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            raise JournalRefusal("JOURNAL_MISSING")
        try:
            raw = self.events_path.read_bytes()
        except OSError as error:
            raise JournalRefusal("JOURNAL_UNREADABLE") from error
        _require(not raw or raw.endswith(b"\n"), "JOURNAL_TRUNCATED")
        rows = []
        for line in raw.splitlines():
            _require(bool(line), "JOURNAL_EMPTY_ROW")
            rows.append(strict_loads(line))
        return rows

    def verify(self) -> list[dict[str, Any]]:
        rows = self._read_lines()
        predecessor = GENESIS
        seen_ids: dict[str, str] = {}
        verified = []
        for sequence, row in enumerate(rows, 1):
            event = verify_event(row, sequence=sequence, predecessor=predecessor)
            if event["event_id"] in seen_ids:
                _require(seen_ids[event["event_id"]] == event["event_root"],
                         "JOURNAL_IDEMPOTENCY_CONFLICT")
            seen_ids[event["event_id"]] = event["event_root"]
            verified.append(event)
            predecessor = event["event_root"]
        expected_head = self._head_record(verified)
        if not self.head_path.exists() or strict_loads(self.head_path.read_bytes()) != expected_head:
            _write_atomic(self.head_path, canonical_bytes(expected_head))
        return verified

    def _head_record(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        body = {
            "schema": "mosaic.ucm.integration-journal-head.v0.1",
            "sequence": len(events),
            "head": events[-1]["event_root"] if events else GENESIS,
            "events_sha256": __import__("hashlib").sha256(
                b"".join(canonical_bytes(row) + b"\n" for row in events)).hexdigest(),
            **BOUNDARY,
        }
        return {**body, "root": root(body)}

    def head(self) -> dict[str, Any]:
        return self._head_record(self.verify())

    def append(self, *, event_id: str, event_type: str, actor: dict[str, Any],
               payload: dict[str, Any], expected_head: str | None = None) -> dict[str, Any]:
        with _exclusive_lock(self.lock_path):
            events = self.verify()
            current = events[-1]["event_root"] if events else GENESIS
            # A retry is identified by its logical request, not by the sequence
            # and predecessor that would be allocated to a new event.  Looking
            # up the event before allocating those chain fields makes a
            # byte-identical lost-response retry truly idempotent.
            for existing in events:
                if existing["event_id"] == event_id:
                    _require(existing["event_type"] == event_type
                             and existing["actor"] == actor
                             and existing["payload"] == _validate_payload(payload),
                             "JOURNAL_IDEMPOTENCY_CONFLICT")
                    return deepcopy(existing)
            if expected_head is not None:
                _require(current == require_root(expected_head), "JOURNAL_HEAD_CHANGED")
            candidate = build_event(sequence=len(events) + 1, predecessor=current,
                                    event_id=event_id, event_type=event_type,
                                    actor=actor, payload=payload)
            updated = [*events, candidate]
            _write_atomic(self.events_path,
                          b"".join(canonical_bytes(row) + b"\n" for row in updated))
            _write_atomic(self.head_path, canonical_bytes(self._head_record(updated)))
            return deepcopy(candidate)

    def checkpoint(self) -> dict[str, Any]:
        events = self.verify()
        counts: dict[str, int] = {}
        for event in events:
            counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1
        body = {
            "schema": "mosaic.ucm.integration-checkpoint.v0.1",
            "head": self._head_record(events), "event_type_counts": counts,
            "open_operations": _open_operation_ids(events), **BOUNDARY,
        }
        return {**body, "checkpoint_root": root(body)}


def _open_operation_ids(events: list[dict[str, Any]]) -> list[str]:
    states: dict[str, str] = {}
    for event in events:
        operation_id = event["payload"].get("operation_id")
        if type(operation_id) is str:
            states[operation_id] = event["event_type"]
    terminal = {"DIAGNOSTIC_RECORDED", "OPERATION_G3_RECORDED",
                "OPERATION_CANCELLED"}
    return sorted(operation_id for operation_id, state in states.items() if state not in terminal)


def _pid_alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
