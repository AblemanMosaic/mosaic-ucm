"""Loopback-only browser realization of the governed semantic UI protocol."""
from __future__ import annotations

import argparse
import copy
import html
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .canonical import commitment
from .browser_session_store import SQLiteBrowserSessionStore, StoredBrowserSession
from .headless import HeadlessUI, LayoutProvider
from .localization import resolve_locale
from .model import UIRefusal, walk
from mosaic_ui_std.catalog import check_realizable


BROWSER_POLICY = {
    "schema": "mosaic.ui.browser-policy.v0.1",
    "transport": "LOOPBACK_HTTP",
    "allowed_hosts": ["127.0.0.1", "localhost"],
    "network_effect": "LOOPBACK_ONLY",
    "session_isolation": "PER_BROWSER_SESSION",
    "origin_policy": "SAME_LOOPBACK_ORIGIN",
    "event_ordering": "STRICT_MONOTONIC_SEQUENCE",
    "max_request_bytes": 65536,
    "max_session_snapshot_bytes": 4194304,
    "default_session_ttl_seconds": 900,
    "default_max_sessions": 128,
    "authority_effect": "NONE",
    "invariant": "BROWSER_REALIZER_CANNOT_INTERMEDIATE_OR_GRANT_APPLICATION_AUTHORITY",
}


def _attrs(item: dict[str, Any], rect: dict[str, int], state: str) -> str:
    semantics = item["semantics"]
    props = item.get("props", {})
    values = {
        "id": item["node_id"],
        "data-node-id": item["node_id"],
        "data-kind": item["kind"],
        "aria-label": semantics["name"],
        "aria-description": semantics.get("description", ""),
        "data-state": state,
        "style": (
            f"left:{rect['x']}px;top:{rect['y']}px;width:{rect['width']}px;"
            f"height:{rect['height']}px"
        ),
    }
    if props.get("required"):
        values["aria-required"] = "true"
    if props.get("multiline"):
        values["aria-multiline"] = "true"
    if state == "REFUSED":
        values["aria-invalid"] = "true"
    return " ".join(f'{key}="{html.escape(str(value), quote=True)}"' for key, value in values.items())


def _options(item: dict[str, Any]) -> list[tuple[str, str]]:
    props = item.get("props", {})
    source = props.get("options") or props.get("tabs") or props.get("items") \
        or props.get("decisions") or props.get("steps") or []
    values = []
    for entry in source if isinstance(source, list) else []:
        if isinstance(entry, dict):
            value = entry.get("value", entry.get("label", entry.get("name")))
            label = entry.get("label", entry.get("name", value))
        else:
            value, label = entry, entry
        if value is not None and label is not None:
            values.append((str(value), str(label)))
    return values


def _theme_v02_css(theme: dict[str, Any] | None) -> str:
    """Add owned fonts, elevation, and motion only when a v0.2 theme is attached."""
    if not theme:
        return ""
    from mosaic_ui_std.theme_v02 import font_face_css, load_font_registry

    tokens = theme["tokens"]
    registry = load_font_registry()["fonts"]
    roles = tokens["typography"]["roles"]
    radii = tokens["radii"]
    motion = tokens["motion"]

    def shadow(level: str) -> str:
        value = tokens["elevation"][level]
        return "0 {y}px {blur}px rgba(0,0,0,{alpha})".format(**value)

    body_font = roles["body"]["font"]
    mono_font = roles["mono"]["font"]
    family = registry[body_font]["family"]
    mono = registry[mono_font]["family"]
    ease = f"{motion['short_ms']}ms {motion['easing']}"
    return (
        "\n" + font_face_css([body_font, mono_font]) + "\n"
        f"html,body{{font-family:'{family}',system-ui,sans-serif}}"
        f"code,kbd,samp{{font-family:'{mono}',ui-monospace,monospace}}\n"
        f"[data-kind=PANEL]{{box-shadow:{shadow('raised')};border-radius:{radii['lg']}px}}\n"
        f"[data-kind=DIALOG],[data-kind=TOOLTIP]{{box-shadow:{shadow('overlay')};border-radius:{radii['lg']}px}}\n"
        f"button,[data-node-id]{{transition:background-color {ease},border-color {ease},color {ease}}}\n"
        "@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}\n"
    )


