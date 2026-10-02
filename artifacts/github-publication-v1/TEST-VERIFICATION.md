# TEST-VERIFICATION — Hermes Cloud Core V1

**Date:** 2026-07-22. Ran on the final integration commit (`b76d18e`).

---

## 1. Command (exact)

```bash
cd "F:\Users\user\Documents\learning os-worktrees\cloud-hermes-core-v1"
C:\Users\user\.workbuddy\binaries\python\versions\3.13.12\python.exe \
  -m unittest discover -s tests/cloud_hermes -p "test_*.py"
```

> Note: `git -C "<path with spaces>"` mis-parses under Git-Bash; `cd` into the worktree is used.

## 2. Result

```
Ran 38 tests in 35.480s

OK
```

| Metric | Count |
|--------|-------|
| Passed | **38** |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |

(The Report-WARNING lines about `AUTH_INVALID` / `RATE_LIMITED` / `AUTH_REQUIRED` are
**expected negative-test output** from auth/rate-limit/authorization test cases — they prove
the controls reject bad input. The suite is green.)

## 3. Coverage (per FINAL-REPORT §12)

unit · storage (migration idempotency, FK, triggers, hostile content) · API (health/unauth/
login/logout/chat/run/conversations/tasks/execution-nodes/idempotency) · contract (health/chat/
run fields, stable codes, no-double-provider-call, client-cannot-forge-run-id) · integration
(real memory retrieval, events survive restart, offline node non-blocking, lease) · security
(SQLi, rate limit, CSRF, authz, secret hygiene, XSS, no-silent-fallback-prod).

## 4. Provider / environment notes

- **Mock provider only** for the suite (deterministic). `HttpProvider` (real key path) is
  implemented and refusal-tested but **not exercised against a live provider** (no key).
- **No real Provider smoke** was run (rule: only if key available).
- **Local real-process deploy + rollback smoke passed** (scripts/smoke_local.sh runs the exact
  container entrypoint as a plain process; health/login/chat/idempotency/read endpoints all
  contract-correct; unauth → 401). Documented in FINAL-REPORT §13 and DEPLOYMENT-REPORT §2.
- **Docker runtime smoke NOT executed**: the Docker daemon is not running in this environment,
  so `docker build`/`up` could not run. The identical container entrypoint was validated as a
  local process instead (documented, not faked). This is the `BLOCKED_CLOUD_ACCESS` item, not a
  test failure.

## 5. Additional checks performed

- `git diff --check` — no trailing-whitespace / conflict-marker issues introduced by the new
  commits (standard diff hygiene).
- DB fixture integrity — `database-checks/integrity.txt` confirms `PRAGMA integrity_check = ok`,
  0 FK violations, append-only triggers present (schema committed; the smoke DB itself excluded).

## 6. Reproducibility

The current final commit (`b76d18e`) is the commit under test. Because the code was previously
untracked, this run is the authoritative baseline for the RC1 tag (re-run not required; identical
source now committed).
