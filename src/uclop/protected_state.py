from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root, strict_loads
from .custody import OpaqueEd25519KeyStore, verify_asymmetric

STATE_DOMAIN = "UCL_UCM_PROTECTED_MONOTONIC_STATE_V2"


def _anchor_record(sequence: int, head: str, journal_sequence: int, journal_head: str) -> dict[str, Any]:
    require(type(sequence) is int and type(sequence) is not bool and sequence >= 0, "MONOTONIC_ANCHOR_SEQUENCE_INVALID")
    require(type(journal_sequence) is int and type(journal_sequence) is not bool and journal_sequence >= 0, "MONOTONIC_JOURNAL_SEQUENCE_INVALID")
    require(sequence == journal_sequence, "MONOTONIC_STATE_JOURNAL_SEQUENCE_MISMATCH")
    require(head == "GENESIS" if sequence == 0 else bool(require_root(head)), "MONOTONIC_ANCHOR_HEAD_INVALID")
    require(journal_head == "GENESIS" if journal_sequence == 0 else bool(require_root(journal_head)), "MONOTONIC_JOURNAL_HEAD_INVALID")
    return {
        "schema": "ucl.ucm.monotonic_anchor.v2", "sequence": sequence, "head": head,
        "journal_sequence": journal_sequence, "journal_head": journal_head,
    }


class InMemoryMonotonicAnchor:
    def __init__(self) -> None:
        self.record = _anchor_record(0, "GENESIS", 0, "GENESIS")

    def observe(self) -> tuple[int, str]:
        return self.record["sequence"], self.record["head"]

    def observe_record(self) -> dict[str, Any]:
        return dict(self.record)

    def advance(self, *, expected_sequence: int, expected_head: str, next_sequence: int, next_head: str) -> None:
        self.advance_bound(
            expected=self.record,
            successor=_anchor_record(next_sequence, next_head, next_sequence, self.record["journal_head"]),
        )

    def advance_bound(self, *, expected: dict[str, Any], successor: dict[str, Any]) -> None:
        require(self.record == expected, "MONOTONIC_ANCHOR_CONFLICT")
        checked = _anchor_record(successor["sequence"], successor["head"], successor["journal_sequence"], successor["journal_head"])
        require(checked["sequence"] == expected["sequence"] + 1, "MONOTONIC_SEQUENCE_INVALID")
        self.record = checked


