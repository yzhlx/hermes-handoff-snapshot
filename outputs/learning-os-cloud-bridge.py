"""Learning OS -> Cloud Hermes bridge (Track C owns).

OWNER: Track C (Learning OS Client / Web). This is the client proxy layer that the local
Windows API uses. When cloud mode is enabled it forwards chat to Cloud Hermes over HTTPS and
returns the cloud response (with a real hermes_run_id). When disabled, the caller falls back
to the existing local provider path (kept intact for rollback).

Security:
- Never reads or forwards the Provider API key. The cloud token is separate and is read only
  from env / credential manager, never logged.
- No silent fallback to a direct provider on cloud failure: a CloudChatError is raised and the
  caller surfaces the stable error code to the user.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path


class CloudChatError(Exception):
    """Raised when Cloud Hermes returns an error; carries a stable code + HTTP status."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent  # outputs/.. -> worktree root


def _device_id() -> str:
    p = Path(os.environ.get("HERMES_DEVICE_ID_FILE", str(Path.home() / ".hermes_device_id")))
    try:
        if p.exists():
            return p.read_text(encoding="utf-8").strip() or p.write_text("") or ""
    except Exception:
        pass
    did = "dev_" + uuid.uuid4().hex[:16]
    try:
        p.write_text(did, encoding="utf-8")
    except Exception:
        pass
    return did


def get_cloud_config() -> dict:
    enabled = os.environ.get("HERMES_CLOUD_MODE", "0") in ("1", "true", "True")
    url = os.environ.get("HERMES_CLOUD_URL", "")
    token = os.environ.get("HERMES_CLOUD_TOKEN", "")
    device_id = os.environ.get("HERMES_DEVICE_ID", "") or _device_id()
    return {
        "enabled": bool(enabled and url),
        "url": url.rstrip("/") if url else "",
        "token": token,
        "device_id": device_id,
    }


def _ensure_import() -> None:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


class CloudBridge:
    def __init__(self):
        self._cfg: dict | None = None

    def config(self) -> dict:
        if self._cfg is None:
            self._cfg = get_cloud_config()
        return self._cfg

    def is_enabled(self) -> bool:
        return self.config()["enabled"]

    def chat(self, chat_id: str, payload: dict, headers: dict | None = None) -> dict:
        """Forward a chat message to Cloud Hermes. Returns the cloud response dict.

        Raises CloudChatError on any cloud failure (no silent local-provider fallback).
        """
        cfg = self.config()
        if not cfg["enabled"]:
            return None
        _ensure_import()
        from cloud_hermes.client.learning_os_cloud_client import CloudHermesClient, CloudClientError

        client = CloudHermesClient(cfg["url"], token=cfg.get("token"), device_id=cfg.get("device_id"))
        message = payload.get("content") or payload.get("message", "")
        idem = (headers or {}).get("Idempotency-Key") if headers else None
        if not idem:
            idem = f"win:{chat_id}:{abs(hash(message))}"
        try:
            return client.chat(
                message,
                conversation_id=chat_id,
                role_id=payload.get("role_id", "master"),
                idempotency_key=idem,
                client={"type": "windows", "device_id": cfg.get("device_id"), "client_version": "v1"},
            )
        except CloudClientError as e:
            raise CloudChatError(e.code, e.message, e.status)
