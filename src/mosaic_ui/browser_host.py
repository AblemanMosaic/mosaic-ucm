"""Explicitly configured WSGI host for the governed browser realizer."""
from __future__ import annotations

import argparse
import copy
import io
import json
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlparse
from wsgiref.simple_server import make_server

from .browser_realizer import BROWSER_POLICY, BrowserSession, BrowserSessionManager, render_document
from .canonical import commitment
from .headless import LayoutProvider
from .model import UIRefusal
from .realizer import PROTOCOL_SCHEMA, SUPPORTED_PROTOCOLS, negotiate_protocol
from .web_distribution import WEB_FILES, demo_document


ADAPTER_FILES = ("react.js", "vue.js", "svelte.js", "index.d.ts", "package.json")


StartResponse = Callable[[str, list[tuple[str, str]]], Any]
Authenticate = Callable[[dict[str, Any]], str | None]


@dataclass(frozen=True)
class BrowserHostPolicy:
    public_origin: str
    trusted_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...] = ()
    secure_cookies: bool = True
    frame_ancestors: tuple[str, ...] = ("'self'",)
    max_request_bytes: int = 65536
    authentication_required: bool = False
    session_storage: str = "PROCESS_LOCAL"

    def __post_init__(self) -> None:
        parsed = urlparse(self.public_origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "PUBLIC_ORIGIN")
        if parsed.scheme != "https" and self.secure_cookies:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "SECURE_COOKIE_REQUIRES_HTTPS")
        if not self.trusted_hosts or parsed.netloc not in self.trusted_hosts:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "PUBLIC_HOST_NOT_TRUSTED")
        for host in self.trusted_hosts:
            if not host or any(character in host for character in " /\\?#") or host == "*":
                raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", f"TRUSTED_HOST:{host}")
        for origin in self.allowed_origins:
            candidate = urlparse(origin)
            if candidate.scheme not in {"http", "https"} or not candidate.netloc \
                    or candidate.path not in {"", "/"} or origin == "*":
                raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", f"ALLOWED_ORIGIN:{origin}")
        if self.max_request_bytes <= 0 or self.max_request_bytes > 16 * 1024 * 1024:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "MAX_REQUEST_BYTES")
        if not self.frame_ancestors or any(";" in value for value in self.frame_ancestors):
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "FRAME_ANCESTORS")
        if self.session_storage not in {"PROCESS_LOCAL", "SQLITE_WAL_SHARED"}:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "SESSION_STORAGE")

    @property
    def origins(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.public_origin, *self.allowed_origins)))

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.browser-host-policy.v0.1",
            "public_origin": self.public_origin,
            "trusted_hosts": list(self.trusted_hosts),
            "allowed_origins": list(self.origins),
            "secure_cookies": self.secure_cookies,
            "frame_ancestors": list(self.frame_ancestors),
            "max_request_bytes": self.max_request_bytes,
            "authentication": "REQUIRED_DELEGATED_HOOK" if self.authentication_required else "OPTIONAL_DELEGATED_HOOK",
            "session_storage": self.session_storage,
            "tls_termination": "APPLICATION_OR_TRUSTED_REVERSE_PROXY",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_HOST_POLICY.v0.1", value)
        return value


