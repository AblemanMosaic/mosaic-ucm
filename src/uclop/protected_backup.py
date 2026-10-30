from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import CustodyProvider, OpaqueEd25519KeyStore, verify_asymmetric
from .protected_state import InMemoryMonotonicAnchor, ProtectedStateStore


BACKUP_DOMAIN = "UCL_UCM_PROTECTED_STATE_BACKUP_V1"


def _signed_record(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}


class ProtectedBackupChain:
    """Content-complete, signed backup chain for disposable rehearsals.

    A backup includes the exact final state and complete journal.  Restore is
    permitted only into an empty destination and only from the caller-pinned
    latest backup.  Real protected media and OS ACLs remain outside this class.
    """

    def __init__(self, provider: CustodyProvider, handle: str, *, source_binding_root: str, expected_head_root: str = "GENESIS", expected_head_sequence: int = 0) -> None:
        self.provider = provider
        self.handle = handle
        self.identity = provider.identity(handle)
        self.source_binding_root = require_root(source_binding_root)
        require(type(expected_head_sequence) is int and type(expected_head_sequence) is not bool and expected_head_sequence >= 0, "BACKUP_HEAD_SEQUENCE_INVALID")
        require((expected_head_sequence == 0 and expected_head_root == "GENESIS") or (expected_head_sequence > 0 and require_root(expected_head_root)), "BACKUP_HEAD_ROOT_INVALID")
        self.head_root = expected_head_root
        self.head_sequence = expected_head_sequence
        self.records: list[dict[str, Any]] = []

    def capture(self, store: ProtectedStateStore, *, runtime_root: str, reason_code: str) -> dict[str, Any]:
        require(type(reason_code) is str and reason_code, "BACKUP_REASON_INVALID")
        state = store.load()
        journal = store.verify_journal()
        anchor = store.anchor.observe_record()
        require(journal and journal[-1]["body"]["state_root"] == state["state_root"], "BACKUP_STATE_JOURNAL_MISMATCH")
        body = {
            "schema": "ucl.ucm.protected_state_backup.v1",
            "backup_sequence": self.head_sequence + 1,
            "predecessor_backup_root": self.head_root,
            "source_binding_root": self.source_binding_root,
            "runtime_root": require_root(runtime_root),
            "state_record": deepcopy(state),
            "state_root": state["state_root"],
            "journal_rows": deepcopy(journal),
            "journal_head": journal[-1]["journal_root"],
            "anchor_record": anchor,
            "reason_code": reason_code,
            "restore_effect_ceiling": "DISPOSABLE_FIXTURE_ONLY",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.provider.sign(self.handle, BACKUP_DOMAIN, body)
        record = {**signed, "backup_root": root(signed)}
        self.records.append(record)
        self.head_root = record["backup_root"]
        self.head_sequence = body["backup_sequence"]
        return deepcopy(record)

    def verify(
        self,
        value: Any,
        *,
        expected_backup_root: str,
        expected_minimum_sequence: int,
        expected_predecessor_root: str | None = None,
    ) -> dict[str, Any]:
        item = exact_keys(value, {
            "body", "body_root", "signature", "key_root", "signature_algorithm", "backup_root",
        }, "$.backup")
        signed = _signed_record(item)
        body = exact_keys(item["body"], {
            "schema", "backup_sequence", "predecessor_backup_root", "source_binding_root",
            "runtime_root", "state_record", "state_root", "journal_rows", "journal_head",
            "anchor_record", "reason_code", "restore_effect_ceiling", "standing", "authority_effect",
        }, "$.backup.body")
        verify_asymmetric(
            signed, BACKUP_DOMAIN,
            expected_key_root=self.identity["key_root"],
            public_key_hex=self.identity["public_key_hex"],
        )
        require(item["backup_root"] == root(signed) == require_root(expected_backup_root), "BACKUP_ROOT_MISMATCH")
        require(body["schema"] == "ucl.ucm.protected_state_backup.v1", "BACKUP_SCHEMA_INVALID")
        require(type(body["backup_sequence"]) is int and type(body["backup_sequence"]) is not bool and body["backup_sequence"] >= expected_minimum_sequence > 0, "BACKUP_SEQUENCE_ROLLBACK")
        require(body["source_binding_root"] == self.source_binding_root, "BACKUP_SOURCE_BINDING_MISMATCH")
        require(expected_backup_root == self.head_root and item["backup_root"] == self.head_root, "BACKUP_SUPERSEDED")
        require(body["backup_sequence"] == self.head_sequence, "BACKUP_CHAIN_LENGTH_MISMATCH")
        if expected_predecessor_root is not None:
            require(body["predecessor_backup_root"] == expected_predecessor_root, "BACKUP_PREDECESSOR_MISMATCH")
        require(body["state_root"] == body["state_record"].get("state_root"), "BACKUP_STATE_ROOT_MISMATCH")
        rows = body["journal_rows"]
        require(type(rows) is list and rows, "BACKUP_JOURNAL_INVALID")
        predecessor = "GENESIS"
        for sequence, row in enumerate(rows, 1):
            require(row.get("body", {}).get("sequence") == sequence, "BACKUP_JOURNAL_SEQUENCE_INVALID")
            require(row.get("body", {}).get("predecessor") == predecessor, "BACKUP_JOURNAL_PREDECESSOR_INVALID")
            require(row.get("journal_root") == root(_signed_record(row)), "BACKUP_JOURNAL_ROOT_INVALID")
            predecessor = row["journal_root"]
        require(body["journal_head"] == predecessor, "BACKUP_JOURNAL_HEAD_MISMATCH")
        require(rows[-1]["body"]["state_root"] == body["state_root"], "BACKUP_STATE_JOURNAL_MISMATCH")
        anchor = body["anchor_record"]
        require(anchor == {
            "schema": "ucl.ucm.monotonic_anchor.v2",
            "sequence": len(rows), "head": body["state_root"],
            "journal_sequence": len(rows), "journal_head": body["journal_head"],
        }, "BACKUP_ANCHOR_MISMATCH")
        require(body["restore_effect_ceiling"] == "DISPOSABLE_FIXTURE_ONLY", "BACKUP_EFFECT_CEILING_INVALID")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "BACKUP_EFFECT_FORBIDDEN")
        return deepcopy(body)

    def restore_disposable(
        self,
        value: Any,
        *,
        expected_backup_root: str,
        expected_minimum_sequence: int,
        destination: Path,
        keys: OpaqueEd25519KeyStore,
        signing_handle: str,
    ) -> ProtectedStateStore:
        body = self.verify(
            value,
            expected_backup_root=expected_backup_root,
            expected_minimum_sequence=expected_minimum_sequence,
        )
        destination = destination.resolve()
        require(not destination.exists() or not any(destination.iterdir()), "BACKUP_RESTORE_DESTINATION_NOT_EMPTY")
        destination.mkdir(parents=True, exist_ok=True)
        anchor = InMemoryMonotonicAnchor()
        for row in body["journal_rows"]:
            old = anchor.observe_record()
            successor = {
                "schema": "ucl.ucm.monotonic_anchor.v2",
                "sequence": row["body"]["sequence"],
                "head": row["body"]["state_root"],
                "journal_sequence": row["body"]["sequence"],
                "journal_head": row["journal_root"],
            }
            anchor.advance_bound(expected=old, successor=successor)
        (destination / "state.json").write_text(json.dumps(body["state_record"], indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (destination / "journal.jsonl").write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in body["journal_rows"]), encoding="utf-8", newline="\n")
        store = ProtectedStateStore(destination, anchor=anchor, keys=keys, signing_handle=signing_handle)
        restored = store.load()
        require(restored["state_root"] == body["state_root"], "BACKUP_RESTORE_RESULT_MISMATCH")
        return store
