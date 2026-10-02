# SECURITY-BOUNDARIES.md

## Authorized this task
1. New cloud Hermes API. 2. New cloud persistence. 3. New cloud auth. 4. Protected public
HTTPS entry. 5. Change Learning OS AI request protocol. 6. Change client AI config. 7. DB
migrations. 8. New Run/Memory/Event/ToolRun models. 9. Cloud static web deploy. 10. Windows
client connects to cloud Hermes. 11. Explicit rollback switch keeps old provider code, but
production forbids auto-fallback. 12. Independent branches/worktrees + test/integration.

## Forbidden this task
- Exposing the local Windows Python service to the public internet.
- Sending Provider API Key to the browser.
- Writing secrets into SQLite, frontend code, localStorage, or logs.
- Deleting the verified-working local version.
- One-shot migrating/overwriting all existing CRUD data.
- Making Obsidian/Anki the cloud source of truth.
- Overwriting production before testing.
- Faking Hermes access by renaming things.
- Letting the model CLAIM it called Memory/Tool as proof of implementation.
- Auto-writing all chat content into long-term memory.

## Concrete boundary controls implemented
- Provider key is read ONLY from env / secret manager at runtime (`PROVIDER_API_KEY`); never
  persisted, never returned, never logged. Health endpoint reports `provider_configured`
  (boolean) without revealing the key.
- Cloud service binds loopback / internal interface behind a reverse proxy on 443; DB is not
  exposed publicly; local Windows service stays bound to 127.0.0.1 only.
- Auth: PBKDF2-HMAC-SHA256 password hash (per-user salt), DB-backed sessions with expiry,
  HttpOnly+Secure+SameSite cookies, Bearer access token for non-browser clients, CSRF token
  for cookie state-changing requests, login attempt rate limiting, session/device revocation,
  audited login/logout events.
- Local Execution Node pulls from cloud (outbound only); cloud never scans the user LAN.