class HostedBrowserApp:
    """WSGI application with host/origin checks and isolated governed sessions."""

    def __init__(
        self,
        payload: dict[str, Any],
        policy: BrowserHostPolicy,
        layout_provider: LayoutProvider | None = None,
        *,
        catalog: dict[str, Any] | None = None,
        width: int = 1280,
        height: int = 800,
        session_ttl_seconds: int = 900,
        max_sessions: int = 128,
        authenticate: Authenticate | None = None,
        session_database: Path | None = None,
    ) -> None:
        if not 1 <= width <= 16384 or not 1 <= height <= 16384:
            raise UIRefusal("BROWSER_VIEWPORT_REFUSED", f"{width}x{height}")
        self.policy = policy
        if policy.authentication_required and authenticate is None:
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "AUTHENTICATOR_REQUIRED")
        shared = session_database is not None
        if shared != (policy.session_storage == "SQLITE_WAL_SHARED"):
            raise UIRefusal("BROWSER_HOST_POLICY_REFUSED", "SESSION_STORAGE_CONFIGURATION_MISMATCH")
        self.authenticate = authenticate
        self.width, self.height = width, height
        self.manager = BrowserSessionManager(
            copy.deepcopy(payload), layout_provider, catalog=catalog,
            ttl_seconds=session_ttl_seconds, max_sessions=max_sessions, session_database=session_database,
        )
        self.request_count = 0
        self.refusal_count = 0

    def close(self) -> None:
        self.manager.close()

    def evidence(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.browser-host-evidence.v0.1",
            "policy_commitment": self.policy.as_dict()["commitment"],
            "request_count": self.request_count,
            "refusal_count": self.refusal_count,
            "sessions": self.manager.evidence(),
            "protocol": PROTOCOL_SCHEMA,
            "deployment_boundary": "WSGI_APPLICATION_REQUIRES_EXTERNAL_TLS_AND_PROCESS_SUPERVISION",
            "session_storage": self.policy.session_storage,
            "authentication": self.policy.as_dict()["authentication"],
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.BROWSER_HOST_EVIDENCE.v0.1", value)
        return value

    def _validate_request(self, environ: dict[str, Any]) -> str | None:
        host = str(environ.get("HTTP_HOST", ""))
        if host not in self.policy.trusted_hosts:
            raise UIRefusal("BROWSER_HOST_HEADER_REFUSED", host)
        origin = environ.get("HTTP_ORIGIN")
        if origin is not None and origin not in self.policy.origins:
            raise UIRefusal("BROWSER_ORIGIN_REFUSED", str(origin))
        fetch_site = environ.get("HTTP_SEC_FETCH_SITE")
        if fetch_site not in {None, "none", "same-origin", "same-site", "cross-site"}:
            raise UIRefusal("BROWSER_ORIGIN_REFUSED", str(fetch_site))
        if fetch_site == "cross-site" and origin not in self.policy.allowed_origins:
            raise UIRefusal("BROWSER_ORIGIN_REFUSED", str(origin or fetch_site))
        return str(origin) if origin is not None else None

    @staticmethod
    def _cookie_session_id(environ: dict[str, Any]) -> str:
        cookie = SimpleCookie()
        cookie.load(str(environ.get("HTTP_COOKIE", "")))
        morsel = cookie.get("Mosaic-Session")
        return morsel.value if morsel is not None else ""

    def _session(self, environ: dict[str, Any], *, require_token: bool) -> BrowserSession:
        session_id = str(environ.get("HTTP_X_MOSAIC_SESSION", "")) or self._cookie_session_id(environ)
        token = str(environ.get("HTTP_X_MOSAIC_SESSION_TOKEN", "")) if require_token else None
        if not session_id or (require_token and not token):
            raise UIRefusal("BROWSER_SESSION_REFUSED", "MISSING_CREDENTIALS")
        return self.manager.get_session(session_id, token, self._principal(environ))

    def _principal(self, environ: dict[str, Any]) -> str | None:
        if self.authenticate is None:
            return None
        principal = self.authenticate(environ)
        if not isinstance(principal, str) or not principal or len(principal) > 256:
            raise UIRefusal("BROWSER_AUTHENTICATION_REFUSED", "MISSING_OR_INVALID_PRINCIPAL")
        return principal

    def _headers(
        self, content_type: str, length: int, origin: str | None,
        extra: Iterable[tuple[str, str]] = (),
    ) -> list[tuple[str, str]]:
        frame_ancestors = " ".join(self.policy.frame_ancestors)
        headers = [
            ("Content-Type", content_type), ("Content-Length", str(length)),
            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; "
             f"script-src 'self' 'unsafe-inline'; frame-ancestors {frame_ancestors}"),
            ("Vary", "Origin"),
        ]
        if origin is not None:
            headers.extend([
                ("Access-Control-Allow-Origin", origin),
                ("Access-Control-Allow-Credentials", "true"),
            ])
        headers.extend(extra)
        return headers

    def _respond(
        self, start_response: StartResponse, status: str, body: bytes, content_type: str,
        origin: str | None, extra: Iterable[tuple[str, str]] = (),
    ) -> list[bytes]:
        start_response(status, self._headers(content_type, len(body), origin, extra))
        return [body]

    def _json(
        self, start_response: StartResponse, status: str, value: dict[str, Any], origin: str | None,
        extra: Iterable[tuple[str, str]] = (),
    ) -> list[bytes]:
        body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return self._respond(start_response, status, body, "application/json", origin, extra)

    def _body(self, environ: dict[str, Any]) -> dict[str, Any]:
        try:
            size = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError as exc:
            raise UIRefusal("BROWSER_REQUEST_SIZE_REFUSED", "INVALID") from exc
        if size <= 0 or size > self.policy.max_request_bytes:
            raise UIRefusal("BROWSER_REQUEST_SIZE_REFUSED", str(size))
        if str(environ.get("CONTENT_TYPE", "")).split(";", 1)[0].strip() != "application/json":
            raise UIRefusal("BROWSER_CONTENT_TYPE_REFUSED", str(environ.get("CONTENT_TYPE", "")))
        raw = environ.get("wsgi.input", io.BytesIO()).read(size)
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UIRefusal("BROWSER_EVENT_REFUSED", "INVALID_JSON") from exc
        if not isinstance(value, dict):
            raise UIRefusal("BROWSER_EVENT_REFUSED", "NOT_OBJECT")
        return value

    def __call__(self, environ: dict[str, Any], start_response: StartResponse) -> list[bytes]:
        self.request_count += 1
        origin: str | None = None
        try:
            origin = self._validate_request(environ)
            method, path = str(environ.get("REQUEST_METHOD", "GET")).upper(), str(environ.get("PATH_INFO", "/"))
            if method == "OPTIONS":
                return self._respond(start_response, "204 No Content", b"", "text/plain", origin, (
                    ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type, X-Mosaic-Session, X-Mosaic-Session-Token, X-Mosaic-Protocol, X-Mosaic-Event-Sequence"),
                    ("Access-Control-Max-Age", "600"),
                ))
            if method == "GET" and path == "/healthz":
                return self._json(start_response, "200 OK", {
                    "schema": "mosaic.ui.browser-host-health.v0.1", "status": "ok",
                    "policy_commitment": self.policy.as_dict()["commitment"], "authority_effect": "NONE",
                }, origin)
            if method == "GET" and path == "/readyz":
                try:
                    readiness = self.manager.readiness()
                    return self._json(start_response, "200 OK", {
                        "schema": "mosaic.ui.browser-host-readiness.v0.1", "status": "ready",
                        "storage": readiness, "authority_effect": "NONE",
                    }, origin)
                except UIRefusal as exc:
                    self.refusal_count += 1
                    return self._json(start_response, "503 Service Unavailable", {
                        "schema": "mosaic.ui.browser-host-readiness.v0.1", "status": "not-ready",
                        "refusal_code": exc.code, "detail": exc.detail, "authority_effect": "NONE",
                    }, origin)
            if method == "GET" and path == "/protocol":
                offers = tuple(parse_qs(str(environ.get("QUERY_STRING", ""))).get("offer", SUPPORTED_PROTOCOLS))
                return self._json(start_response, "200 OK", {
                    **negotiate_protocol(offers), "browser_policy": BROWSER_POLICY,
                    "host_policy": self.policy.as_dict(),
                }, origin)
            if method == "GET" and path in {"/web/demo", "/bindings/demo"}:
                body = demo_document(self.policy.public_origin).encode("utf-8")
                return self._respond(start_response, "200 OK", body, "text/html; charset=utf-8", origin)
            if method == "GET" and (path.startswith("/web/") or path == "/bindings/core.js"):
                name = "core.js" if path == "/bindings/core.js" else path.removeprefix("/web/")
                if name not in WEB_FILES:
                    return self._respond(start_response, "404 Not Found", b"not found", "text/plain; charset=utf-8", origin)
                from importlib.resources import files

                body = files("mosaic_ui").joinpath("web", name).read_bytes()
                content_type = "application/javascript" if name.endswith(".js") else \
                    "application/json" if name.endswith(".json") else "text/plain; charset=utf-8"
                return self._respond(start_response, "200 OK", body, content_type, origin)
            if method == "GET" and path.startswith("/adapters/"):
                name = path.removeprefix("/adapters/")
                if name not in ADAPTER_FILES:
                    return self._respond(start_response, "404 Not Found", b"not found", "text/plain; charset=utf-8", origin)
                from importlib.resources import files

                asset = files("mosaic_ui").joinpath("contrib", "web_adapters", name)
                if not asset.is_file():
                    return self._respond(start_response, "404 Not Found", b"not found", "text/plain; charset=utf-8", origin)
                body = asset.read_bytes()
                content_type = "application/javascript" if name.endswith(".js") else \
                    "application/json" if name.endswith(".json") else "text/plain; charset=utf-8"
                return self._respond(start_response, "200 OK", body, content_type, origin)
            if method == "GET" and path == "/state":
                negotiate_protocol((str(environ.get("HTTP_X_MOSAIC_PROTOCOL", "")),))
                session = self._session(environ, require_token=True)
                with session.lock:
                    return self._json(start_response, "200 OK", session.realizer.snapshot(), origin, (
                        ("X-Mosaic-Next-Sequence", str(session.next_sequence)),
                    ))
            if method == "POST" and path == "/event":
                negotiate_protocol((str(environ.get("HTTP_X_MOSAIC_PROTOCOL", "")),))
                session = self._session(environ, require_token=True)
                sequence = int(environ.get("HTTP_X_MOSAIC_EVENT_SEQUENCE", "0"))
                state, next_sequence = self.manager.apply_session(
                    session.session_id, session.token, sequence, self._body(environ), session.owner_id,
                )
                return self._json(start_response, "200 OK", state, origin, (
                    ("X-Mosaic-Next-Sequence", str(next_sequence)),
                ))
            if method != "GET" or path != "/":
                return self._respond(start_response, "404 Not Found", b"not found", "text/plain; charset=utf-8", origin)
            query = parse_qs(str(environ.get("QUERY_STRING", "")))
            width = int(query.get("width", [self.width])[0])
            height = int(query.get("height", [self.height])[0])
            if not 1 <= width <= 16384 or not 1 <= height <= 16384:
                raise UIRefusal("BROWSER_VIEWPORT_REFUSED", f"{width}x{height}")
            session_id = self._cookie_session_id(environ)
            principal = self._principal(environ)
            requested_locale = query.get("locale", [None])[0]
            accept_language = str(environ.get("HTTP_ACCEPT_LANGUAGE", "")) or None
            selected_locale = self.manager.negotiate_locale(requested_locale, accept_language)
            try:
                session = self.manager.get_session(session_id, owner_id=principal) if session_id else \
                    self.manager.create_session(principal, locale=selected_locale)
                if session.realizer.runtime.localization.locale != selected_locale:
                    session = self.manager.create_session(principal, locale=selected_locale)
            except UIRefusal:
                session = self.manager.create_session(principal, locale=selected_locale)
            with session.lock:
                body = render_document(
                    session.realizer.runtime, width, height, client=self.manager.client_material(session),
                ).encode("utf-8")
            cookie = f"Mosaic-Session={session.session_id}; Path=/; HttpOnly; SameSite=Strict"
            if self.policy.secure_cookies:
                cookie += "; Secure"
            return self._respond(start_response, "200 OK", body, "text/html; charset=utf-8", origin, (
                ("Set-Cookie", cookie), ("X-Mosaic-Session", session.session_id),
                ("X-Mosaic-Session-Token", session.token), ("X-Mosaic-Protocol", PROTOCOL_SCHEMA),
                ("X-Mosaic-Next-Sequence", str(session.next_sequence)),
            ))
        except (UIRefusal, ValueError) as exc:
            self.refusal_count += 1
            status = "401 Unauthorized" if getattr(exc, "code", "") == "BROWSER_AUTHENTICATION_REFUSED" else "409 Conflict"
            return self._json(start_response, status, {
                "schema": "mosaic.ui.browser-refusal.v0.1", "disposition": "REFUSE",
                "refusal_code": getattr(exc, "code", "INVALID_REQUEST"),
                "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE",
            }, origin)


