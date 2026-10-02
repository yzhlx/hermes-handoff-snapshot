# Handoff — Hermes Cloud Core V1

**From:** Track D coordinator (single integration session). **Date:** 2026-07-22.
**Repository / worktree:** `integration/cloud-hermes-core-v1` (dir `cloud-hermes-core-v1/`).
**Baseline:** `ui/hermes-ui-2-program` @ `058e0a8`.

---

## What was delivered (real)

- **A working cloud Hermes main call chain** (`cloud_hermes/*`): Gateway → Auth → Context/Memory
  → Provider (env-key only, no silent fallback) → Event/Memory writeback.
- **38 automated tests, all passing** (`tests/cloud_hermes/*`).
- **Local deploy + rollback smoke** passed (`scripts/smoke_local.sh`, `rollback_smoke.sh`; logs in `logs/`).
- **Containerization**: `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `scripts/deploy.sh`, `scripts/rollback.sh`.
- **Client bridge + API wiring**: `outputs/learning-os-cloud-bridge.py`, cloud-mode branch in `outputs/learning-os-api.py` (local path retained).
- **Tablet/web UI**: `web/*` served same-origin from the cloud service.
- **Phase 0 frozen contracts** + all Track D reports + evidence under `artifacts/cloud-hermes-core-v1/`.

## Status (honest)

`PARTIALLY COMPLETED` — implementation, integration, containerization, tests, and local
validation are real and green. **Public-cloud deploy is `BLOCKED_CLOUD_ACCESS`** (no host/SSH/
running Docker daemon here). See `FINAL-REPORT.md` §status.

**Deployment-package repair (2026-07-23): `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS`.** The 6 known
deployment-package defects (loopback ingress, data/rollback DB-path mismatch, deploy health
probe, `https://127.0.0.1` in rollback, unified dir contract, missing repair artifact) are fixed,
committed, and verified (38 tests OK; isolated Docker smoke `ALL CHECKS PASSED` on the candidate
cloud host with temp resources only). Evidence + retrievable status in
`artifacts/cloud-deployment-package-repair/`. This clears the UI Integration prerequisite gate #2.
The `BLOCKED_CLOUD_ACCESS` note above refers to a *real public-cloud rollout*, which remains a
separate stage (no TLS/DNS here).

## How to run / verify locally

```bash
cd cloud-hermes-core-v1
# unit/integration/security tests (38, green)
C:\Users\user\.workbuddy\binaries\python\versions\3.13.12\python.exe \
  -m unittest discover -s tests/cloud_hermes -p "test_*.py"

# local deploy smoke (runs the container entrypoint as a process; mock provider)
bash scripts/smoke_local.sh

# rollback safety smoke
bash scripts/rollback_smoke.sh

# database checks
C:\Users\user\.workbuddy\binaries\python\versions\3.13.12\python.exe scripts/gen_db_checks.py
```

## How to deploy for real (operator)

1. On a host with Docker daemon running, export secrets (`HERMES_SECRET_KEY`, `PROVIDER_API_KEY`,
   `PROVIDER_BASE_URL`, `PROVIDER_MODEL`, `ADMIN_INIT_TOKEN`).
2. `docker compose -f docker-compose.yml build`
3. `docker compose -f docker-compose.yml run --rm hermes-cloud python -m cloud_hermes.main --bootstrap-admin "$ADMIN_INIT_TOKEN" admin "<pw>"`
4. `docker compose -f docker-compose.yml up -d`
5. `curl -fsS https://<domain>/api/hermes/v1/health`
6. Rollback: `BACKUP_DIR=/var/backups/hermes-cloud DEPLOY_DIR=/opt/hermes-cloud ./scripts/rollback.sh <stable_commit>`

Full runbook: `DEPLOYMENT-REPORT.md`.

## File / track ownership (do not cross-edit)

See `WORKTREE-OWNERSHIP.md` and `DATA-OWNERSHIP.md`. One module = one writer. Future work must
add new modules under the owning track; merges only in the integration worktree.

## Key contracts (frozen V1)

- `API-CONTRACT.md`, `AUTH-CONTRACT.md`, `MEMORY-CONTRACT.md`, `EVENT-CONTRACT.md`,
  `EXECUTION-NODE-CONTRACT.md`, `SECURITY-BOUNDARIES.md`.

## Next steps (V2, not in this V1)

- Real provider smoke with a supplied key; streaming (SSE) responses.
- Execution-node worker binary (actual command execution on tablet/PC).
- Shared rate-limit store + horizontal scaling; Postgres persistence swap.
- Semantic memory retrieval (embeddings); per-user promotion tuning.
- PC-OFF manual acceptance run on a real tablet (plan in `TABLET-OFFLINE-PC-ACCEPTANCE.md`).

## Do NOT claim

- That the cloud service is "live in production" — it is not; deploy is blocked here.
- That any capability exists from system prompt / class names / UI copy alone — it is backed by
  real code, tests, and the local smoke.