class FileMonotonicAnchor:
    """Atomic anchor binding the state head and the complete journal head."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(_anchor_record(0, "GENESIS", 0, "GENESIS"))

    def _read(self) -> dict[str, Any]:
        value = strict_loads(self.path.read_bytes())
        item = exact_keys(value, {"schema", "sequence", "head", "journal_sequence", "journal_head"}, "$.anchor")
        require(item["schema"] == "ucl.ucm.monotonic_anchor.v2", "MONOTONIC_ANCHOR_SCHEMA_INVALID")
        return _anchor_record(item["sequence"], item["head"], item["journal_sequence"], item["journal_head"])

    def _write(self, value: dict[str, Any]) -> None:
        pending = self.path.with_name("." + self.path.name + ".pending")
        pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        with pending.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(pending, self.path)

    def observe(self) -> tuple[int, str]:
        item = self._read()
        return item["sequence"], item["head"]

    def observe_record(self) -> dict[str, Any]:
        return self._read()

    def advance(self, *, expected_sequence: int, expected_head: str, next_sequence: int, next_head: str) -> None:
        current = self._read()
        successor = _anchor_record(next_sequence, next_head, next_sequence, current["journal_head"])
        self.advance_bound(expected=current, successor=successor)

    def advance_bound(self, *, expected: dict[str, Any], successor: dict[str, Any]) -> None:
        current = self._read()
        require(current == expected, "MONOTONIC_ANCHOR_CONFLICT")
        checked = _anchor_record(successor["sequence"], successor["head"], successor["journal_sequence"], successor["journal_head"])
        require(checked["sequence"] == expected["sequence"] + 1, "MONOTONIC_SEQUENCE_INVALID")
        self._write(checked)


class ProtectedStateStore:
    """Recoverable state/journal transaction bound to one monotonic anchor."""

    def __init__(self, directory: Path, *, anchor: InMemoryMonotonicAnchor | FileMonotonicAnchor, keys: OpaqueEd25519KeyStore, signing_handle: str) -> None:
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "state.json"
        self.journal_path = self.directory / "journal.jsonl"
        self.transaction_path = self.directory / ".commit-transaction.json"
        self.anchor = anchor
        self.keys = keys
        self.signing_handle = signing_handle
        self.identity = keys.identity(signing_handle)

    @staticmethod
    def _write_atomic(path: Path, data: bytes) -> None:
        pending = path.with_name("." + path.name + ".pending")
        pending.write_bytes(data)
        with pending.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(pending, path)

    def _verify_state(self, value: Any) -> dict[str, Any]:
        item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "state_root"}, "$.state")
        signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        body = verify_asymmetric(signed, STATE_DOMAIN, expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
        exact_keys(body, {"schema", "sequence", "predecessor", "payload", "payload_root", "standing", "authority_effect"}, "$.state.body")
        require(body["schema"] == "ucl.ucm.protected_monotonic_state.v2", "PROTECTED_STATE_SCHEMA_INVALID")
        require(item["state_root"] == root(signed), "PROTECTED_STATE_ROOT_MISMATCH")
        require(body["payload_root"] == root(body["payload"]), "PROTECTED_STATE_PAYLOAD_MISMATCH")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "PROTECTED_STATE_EFFECT_INVALID")
        return item

    def _journal_row(self, record: dict[str, Any], *, sequence: int, predecessor: str) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.protected_state_journal.v2", "sequence": sequence,
            "predecessor": predecessor, "state_root": record["state_root"],
            "state_sequence": record["body"]["sequence"], "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.keys.sign(self.signing_handle, STATE_DOMAIN + ":JOURNAL", body)
        return {**signed, "journal_root": root(signed)}

    def verify_journal(self, *, bind_anchor: bool = True) -> list[dict[str, Any]]:
        anchor = self.anchor.observe_record()
        if not self.journal_path.is_file():
            require(anchor["journal_sequence"] == 0 and anchor["journal_head"] == "GENESIS", "PROTECTED_JOURNAL_MISSING")
            return []
        rows: list[dict[str, Any]] = []
        predecessor = "GENESIS"
        for number, line in enumerate(self.journal_path.read_text(encoding="utf-8").splitlines(), 1):
            require(bool(line), "PROTECTED_JOURNAL_EMPTY_ROW")
            item = exact_keys(strict_loads(line.encode("utf-8")), {"body", "body_root", "signature", "key_root", "signature_algorithm", "journal_root"}, f"$.journal[{number}]")
            signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
            body = verify_asymmetric(signed, STATE_DOMAIN + ":JOURNAL", expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
            exact_keys(body, {"schema", "sequence", "predecessor", "state_root", "state_sequence", "standing", "authority_effect"}, f"$.journal[{number}].body")
            require(body["schema"] == "ucl.ucm.protected_state_journal.v2", "PROTECTED_JOURNAL_SCHEMA_INVALID")
            require(body["sequence"] == number and body["state_sequence"] == number, "PROTECTED_JOURNAL_SEQUENCE_INVALID")
            require(body["predecessor"] == predecessor, "PROTECTED_JOURNAL_PREDECESSOR_INVALID")
            require(item["journal_root"] == root(signed), "PROTECTED_JOURNAL_ROOT_INVALID")
            require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "PROTECTED_JOURNAL_EFFECT_INVALID")
            predecessor = item["journal_root"]
            rows.append(item)
        if bind_anchor:
            require(len(rows) == anchor["journal_sequence"], "PROTECTED_JOURNAL_ANCHOR_SEQUENCE_MISMATCH")
            require((rows[-1]["journal_root"] if rows else "GENESIS") == anchor["journal_head"], "PROTECTED_JOURNAL_ANCHOR_HEAD_MISMATCH")
            require((rows[-1]["body"]["state_root"] if rows else "GENESIS") == anchor["head"], "PROTECTED_JOURNAL_STATE_HEAD_MISMATCH")
        return rows

    def _record(self, payload: dict[str, Any], sequence: int, predecessor: str) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.protected_monotonic_state.v2", "sequence": sequence,
            "predecessor": predecessor, "payload": payload, "payload_root": root(payload),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        signed = self.keys.sign(self.signing_handle, STATE_DOMAIN, body)
        return {**signed, "state_root": root(signed)}

    def _transaction(self, record: dict[str, Any], row: dict[str, Any], old_anchor: dict[str, Any]) -> dict[str, Any]:
        successor = _anchor_record(
            record["body"]["sequence"], record["state_root"],
            row["body"]["sequence"], row["journal_root"],
        )
        body = {
            "schema": "ucl.ucm.protected_commit_transaction.v2",
            "old_anchor": old_anchor, "successor_anchor": successor,
            "state_record": record, "journal_row": row,
        }
        return {**body, "transaction_root": root(body)}

    def commit(self, payload: dict[str, Any], *, expected_sequence: int, expected_head: str, crash_at: str | None = None) -> dict[str, Any]:
        require(not self.transaction_path.exists(), "PROTECTED_COMMIT_RECOVERY_REQUIRED")
        old_anchor = self.anchor.observe_record()
        require((old_anchor["sequence"], old_anchor["head"]) == (expected_sequence, expected_head), "MONOTONIC_EXPECTATION_MISMATCH")
        rows = self.verify_journal()
        record = self._record(payload, expected_sequence + 1, expected_head)
        row = self._journal_row(record, sequence=len(rows) + 1, predecessor=rows[-1]["journal_root"] if rows else "GENESIS")
        transaction = self._transaction(record, row, old_anchor)
        self._write_atomic(self.transaction_path, (json.dumps(transaction, indent=2, sort_keys=True) + "\n").encode())
        if crash_at == "BEFORE_REPLACE":
            raise Refusal("SIMULATED_CRASH_BEFORE_REPLACE")
        self._write_atomic(self.path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
        if crash_at in {"AFTER_REPLACE_BEFORE_ANCHOR", "AFTER_STATE"}:
            raise Refusal("SIMULATED_CRASH_AFTER_STATE")
        journal_bytes = b"".join((json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n").encode() for item in [*rows, row])
        self._write_atomic(self.journal_path, journal_bytes)
        if crash_at == "AFTER_JOURNAL":
            raise Refusal("SIMULATED_CRASH_AFTER_JOURNAL")
        self.anchor.advance_bound(expected=old_anchor, successor=transaction["successor_anchor"])
        if crash_at == "AFTER_ANCHOR":
            raise Refusal("SIMULATED_CRASH_AFTER_ANCHOR")
        self.transaction_path.unlink()
        return record

    def load(self) -> dict[str, Any]:
        require(not self.transaction_path.exists(), "PROTECTED_COMMIT_RECOVERY_REQUIRED")
        require(self.path.is_file(), "PROTECTED_STATE_MISSING")
        record = self._verify_state(strict_loads(self.path.read_bytes()))
        anchor = self.anchor.observe_record()
        require(record["body"]["sequence"] == anchor["sequence"] and record["state_root"] == anchor["head"], "PROTECTED_STATE_ROLLBACK_OR_AHEAD")
        self.verify_journal()
        return record

    def _inspect_interrupted_commit(self) -> dict[str, Any]:
        require(self.transaction_path.is_file(), "PROTECTED_COMMIT_TRANSACTION_MISSING")
        transaction = strict_loads(self.transaction_path.read_bytes())
        item = exact_keys(transaction, {"schema", "old_anchor", "successor_anchor", "state_record", "journal_row", "transaction_root"}, "$.transaction")
        body = {key: item[key] for key in ("schema", "old_anchor", "successor_anchor", "state_record", "journal_row")}
        require(item["schema"] == "ucl.ucm.protected_commit_transaction.v2" and item["transaction_root"] == root(body), "PROTECTED_COMMIT_TRANSACTION_INVALID")
        record = self._verify_state(item["state_record"])
        row = item["journal_row"]
        signed = {key: row[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        verify_asymmetric(signed, STATE_DOMAIN + ":JOURNAL", expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
        require(row["journal_root"] == root(signed), "PROTECTED_JOURNAL_ROOT_INVALID")
        expected_transaction = self._transaction(record, row, item["old_anchor"])
        require(expected_transaction == item, "PROTECTED_COMMIT_TRANSACTION_BINDING_INVALID")
        old_anchor = item["old_anchor"]
        successor = item["successor_anchor"]
        require(record["body"]["sequence"] == old_anchor["sequence"] + 1, "PROTECTED_COMMIT_STATE_SEQUENCE_INVALID")
        require(record["body"]["predecessor"] == old_anchor["head"], "PROTECTED_COMMIT_STATE_PREDECESSOR_INVALID")
        require(row["body"]["sequence"] == old_anchor["journal_sequence"] + 1, "PROTECTED_COMMIT_JOURNAL_SEQUENCE_INVALID")
        require(row["body"]["state_sequence"] == record["body"]["sequence"], "PROTECTED_COMMIT_JOURNAL_STATE_SEQUENCE_INVALID")
        require(row["body"]["predecessor"] == old_anchor["journal_head"], "PROTECTED_COMMIT_JOURNAL_PREDECESSOR_INVALID")
        require(row["body"]["state_root"] == record["state_root"], "PROTECTED_COMMIT_JOURNAL_STATE_ROOT_INVALID")
        current = self.anchor.observe_record()
        require(current in (old_anchor, successor), "PROTECTED_COMMIT_ANCHOR_DIVERGED")

        # Read the journal without binding it to the current anchor.  During a
        # valid interrupted commit it may be either the old prefix or the old
        # prefix plus the transaction's new row.  Binding to the old anchor at
        # this point is precisely what made AFTER_JOURNAL unrecoverable once a
        # prior row existed.
        all_rows = self.verify_journal(bind_anchor=False) if self.journal_path.is_file() else []
        old_count = old_anchor["journal_sequence"]
        require(len(all_rows) in {old_count, old_count + 1}, "PROTECTED_JOURNAL_RECOVERY_LENGTH_INVALID")
        previous_rows = all_rows[:old_count]
        if old_count:
            require(len(previous_rows) == old_count, "PROTECTED_JOURNAL_RECOVERY_PREFIX_MISSING")
            require(previous_rows[-1]["journal_root"] == old_anchor["journal_head"], "PROTECTED_JOURNAL_RECOVERY_PREFIX_INVALID")
            require(previous_rows[-1]["body"]["state_root"] == old_anchor["head"], "PROTECTED_JOURNAL_RECOVERY_STATE_PREFIX_INVALID")
        else:
            require(old_anchor["journal_head"] == old_anchor["head"] == "GENESIS", "PROTECTED_JOURNAL_RECOVERY_GENESIS_INVALID")
        if len(all_rows) == old_count + 1:
            require(all_rows[-1] == row, "PROTECTED_JOURNAL_RECOVERY_PENDING_ROW_INVALID")
        if current == successor:
            require(len(all_rows) == old_count + 1, "PROTECTED_JOURNAL_RECOVERY_SUCCESSOR_ROW_MISSING")

        return {"transaction": item, "previous_rows": previous_rows}

    def inspect_interrupted_commit(self) -> dict[str, Any]:
        """Validate the exact pending signed commit and journal without writing."""
        return deepcopy(self._inspect_interrupted_commit()["transaction"])

    def recover_interrupted_commit(self, *, expected_transaction_root: str | None = None) -> dict[str, Any]:
        checked = self._inspect_interrupted_commit()
        item, previous_rows = checked["transaction"], checked["previous_rows"]
        if expected_transaction_root is not None:
            require(item["transaction_root"] == require_root(expected_transaction_root), "PROTECTED_COMMIT_TRANSACTION_PIN_MISMATCH")
        record, row = item["state_record"], item["journal_row"]
        old_anchor, successor = item["old_anchor"], item["successor_anchor"]
        current = self.anchor.observe_record()
        require(current in (old_anchor, successor), "PROTECTED_COMMIT_ANCHOR_DIVERGED")

        self._write_atomic(self.path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
        journal_bytes = b"".join((json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n").encode() for entry in [*previous_rows, row])
        self._write_atomic(self.journal_path, journal_bytes)
        if current == old_anchor:
            self.anchor.advance_bound(expected=old_anchor, successor=successor)
        self.transaction_path.unlink()
        return self.load()
