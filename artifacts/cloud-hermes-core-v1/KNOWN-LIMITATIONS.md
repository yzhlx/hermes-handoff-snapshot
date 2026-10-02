# Known Limitations — Hermes Cloud Core V1

**Date:** 2026-07-22. Honest list of what is NOT (yet) implemented or verified, so no capability
is over-claimed.

---

## 1. Environment / Deployment

- **Public-cloud deploy not executed** (`BLOCKED_CLOUD_ACCESS`): no cloud host, no SSH, and the
  Docker daemon is not running in this sandbox. The `Dockerfile`, `docker-compose.yml`,
  `nginx.conf`, and `scripts/deploy.sh`/`rollback.sh` are real and reviewed, and the service was
  validated via the identical container entrypoint as a local process. The final `docker build`
  + `up` on a live host is the operator's step (see `DEPLOYMENT-REPORT.md`).
- **Docker image not built here:** `docker build` was not run because the daemon is down. The
  image definition is valid; only the build artifact is absent.

## 2. Runtime / Scaling

- **In-process rate limiting:** login rate limiting lives in `AuthService._attempts` (memory,
  per process). The container runs a single `ThreadingHTTPServer` worker, so this is fine for
  V1, but it would not share state across multiple worker processes. Needs Redis/shared store
  before horizontal scaling.
- **No horizontal scaling / load balancing of the cloud service itself:** single instance; the
  nginx/LB layer is provided but multi-replica session sharing is out of scope for V1.
- **Single SQLite file:** fine for V1 scale; not suitable for high write concurrency. A managed
  Postgres/MySQL is the planned V2 persistence swap (schema is abstracted in `db.py`).

## 3. Auth / Session

- **Browser cookie `Secure` flag** requires HTTPS. The local smoke runs over HTTP, so the
  cookie+CSRF path is verified at the contract/unit level (`test_security.py`) but not over real
  TLS in this sandbox. Production (nginx TLS) satisfies it.
- **No refresh-token rotation / device fingerprinting** beyond `device_id` + CSRF. Acceptable
  for V1.
- **Admin bootstrap is one-time** via `ADMIN_INIT_TOKEN`; there is no self-service user
  registration yet (single admin + future users out of scope for V1).

## 4. Memory / Context

- **Memory promotion threshold** is fixed at 0.6 (`memory.py`); no per-user tuning UI yet.
- **Memory retrieval is namespace-scoped** (`user` / `shared` / `role`); cross-role leakage is
  prevented by `test_retrieve_excludes_other_roles`, but semantic dedup of candidates is minimal.
- **No vector/embedding search:** retrieval is exact/metadata filtered, not semantic similarity.
  Planned for V2.

## 5. Provider / Execution

- **Mock provider only for tests/smoke:** real provider calls require `PROVIDER_API_KEY`; the
  `HttpProvider` path is implemented and refusal-tested but was NOT exercised against a live
  provider here (no key). The "real Provider smoke only if key available" rule was honored.
- **Execution nodes are stubbed:** the lease queue and offline status are real, but the actual
  command execution on a tablet/PC worker is not implemented in this V1 (enqueue/claim/complete
  lifecycle is; the executor binary is a follow-up).
- **No streaming responses:** chat returns the full reply; SSE/streaming is V2.

## 6. Testing / QA

- **Unrelated pre-existing tests fail** in the broader `tests/` tree (`test_windows_app_graceful_exit`,
  `test_ui_2_handwriting_entry` needs `playwright`). These are **outside** Cloud Hermes Core V1
  and were not modified; the 38 cloud_hermes tests are the relevant suite and are green.
- **No load/performance test:** V1 has no throughput/latency benchmark.
- **No fuzzing / dependency CVE scan:** surface is stdlib-only, so risk is minimal, but no
  automated scanner was run.
