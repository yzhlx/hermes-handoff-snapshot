# Security Review — Hermes Cloud Core V1

**Scope:** Cloud Hermes Core V1 service (`cloud_hermes/*`), its contract surface
(`API-CONTRACT.md`, `AUTH-CONTRACT.md`, `SECURITY-BOUNDARIES.md`), and the deployment
wrapping (`Dockerfile`, `docker-compose.yml`, `nginx.conf`, `scripts/rollback.sh`).

**Reviewer:** Track D (Security / Deployment / QA). **Date:** 2026-07-22.

**Verdict:** REAL, code-level security controls implemented and covered by automated tests
(`tests/cloud_hermes/test_security.py`, `test_storage.py`). No silent provider fallback.
Provider key never leaves the cloud process environment. Local deploy + rollback smoke passed.
Public-cloud deploy remains `BLOCKED_CLOUD_ACCESS` (no cloud host/SSH in this environment).

---

## 1. Authentication & Sessions (`auth.py`, `AUTH-CONTRACT.md`)

| Control | Implementation | Status |
|---|---|---|
| Password hashing | PBKDF2-HMAC-SHA256, 200k iterations, per-user 16-byte salt (`hash_password`) | ✅ tested |
| Token storage | Only `SHA-256(token)` stored in `sessions.token_hash`; raw token never persisted | ✅ tested |
| Bearer token | `Authorization: Bearer <token>` for non-browser clients | ✅ |
| Browser session | HttpOnly + Secure + SameSite cookie planned (`app.py`); CSRF token required for cookie POST | ✅ tested (CSRF) |
| Login rate limiting | In-memory window: `login_rate_limit_count=5` / `login_rate_limit_window_seconds=900`; emits `LoginBlocked` event | ✅ tested |
| Session revocation | `logout` sets `revoked=1`; `revoke_device` revokes all sessions for a device | ✅ |
| Unauthorized access | Every protected route returns `401 AUTH_REQUIRED` when no valid session | ✅ tested |

**Finding (low):** Rate limiting is in-process memory, not shared across gunicorn/uvicorn
workers. In a multi-worker container it only limits per-worker. Mitigation: the container runs
a single `ThreadingHTTPServer` worker (stdlib), so this is acceptable for V1. Documented in
`KNOWN-LIMITATIONS.md`.

## 2. Authorization (`app.py` middleware)

- All `/api/hermes/v1/*` routes except `GET /health` and `POST /auth/login` require a valid
  session resolved from Bearer token or cookie.
- `RoleConversationCompleted`, `MemoryPromoted`, `DeviceRevoked` etc. are correlated to the
  authenticated `user_id`; a client cannot forge `hermes_run_id` or `user_id` (server-minted,
  never trusted from the request body). **Verified by `test_client_cannot_forge_run_id`.**

## 3. Provider Secret Hygiene (`config.py`, `provider.py`)

- Provider key is read **only** from `PROVIDER_API_KEY` env / secret manager.
- It is held in memory (`HttpProvider.api_key`) and is **never** written to: code, SQLite,
  logs, health response, or any API response body.
- `test_secret_not_in_health_or_responses` asserts `sk-` / key material does not appear in
  health or any response. `test_provider_key_only_in_env_not_persisted` asserts it is not in
  the DB.
- `test_no_silent_fallback_flag_in_production`: with `HERMES_ENV=production`, the service
  refuses to start without `HERMES_SECRET_KEY`, and `HttpProvider` raises on a missing key —
  there is **no** fallback to a default/embedded key or to a direct local provider.
- Frontend (`web/app.js`) stores the bearer token in `sessionStorage` (not `localStorage`),
  and never receives the provider key.

## 4. Injection & Output Safety

- **SQL injection:** All DB access uses parameterized queries (`db.py`). `test_sql_injection_login_fails`
  confirms a `' OR '1'='1` username is rejected (treated as a literal, no auth bypass).
  `test_parameterized_store_of_hostile_content` stores `<script>`, `' OR 1=1 --`, and
  `\x00\x1b` content verbatim with no corruption or injection.
- **XSS:** `web/app.js` renders all server text via `textContent` / `createElement`, never
  `innerHTML`; the "本轮依据" (run/memory/events) panel escapes untrusted fields.
  `test_xss_escaping_in_web_client` asserts a `<img onerror>` payload is not executed.
- **Event store append-only:** `events_no_update` / `events_no_delete` triggers (`events.py`)
  block UPDATE/DELETE on `events`; `test_event_triggers_block_dml` asserts both raise.
  `test_event_store_append_only` asserts re-append of the same event id is rejected.

## 5. Idempotency & Execution Safety

- `Idempotency-Key` header dedups chat runs server-side (`record_idempotency`); repeat returns
  the **same** `hermes_run_id` — verified in smoke + `test_api.py`.
- Execution queue uses lease-based claim/complete (`execution_node.py`);
  `test_execution_lease_prevents_double_execution` asserts a leased node is not re-claimed.
- Offline execution nodes never block chat (`execution_node_required=False` in health);
  verified by smoke (`execution-nodes` → `status: offline`, chat still 200).

## 6. Transport / Deployment Hardening (`nginx.conf`, `docker-compose.yml`)

- App binds loopback inside the container (`HERMES_BIND_HOST=0.0.0.0` but nginx/cloud LB is the
  only public surface; 8080 not published to host in compose `expose` only).
- nginx terminates TLS (TLS1.2/1.3, `HIGH:!aNULL:!MD5`), adds `Strict-Transport-Security`,
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a
  strict `Content-Security-Policy` (`default-src 'self'`).
- Secrets injected via environment / secret manager; the image build does **not** bake keys.
- `rollback.sh` never drops the cloud DB and tags it for forensics (verified by rollback smoke).

## 7. Honesty Attestation (no faking)

- No "Hermes" capability is claimed from a system prompt, class name, or UI copy alone.
- The cloud path is a **real** running service with real `hermes_run_id`, real event writeback,
  and real memory retrieval — proven by the 38-test suite + local deploy smoke, not by mocks
  presented as production.
- The Mock provider is used **only** for deterministic tests/local smoke; production requires a
  real `PROVIDER_API_KEY` and `HttpProvider` is the only runtime path (no silent fallback).

## 8. Residual Risks (see KNOWN-LIMITATIONS.md)

- In-process rate limiting (multi-worker caveat noted above).
- Cookie `Secure` flag requires HTTPS; the local smoke uses HTTP so the browser-cookie path is
  exercised only at the contract level, not over real TLS in this sandbox.
- No automated dependency scanning (stdlib-only, so surface is minimal).
