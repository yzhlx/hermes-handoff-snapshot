# HANDOFF — Deployment Package Repair → UI Integration

## What was delivered

The 6 known deployment-package defects in `cloud-hermes-core-v1` (baseline
`ea81dce3ebb1445a73f6f155f0d565888740deeb`) are fixed, committed, and verified.
Authoritative status: **`CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS`** (see `STATE.md`).

## New commit

- Commit message: `fix(cloud): align loopback ingress persistence and rollback`
- Branch: `integration/cloud-hermes-core-v1` (PR #1 remains **Draft**).
- Files changed (7): `.env.example`, `cloud_hermes/main.py`, `docker-compose.yml`,
  `scripts/deploy.sh`, `scripts/rollback.sh`, `scripts/rollback_smoke.sh`,
  `tests/cloud_hermes/helpers.py` — plus this `artifacts/cloud-deployment-package-repair/` set.

## Verification at a glance

| Check | Result |
|-------|--------|
| 38-test suite | `Ran 38 tests ... OK` |
| `compileall` / `py_compile` | exit 0 |
| `docker compose config` | loopback ingress + unified data dir |
| Docker smoke (isolated, cloud host) | `ALL CHECKS PASSED` |
| Rollback safe backup | exists / integrity ok / marker preserved / original not dropped |
| Security scan | no real secrets/keys/DB; no public `0.0.0.0` ingress |

## For the UI Integration agent

1. Re-run the prerequisite gate #1–#6. Gate #2 should now resolve to
   `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS` (present in this repo).
2. Do **not** rely on the isolated smoke's temp resources for production; use the unified
   contract vars (`DEPLOY_DIR`, `HERMES_DATA_DIR`, `BACKUP_DIR`, `HEALTH_URL`,
   `COMPOSE_PROJECT_NAME`) documented in `IMPLEMENTATION-REPORT.md` and `.env.example`.
3. Public HTTPS (443 → `http://127.0.0.1:8080`) is a separate stage — `nginx.conf` and the
   compose file deliberately stop at loopback ingress.

## How to re-run the isolated smoke

```
# on a Docker host (e.g. the candidate cloud host) with sudo docker:
DOCKER="sudo -E docker" PYTHON=python3 bash scripts/rollback_smoke.sh
# or, if docker works without sudo:
DOCKER=docker PYTHON=python3 bash scripts/rollback_smoke.sh
```

It is self-contained and uses only throwaway `/tmp` resources; it never touches production
defaults or public ports.