def _element(item: dict[str, Any], rect: dict[str, int], value: Any, state: str) -> str:
    kind = item["kind"]
    props = item.get("props", {})
    label = html.escape(str(props.get("display_text") or item["semantics"]["name"]))
    attrs = _attrs(item, rect, state)
    disabled = " disabled" if state == "DISABLED" else ""
    selected_value = value.get("selected") if isinstance(value, dict) else value
    selected = str(selected_value if selected_value is not None else props.get("default", ""))
    choices = _options(item)
    if kind == "BUTTON":
        return f'<button {attrs} data-intent="ACTIVATE"{disabled}>{label}</button>'
    if kind == "TEXT_FIELD":
        readonly = " readonly" if props.get("readonly") else ""
        required = " required" if props.get("required") else ""
        limits = (f' minlength="{int(props["min_length"])}"' if "min_length" in props else "") + \
            (f' maxlength="{int(props["max_length"])}"' if props.get("max_length") is not None else "")
        if props.get("multiline"):
            return f'<textarea {attrs}{readonly}{required}{limits}{disabled}>{html.escape(selected)}</textarea>'
        return f'<input {attrs} type="text" value="{html.escape(selected, quote=True)}"{readonly}{required}{limits}{disabled}>'
    if kind in {"SELECT", "COMBOBOX"}:
        body = "".join(
            f'<option value="{html.escape(option, quote=True)}"'
            f'{" selected" if option == selected else ""}>{html.escape(label)}</option>' for option, label in choices
        )
        return f'<select {attrs}{disabled}>{body}</select>'
    if kind == "CHECKBOX":
        checked = " checked" if bool(value) else ""
        return f'<label {attrs} class="check"><input type="checkbox"{checked}{disabled}><span>{label}</span></label>'
    if kind in {"SEGMENTED", "TAB_BAR", "RADIO_GROUP", "MENU", "NAVIGATION"}:
        role = {"TAB_BAR": "tablist", "RADIO_GROUP": "radiogroup", "MENU": "menu", "NAVIGATION": "navigation"}.get(kind, "group")
        choice_role = {"TAB_BAR": "tab", "RADIO_GROUP": "radio", "MENU": "menuitemradio"}.get(kind)
        state_name = "aria-selected" if kind == "TAB_BAR" else "aria-checked" if kind in {"RADIO_GROUP", "MENU"} else "aria-pressed"
        buttons = "".join(
            f'<button type="button" data-choice="{html.escape(option, quote=True)}"'
            f'{f" role={choice_role}" if choice_role else ""} {state_name}="{str(option == selected).lower()}"'
            f'{disabled}>{html.escape(label)}</button>' for option, label in choices
        )
        return f'<div {attrs} class="choices" role="{role}">{buttons}</div>'
    if kind in {"LIST", "TREE"}:
        role = "tree" if kind == "TREE" else "listbox"
        rows = "".join(
            f'<button type="button" role="{("treeitem" if kind == "TREE" else "option")}" '
            f'data-choice="{html.escape(option, quote=True)}" aria-selected="{str(option == selected).lower()}"'
            f'{disabled}>{html.escape(label)}</button>' for option, label in choices
        )
        return f'<div {attrs} class="collection" role="{role}">{rows}</div>'
    if kind in {"TABLE", "DATA_GRID"}:
        columns = props.get("columns", [])
        rows = value.get("rows", []) if isinstance(value, dict) else value if isinstance(value, list) else props.get("rows", [])
        head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
        body = []
        for row in rows if isinstance(rows, list) else []:
            cells = row if isinstance(row, (list, tuple)) else [row]
            row_value = str(cells[0]) if cells else ""
            cell_html = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in cells)
            if kind == "DATA_GRID":
                body.append(f'<tr data-choice="{html.escape(row_value, quote=True)}" tabindex="0">{cell_html}</tr>')
            else:
                body.append(f"<tr>{cell_html}</tr>")
        return f'<div {attrs} class="table-wrap"><table role="{("grid" if kind == "DATA_GRID" else "table")}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    if kind == "PROGRESS":
        percent = float(value or 0)
        return f'<div {attrs} class="progress-wrap"><progress max="100" value="{percent}"></progress><span>{percent:.0f}%</span></div>'
    if kind == "DIALOG":
        buttons = "".join(
            f'<button data-decision="{html.escape(choice, quote=True)}">{html.escape(label)}</button>'
            for choice, label in choices
        )
        return f'<section {attrs} class="dialog" role="dialog"><strong>{label}</strong><p>{html.escape(str(props.get("message", "")))}</p><div>{buttons}</div></section>'
    if kind == "NOTIFICATION":
        text = html.escape(str(value)) if value is not None and value != "" else label
        return f'<aside {attrs} class="notification" role="status">{text}</aside>'
    tag = "section" if kind in {"WINDOW", "PANEL"} else "div"
    role = html.escape({
        "BADGE": "status", "KEY_VALUE": "group", "LABEL": "text", "PANEL": "group",
        "STATUS": "status", "STEPPER": "group", "TOOLTIP": "tooltip", "WINDOW": "application",
    }.get(kind, str(item["semantics"].get("role", "group"))), quote=True)
    text = html.escape(str(value)) if kind in {"BADGE", "LABEL", "STATUS"} and value is not None and value != "" else label
    return f'<{tag} {attrs} role="{role}">{text}</{tag}>'


