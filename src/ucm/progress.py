"""Best-effort nonsemantic progress stream.

Progress may be missing, delayed, duplicated, truncated, redirected, or
unwritable without changing any journal event, receipt, root, or verdict.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any


class Progress:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.sequence = 0
        self.started = 0
        self.completed = 0
        self.failed = 0
        self.phase = None
        self.phase_started_ns: dict[str, int] = {}
        self.last_event = None

    def emit(self, event: str, **fields: Any) -> None:
        self.sequence += 1
        if event in {"TEST_START", "CASE_START", "PHASE_START"}:
            self.started += 1
        if event in {"TEST_PASS", "CASE_PASS", "PHASE_PASS"}:
            self.completed += 1
        if event in {"TEST_FAIL", "TEST_ERROR", "CASE_FAIL", "PHASE_FAIL"}:
            self.failed += 1
        if "phase" in fields:
            self.phase = fields["phase"]
            if event == "PHASE_START":
                self.phase_started_ns[self.phase] = time.perf_counter_ns()
            elif event in {"PHASE_PASS", "PHASE_FAIL"} and self.phase in self.phase_started_ns:
                fields.setdefault("elapsed_ms", round(
                    (time.perf_counter_ns() - self.phase_started_ns.pop(self.phase)) / 1_000_000, 3))
        self.last_event = event
        row = {"schema": "mosaic.ucm.nonsemantic-progress.v0.1",
               "sequence": self.sequence, "event": event,
               "observed_unix_ns": time.time_ns(), **fields}
        line = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            print(line, flush=True)
        except (OSError, UnicodeError):
            pass
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(line + "\n")
                    stream.flush()
            except (OSError, UnicodeError):
                pass
        self.write_summary(status="FAILED" if self.failed else "RUNNING")

    def write_summary(self, *, total: int | None = None,
                      status: str = "RUNNING") -> None:
        """Best-effort compact sibling projection; never part of semantic state."""
        if self.path is None:
            return
        target = self.path.with_suffix(self.path.suffix + ".summary.json")
        temporary = target.with_suffix(target.suffix + f".{os.getpid()}.tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(self.summary(total=total, status=status),
                ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8", newline="\n")
            os.replace(temporary, target)
        except (OSError, UnicodeError):
            try:
                temporary.unlink()
            except OSError:
                pass

    def summary(self, *, total: int | None = None, status: str = "RUNNING") -> dict[str, Any]:
        """Return a nonsemantic compact live projection.

        The projection is deliberately excluded from all roots and verdicts.
        """
        return {"schema": "mosaic.ucm.nonsemantic-progress-summary.v0.1",
                "status": status, "phase": self.phase, "started": self.started,
                "completed": self.completed, "failed": self.failed, "total": total,
                "remaining": (max(0, total - self.completed) if total is not None else None),
                "last_sequence": self.sequence, "last_event": self.last_event,
                "semantic_effect": "NONE"}
