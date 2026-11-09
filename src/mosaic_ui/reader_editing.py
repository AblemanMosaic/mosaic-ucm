"""Reversible source editing and explicitly admitted atomic save custody."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import secrets
from typing import Callable

from .canonical import atomic_write, commitment
from .document_model import DocumentIR, DocumentLimits, import_document


class EditingRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


@dataclass(frozen=True)
class SavePlan:
    plan_root: str
    target: str
    permitted_root: str
    source_root: str
    document_root: str
    baseline_file_sha256: str | None
    allow_create: bool
    byte_count: int
    status: str = "PENDING_HOST_ADMISSION"


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class DocumentEditSession:
    """Own one source buffer, its parseable IR, and bounded undo/save history."""

    def __init__(
        self,
        document: DocumentIR,
        *,
        limits: DocumentLimits = DocumentLimits(),
        history_limit: int = 100,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if history_limit < 1 or history_limit > 10_000:
            raise EditingRefusal("EDIT_HISTORY_LIMIT_REFUSED", str(history_limit))
        self._document = document
        self._limits = limits
        self._history_limit = history_limit
        self._undo: list[DocumentIR] = []
        self._redo: list[DocumentIR] = []
        self._plans: dict[str, SavePlan] = {}
        self._save_capabilities: dict[str, dict[str, str]] = {}
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._receipts: list[dict] = []
        self._previous_receipt_root = "GENESIS"

    @property
    def document(self) -> DocumentIR:
        return self._document

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def receipts(self) -> tuple[dict, ...]:
        return tuple(dict(item) for item in self._receipts)

    def _record(self, event: str, detail: dict, *, authority_effect: str = "NONE") -> dict:
        value = {
            "schema": "mosaic.reader.edit-receipt.v0.1",
            "sequence": len(self._receipts) + 1,
            "event": event,
            "detail": detail,
            "previous_receipt_root": self._previous_receipt_root,
            "authority_effect": authority_effect,
        }
        value["receipt_root"] = commitment("MOSAIC.READER.EDIT_RECEIPT.v0.1", value)
        self._previous_receipt_root = value["receipt_root"]
        self._receipts.append(value)
        return dict(value)

    def _refuse(self, code: str, detail: str = "") -> None:
        self._record("REFUSED", {"code": code, "detail": detail})
        raise EditingRefusal(code, detail)

    def apply(
        self,
        start: int,
        end: int,
        replacement: str,
        *,
        expected_source_root: str,
    ) -> dict:
        if expected_source_root != self._document.source_root:
            self._refuse("EDIT_STALE_SOURCE_REFUSED", expected_source_root)
        source = self._document.source
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            self._refuse("EDIT_RANGE_REFUSED", f"{start}:{end}")
        if start < 0 or end < start or end > len(source):
            self._refuse("EDIT_RANGE_REFUSED", f"{start}:{end}:{len(source)}")
        if not isinstance(replacement, str):
            self._refuse("EDIT_REPLACEMENT_REFUSED", type(replacement).__name__)
        candidate_source = source[:start] + replacement + source[end:]
        candidate = import_document(
            candidate_source,
            self._document.source_format,
            limits=self._limits,
        )
        before = self._document
        self._undo.append(before)
        if len(self._undo) > self._history_limit:
            self._undo.pop(0)
        self._redo.clear()
        self._document = candidate
        return self._record("EDIT_APPLIED", {
            "start": start,
            "end": end,
            "replacement_root": sha256(replacement.encode("utf-8")).hexdigest(),
            "before_source_root": before.source_root,
            "after_source_root": candidate.source_root,
            "before_document_root": before.document_root,
            "after_document_root": candidate.document_root,
        })

    def undo(self) -> dict:
        if not self._undo:
            self._refuse("EDIT_UNDO_REFUSED", "EMPTY")
        before = self._document
        self._redo.append(before)
        self._document = self._undo.pop()
        return self._record("EDIT_UNDONE", {
            "before_source_root": before.source_root,
            "after_source_root": self._document.source_root,
        })

    def redo(self) -> dict:
        if not self._redo:
            self._refuse("EDIT_REDO_REFUSED", "EMPTY")
        before = self._document
        self._undo.append(before)
        self._document = self._redo.pop()
        return self._record("EDIT_REDONE", {
            "before_source_root": before.source_root,
            "after_source_root": self._document.source_root,
        })

    def prepare_save(
        self,
        target: Path,
        *,
        permitted_root: Path,
        expected_file_sha256: str | None = None,
        allow_create: bool = False,
    ) -> SavePlan:
        root = permitted_root.resolve()
        if not root.exists() or not root.is_dir():
            self._refuse("SAVE_ROOT_REFUSED", str(root))
        resolved = target.resolve()
        if resolved == root or not resolved.is_relative_to(root):
            self._refuse("SAVE_TARGET_OUTSIDE_ROOT_REFUSED", str(resolved))
        exists = resolved.exists()
        if exists and not resolved.is_file():
            self._refuse("SAVE_TARGET_TYPE_REFUSED", str(resolved))
        baseline = _file_hash(resolved) if exists else None
        if exists and expected_file_sha256 is None:
            self._refuse("SAVE_EXPECTED_FILE_ROOT_REQUIRED", str(resolved))
        if exists and expected_file_sha256 != baseline:
            self._refuse("SAVE_STALE_FILE_REFUSED", str(resolved))
        if not exists and not allow_create:
            self._refuse("SAVE_CREATE_REFUSED", str(resolved))
        body = {
            "target": str(resolved),
            "permitted_root": str(root),
            "source_root": self._document.source_root,
            "document_root": self._document.document_root,
            "baseline_file_sha256": baseline,
            "allow_create": bool(allow_create),
            "byte_count": len(self._document.source.encode("utf-8")),
            "status": "PENDING_HOST_ADMISSION",
        }
        plan = SavePlan(
            plan_root=commitment("MOSAIC.READER.SAVE_PLAN.v0.1", body),
            **body,
        )
        self._plans[plan.plan_root] = plan
        self._record("SAVE_PREPARED", {
            "plan_root": plan.plan_root,
            "target": plan.target,
            "source_root": plan.source_root,
            "baseline_file_sha256": plan.baseline_file_sha256,
            "allow_create": plan.allow_create,
        })
        return plan

    def authorize_save(self, plan_root: str, *, host_actor: str) -> str:
        plan = self._plans.get(plan_root)
        actor = str(host_actor).strip()
        if plan is None:
            self._refuse("SAVE_PLAN_STATE_REFUSED", plan_root)
        if not actor:
            self._refuse("SAVE_HOST_ACTOR_REFUSED", "EMPTY")
        if plan.source_root != self._document.source_root:
            self._refuse("SAVE_PLAN_STALE_SOURCE_REFUSED", plan_root)
        token = self._token_factory()
        if not isinstance(token, str) or len(token) < 16:
            self._refuse("SAVE_CAPABILITY_REFUSED", "TOKEN_FACTORY")
        token_root = sha256(token.encode("utf-8")).hexdigest()
        if token_root in self._save_capabilities:
            self._refuse("SAVE_CAPABILITY_REFUSED", "COLLISION")
        self._save_capabilities[token_root] = {
            "plan_root": plan_root,
            "host_actor": actor,
        }
        self._record("SAVE_AUTHORIZED", {
            "plan_root": plan_root,
            "host_actor": actor,
            "capability_root": token_root,
        })
        return token

    def commit_save(self, capability: str, *, host_actor: str) -> dict:
        token_root = sha256(str(capability).encode("utf-8")).hexdigest()
        binding = self._save_capabilities.get(token_root)
        if binding is None:
            self._refuse("SAVE_CAPABILITY_STATE_REFUSED", token_root)
        actor = str(host_actor).strip()
        if actor != binding["host_actor"]:
            self._refuse("SAVE_HOST_ACTOR_MISMATCH", actor)
        plan = self._plans.get(binding["plan_root"])
        if plan is None:
            self._refuse("SAVE_PLAN_STATE_REFUSED", binding["plan_root"])
        if plan.source_root != self._document.source_root:
            self._refuse("SAVE_PLAN_STALE_SOURCE_REFUSED", plan.plan_root)
        root = Path(plan.permitted_root).resolve()
        target = Path(plan.target).resolve()
        if target == root or not target.is_relative_to(root):
            self._refuse("SAVE_TARGET_OUTSIDE_ROOT_REFUSED", str(target))
        if target.exists() and not target.is_file():
            self._refuse("SAVE_TARGET_TYPE_REFUSED", str(target))
        current = _file_hash(target) if target.exists() and target.is_file() else None
        if current != plan.baseline_file_sha256:
            self._refuse("SAVE_STALE_FILE_REFUSED", str(target))
        data = self._document.source.encode("utf-8")
        atomic_write(target, data)
        written = _file_hash(target)
        expected = sha256(data).hexdigest()
        if written != expected:
            self._refuse("SAVE_VERIFY_REFUSED", str(target))
        self._save_capabilities.pop(token_root)
        self._plans.pop(plan.plan_root, None)
        return self._record("SAVE_COMMITTED", {
            "plan_root": plan.plan_root,
            "host_actor": actor,
            "target": str(target),
            "source_root": self._document.source_root,
            "file_sha256": written,
            "byte_count": len(data),
            "atomic_replace": True,
        }, authority_effect="LOCAL_FILE_MUTATION")


__all__ = ["DocumentEditSession", "EditingRefusal", "SavePlan"]
