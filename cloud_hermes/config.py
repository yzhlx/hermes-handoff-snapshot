"""Cloud Hermes Core — configuration contract (Track D owns secret-handling policy).

OWNER: Track D (Security/Deployment). Any Track may READ config; only Track D changes the
secret-handling policy. Provider secret is read ONLY from the environment / secret manager
and is never persisted, returned, or logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


@dataclass
class Config:
    # Runtime
    env: str = "production"                       # production | development
    bind_host: str = "127.0.0.1"                  # reverse proxy forwards from 443
    port: int = 8080
    base_url: str = "http://127.0.0.1:8080"
    log_level: str = "INFO"

    # Persistence
    db_path: str = "hermes_cloud.db"

    # Auth / sessions (Track D)
    secret_key: str = ""                          # HMAC key for tokens/CSRF; required in prod
    admin_init_token: str = ""                    # one-time admin bootstrap token
    access_token_ttl_seconds: int = 43200         # 12h
    login_rate_limit_count: int = 5
    login_rate_limit_window_seconds: int = 900

    # Provider (key from env/secret manager ONLY — never in code, DB, logs, or frontend)
    provider_base_url: str = ""
    provider_api_key: str = ""                    # populated at runtime from env/secret manager
    provider_model: str = ""
    provider_protocol: str = "chat_completions"   # chat_completions | responses

    # Transport policy
    ai_transport: str = "cloud"                   # cloud | direct (direct = DEV ONLY, default off)
    mock_provider: bool = False                   # deterministic provider for tests
    mock_provider_reply: str = "MOCK_REPLY"       # default deterministic reply

    def is_production(self) -> bool:
        return self.env != "development"

    def direct_transport_allowed(self) -> bool:
        # Explicit development mode only; never in production builds.
        return (not self.is_production()) and self.ai_transport == "direct"

    def provider_configured(self) -> bool:
        return bool(self.provider_base_url and self.provider_api_key and self.provider_model)

    @classmethod
    def from_env(cls, overrides: dict | None = None) -> "Config":
        o = overrides or {}
        cfg = cls(
            env=_env("HERMES_ENV", "production"),
            bind_host=_env("HERMES_BIND_HOST", "127.0.0.1"),
            port=int(_env("HERMES_PORT", "8080") or 8080),
            base_url=_env("HERMES_BASE_URL", "http://127.0.0.1:8080"),
            log_level=_env("HERMES_LOG_LEVEL", "INFO"),
            db_path=_env("HERMES_DB_PATH", "hermes_cloud.db"),
            secret_key=_env("HERMES_SECRET_KEY", ""),
            admin_init_token=_env("ADMIN_INIT_TOKEN", ""),
            access_token_ttl_seconds=int(_env("HERMES_TOKEN_TTL", "43200") or 43200),
            login_rate_limit_count=int(_env("HERMES_LOGIN_LIMIT", "5") or 5),
            login_rate_limit_window_seconds=int(_env("HERMES_LOGIN_WINDOW", "900") or 900),
            provider_base_url=_env("PROVIDER_BASE_URL", ""),
            provider_api_key=_env("PROVIDER_API_KEY", ""),
            provider_model=_env("PROVIDER_MODEL", ""),
            provider_protocol=_env("PROVIDER_PROTOCOL", "chat_completions"),
            ai_transport=_env("AI_TRANSPORT", "cloud"),
            mock_provider=_env("HERMES_MOCK_PROVIDER", "0") in ("1", "true", "True"),
            mock_provider_reply=_env("HERMES_MOCK_REPLY", "MOCK_REPLY"),
        )
        return cfg
