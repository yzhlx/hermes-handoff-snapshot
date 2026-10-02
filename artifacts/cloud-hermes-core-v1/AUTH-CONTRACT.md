# AUTH-CONTRACT.md

## Model (Track D, owned by D; used by A)
Single-user system today (no multi-tenant SaaS required). Public access MUST be authenticated.

### User / admin
- One admin user seeded on first boot via `ADMIN_INIT_TOKEN` (one-time). Password set, then
  the init token is invalidated (single-use, stored flag).
- Password hash: PBKDF2-HMAC-SHA256, 200k iterations, 16-byte random salt, stored as
  `pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`. Never stored plaintext.

### Sessions
- `sessions(id, user_id, token_hash, device_id, created_at, expires_at, revoked)`
- `token` = 32-byte random; only the SHA-256 hash is stored (token itself returned once to
  client as Bearer `access_token`).
- Expiry: access token 12h (configurable). Refresh: issue a new token on `/auth/refresh`
  (optional; V1 issues long-ish bearer + cookie).
- Revocation: `revoked=1` + delete; also device-level revoke (`revoke_device`).

### Browser SSO
- `Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=...`
- State-changing cookie requests require a `X-CSRF-Token` header matching the session's
  rotating CSRF token (issued on login, rotated on privileged action).

### Non-browser clients (Windows app, tablet web via Bearer)
- `Authorization: Bearer <access_token>`. No cookie needed.

### Rate limiting
- Login attempts: max 5 failures / 15 min per username+IP; returns `RATE_LIMITED` (429) and
  records a `LoginBlocked` audit event.

### Audit
- `LoginSucceeded`, `LoginFailed`, `Logout`, `TokenRevoked`, `DeviceRevoked` events appended
  (correlation_id = session id).

### Error codes
`AUTH_REQUIRED` (401, missing creds), `AUTH_EXPIRED` (401, expired/revoked),
`AUTH_INVALID` (401, bad token), `RATE_LIMITED` (429).

### Hard rules
- No long-lived token in `localStorage` (we use httpOnly cookie for browser; bearer in memory
  for SPA; Windows app stores bearer in OS credential store, not plaintext file).
- Provider key is NEVER used as an auth secret.
- Token/session values never logged.
