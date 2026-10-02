# GITIGNORE-REVIEW — Hermes Cloud Core V1

**Date:** 2026-07-22.

---

## 1. Pre-existing `.gitignore` (worktree root)

Covered: `/outputs/*.log`, `/outputs/__pycache__/`, `/outputs/visual-checks/`,
`/outputs/*.pptx`, `/work/presentations/learning-os-ui/tmp/...`,
`/artifacts/ui-2.0-program/screenshots/`, `/package*/`, `/build/`, `/dist/`, `/tmp/`,
`*.db`, `*.sqlite`, `*.sqlite3`, `__pycache__/`.

**Gaps for Cloud Hermes Core V1 publication:** missing rules for `.env`/secrets, WAL/SHM/journal
DB files, generic `*.log`/`*.out`, `logs/`, Python caches/coverage, `*.spec`/`_internal/`,
local runtime state (`work/`, `scratch_smoke.py`), and IDE/OS files.

## 2. Changes applied (appended, existing rules preserved)

Added (no existing rule overwritten):

```gitignore
# Secrets
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
secrets/
credentials/

# Runtime databases (WAL / SHM / journal)
*.db-wal
*.db-shm
*.db-journal

# Backups
backups/
*.backup
*.bak

# Logs (runtime + smoke outputs)
*.log
*.out
logs/

# Python
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/

# Build
*.spec
_internal/

# Local state / runtime
.local/
runtime/
data/
work/
scratch_smoke.py

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
desktop.ini
```

A precise exception `!.env.example` keeps the placeholder template tracked while ignoring real
`.env`.

## 3. Verification

```
git check-ignore scratch_smoke.py        # -> ignored (correct)
git ls-files | grep -E "scratch_smoke.py|^work/smoke|^work/rollback"   # -> empty (correct)
git status --short                       # -> clean after commits
```

`*.db` already covered the smoke DBs; the new `*.db-wal/*.db-shm/*.db-journal` hardens against
WAL/SHM leftovers. `work/` (whole runtime dir) and `logs/` are now ignored, so any future smoke
output can never be committed by accident.

## 4. `.env.example` added

Placeholder-only (`HERMES_SECRET_KEY=replace-me`, `PROVIDER_API_KEY=replace-me`,
`ADMIN_INIT_TOKEN=replace-me`, etc.). No real values. This is the only env template committed.
