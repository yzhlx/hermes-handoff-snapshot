# PRIVATE-DATA-SCAN — Hermes Cloud Core V1

**Date:** 2026-07-22. Goal: ensure no production database, no user private learning data, no
token-bearing logs, and no build zips are uploaded.

---

## 1. Patterns / extensions searched

```
*.db *.sqlite *.sqlite3 *.db-wal *.db-shm *.db-journal
*.backup *.bak *.zip *.tar *.gz *.log *.out
```

Plus a content scan of `logs/` and `api-results/` for `token`, `bearer`, `authorization`,
`secret`, `password`, `api_key`, `cookie`.

## 2. Findings (by location)

### A. Integration worktree `cloud-hermes-core-v1/`

| Path | Type | Decision |
|------|------|----------|
| `work/smoke-data/hermes_cloud.db` | runtime SQLite (smoke) | **EXCLUDED** — `*.db` git-ignored; not committed |
| `work/rollback-backup/pre-rollback-20260722-230203.db` | rollback backup DB | **EXCLUDED** — `*.db` ignored; not committed |
| `work/presentations/learning-os-ui/tmp/*` | pre-existing UI test fixtures (tracked on base) | left as-is; not Cloud Hermes data, no secrets |
| `scratch_smoke.py` | dev scratch (fake creds) | **EXCLUDED** — added to `.gitignore`; not committed |

### B. Loose artifact dir `learning os-worktrees/artifacts/cloud-hermes-core-v1/`

| Path | Type | Decision |
|------|------|----------|
| `logs/deploy-smoke.log` (9.6 KB) | runtime smoke log; contains `access_token` | **EXCLUDED** — runtime log, token-bearing |
| `logs/rollback-smoke.log` (1.6 KB) | runtime log; contains `access_token` | **EXCLUDED** |
| `logs/server.out` | server stdout | **EXCLUDED** |
| `api-results/login.json` | contains real `access_token` + `csrf_token` | **EXCLUDED** — token-bearing API response |
| `api-results/{chat,conversations,...}.json` | contract payloads (no token except login) | **EXCLUDED** as a set (login.json taints the dir) |
| `local-docker-smoke.zip` (4.6 KB) | build/product artifact | **EXCLUDED** — build product |
| `test-results/full-suite.txt` | `Ran 38 tests ... OK` | **INCLUDED** — desensitized evidence |
| `database-checks/schema.sql` | 16-table schema (no data) | **INCLUDED** — schema only |
| `database-checks/integrity.txt` | `PRAGMA integrity_check = ok`, 0 FK violations | **INCLUDED** — metadata |
| `database-checks/tables.csv` | table inventory | **INCLUDED** — metadata |
| `*.md` (reports + contracts) | documentation | **INCLUDED** — verified token-free |

## 3. Production / private-data checks

- **No `learning-os-v2.db` / `learning-os.db` production copy** present anywhere.
- **No real Cloud Hermes database** (only the smoke `hermes_cloud.db`, excluded).
- **No WAL/SHM** files (the smoke DB was checkpointed; not committed anyway).
- **No production database backup** uploaded.
- **No user private learning data** (chat/tasks/wrong-answers/memory) — the smoke DB is synthetic
  and excluded; nothing private reaches the repo.
- **No user private PDF / image / Obsidian content.**
- **No token-bearing API response** in the committed set.
- **No private-content server log** in the committed set.

## 4. Conclusion

All prohibited artifacts are excluded by a combination of (a) explicit non-inclusion and
(b) `.gitignore` rules (`*.db`, `*.db-wal/shm/journal`, `*.log`, `*.out`, `logs/`, `work/`,
`*.zip`, `*.backup`, `*.bak`, `scratch_smoke.py`). The committed set contains only source,
tests, deploy scripts, contracts, reports, and desensitized schema/test evidence.
