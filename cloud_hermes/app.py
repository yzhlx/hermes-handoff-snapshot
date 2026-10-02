"""Cloud Hermes Core — HTTP API server (Track A owns).

OWNER: Track A (Gateway/Runtime). stdlib-only HTTP server (no external deps) so it runs on
the managed Python. Handles routing, auth middleware, CSRF for cookie POSTs, CORS, and
structured logging. Serves the static web UI from /web on the same origin (preferred deploy).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .errors import HermesError, status_for
from .run_orchestrator import HermesService

LOG = logging.getLogger("hermes.cloud")

MAX_BODY_BYTES = 1_048_576  # 1 MiB

PATH_RE = re.compile(r"^/api/hermes/v1(/.*)?$")
RUN_RE = re.compile(r"^/api/hermes/v1/runs/(?P<run_id>[^/]+)$")
CONV_RE = re.compile(r"^/api/hermes/v1/conversations/(?P<conv_id>[^/]+)$")
EXEC_NODE_RE = re.compile(r"^/api/hermes/v1/execution-nodes/(?P<device>[^/]+)/commands$")
EXEC_RESULT_RE = re.compile(r"^/api/hermes/v1/execution-nodes/(?P<device>[^/]+)/commands/(?P<cmd_id>[^/]+)/result$")

# Routes that require authentication.
PROTECTED_PREFIXES = (
    "/api/hermes/v1/chat",
    "/api/hermes/v1/runs",
    "/api/hermes/v1/conversations",
    "/api/hermes/v1/tasks",
    "/api/hermes/v1/execution-nodes",
    "/api/hermes/v1/auth/me",
)

# State-changing methods that require CSRF when authenticated via cookie.
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


def _client_ip(handler) -> str:
    return handler.client_address[0] if handler.client_address else "unknown"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "HermesCloudCore/1"

    # ---- low-level ----
    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > MAX_BODY_BYTES:
            raise HermesError("VALIDATION_ERROR", "Request body too large.", 413)
        raw = b""
        if length > 0:
            raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HermesError("VALIDATION_ERROR", "Invalid JSON body.", 400) from e

    def _send_json(self, status: int, payload: dict, extra_headers: dict | None = None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, err: HermesError):
        status = err.status or status_for(err.code, 400)
        self._send_json(status, err.payload())

    def _cors_headers(self):
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Idempotency-Key, X-CSRF-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Vary", "Origin")

    def _cookie_token(self):
        cookie = self.headers.get("Cookie")
        if not cookie:
            return None
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("session="):
                return part[len("session="):]
        return None

    def _authenticate(self):
        authz = self.headers.get("Authorization")
        cookie_token = self._cookie_token()
        session = self.server.service.auth.authenticate(authz, cookie_token)
        # CSRF check for cookie-authenticated state-changing requests.
        if not authz and cookie_token and self.command in STATE_CHANGING:
            csrf = self.headers.get("X-CSRF-Token")
            if not self.server.service.auth.csrf_valid(session, csrf):
                raise HermesError("AUTH_INVALID", "CSRF token missing or invalid.", 403)
        return session

    # ---- routing ----
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        path = urllib.parse.urlparse(self.path).path
        svc: HermesService = self.server.service
        try:
            # Health is public
            if method == "GET" and path == "/api/hermes/v1/health":
                return self._send_json(200, svc.health())

            # Auth endpoints (public)
            if method == "POST" and path == "/api/hermes/v1/auth/login":
                body = self._read_json()
                result = svc.auth.login(
                    body.get("username", ""), body.get("password", ""),
                    self.headers.get("X-Device-Id"), _client_ip(self),
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                body_b = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_header("Content-Length", str(len(body_b)))
                self.send_header("Set-Cookie",
                                 f"session={result['access_token']}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={svc.config.access_token_ttl_seconds}")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(body_b)
                return
            if method == "POST" and path == "/api/hermes/v1/auth/logout":
                session = self._authenticate()
                svc.auth.logout(session)
                return self._send_json(200, {"ok": True})
            if method == "GET" and path == "/api/hermes/v1/auth/me":
                session = self._authenticate()
                return self._send_json(200, {"user_id": session["user_id"], "device_id": session.get("device_id")})

            # Protected routes
            if any(path.startswith(p) for p in PROTECTED_PREFIXES):
                session = self._authenticate()
                user_id = session["user_id"]
                device_id = session.get("device_id")
                return self._protected(method, path, svc, user_id, device_id, session)

            # Same-origin static web UI
            if method == "GET" and (path == "/" or path.startswith("/web/") or path in ("/app.js", "/style.css", "/index.html")):
                return self._serve_static(path)

            return self._send_json(404, {"code": "NOT_FOUND", "error": "Not found"})

        except HermesError as e:
            LOG.warning("request failed %s %s code=%s msg=%s", method, path, e.code, e.message)
            return self._send_error(e)
        except Exception as e:  # never leak raw traces to clients
            LOG.exception("unexpected error on %s %s", method, path)
            return self._send_json(500, {"code": "INTERNAL_ERROR", "error": "Internal error"})

    def _protected(self, method, path, svc, user_id, device_id, session):
        if method == "POST" and path == "/api/hermes/v1/chat":
            body = self._read_json()
            idem = self.headers.get("Idempotency-Key")
            resp = svc.chat(
                user_id=user_id,
                conversation_id=body.get("conversation_id"),
                role_id=body.get("role_id", "master"),
                message=body.get("message", ""),
                client=body.get("client"),
                idempotency_key=idem,
                device_id=device_id,
            )
            return self._send_json(200, resp)
        if method == "GET":
            m = RUN_RE.match(path)
            if m:
                return self._send_json(200, svc.get_run(m.group("run_id")))
            if path == "/api/hermes/v1/conversations":
                return self._send_json(200, svc.list_conversations(user_id))
            m = CONV_RE.match(path)
            if m:
                return self._send_json(200, svc.get_conversation(user_id, m.group("conv_id")))
            if path == "/api/hermes/v1/tasks":
                return self._send_json(200, svc.list_tasks(user_id))
            if path == "/api/hermes/v1/execution-nodes":
                return self._send_json(200, svc.execution_nodes_status(device_id))
        if method == "POST":
            if path == "/api/hermes/v1/tasks":
                body = self._read_json()
                idem = self.headers.get("Idempotency-Key")
                return self._send_json(201, svc.create_task(user_id, body.get("title", ""), body.get("description"), idem))
            m = EXEC_NODE_RE.match(path)
            if m:
                body = self._read_json()
                idem = self.headers.get("Idempotency-Key")
                res = svc.enqueue_local_command(m.group("device"), body.get("command_type", "local_exec"),
                                                body.get("payload", {}), idem, user_id)
                return self._send_json(201, res)
        if method == "GET" and EXEC_NODE_RE.match(path):
            m = EXEC_NODE_RE.match(path)
            cmds = svc.claim_commands(m.group("device"), user_id)
            return self._send_json(200, {"items": cmds})
        if method == "POST" and EXEC_RESULT_RE.match(path):
            m = EXEC_RESULT_RE.match(path)
            body = self._read_json()
            ok = svc.complete_command(m.group("cmd_id"), body.get("lease_token", ""), body.get("result"), bool(body.get("failed")))
            return self._send_json(200, {"ok": ok})
        return self._send_json(404, {"code": "NOT_FOUND", "error": "Not found"})

    def _serve_static(self, path: str):
        web_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
        rel = "index.html" if path in ("/", "/index.html", "/web/") else path.lstrip("/")
        if rel.startswith("web/"):
            rel = rel[len("web/"):]
        full = os.path.normpath(os.path.join(web_root, rel))
        if not full.startswith(os.path.normpath(web_root)) or not os.path.isfile(full):
            return self._send_json(404, {"code": "NOT_FOUND", "error": "Not found"})
        ctype = "text/html; charset=utf-8" if full.endswith(".html") else (
            "application/javascript; charset=utf-8" if full.endswith(".js") else "text/css; charset=utf-8")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # silence default stderr logging; we use structured LOG
        return


def make_server(config, service: HermesService, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host or config.bind_host, port or config.port), Handler)
    srv.service = service
    srv.config = config
    srv.daemon_threads = True
    return srv