def render_document(
    runtime: HeadlessUI, width: int, height: int, *, client: dict[str, Any] | None = None,
) -> str:
    projection = runtime.project(width, height).as_dict()
    geometry = {row["node_id"]: row["rect"] for row in projection["geometry"]["nodes"]}
    nodes = {str(item["node_id"]): item for item in walk(runtime.tree)}
    state = runtime.state
    body = []
    for semantic in projection["semantics"]["nodes"]:
        item = nodes[semantic["node_id"]]
        body.append(_element(item, geometry[semantic["node_id"]], semantic.get("value"), semantic["state"]))
    tokens = runtime.payload["library"]["tokens"]
    colors, radii, spacing = tokens["colors"], tokens["radii"], tokens["spacing"]
    body_type = tokens["typography"]["roles"]["body"]
    font_family = json.dumps(str(body_type["family"]))
    css = f"""
*{{box-sizing:border-box;letter-spacing:0}} html,body{{margin:0;width:100%;height:100%;overflow:auto;background:{colors['canvas']};color:{colors['text']};font:{body_type['size']}px {font_family},sans-serif}}
#mosaic-root{{position:relative;width:{width}px;height:{height}px;background:{colors['canvas']}}}
[data-node-id]{{position:absolute;min-width:0;overflow:hidden;border:1px solid {colors['border']};border-radius:{radii['sm']}px;background:{colors['surface']};color:{colors['text']}}}
button,input,select{{font:inherit;color:inherit}} button{{cursor:pointer}} button:focus-visible,input:focus-visible,select:focus-visible,[tabindex]:focus-visible{{outline:2px solid {colors['focus']};outline-offset:1px}}
.choices{{display:flex;gap:{spacing['xs']}px;padding:{spacing['xs']}px;container-type:inline-size}} .choices button{{flex:1;min-width:0;padding:2px;border:0;border-radius:{radii['sm']}px;background:{colors['surface_hover']};overflow-wrap:anywhere;line-height:1.15}} .choices button[aria-pressed=true],.choices button[aria-checked=true],.choices button[aria-selected=true]{{background:{colors['selection']};color:{colors['accent_hover']}}}
@container (max-width:220px){{.choices button{{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}}}
.collection{{display:flex;flex-direction:column;padding:4px;gap:2px;overflow:auto}} .collection button{{text-align:start;border:0;padding:6px;background:transparent}} .collection button[aria-selected=true]{{background:{colors['selection']}}}
.check{{display:flex;align-items:center;gap:8px;padding:6px 10px}} .check input{{position:static}}
.table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse}} th,td{{padding:7px;text-align:start;border-bottom:1px solid {colors['border']}}} th{{color:{colors['text_quiet']}}} tr[data-choice]{{cursor:pointer}}
.progress-wrap{{display:flex;align-items:center;gap:8px;padding:8px}} progress{{width:100%;accent-color:{colors['accent']}}}
.dialog{{padding:12px}} .dialog p{{margin:8px 0}} .dialog button{{margin-inline-end:6px}} .notification{{padding:10px;border-inline-start:3px solid {colors['info']}}}
[data-state=REFUSED]{{border-color:{colors['refused']}}} [data-state=PENDING]{{border-color:{colors['pending']}}}
"""
    css += _theme_v02_css(runtime.payload["library"].get("theme_v02"))
    policy_root = commitment("MOSAIC.UI.BROWSER_POLICY.v0.1", BROWSER_POLICY)
    client = client or {}
    session_id = json.dumps(str(client.get("session_id", "")))
    session_token = json.dumps(str(client.get("session_token", "")))
    protocol = json.dumps(str(client.get("protocol", "")))
    sequence = int(client.get("next_sequence", 1))
    lang = html.escape(runtime.localization.locale, quote=True)
    direction = html.escape(runtime.localization.direction.lower(), quote=True)
    return f"""<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(runtime.tree['semantics']['name'])}</title><style>{css}</style></head><body><main id="mosaic-root" data-policy-root="{policy_root}">{''.join(body)}</main><script>
const mosaicSession={session_id},mosaicToken={session_token},mosaicProtocol={protocol};let mosaicSequence={sequence};
const send=async e=>{{const response=await fetch('/event',{{method:'POST',headers:{{'content-type':'application/json','x-mosaic-session':mosaicSession,'x-mosaic-session-token':mosaicToken,'x-mosaic-protocol':mosaicProtocol,'x-mosaic-event-sequence':String(mosaicSequence)}},body:JSON.stringify(e)}});mosaicSequence=Number(response.headers.get('x-mosaic-next-sequence')||mosaicSequence+1);if(!response.ok)throw new Error((await response.json()).refusal_code||'EVENT_REFUSED');location.reload()}};
document.querySelectorAll('[data-intent=ACTIVATE]').forEach(x=>x.onclick=()=>send({{intent:'ACTIVATE',node_id:x.dataset.nodeId}}));
document.querySelectorAll('select[data-node-id]').forEach(x=>x.onchange=()=>send({{intent:'SELECT',node_id:x.dataset.nodeId,value:x.value}}));
document.querySelectorAll('input[type=text][data-node-id],textarea[data-node-id]').forEach(x=>x.onchange=()=>send({{intent:'TEXT_COMMIT',node_id:x.dataset.nodeId,value:x.value}}));
document.querySelectorAll('.check[data-node-id] input').forEach(x=>x.onchange=()=>send({{intent:'TOGGLE',node_id:x.parentElement.dataset.nodeId,value:x.checked}}));
document.querySelectorAll('[data-choice]').forEach(x=>x.onclick=()=>send({{intent:'SELECT',node_id:x.closest('[data-node-id]').dataset.nodeId,value:x.dataset.choice}}));
document.querySelectorAll('[data-decision]').forEach(x=>x.onclick=()=>send({{intent:'DIALOG_DECISION',node_id:x.closest('[data-node-id]').dataset.nodeId,value:x.dataset.decision}}));
</script></body></html>"""


