"""Shared test harness: real HTTP server on a free port, temp DB, MockProvider, admin bootstrap.

These are REAL integration tests (actual HTTP requests through app.py), not mocks of the
transport. Only the Provider is mocked (deterministic), per task §18.
"""
import json
import os
import sys
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer

from cloud_hermes.config import Config
from cloud_hermes.main import CloudHermesApp
from cloud_hermes.provider import MockProvider
from cloud_hermes import app as app_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class TestHTTPServer(ThreadingHTTPServer):
    """Test-only server: non-daemon handler threads + graceful shutdown.

    daemon_threads=False lets in-flight handlers finish their response and close the
    socket normally (instead of being killed mid-send). shutdown() also joins the
    serve_forever thread so the test never tears down while the loop is still exiting.
    This removes the intermittent WinError 10053 "connection aborted" race that occurred
    when tearDown() shut the server down while a response was still on the wire.
    """

    daemon_threads = False

    def shutdown(self):
        super().shutdown()
        super().server_close()
        th = getattr(self, "_serve_thread", None)
        if th is not None:
            th.join(timeout=10)


class TestHandler(app_mod.Handler):
    """Test-only handler: HTTP/1.0 so each response closes its connection.

    Without this, urllib's opener reuses a keep-alive connection across requests; when
    tearDown() shuts the server down, the lingering idle socket is reset and the next
    reused request aborts with WinError 10053. HTTP/1.0 forces Connection: close after
    every response, eliminating that reuse race. API behavior is unchanged.
    """

    protocol_version = "HTTP/1.0"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def make_app(db_path=None, secret="test-secret", admin_token="INIT123", mock_reply="MOCK", env="development"):
    db_path = db_path or tempfile.mktemp(suffix=".db")
    cfg = Config(
        env=env, secret_key=secret, admin_init_token=admin_token, db_path=db_path,
        mock_provider=True, mock_provider_reply=mock_reply, bind_host="127.0.0.1", port=0,
        # A fake provider secret is set ONLY to make secret-hygiene assertions meaningful.
        # It is never used (MockProvider is injected) and must never appear in responses/DB.
        provider_api_key="sk-FAKE_PROVIDER_KEY_DO_NOT_LEAK",
        provider_base_url="https://provider.example/v1",
        provider_model="fake-model",
    )
    app = CloudHermesApp(cfg, provider=MockProvider(mock_reply))
    app.auth.bootstrap_admin(admin_token, "admin", "Password123")
    return app, cfg, db_path


def start_server(app, port=None):
    port = port or free_port()
    srv = TestHTTPServer((app.config.bind_host, port), TestHandler)
    srv.service = app.service
    srv.config = app.config
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    srv._serve_thread = t
    t.start()
    time.sleep(0.25)
    return srv, port


class Client:
    def __init__(self, base, token=None, cookie_jar=None):
        self.base = base
        self.token = token
        self.cookie_jar = cookie_jar or CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def set_token(self, token):
        self.token = token

    def request(self, method, path, body=None, headers=None, raw=False):
        url = self.base + path
        data = json.dumps(body or {}).encode() if body is not None else None
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        for k, v in (headers or {}).items():
            h[k] = v
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            resp = self.opener.open(req, timeout=5)
            raw_body = resp.read().decode("utf-8")
            if raw:
                return resp.status, raw_body
            return resp.status, (json.loads(raw_body) if raw_body else {})
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except Exception:
                payload = {"code": "INTERNAL_ERROR", "error": raw_body}
            return e.code, payload

    def login(self, username, password):
        st, data = self.request("POST", "/api/hermes/v1/auth/login", {"username": username, "password": password})
        if st == 200 and data.get("access_token"):
            self.set_token(data["access_token"])
        return st, data

    def health(self):
        return self.request("GET", "/api/hermes/v1/health")

    def chat(self, message, *, conversation_id=None, role_id="master", idempotency_key=None, headers=None):
        body = {"message": message, "role_id": role_id}
        if conversation_id:
            body["conversation_id"] = conversation_id
        h = dict(headers or {})
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return self.request("POST", "/api/hermes/v1/chat", body, headers=h)

    def get_run(self, run_id):
        return self.request("GET", f"/api/hermes/v1/runs/{run_id}")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
