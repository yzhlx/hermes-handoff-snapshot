# WORKTREE-INVENTORY — Hermes Learning OS

**Date:** 2026-07-22. Covers the 21 git worktrees and the Cloud Hermes Core V1 consolidation.

---

## 1. Method

For every worktree: `git -C <wt> status --short`, `git -C <wt> branch --show-current`,
`git -C <wt> rev-parse --short HEAD`, `git -C <wt> log --oneline -5` (run via `cd` because
`git -C` mis-parses the space in `learning os` under Git-Bash). Plus a filesystem scan for any
`cloud_hermes/` directory outside the integration worktree.

## 2. Cloud Hermes track mapping (per FINAL-REPORT.md)

The four "parallel tracks" (A Gateway/Runtime, B Memory/Event, C Client/Web, D Security/Deploy/QA)
were executed as **module-ownership boundaries inside a single integration worktree** (disclosed
in FINAL-REPORT §10 and INTEGRATION-REPORT §1). No separate track worktrees exist for Cloud
Hermes Core V1.

## 3. Where the code lives

```
find learning os-worktrees -type d -name cloud_hermes
# F:\...\cloud-hermes-core-v1\cloud_hermes
# F:\...\cloud-hermes-core-v1\tests\cloud_hermes
```

**Only** the `integration/cloud-hermes-core-v1` worktree contains `cloud_hermes/`. No other
worktree has unmerged Cloud Hermes commits or untracked `cloud_hermes/`. Therefore there is no
overlapping/conflicting integration state → no `BLOCKED_UNCLEAR_INTEGRATION_STATE`.

## 4. Integration worktree detail (`cloud-hermes-core-v1`)

| Item | Value |
|------|-------|
| Branch | `integration/cloud-hermes-core-v1` |
| HEAD (post-task) | `b76d18e` |
| Tracked source | `cloud_hermes/`, `tests/cloud_hermes/`, `web/`, `outputs/learning-os-cloud-bridge.py`, modified `outputs/learning-os-api.py`, `scripts/`, `Dockerfile`, `docker-compose.yml`, `nginx.conf` |
| Committed docs | `artifacts/cloud-hermes-core-v1/*` (contracts + reports + desensitized test products) |
| Excluded (not committed) | `scratch_smoke.py`, `work/` (runtime DBs/backups), `logs/`, `api-results/`, `local-docker-smoke.zip` (see PRIVATE-DATA-SCAN.md) |

## 5. Other worktrees (not part of Cloud Hermes Core V1)

These carry unrelated features and were **not** merged into the integration branch:
`artifact-registry-*`, `backup-export-v1`, `data-platform-*`, `handwriting-canvas-parity`,
`hermes-ai-evals`, `hermes-engineering-skills`, `hermes-function-v1`, `hermes-learning-journal-v2`,
`hermes-release-qa`, `learning-domain-event-model-v1`, `repository-foundation`,
`task-lifecycle-v1`, `windows-app-graceful-exit`, `wrong-answer-lifecycle-v1`,
`ui/hermes-ui-2-program` (stable baseline), `review/learning-domain-event-model-v1` (orphaned).

## 6. Decision

Only `integration/cloud-hermes-core-v1` is published. The stable baseline
`ui/hermes-ui-2-program` is the PR base. No other worktree is pushed as part of this task
(though it may be pushed as a backup later if the user requests).
