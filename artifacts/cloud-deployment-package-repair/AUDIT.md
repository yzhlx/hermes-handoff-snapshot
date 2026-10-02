# AUDIT — Deployment Package Defect Mapping

Pre-repair defect list (from the repair mandate) and the exact change that closes each item.
All file paths are relative to the `cloud-hermes-core-v1` worktree root.

## 1. Container port not mapped to host `127.0.0.1:8080`

- **Before:** `docker-compose.yml` published `8080:8080` (binds `0.0.0.0` on the host) — a
  public-ingress exposure, violating the loopback-ingress contract.
- **After:** `ports: ["127.0.0.1:8080:8080"]` plus `expose: ["8080"]`. The app still binds
  `0.0.0.0:8080` *inside* the container (required for the healthcheck and the reverse proxy
  on `127.0.0.1`); the host publishes it **only** on loopback.
- **Evidence:** `docker compose config` → `host_ip: 127.0.0.1, target: 8080, published: "8080"`.
  Docker smoke step [5]: `port bound to 127.0.0.1` + `no 0.0.0.0 listener`.

## 2. Compose data persistence path vs rollback script DB path inconsistency

- **Before:** compose wrote the DB via a volume, but `rollback.sh` read `${DEPLOY_DIR}/data/...`
  (a different path), so a rollback could not locate the live DB.
- **After:** single source of truth `HERMES_DATA_DIR` (default `/var/lib/hermes-cloud`).
  Compose mounts `${HERMES_DATA_DIR}:/data`; container DB path `HERMES_DB_PATH=/data/hermes_cloud.db`.
  `deploy.sh` creates + validates `HERMES_DATA_DIR`/`BACKUP_DIR`; `rollback.sh` reads
  `${HERMES_DATA_DIR}/hermes_cloud.db`. Both reference the identical host path.
- **Evidence:** compose `config` volume `source: <HERMES_DATA_DIR> -> target: /data`;
  `HERMES_DB_PATH: /data/hermes_cloud.db`; rollback `DB="${HERMES_DATA_DIR}/hermes_cloud.db"`.

## 3. `deploy.sh` host health check cannot reach container

- **Before:** deploy relied solely on `docker ps`/container health; the host-side HTTP health
  (the actual readiness signal) was not awaited, so a "deployed" service could be unreachable.
- **After:** `deploy.sh` waits for **both** container health (`docker inspect` health status)
  and a real `curl -fsS "$HEALTH_URL"` (loopback `http://127.0.0.1:8080/api/hermes/v1/health`).
  On timeout it dumps `dc ps`, health status, and sanitized (secret-redacted) logs. No 80/443/HTTPS
  dependency.
- **Evidence:** Docker smoke step [4] `container healthy` + `loopback health OK`.

## 4. `rollback.sh` wrongly hardcodes `https://127.0.0.1`

- **Before:** rollback health probe used `https://127.0.0.1` — wrong scheme (no TLS terminates
  at the container; TLS is a separate nginx/LB stage) and would always fail.
- **After:** rollback uses `HEALTH_URL` (`http://127.0.0.1:8080/api/hermes/v1/health`), the same
  loopback HTTP URL as deploy. No `https://127.0.0.1` value remains (only a comment warning
  against it).
- **Evidence:** grep shows `HEALTH_URL=http://127.0.0.1:8080/.../health`; no hardcoded `https://127`
  runtime value.

## 5. Deployment / backup / rollback directory contract not unified

- **Before:** scripts used ad-hoc, diverging paths for deploy root, data, and backups.
- **After:** every script sources the same unified, defaulted contract:
  `DEPLOY_DIR=/opt/hermes-cloud`, `HERMES_DATA_DIR=/var/lib/hermes-cloud`,
  `BACKUP_DIR=/var/backups/hermes-cloud`, `HEALTH_URL=http://127.0.0.1:8080/api/hermes/v1/health`,
  `COMPOSE_PROJECT_NAME=hermes-cloud`, `DOCKER` (prefix). `deploy.sh`/`rollback.sh` create and
  validate the data + backup dirs up front.
- **Evidence:** shared variable block in `deploy.sh` + `rollback.sh`; smoke uses the same names.

## 6. No formal retrievable deployment-package-repair status artifact

- **Before:** there was no committed, grep-able status proving the repair was done — which is
  exactly why the UI Integration gate #2 blocked earlier.
- **After:** this `artifacts/cloud-deployment-package-repair/` document set, anchored by
  `STATE.md` containing the literal `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS`.

## Verification artifacts in this directory

`STATE.md` · `AUDIT.md` · `IMPLEMENTATION-REPORT.md` · `TEST-REPORT.md` · `DOCKER-SMOKE.md` ·
`ROLLBACK-SMOKE.md` · `SECURITY-REVIEW.md` · `KNOWN-LIMITATIONS.md` · `HANDOFF.md` ·
`FINAL-REPORT.md`.
