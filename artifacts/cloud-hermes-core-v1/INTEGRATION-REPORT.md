# Integration Report — Hermes Cloud Core V1

**Scope:** How the four implementation tracks (A: Gateway/Runtime, B: Memory/Event/Persistence,
C: Client/Web, D: Security/Deployment/QA) were brought together in the single integration
worktree `integration/cloud-hermes-core-v1`, and how the end-to-end cloud Hermes main call
chain was verified.

**Date:** 2026-07-22. **Integration worktree:** `cloud-hermes-core-v1/`
(based on `ui/hermes-ui-2-program` @ `058e0a8`).

---

## 1. Integration Strategy (per task mandate)

- **Phase 0 first, frozen:** `PHASE-0-AUDIT.md`, `API-CONTRACT.md` (FROZEN V1), `DATA-OWNERSHIP.md`,
  `WORKTREE-OWNERSHIP.md`, `SECURITY-BOUNDARIES.md`, `MIGRATION-PLAN.md`, `ROLLBACK-PLAN.md`,
  `ACCEPTANCE-CRITERIA.md`, plus `MEMORY-CONTRACT.md`, `EVENT-CONTRACT.md`, `AUTH-CONTRACT.md`,
  `EXECUTION-NODE-CONTRACT.md`, `CURRENT-/TARGET-CALL-CHAIN.md`, `STATE.md`.
- **Strict ownership:** one file/subsystem = one writer. Cross-track edits were prohibited; all
  merges happened only in this integration worktree. `WORKTREE-OWNERSHIP.md` records the
  module→track mapping.
- **Single integration worktree:** all service modules (`cloud_hermes/*`), the client bridge
  (`outputs/learning-os-cloud-bridge.py`), the API wiring (`outputs/learning-os-api.py`), and
  the web UI (`web/*`) live here and were wired together here — not merged from parallel trees.

> Honesty note: the four "parallel worktrees" were executed as **module ownership boundaries**
> within one coordinator session (a single machine cannot truly parallelize git worktrees across
> independent agents here). The contracts and file ownership were still enforced as if parallel:
> no Track edited another Track's files. This is disclosed in `FINAL-REPORT.md`.

## 2. Target Call Chain (now REAL)

```
Learning OS Client/Web
   │  (HERMES_CLOUD_MODE=cloud, HERMES_CLOUD_URL, HERMES_CLOUD_TOKEN)
   ▼
CloudHermesClient  ──POST /api/hermes/v1/chat──▶  Cloud Hermes Gateway (app.py)
                                                       │
                                                       ▼
                                            AuthService (Bearer/CSRF)
                                                       │
                                          HermesService.run_orchestrator
                                           1. Idempotency-Key dedup
                                           2. ContextBuilder.build()  ──▶ MemoryStore.retrieve()
                                           3. Provider (Mock | Http, key=env only, NO fallback)
                                           4. RoleConversationCompleted event + writeback
                                           5. Memory candidate ONLY on explicit "请记住"
                                           6. run completed → hermes_run_id + event_ids
                                                       │
                                          EventStore.append() (append-only, triggers)
                                          MemoryStore (candidates / promoted)
```

Local-only fallback is **retained** in `learning-os-api.py` for `HERMES_CLOUD_MODE=off`; the
cloud bridge raises `CloudChatError` and does **not** silently fall back.

## 3. Module Wiring (integration worktree)

| Module | Track | Role in integration |
|---|---|---|
| `cloud_hermes/config.py` | D | Env-only config; secret key required in prod; no silent fallback flag |
| `cloud_hermes/db.py` | B | WAL SQLite, parameterized, idempotency records, migrations V1 |
| `cloud_hermes/events.py` | B | Append-only event store + no-update/no-delete triggers |
| `cloud_hermes/memory.py` | B | Namespaced memory retrieve / candidate / promote (threshold 0.6) |
| `cloud_hermes/execution_node.py` | B | Lease-based execution queue |
| `cloud_hermes/auth.py` | D | PBKDF2, sessions, rate limit, CSRF, revocation |
| `cloud_hermes/provider.py` | A | `MockProvider` (tests) / `HttpProvider` (env key, no fallback) |
| `cloud_hermes/context.py` | A | Memory retrieval → system prompt influence |
| `cloud_hermes/run_orchestrator.py` | A | `HermesService` end-to-end run orchestration |
| `cloud_hermes/app.py` | A | HTTP routing, auth middleware, CSRF, CORS, same-origin `/web` |
| `cloud_hermes/main.py` | A | Composition root + `--bootstrap-admin` |
| `cloud_hermes/client/*` | C | `CloudHermesClient` (Track C owns the client) |
| `outputs/learning-os-cloud-bridge.py` | C | `CloudBridge.chat()` — no silent fallback |
| `outputs/learning-os-api.py` | C | cloud-mode branch returns `hermes_run_id`/memory/events |
| `web/*` | C | Responsive tablet/web UI, login, "本轮依据" panel |

## 4. Integration Test Evidence

- **38 automated tests, all green** (`tests/cloud_hermes/*`): unit, storage, API, contract,
  integration, security. Saved to `test-results/full-suite.txt` → `Ran 38 tests ... OK`.
- **Integration tests (`test_integration.py`) specifically prove the real chain:**
  - real memory retrieval after seeding shared memory influences context (`memory_count>0`);
  - events survive a server restart (event store durability);
  - an offline execution node does **not** block chat;
  - lease claim/complete prevents double execution.
- **Local deploy smoke** (`scripts/smoke_local.sh`, `logs/deploy-smoke.log`): real process
  boots via the container's exact entrypoint, health→login→chat→idempotency→conversations→
  tasks→execution-nodes→run all return contract-correct payloads; unauth → 401.
- **Rollback smoke** (`scripts/rollback_smoke.sh`, `logs/rollback-smoke.log`): cloud DB
  preserved byte-identical, backup intact (non-destructive guarantee verified).

## 5. Integration Gaps Closed During Smoke

- Initially the smoke's token extraction failed (script bug, not a service bug). Fixed; the
  service was always returning a valid bearer token. **No service defect found.**
- DB path translation (`/f/...` vs `F:\...`) between Git-Bash and the managed Windows Python
  was corrected in the smoke harness so the persisted DB is at a stable, checkable location.

## 6. Outcome

The cloud Hermes main call chain is **integrated and verified** at the code, contract, and
runtime levels. The only unmet item is executing the container on a real cloud host / via the
running Docker engine, which is blocked by environment (no cloud host, no running Docker daemon
here). See `DEPLOYMENT-REPORT.md` and `FINAL-REPORT.md`.
