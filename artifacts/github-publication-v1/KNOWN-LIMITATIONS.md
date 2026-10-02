# KNOWN-LIMITATIONS — GitHub Publication V1 & Cloud Hermes Core V1

**Date:** 2026-07-22.

---

## A. Publication-task limitations (this task)

1. **GitHub upload not completed** — `BLOCKED_GITHUB_REPOSITORY_REQUIRED`. No `gh` CLI, no stored
   GitHub credential, no private repo created, and the user's GitHub owner is unknown. Local
   preparation (audit, commit, tag) is complete and ready to push.
2. The annotated RC1 tag exists **locally only**; it is not on the remote until the user pushes.
3. The Draft PR is **not created**; it depends on the repo + push.

## B. Cloud Hermes Core V1 limitations (from FINAL-REPORT / KNOWN-LIMITATIONS.md)

1. **Public-cloud deploy not executed** (`BLOCKED_CLOUD_ACCESS`): no cloud host, no SSH, Docker
   daemon not running. Container definition + scripts are real and reviewed; final `docker build`
   + `up` is the operator's step on a live host.
2. Docker image not built here (daemon down); entrypoint validated as a local process instead.
3. In-process rate limiting (per single worker); no shared store before horizontal scaling.
4. Single SQLite file; Postgres swap planned for V2.
5. Browser cookie `Secure` flag verified at contract/unit level (local smoke is HTTP).
6. No refresh-token rotation / device fingerprinting beyond `device_id` + CSRF.
7. Memory promotion threshold fixed at 0.6; namespace-scoped; no vector/embedding search yet.
8. Real provider calls require `PROVIDER_API_KEY`; `HttpProvider` implemented and refusal-tested
   but not exercised against a live provider (no key).
9. Execution nodes are stubbed (lease queue + offline status real; executor binary is V2).
10. No streaming (SSE) responses.
11. Unrelated pre-existing tests fail (`test_windows_app_graceful_exit`,
    `test_ui_2_handwriting_entry` needs playwright) — outside V1, untouched.
12. No load/performance test; no fuzzing / dependency CVE scan (stdlib-only surface).

## C. Honesty notes

- The cloud path is a **real** running service (real `hermes_run_id`, real event writeback, real
  memory retrieval) proven by 38 tests + local smoke — not mocks presented as production.
- Tablet-while-PC-on is **never** reported as PC-off.
- Public-cloud deploy is explicitly marked blocked, not silently claimed done.
- The overall Hermes Cloud Core V1 status remains **PARTIALLY COMPLETED**; this publication task
  is **BLOCKED** at the upload step only.
