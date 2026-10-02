# STATE — Hermes Cloud Deployment Package Repair

**Generated:** 2026-07-23 (Beijing). **Author:** Deployment Package Repair Agent (嘉蟹).
**Worktree:** `cloud-hermes-core-v1` · **Branch:** `integration/cloud-hermes-core-v1`

## STATUS

```
CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS
```

This is the authoritative gate string consumed by the *Hermes Cloud UI Integration V1*
prerequisite gate (#2). It means all 6 known deployment-package defects are fixed, the
fixes are committed, and the package is verified by tests + a real (isolated, temp-resource)
Docker smoke on the candidate cloud host.

## Baseline

- Repo baseline before this repair: `ea81dce3ebb1445a73f6f155f0d565888740deeb` (HEAD).
- This repair introduces a NEW commit on top of that baseline (see HANDOFF.md / FINAL-REPORT.md
  for the resulting SHA). PR #1 on `integration/cloud-hermes-core-v1` stays **Draft**.
- Cloud host used for Docker verification: `ubuntu@129.211.0.213` (SSH + `sudo -E docker`,
  Docker 29.6.2). Only throwaway `/tmp` resources were used; no production defaults touched.

## Gate mapping (6 known problems -> fixes -> evidence)

| # | Problem | Fix location | Verification |
|---|---------|--------------|--------------|
| 1 | Container port not mapped to host `127.0.0.1:8080` | `docker-compose.yml` `ports: ["127.0.0.1:8080:8080"]` + `expose` | compose `config` host_ip=127.0.0.1; Docker smoke step [5] |
| 2 | Compose data path vs rollback DB path inconsistency | unified `HERMES_DATA_DIR` (default `/var/lib/hermes-cloud`); volume `${HERMES_DATA_DIR}:/data`; DB `/data/hermes_cloud.db` | compose `config` volume + `HERMES_DB_PATH`; rollback read `${HERMES_DATA_DIR}/hermes_cloud.db` |
| 3 | `deploy.sh` host health check cannot reach container | `deploy.sh` waits for container health AND `curl -fsS "$HEALTH_URL"` (loopback http) | Docker smoke step [4] healthy + loopback health OK |
| 4 | `rollback.sh` hardcodes `https://127.0.0.1` | `rollback.sh` now uses `HEALTH_URL` (http://127.0.0.1:8080/.../health) | grep: no `https://127` value; only a "never do this" comment |
| 5 | Deploy/backup/rollback dir contract not unified | unified defaulted vars `DEPLOY_DIR`/`HERMES_DATA_DIR`/`BACKUP_DIR`/`HEALTH_URL`/`COMPOSE_PROJECT_NAME` across all scripts | scripts + compose share the same contract |
| 6 | No retrievable repair-status artifact | this `artifacts/cloud-deployment-package-repair/` set + `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS` | this file |

## Verification summary (all green)

- **Unit/integration tests:** `Ran 38 tests ... OK` (Windows local).
- **Compile:** `python -m compileall cloud_hermes` → exit 0; `py_compile scripts/*.py` → exit 0.
- **Compose render:** `docker compose config` → loopback ingress only, unified data dir, DB path correct.
- **Docker smoke (isolated, cloud host):** `ALL CHECKS PASSED` (13 checks + SMOKE RESULT).
- **Rollback safety:** online SQLite backup verified (exists, integrity=ok, marker present); original DB not dropped.
- **Security scan:** no real secrets/keys/DB/`.env`; only `.env.example` placeholders; no `0.0.0.0` public ingress.

## Honest scope boundaries (prohibitions honored)

No real deployment; no HTTPS/nginx/cert/DNS changes (nginx.conf untouched, upstream still
`http://127.0.0.1:8080`); no real keys/passwords/DB; no SSH config change; no public
80/443/8080 bind; PR #1 not merged/readied; no Release/Tag; no `ui/hermes-ui-2-program`
edits; UI integration not started.

## Next action (for the UI Integration agent)

Re-run the *Hermes Cloud UI Integration V1* prerequisite gate #1–#6. Gate #2 should now
resolve to `CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS` (present in this repo). Proceed with the
UI → Cloud Core integration only after all 6 gates pass.
