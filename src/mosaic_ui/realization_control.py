"""Loopback-only, render-thread-safe control plane for live realization changes."""

from __future__ import annotations

import json
import hashlib
import os
import queue
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


MAX_REQUEST_BYTES = 64 * 1024


def verify_receipt_chain(path: Path) -> dict[str, Any]:
    previous = None
    count = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        claimed = row.pop("event_root", None)
        if row.get("previous_event_root") != previous:
            raise ValueError("RSC_EVENT_PREDECESSOR_REFUSED")
        actual = hashlib.sha256(json.dumps(
            row, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if claimed != actual:
            raise ValueError("RSC_EVENT_ROOT_REFUSED")
        previous, count = claimed, count + 1
    return {"event_count": count, "terminal_event_root": previous,
            "authority_effect": "NONE"}


@dataclass
class PendingCommand:
    payload: dict[str, Any]
    completed: threading.Event = field(default_factory=threading.Event)
    result: dict[str, Any] | None = None
    expires_at: float = 0.0
    cancelled: bool = False
    queued_ns: int = 0


class LocalRealizationControlPlane:
    """Accept bounded JSON commands while keeping engine mutation on its main thread."""

    def __init__(self, session_root: Path, *, title: str, timeout_s: float = 4.0) -> None:
        self.session_root = Path(session_root).resolve()
        self.title = str(title)
        self.timeout_s = float(timeout_s)
        self._mutation_thread_id = threading.get_ident()
        self._mutation_thread_name = threading.current_thread().name
        self.token = secrets.token_hex(32)
        self.started_ns = time.time_ns()
        self._commands: queue.Queue[PendingCommand] = queue.Queue(maxsize=64)
        self._closed = False
        self._receipt_root: str | None = None
        self._event_sequence = 0
        plane = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "MosaicRSC/0.1"
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:
                return

            def _reply(self, status: int, value: dict[str, Any]) -> None:
                body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path != "/v1/health":
                    self._reply(404, {"error": "RSC_ENDPOINT_NOT_FOUND", "authority_effect": "NONE"})
                    return
                self._reply(200, {
                    "status": "READY", "pid": os.getpid(), "title": plane.title,
                    "authority_effect": "NONE",
                })

            def do_POST(self) -> None:
                if self.path != "/v1/command":
                    self._reply(404, {"error": "RSC_ENDPOINT_NOT_FOUND", "authority_effect": "NONE"})
                    return
                if not secrets.compare_digest(self.headers.get("X-Mosaic-Session", ""), plane.token):
                    self._reply(403, {"error": "RSC_SESSION_TOKEN_REFUSED", "authority_effect": "NONE"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = -1
                if length < 2 or length > MAX_REQUEST_BYTES:
                    self._reply(413, {"error": "RSC_REQUEST_SIZE_REFUSED", "authority_effect": "NONE"})
                    return
                try:
                    value = json.loads(self.rfile.read(length))
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    result = plane.submit(value)
                except queue.Full:
                    self._reply(503, {"error": "RSC_COMMAND_BACKLOG_FULL", "authority_effect": "NONE"})
                    return
                except TimeoutError as exc:
                    self._reply(504, {"error": str(exc), "authority_effect": "NONE"})
                    return
                except BaseException as exc:
                    self._reply(400, {"error": f"{type(exc).__name__}:{exc}", "authority_effect": "NONE"})
                    return
                self._reply(200, result)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="mosaic-rsc-loopback", daemon=True,
        )
        self._thread.start()
        self.session_root.mkdir(parents=True, exist_ok=True)
        self.session_path = self.session_root / f"{os.getpid()}.json"
        self.receipt_path = self.session_root / "receipts" / f"{os.getpid()}.jsonl"
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.descriptor = {
            "schema": "mosaic.realization-control-session.v0.1",
            "pid": os.getpid(), "title": self.title,
            "url": f"http://127.0.0.1:{self._server.server_address[1]}",
            "token": self.token, "started_ns": self.started_ns,
            "transport": "LOOPBACK_HTTP_BOUNDED_JSON",
            "mutation_thread": "NATIVE_RENDER_THREAD",
            "mutation_thread_id": self._mutation_thread_id,
            "mutation_thread_name": self._mutation_thread_name,
            "receipt_path": str(self.receipt_path),
            "authority_effect": "NONE",
        }
        temporary = self.session_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.descriptor, indent=2), encoding="utf-8")
        temporary.replace(self.session_path)

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("RSC_CONTROL_PLANE_CLOSED")
        pending = PendingCommand(dict(payload), queued_ns=time.perf_counter_ns())
        pending.expires_at = time.monotonic() + self.timeout_s
        self._commands.put_nowait(pending)
        if not pending.completed.wait(self.timeout_s):
            pending.cancelled = True
            raise TimeoutError("RSC_RENDER_THREAD_TIMEOUT")
        assert pending.result is not None
        return pending.result

    def drain(self, handler: Callable[[dict[str, Any]], dict[str, Any]], *, limit: int = 8) -> int:
        if threading.get_ident() != self._mutation_thread_id:
            raise RuntimeError("RSC_MUTATION_THREAD_REFUSED")
        count = 0
        for _ in range(max(0, int(limit))):
            try:
                pending = self._commands.get_nowait()
            except queue.Empty:
                break
            try:
                drain_started_ns = time.perf_counter_ns()
                if pending.cancelled or time.monotonic() >= pending.expires_at:
                    pending.result = {"status": "EXPIRED", "error": "RSC_COMMAND_EXPIRED",
                                      "authority_effect": "NONE"}
                else:
                    result = handler(dict(pending.payload))
                    if not isinstance(result, dict):
                        raise TypeError("RSC_COMMAND_RESULT_OBJECT_REQUIRED")
                    pending.result = {**result, "authority_effect": "NONE"}
                completed_ns = time.perf_counter_ns()
                pending.result["control_timing"] = {
                    "queue_to_apply_ms": round(
                        (drain_started_ns - pending.queued_ns) / 1_000_000, 6,
                    ),
                    "handler_ms": round((completed_ns - drain_started_ns) / 1_000_000, 6),
                    "queue_depth_after_dequeue": self._commands.qsize(),
                    "mutation_thread": "NATIVE_RENDER_THREAD",
                }
            except BaseException as exc:
                pending.result = {
                    "status": "REFUSED", "error": f"{type(exc).__name__}:{exc}",
                    "authority_effect": "NONE",
                }
            finally:
                self._event_sequence += 1
                event = {
                    "schema": "mosaic.realization-control-event.v0.1",
                    "sequence": self._event_sequence,
                    "observed_ns": time.time_ns(),
                    "command": pending.payload.get("command"),
                    "contract_id": pending.payload.get("contract_id"),
                    "result_status": pending.result.get("status") if pending.result else "REFUSED",
                    "result_receipt_root": ((pending.result or {}).get("receipt") or {}).get("receipt_root"),
                    "queue_to_apply_ms": ((pending.result or {}).get("control_timing") or {}).get("queue_to_apply_ms"),
                    "handler_ms": ((pending.result or {}).get("control_timing") or {}).get("handler_ms"),
                    "previous_event_root": self._receipt_root,
                    "authority_effect": "NONE",
                }
                canonical = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
                event["event_root"] = hashlib.sha256(canonical).hexdigest()
                with self.receipt_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                self._receipt_root = event["event_root"]
                pending.completed.set()
                self._commands.task_done()
                count += 1
        return count

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2.0)
        try:
            self.session_path.unlink()
        except FileNotFoundError:
            pass

