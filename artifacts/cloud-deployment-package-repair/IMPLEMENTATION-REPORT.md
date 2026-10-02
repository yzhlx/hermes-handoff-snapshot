# IMPLEMENTATION-REPORT — Deployment Package Repair

## Scope

Repair of 6 known deployment-package defects in `cloud-hermes-core-v1` (baseline
`ea81dce3ebb1445a73f6f155f0d565888740deeb`), without performing a real deployment or
touching the UI worktree. Plus three collateral fixes discovered during verification.

## Files changed

| File | Change | Purpose |
|------|--------|---------|
| `docker-compose.yml` | rewrite ports/volumes/env | gate #1 loopback ingress; gate #2 unified data dir; container binds `0.0.0.0:8080` internally, host publishes `127.0.0.1:8080` |
| `scripts/deploy.sh` | rewrite | gate #3 host loopback health wait; gate #5 unified dir contract; secret-name-only validation; sanitized diagnostics |
| `scripts/rollback.sh` | rewrite | gate #2 correct DB path; gate #4 `HEALTH_URL` (http, not https); gate #5 unified dir contract; non-destructive online SQLite backup |
| `scripts/rollback_smoke.sh` | rewrite (canonical isolated smoke) | gate #6 verifiable, self-contained temp-resource Docker smoke |
| `.env.example` | add `HERMES_DATA_DIR`, `HERMES_MOCK_PROVIDER` | document the unified contract |
| `cloud_hermes/main.py` | `--bootstrap-admin` one-shot | bug fix: bootstrap must exit, not fall through to `app.start()` (blocked deploy/rollback bootstrap) |
| `tests/cloud_hermes/helpers.py` | HTTP/1.0 handler + graceful shutdown | bug fix: eliminate Windows `WinError 10053` test race so 38 tests pass |

## `docker-compose.yml` (gates #1, #2)

```yaml
services:
  hermes-cloud:
    ports:
      - "127.0.0.1:8080:8080"   # loopback ingress only; NEVER "8080:8080" (0.0.0.0)
    expose:
      - "8080"
    environment:
      HERMES_BIND_HOST: "0.0.0.0"   # inside container
      HERMES_DB_PATH: /data/hermes_cloud.db
      HERMES_MOCK_PROVIDER: "${HERMES_MOCK_PROVIDER:-0}"
    volumes:
      - "${HERMES_DATA_DIR:-/var/lib/hermes-cloud}:/data"
```

Public HTTPS (443 → `http://127.0.0.1:8080`) is a separate deployment stage and is **not**
configured here; `nginx.conf` upstream remains `http://127.0.0.1:8080` and was not modified.

## `scripts/deploy.sh` (gates #3, #5)

- `set -euo pipefail`, unified defaulted vars, `dc()` wrapper pins project name + compose file.
- Validates required secret **names** only (never prints values).
- Creates + validates `HERMES_DATA_DIR` / `BACKUP_DIR`.
- Runs `dc config`, `dc build`, `dc up -d`.
- Waits for container health **and** `curl -fsS "$HEALTH_URL"` with a timeout; on failure prints
  `dc ps`, health status, and secret-redacted last logs.

## `scripts/rollback.sh` (gates #2, #4, #5)

- Unified defaulted vars; reads DB from `${HERMES_DATA_DIR}/hermes_cloud.db` (matches compose).
- Optional systemd stop **only if** `hermes-cloud.service` exists.
- Performs a **non-destructive** online SQLite backup (`sqlite3` `connection.backup`) to
  `${BACKUP_DIR}/pre-rollback-<ts>.db`, verifies it (exists + non-zero + `integrity_check`),
  verifies the original integrity, **only then** runs `git checkout <stable>`.
- Health via `HEALTH_URL` (HTTP loopback), never `https://127.0.0.1`. Original DB is never dropped.

## Collateral fixes (required for verification to pass)

1. **`main.py` one-shot bootstrap** — without it, `docker compose run --rm ... --bootstrap-admin`
   fell through to `app.start()` and blocked forever, hanging the smoke. Now returns `0`.
2. **`helpers.py` test race** — `WinError 10053` on Windows from keep-alive connection reuse
   during server teardown. Fixed with an HTTP/1.0 test handler + non-daemon graceful shutdown.
3. **`rollback_smoke.sh` robustness** — unquoted `$DOCKER` so `DOCKER="sudo -E docker"` splits
   correctly (plain `sudo` strips compose env vars; `-E` preserves them), and an `ss` local-bind
   check that no longer false-positives on the peer-address column.

## Honesty note

The Docker verification used `sudo -E docker` on the candidate cloud host with **temp**
`/tmp` resources only (random project name, isolated `18080` loopback port, throwaway DB/backup
dirs). It does **not** constitute a production rollout. No cloud DNS/TLS/listener on 80/443/8080
was created.