def create_wsgi_app(
    payload: dict[str, Any], policy: BrowserHostPolicy, layout_provider: LayoutProvider | None = None,
    **kwargs: Any,
) -> HostedBrowserApp:
    return HostedBrowserApp(payload, policy, layout_provider, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--public-origin", required=True)
    parser.add_argument("--trusted-host", action="append", required=True)
    parser.add_argument("--allowed-origin", action="append", default=[])
    parser.add_argument("--insecure-cookie", action="store_true")
    parser.add_argument("--session-database", type=Path)
    args = parser.parse_args(argv)
    from .sufficiency import build_sufficiency_payload

    policy = BrowserHostPolicy(
        args.public_origin, tuple(args.trusted_host), tuple(args.allowed_origin),
        secure_cookies=not args.insecure_cookie,
        session_storage="SQLITE_WAL_SHARED" if args.session_database else "PROCESS_LOCAL",
    )
    app = create_wsgi_app(build_sufficiency_payload(), policy, session_database=args.session_database)
    server = make_server(args.host, args.port, app)
    print(json.dumps({
        "schema": "mosaic.ui.browser-host.v0.1", "url": args.public_origin,
        "server": "WSGI_REFERENCE_DEVELOPMENT_SERVER", "authority_effect": "NONE",
    }), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()
    return 0


__all__ = ["BrowserHostPolicy", "HostedBrowserApp", "create_wsgi_app"]


if __name__ == "__main__":
    raise SystemExit(main())
