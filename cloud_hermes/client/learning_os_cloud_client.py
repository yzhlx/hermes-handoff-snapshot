"""Cloud Hermes Client — used by the Windows local API adapter and the web UI (Track C owns).

OWNER: Track C (Learning OS Client / Web). Talks to Cloud Hermes over HTTPS with a Bearer
token + Idempotency-Key. Never receives or stores the Provider API key. No silent fallback
to a direct provider.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import urljoin


class CloudClientError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    @classmethod
    def from_payload(cls, payload: dict, status: int) -> "CloudClientError":
        code = payload.get("code", "INTERNAL_ERROR")
        msg = payload.get("error", "Cloud Hermes request failed")
        return cls(code, msg, status)


class CloudHermesClient:
    def __init__(self, base_url: str, token: str | None = None, device_id: str | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.device_id = device_id
        self.timeout = timeout

    def set_token(self, token: str) -> None:
        self.token = token

    # ---- low-level ----
    def _request(self, method: str, path: str, body: dict | None = None, *, anon: bool = False, idempotency_key: str | None = None) -> dict:
        url = self.base_url + path
        data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if not anon and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.device_id:
            headers["X-Device-Id"] = self.device_id
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = {"code": "INTERNAL_ERROR", "error": f"HTTP {e.code}"}
            raise CloudClientError.from_payload(payload, e.code)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CloudClientError("HERMES_UNAVAILABLE", "Cannot reach Cloud Hermes.", 503)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise CloudClientError("INVALID_RESPONSE", "Cloud Hermes returned non-JSON.", 502)

    # ---- auth ----
    def health(self) -> dict:
        return self._request("GET", "/api/hermes/v1/health", anon=True)

    def login(self, username: str, password: str) -> dict:
        result = self._request("POST", "/api/hermes/v1/auth/login",
                                {"username": username, "password": password}, anon=True)
        if result.get("access_token"):
            self.set_token(result["access_token"])
        return result

    def logout(self) -> dict:
        return self._request("POST", "/api/hermes/v1/auth/logout")

    def whoami(self) -> dict:
        return self._request("GET", "/api/hermes/v1/auth/me")

    # ---- chat ----
    def chat(self, message: str, *, conversation_id: str | None = None, role_id: str = "master",
             idempotency_key: str | None = None, client: dict | None = None) -> dict:
        return self._request(
            "POST", "/api/hermes/v1/chat",
            {"conversation_id": conversation_id, "role_id": role_id, "message": message,
             "client": client or {"type": "web", "device_id": self.device_id or "unknown", "client_version": "v1"}},
            idempotency_key=idempotency_key,
        )

    # ---- runs / conversations / tasks / execution ----
    def get_run(self, run_id: str) -> dict:
        return self._request("GET", f"/api/hermes/v1/runs/{run_id}")

    def list_conversations(self) -> dict:
        return self._request("GET", "/api/hermes/v1/conversations")

    def get_conversation(self, conv_id: str) -> dict:
        return self._request("GET", f"/api/hermes/v1/conversations/{conv_id}")

    def list_tasks(self) -> dict:
        return self._request("GET", "/api/hermes/v1/tasks")

    def create_task(self, title: str, description: str | None = None, idempotency_key: str | None = None) -> dict:
        return self._request("POST", "/api/hermes/v1/tasks", {"title": title, "description": description},
                             idempotency_key=idempotency_key)

    def execution_nodes(self) -> dict:
        return self._request("GET", "/api/hermes/v1/execution-nodes")

    def enqueue_local_command(self, device_id: str, command_type: str, payload: dict, idempotency_key: str | None = None) -> dict:
        return self._request("POST", f"/api/hermes/v1/execution-nodes/{device_id}/commands",
                             {"command_type": command_type, "payload": payload}, idempotency_key=idempotency_key)
