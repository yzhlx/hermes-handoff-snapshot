# REPOSITORY-AUDIT — Hermes Learning OS

**Date:** 2026-07-22. **Auditor:** publication agent.

---

## 1. Real git root

```
git rev-parse --show-toplevel
# F:\Users\user\Documents\learning os
```

Confirmed: `F:\Users\user\Documents\learning os` is the real git root (contains `.git`).
The directory `F:\Users\user\Documents\learning os-worktrees` holds git **worktrees** (separate
checkouts), not a separate repo. The `learning os-worktrees` folder is a sibling of the repo
root, so loose files under it (e.g. `learning os-worktrees/artifacts/...`) are **outside** git
unless copied into a worktree.

## 2. Current branch / HEAD (at audit start)

| Item | Value |
|------|-------|
| Branch (main repo checkout) | `rescue/mixed-work-20260722` |
| HEAD | `91c4f3edccf9e89e694595a0cecf24e62bda4218` |
| Remote | **none** |
| Tags | none |

The main checkout was on a rescue branch with several untracked files; it is **not** the
publication target.

## 3. Final integration branch

| Item | Value |
|------|-------|
| Branch | `integration/cloud-hermes-core-v1` |
| Worktree | `F:\Users\user\Documents\learning os-worktrees\cloud-hermes-core-v1` |
| Base (stable integration baseline) | `ui/hermes-ui-2-program` (per `AGENTS.md` §31.1) |
| Base HEAD | `058e0a86af7ed2b98fed6a970323a6318ae93d47` |
| Integration HEAD **before** this task | `058e0a8` (identical to base — code was untracked) |
| Integration HEAD **after** this task | `b76d18e23e9bb7f77870b9ff2ad91f9ff7928328` |

The Cloud Hermes Core V1 implementation had been developed as **untracked** files on top of the
base commit and was **never committed**. This task committed it as the final integration commit
(see TEST-VERIFICATION / commit list below).

## 4. Commits added this task (on `integration/cloud-hermes-core-v1`)

```
b76d18e chore(security): harden .gitignore and add .env.example
f052026 docs(cloud): add Cloud Hermes Core V1 contracts and RC1 reports
fcb1083 feat(cloud): integrate Hermes Cloud Core V1
058e0a8 merge(agent): establish shared worktree instructions   <-- base (shared with ui/hermes-ui-2-program)
```

## 5. Worktree list (summary)

`git worktree list --porcelain` reported 21 worktrees. The Cloud Hermes code is isolated to
`integration/cloud-hermes-core-v1`; no other worktree contains `cloud_hermes/`. See
`WORKTREE-INVENTORY.md`.

## 6. Branches

Local branches observed (each with its own worktree): `rescue/mixed-work-20260722`,
`review/learning-domain-event-model-v1`, `chore/agent-governance-sync-v1`,
`integration/artifact-registry-foundation-v1`, `feat/artifact-registry-v1`,
`feat/backup-export-v1`, **`integration/cloud-hermes-core-v1`**,
`fix/data-platform-foundation-finalization`, `feat/data-platform-foundation-v1`,
`fix/data-platform-migration-lock-race`, `fix/handwriting-canvas-parity`,
`feat/hermes-ai-evals`, `feat/hermes-engineering-skills`, `integration/hermes-function-v1`,
`ui/hermes-learning-journal-v2`, `feat/hermes-release-qa`, `ui/hermes-ui-2-program`,
`design/learning-domain-event-model-v1`, `chore/repository-foundation`, `feat/task-lifecycle-v1`,
`fix/windows-app-graceful-exit`, `feat/wrong-answer-lifecycle-v1`.

There is **no** `main`/`master`/`stable` branch. The stable integration baseline is
`ui/hermes-ui-2-program` (documented in `AGENTS.md` §31.1) and is the PR base.

## 7. Orphaned / corrupted worktree note

`review/learning-domain-event-model-v1` appears in `git worktree list` with a **corrupted
doubled path** (`F:/f/Users/...`) and its directory is not present on disk. It is an orphaned
worktree whose metadata should be pruned (`git worktree prune`) by the user later; it does not
affect publication. The governance files it was believed to hold actually reside in the
`cloud-hermes-core-v1` worktree root.

## 8. Remote

No remote configured (`git remote -v` empty). A remote will be added only after the user
creates the private repo and confirms the URL (see PUSH-REPORT.md).
