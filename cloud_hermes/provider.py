"""Cloud Hermes Core — provider abstraction (Track A owns).

OWNER: Track A (Gateway/Runtime). Provider secret (PROVIDER_API_KEY) is read ONLY from the
environment / secret manager at runtime. It is never hardcoded, never persisted, never
returned to clients, never logged. `deepkey.top` is NOT hardcoded in business logic — the
base URL comes from configuration. No silent fallback in production.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from .errors import HermesError, status_for


class Provider:
    """Minimal provider contract."""

    name = "base"
    model = ""

    def complete(self, messages: list[dict], system: str, max_tokens: int) -> str:
        raise NotImplementedError


class MockProvider(Provider):
    """Deterministic provider for tests/CI. Never calls a real network or paid API."""

    name = "mock"
    model = "mock-model"

    def __init__(self, reply: str = "MOCK_REPLY"):
        self._reply = reply
        self.calls: list[dict] = []  # recorded for assertions

    def complete(self, messages: list[dict], system: str, max_tokens: int) -> str:
        self.calls.append({"messages": messages, "system": system, "max_tokens": max_tokens})
        # Echo a deterministic, content-aware reply so tests can assert retrieval influence.
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        return f"{self._reply}:{last_user[-32:]}" if last_user else self._reply


class HttpProvider(Provider):
    """OpenAI-compatible chat-completions provider. Key from env/secret manager only."""

    name = "configured-provider"

    def __init__(self, base_url: str, api_key: str, model: str, protocol: str = "chat_completions", timeout: int = 30):
        self.base_url = base_url
        self._api_key = api_key  # in-memory only
        self.model = model
        self.protocol = protocol
        self.timeout = timeout
        self._endpoint = self._normalize(base_url, protocol)

    @staticmethod
    def _normalize(base_url: str, protocol: str) -> str:
        parsed = urlsplit(base_url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HermesError("PROVIDER_INVALID_RESPONSE", "Provider base URL is invalid.", 502)
        path = parsed.path.rstrip("/")
        if protocol == "chat_completions":
            if not path.endswith("/chat/completions"):
                path = f"{path}/" if path else "/v1/"
                if not path.endswith("/chat/completions"):
                    path = f"{path.rstrip('/')}/chat/completions" if path != "/v1/" else "/v1/chat/completions"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

    def complete(self, messages: list[dict], system: str, max_tokens: int) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_tokens": max_tokens,
        }
        try:
            req = urllib.request.Request(
                self._endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise HermesError("PROVIDER_UNAVAILABLE", "Provider authentication failed.", status_for("PROVIDER_UNAVAILABLE"))
            if e.code == 429:
                raise HermesError("RATE_LIMITED", "Provider rate limited.", status_for("RATE_LIMITED"))
            raise HermesError("PROVIDER_UNAVAILABLE", "Provider rejected the request.", status_for("PROVIDER_UNAVAILABLE"))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise HermesError("PROVIDER_TIMEOUT", "Provider timed out or could not be reached.", status_for("PROVIDER_TIMEOUT"))
        try:
            data = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HermesError("PROVIDER_INVALID_RESPONSE", "Provider returned non-JSON.", status_for("PROVIDER_INVALID_RESPONSE"))
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise HermesError("PROVIDER_INVALID_RESPONSE", "Provider returned an invalid response.", status_for("PROVIDER_INVALID_RESPONSE"))
        if not isinstance(content, str) or not content.strip():
            raise HermesError("PROVIDER_INVALID_RESPONSE", "Provider returned an empty response.", status_for("PROVIDER_INVALID_RESPONSE"))
        return content.strip()


def build_provider(config) -> Provider:
    """Factory. Returns MockProvider for tests, else HttpProvider when configured."""
    if config.mock_provider:
        return MockProvider(config.mock_provider_reply)
    if not config.provider_configured():
        # In production, a missing provider is a hard error (no silent fallback to anything).
        raise HermesError("PROVIDER_UNAVAILABLE", "Provider is not configured on the server.", status_for("PROVIDER_UNAVAILABLE"))
    return HttpProvider(
        config.provider_base_url, config.provider_api_key, config.provider_model,
        config.provider_protocol, timeout=30,
    )
