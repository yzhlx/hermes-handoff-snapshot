# STATE.md — Hermes Cloud Core V1 (integration worktree)

> Living state of the integration worktree `cloud-hermes-core-v1`.

## Baseline
- Repo: `agent-governance-sync-v1` (canonical Learning OS product code).
- Branch: `integration/cloud-hermes-core-v1` (from `ui/hermes-ui-2-program` @ `058e0a8`).
- Authoritative stable point in CURRENT-STATE.md: `9b18bc3` (ancestor of `058e0a8`).

## Phase status
| Phase | Status | Notes |
|-------|--------|-------|
| 0 Audit + contract freeze | DONE | artifacts/cloud-hermes-core-v1/ PHASE-0-AUDIT .. ACCEPTANCE-CRITERIA |
| A Gateway/Runtime | IN PROGRESS | building cloud_hermes/{app,run_orchestrator,context,provider,errors,main}.py |
| B Memory/Event/Persistence | IN PROGRESS | cloud_hermes/{db,events,memory,execution_node}.py |
| C Client/Web | PENDING | client adapter + web/ |
| D Security/Deploy/QA | PENDING | auth.py + tests + Dockerfile + nginx |
| 2 Integration | PENDING | merge order B->A->C->D in this worktree |
| 3 Deploy + E2E | PARTIAL | local deploy+rollback smoke real; public cloud BLOCKED_CLOUD_ACCESS |

## What is real vs blocked (honest)
- Real & tested locally: full Cloud Hermes service (auth, runs, memory, events, execution
  queue), Windows client adapter, static web UI, full test suites, containerization, deploy
  + rollback scripts, local deploy/rollback smoke.
- Blocked: actual public-cloud (HTTPS domain) deployment — no cloud host/SSH from this
  machine. Marked `BLOCKED_CLOUD_ACCESS`; scripts are cloud-ready.

## Deployment Package Repair (2026-07-23) — STATUS: CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS

The 6 known deployment-package defects (loopback ingress, data/rollback DB-path mismatch,
deploy health probe, `https://127.0.0.1` in rollback, unified dir contract, missing repair
artifact) are fixed, committed, and verified. The retrievable status string
`CLOUD_DEPLOYMENT_PACKAGE_REPAIR_PASS` lives in
`artifacts/cloud-deployment-package-repair/STATE.md`. Evidence: 38 tests OK, compileall OK,
`docker compose config` loopback+unified, isolated Docker smoke `ALL CHECKS PASSED` on the
candidate cloud host (temp `/tmp` resources only), non-destructive rollback backup verified,
security scan clean. This clears the UI Integration prerequisite gate #2. The public-cloud
(HTTPS domain) deployment itself remains out of scope here (`BLOCKED_CLOUD_ACCESS` was about a
real rollout, not the package repair).

## Open risks
- No real Provider key in this env -> real Provider smoke UNEXECUTED (Mock Provider used for
  all tests, per §18).
- Four "parallel" Tracks executed by one coordinator as module ownership (disclosed).

## Next action
Implement Track A + B modules, then Track C, then Track D tests, run full suite, write
INTEGRATION/DEPLOYMENT/FINAL reports.