class BrowserRealizer:
    def __init__(
        self, payload: dict[str, Any], layout_provider: LayoutProvider | None = None,
        *, catalog: dict[str, Any] | None = None, locale: str | None = None,
        accept_language: str | None = None,
    ) -> None:
        self.runtime = HeadlessUI(
            copy.deepcopy(payload), layout_provider, catalog=catalog,
            locale=locale, accept_language=accept_language,
        )
        check_realizable(self.runtime.catalog, self.runtime.tree, "BROWSER")

    @property
    def descriptor(self):
        from .realizer import PROTOCOL_SCHEMA, RealizerDescriptor

        return RealizerDescriptor(
            "BROWSER", PROTOCOL_SCHEMA,
            ("SEMANTICS", "GEOMETRY", "ACCESSIBILITY", "DRAW_STREAM", "GATES", "DOM"),
            ("LOOPBACK_HTTP_WHEN_SERVED",),
            tuple(sorted({item["kind"] for item in self.runtime.nodes.values()})),
        )

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.apply(copy.deepcopy(event))

    def snapshot(self) -> dict[str, Any]:
        return self.runtime.snapshot()

    def load_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.runtime.load_snapshot(copy.deepcopy(snapshot))

    def project(self, width: int, height: int) -> dict[str, Any]:
        value = self.runtime.project(width, height).as_dict()
        document = render_document(self.runtime, width, height)
        value["dom"] = {
            "schema": "mosaic.ui.browser-dom-projection.v0.1",
            "document_sha256": commitment("MOSAIC.UI.BROWSER_DOCUMENT.v0.1", document),
            "policy": BROWSER_POLICY,
            "authority_effect": "NONE",
        }
        return value

    def document(self, width: int, height: int) -> str:
        return render_document(self.runtime, width, height)

    def close(self) -> None:
        return None


