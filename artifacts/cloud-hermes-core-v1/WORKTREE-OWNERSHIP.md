# WORKTREE-OWNERSHIP.md

All branches created from the real latest stable HEAD **`058e0a8`** of
`ui/hermes-ui-2-program` (which already contains `9b18bc3`).

| Worktree path | Branch | Track owner | Exclusive files |
|---|---|---|---|
| `cloud-hermes-gateway-v1/` | `feat/cloud-hermes-gateway-v1` | A | app.py, run_orchestrator.py, context.py, provider.py, errors.py, main.py |
| `cloud-hermes-memory-events-v1/` | `feat/cloud-hermes-memory-events-v1` | B | db.py, events.py, memory.py, execution_node.py |
| `learning-os-cloud-hermes-client-v1/` | `feat/learning-os-cloud-hermes-client-v1` | C | client adapter, patched api.py, web/* |
| `cloud-hermes-security-qa-v1/` | `test/cloud-hermes-security-qa-v1` | D | auth.py, tests/*, deploy/*, nginx.conf, Dockerfile |
| `cloud-hermes-core-v1/` | `integration/cloud-hermes-core-v1` | Coordinator | integration merge target + all artifacts |

## Reality note (no fabrication)

The task describes four parallel human Track teams. This environment executed the task with
a **single coordinator agent**. To honor the contract's integrity guarantees without
faking parallel teams, the four Tracks were realized as **strict module-level ownership
boundaries** (see DATA-OWNERSHIP.md): each module file carries an ownership header, and the
merge/integration happened only in `integration/cloud-hermes-core-v1`. The four feature
branches exist and are registered. This is disclosed in FINAL-REPORT.md rather than
pretending four agents ran concurrently.

## State of each worktree
Each worktree MUST contain: the shared governance files (AGENTS.md, CURRENT-STATE.md,
TASK-QUEUE.md, RELEASE-STATUS.md), an independent `STATE.md` and `HANDOFF.md`. The
integration worktree additionally holds `artifacts/cloud-hermes-core-v1/`.

## Merge order (Phase 2)
1. Track B (data contract + migration)
2. Track A (gateway/runtime)
3. Track C (client/web)
4. Track D (tests + deploy)

Conflicts: never auto-accept one side; reconcile against API-CONTRACT.md, keep verified
existing features, record resolution.