@dataclass
class BrowserSession:
    session_id: str
    token: str
    realizer: BrowserRealizer
    created_monotonic: float
    expires_monotonic: float
    last_access_monotonic: float
    next_sequence: int = 1
    lock: threading.RLock = field(default_factory=threading.RLock)
    owner_id: str | None = None


class BrowserSessionManager:
    """Own independent realizers and replay-resistant event streams per browser session."""

    def __init__(
        self,
        payload: dict[str, Any],
        layout_provider: LayoutProvider | None = None,
        *,
        catalog: dict[str, Any] | None = None,
        ttl_seconds: int = 900,
        max_sessions: int = 128,
        session_database: Path | None = None,
    ) -> None:
        if ttl_seconds <= 0 or max_sessions <= 0:
            raise UIRefusal("BROWSER_SESSION_POLICY_REFUSED", "NON_POSITIVE_BOUND")
        self.payload = copy.deepcopy(payload)
        self.layout_provider = layout_provider
        self.catalog = copy.deepcopy(catalog)
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = threading.RLock()
        self._direct = BrowserRealizer(self.payload, self.layout_provider, catalog=self.catalog)
        binding_root = commitment("MOSAIC.UI.BROWSER_SESSION_BINDING.v0.1", {
            "input_root": self.payload.get("input_root"),
            "application": self.payload.get("application"),
            "catalog": self.catalog,
        })
        self.session_store = SQLiteBrowserSessionStore(session_database, binding_root) \
            if session_database is not None else None

    @property
    def descriptor(self):
        return self._direct.descriptor

    def _prune(self, now: float) -> None:
        expired = [key for key, value in self._sessions.items() if value.expires_monotonic <= now]
        for key in expired:
            self._sessions.pop(key).realizer.close()

    def negotiate_locale(self, requested_locale: str | None = None, accept_language: str | None = None) -> str:
        return resolve_locale(
            self.payload.get("application", {}).get("localization"), requested_locale, accept_language,
        )

    def create_session(
        self, owner_id: str | None = None, *, locale: str | None = None,
        accept_language: str | None = None,
    ) -> BrowserSession:
        selected_locale = self.negotiate_locale(locale, accept_language)
        if self.session_store is not None:
            realizer = BrowserRealizer(
                self.payload, self.layout_provider, catalog=self.catalog, locale=selected_locale,
            )
            stored = self.session_store.create(
                owner_id, realizer.snapshot(), ttl_seconds=self.ttl_seconds, max_sessions=self.max_sessions,
            )
            realizer.close()
            return self._materialize(stored)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            while len(self._sessions) >= self.max_sessions:
                oldest = min(self._sessions.values(), key=lambda value: value.last_access_monotonic)
                self._sessions.pop(oldest.session_id).realizer.close()
            session_id = secrets.token_urlsafe(24)
            session = BrowserSession(
                session_id=session_id,
                token=secrets.token_urlsafe(32),
                realizer=BrowserRealizer(
                    self.payload, self.layout_provider, catalog=self.catalog, locale=selected_locale,
                ),
                created_monotonic=now,
                expires_monotonic=now + self.ttl_seconds,
                last_access_monotonic=now,
                owner_id=owner_id,
            )
            self._sessions[session_id] = session
            return session

    def get_session(
        self, session_id: str, token: str | None = None, owner_id: str | None = None,
    ) -> BrowserSession:
        if self.session_store is not None:
            return self._materialize(self.session_store.load(
                session_id, token, owner_id, ttl_seconds=self.ttl_seconds,
            ))
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            session = self._sessions.get(session_id)
            if session is None:
                raise UIRefusal("BROWSER_SESSION_REFUSED", "ABSENT_OR_EXPIRED")
            if token is not None and not hmac.compare_digest(session.token, token):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "TOKEN_MISMATCH")
            if session.owner_id != owner_id:
                raise UIRefusal("BROWSER_SESSION_REFUSED", "OWNER_MISMATCH")
            session.last_access_monotonic = now
            session.expires_monotonic = now + self.ttl_seconds
            return session

    def apply_session(
        self, session_id: str, token: str, sequence: int, event: dict[str, Any],
        owner_id: str | None = None,
    ) -> tuple[dict[str, Any], int]:
        if self.session_store is not None:
            caught: list[Exception] = []

            def mutate(snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
                locale = snapshot.get("locale")
                realizer = BrowserRealizer(
                    self.payload, self.layout_provider, catalog=self.catalog, locale=locale,
                )
                realizer.load_snapshot(snapshot)
                try:
                    result = realizer.apply(copy.deepcopy(event))
                except Exception as exc:
                    caught.append(exc)
                    result = None
                updated = realizer.snapshot()
                realizer.close()
                return updated, result

            stored, result = self.session_store.mutate(
                session_id, token, owner_id, sequence, mutate, ttl_seconds=self.ttl_seconds,
            )
            if caught:
                raise caught[0]
            if result is None:
                raise UIRefusal("BROWSER_SESSION_STORE_REFUSED", "EMPTY_MUTATION_RESULT")
            return result, stored.next_sequence
        session = self.get_session(session_id, token, owner_id)
        with session.lock:
            if sequence != session.next_sequence:
                raise UIRefusal("BROWSER_EVENT_SEQUENCE_REFUSED", f"{sequence}!={session.next_sequence}")
            try:
                return session.realizer.apply(copy.deepcopy(event)), sequence + 1
            finally:
                session.next_sequence += 1

    def _materialize(self, stored: StoredBrowserSession) -> BrowserSession:
        locale = stored.snapshot.get("locale")
        realizer = BrowserRealizer(
            self.payload, self.layout_provider, catalog=self.catalog, locale=locale,
        )
        realizer.load_snapshot(stored.snapshot)
        return BrowserSession(
            session_id=stored.session_id, token=stored.token, realizer=realizer,
            created_monotonic=stored.created_epoch, expires_monotonic=stored.expires_epoch,
            last_access_monotonic=stored.last_access_epoch, next_sequence=stored.next_sequence,
            owner_id=stored.owner_id,
        )

    def client_material(self, session: BrowserSession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "session_token": session.token,
            "protocol": "mosaic.ui.realizer-protocol.v0.1",
            "next_sequence": session.next_sequence,
        }

    def evidence(self) -> dict[str, Any]:
        if self.session_store is not None:
            store = self.session_store.evidence()
            value = {
                "schema": "mosaic.ui.browser-session-manager-evidence.v0.1",
                "active_session_count": store["active_session_count"],
                "ttl_seconds": self.ttl_seconds, "max_sessions": self.max_sessions,
                "request_body_limit_bytes": BROWSER_POLICY["max_request_bytes"],
                "isolation": "COMMITTED_STATE_PER_SESSION_WITH_SQLITE_WRITE_SERIALIZATION",
                "storage_backend": "SQLITE_WAL", "store_evidence_commitment": store["commitment"],
                "authority_effect": "NONE",
            }
            value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_MANAGER.v0.1", value)
            return value
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            value = {
                "schema": "mosaic.ui.browser-session-manager-evidence.v0.1",
                "active_session_count": len(self._sessions),
                "ttl_seconds": self.ttl_seconds,
                "max_sessions": self.max_sessions,
                "request_body_limit_bytes": BROWSER_POLICY["max_request_bytes"],
                "isolation": "ONE_REALIZER_AND_LOCK_PER_SESSION",
                "storage_backend": "PROCESS_LOCAL",
                "authority_effect": "NONE",
            }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_MANAGER.v0.1", value)
        return value

    def readiness(self) -> dict[str, Any]:
        storage = self.session_store.readiness() if self.session_store is not None else {
            "schema": "mosaic.ui.browser-session-store-readiness.v0.1",
            "backend": "PROCESS_LOCAL", "integrity_check": "IN_MEMORY",
            "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
        }
        value = {
            "schema": "mosaic.ui.browser-session-manager-readiness.v0.1",
            "storage_backend": storage["backend"],
            "storage_commitment": storage.get("commitment"),
            "disposition": storage["disposition"], "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_SESSION_MANAGER_READINESS.v0.1", value)
        return value

    def _latest(self) -> BrowserRealizer:
        with self._lock:
            if not self._sessions:
                return self._direct
            return max(self._sessions.values(), key=lambda value: value.last_access_monotonic).realizer

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._direct.apply(copy.deepcopy(event))

    def snapshot(self) -> dict[str, Any]:
        return self._latest().snapshot()

    def project(self, width: int, height: int) -> dict[str, Any]:
        return self._direct.project(width, height)

    def document(self, width: int, height: int) -> str:
        return self._direct.document(width, height)

    def close(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                session.realizer.close()
            self._sessions.clear()
        self._direct.close()
        if self.session_store is not None:
            self.session_store.close()


def create_browser_server(
    payload: dict[str, Any], host: str = "127.0.0.1", port: int = 0,
    *, width: int = 1280, height: int = 800, layout_provider: LayoutProvider | None = None,
    catalog: dict[str, Any] | None = None, session_ttl_seconds: int = 900, max_sessions: int = 128,
    session_database: Path | None = None,
) -> tuple[ThreadingHTTPServer, BrowserSessionManager]:
    if host not in BROWSER_POLICY["allowed_hosts"]:
        raise UIRefusal("BROWSER_HOST_REFUSED", host)
    manager = BrowserSessionManager(
        payload, layout_provider, catalog=catalog,
        ttl_seconds=session_ttl_seconds, max_sessions=max_sessions, session_database=session_database,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args: Any) -> None:
            return None

        def _host(self) -> str:
            observed = self.headers.get("Host", "")
            name, separator, raw_port = observed.rpartition(":")
            if not separator or name not in BROWSER_POLICY["allowed_hosts"]:
                raise UIRefusal("BROWSER_HOST_HEADER_REFUSED", observed)
            try:
                observed_port = int(raw_port)
            except ValueError as exc:
                raise UIRefusal("BROWSER_HOST_HEADER_REFUSED", observed) from exc
            if observed_port != self.server.server_port:
                raise UIRefusal("BROWSER_HOST_HEADER_REFUSED", observed)
            return observed

        def _origin(self, host_header: str) -> None:
            origin = self.headers.get("Origin")
            if origin is not None and origin != f"http://{host_header}":
                raise UIRefusal("BROWSER_ORIGIN_REFUSED", origin)
            fetch_site = self.headers.get("Sec-Fetch-Site")
            if fetch_site not in {None, "none", "same-origin"}:
                raise UIRefusal("BROWSER_ORIGIN_REFUSED", fetch_site)

        def _cookie_session_id(self) -> str:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            morsel = cookie.get("Mosaic-Session")
            return morsel.value if morsel is not None else ""

        def _protocol(self) -> str:
            from .realizer import negotiate_protocol

            observed = self.headers.get("X-Mosaic-Protocol", "")
            return str(negotiate_protocol((observed,))["selected"])

        def _session(self, *, require_token: bool) -> BrowserSession:
            session_id = self.headers.get("X-Mosaic-Session") or self._cookie_session_id()
            token = self.headers.get("X-Mosaic-Session-Token") if require_token else None
            if not session_id or (require_token and not token):
                raise UIRefusal("BROWSER_SESSION_REFUSED", "MISSING_CREDENTIALS")
            return manager.get_session(session_id, token)

        def _send(
            self, status: int, body: bytes, content_type: str,
            *, headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, value: dict[str, Any], *, headers: dict[str, str] | None = None) -> None:
            self._send(status, json.dumps(value, sort_keys=True).encode("utf-8"), "application/json", headers=headers)

        def _refusal(self, exc: Exception, *, status: int = 409, headers: dict[str, str] | None = None) -> None:
            self._json(status, {
                "schema": "mosaic.ui.browser-refusal.v0.1",
                "disposition": "REFUSE",
                "refusal_code": getattr(exc, "code", "INVALID_REQUEST"),
                "detail": getattr(exc, "detail", str(exc)),
                "authority_effect": "NONE",
            }, headers=headers)

        def do_GET(self) -> None:
            try:
                host_header = self._host()
                self._origin(host_header)
                parsed = urlparse(self.path)
                if parsed.path == "/protocol":
                    from .realizer import SUPPORTED_PROTOCOLS, negotiate_protocol

                    offer = tuple(parse_qs(parsed.query).get("offer", SUPPORTED_PROTOCOLS))
                    self._json(200, {**negotiate_protocol(offer), "browser_policy": BROWSER_POLICY})
                    return
                if parsed.path == "/state":
                    self._protocol()
                    session = self._session(require_token=True)
                    with session.lock:
                        self._json(200, session.realizer.snapshot(), headers={
                            "X-Mosaic-Next-Sequence": str(session.next_sequence),
                        })
                    return
                if parsed.path != "/":
                    self._send(404, b"not found", "text/plain; charset=utf-8")
                    return
                query = parse_qs(parsed.query)
                view_width = int(query.get("width", [width])[0])
                view_height = int(query.get("height", [height])[0])
                if not 1 <= view_width <= 16384 or not 1 <= view_height <= 16384:
                    raise UIRefusal("BROWSER_VIEWPORT_REFUSED", f"{view_width}x{view_height}")
                session_id = self._cookie_session_id()
                requested_locale = query.get("locale", [None])[0]
                accept_language = self.headers.get("Accept-Language")
                selected_locale = manager.negotiate_locale(requested_locale, accept_language)
                try:
                    session = manager.get_session(session_id) if session_id else \
                        manager.create_session(locale=selected_locale)
                    if session.realizer.runtime.localization.locale != selected_locale:
                        session = manager.create_session(locale=selected_locale)
                except UIRefusal:
                    session = manager.create_session(locale=selected_locale)
                with session.lock:
                    body = render_document(
                        session.realizer.runtime, view_width, view_height,
                        client=manager.client_material(session),
                    ).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8", headers={
                    "Set-Cookie": f"Mosaic-Session={session.session_id}; Path=/; HttpOnly; SameSite=Strict",
                    "X-Mosaic-Session": session.session_id,
                    "X-Mosaic-Session-Token": session.token,
                    "X-Mosaic-Protocol": "mosaic.ui.realizer-protocol.v0.1",
                    "X-Mosaic-Next-Sequence": str(session.next_sequence),
                })
            except (UIRefusal, ValueError) as exc:
                self._refusal(exc, status=400)

        def do_POST(self) -> None:
            try:
                host_header = self._host()
                self._origin(host_header)
                if urlparse(self.path).path != "/event":
                    self._send(404, b"not found", "text/plain; charset=utf-8")
                    return
                self._protocol()
                session = self._session(require_token=True)
                if self.headers.get_content_type() != "application/json":
                    raise UIRefusal("BROWSER_CONTENT_TYPE_REFUSED", self.headers.get("Content-Type", ""))
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > int(BROWSER_POLICY["max_request_bytes"]):
                    raise UIRefusal("BROWSER_REQUEST_SIZE_REFUSED", str(size))
                sequence = int(self.headers.get("X-Mosaic-Event-Sequence", "0"))
                event = json.loads(self.rfile.read(size))
                if not isinstance(event, dict):
                    raise UIRefusal("BROWSER_EVENT_REFUSED", "NOT_OBJECT")
                result, next_sequence = manager.apply_session(session.session_id, session.token, sequence, event)
                self._json(200, result, headers={"X-Mosaic-Next-Sequence": str(next_sequence)})
            except (UIRefusal, ValueError, json.JSONDecodeError) as exc:
                next_sequence = None
                try:
                    current = self._session(require_token=True)
                    next_sequence = current.next_sequence
                except UIRefusal:
                    pass
                headers = {"X-Mosaic-Next-Sequence": str(next_sequence)} if next_sequence is not None else None
                self._refusal(exc, headers=headers)

    return ThreadingHTTPServer((host, port), Handler), manager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args(argv)
    from .pilot import build_payload

    server, _ = create_browser_server(build_payload(), args.host, args.port, width=args.width, height=args.height)
    print(json.dumps({"schema": "mosaic.ui.browser-server.v0.1", "url": f"http://{args.host}:{server.server_port}/",
                      "authority_effect": "NONE"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
