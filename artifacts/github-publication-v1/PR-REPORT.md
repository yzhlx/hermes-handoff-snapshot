# PR-REPORT — Hermes Cloud Core V1 RC1

**Date:** 2026-07-22. Status: **NOT CREATED — BLOCKED** (depends on repo + push).

---

## 1. Planned PR

| Field | Value |
|-------|-------|
| Head | `integration/cloud-hermes-core-v1` |
| Base | `ui/hermes-ui-2-program` (stable integration baseline, `AGENTS.md` §31.1) |
| Title | `feat(cloud): integrate Hermes Cloud Core V1 RC1` |
| State | **Draft** (not auto-merged) |
| Tag referenced | `cloud-hermes-core-v1-rc1` |

## 2. PR body (ready to paste)

```markdown
## Completed

- Cloud Hermes Gateway and authentication
- Hermes Run tracking
- Conversations and tasks
- Memory persistence foundation
- Append-only Event Store
- Execution command queue
- Idempotency
- Deployment and rollback scripts
- 38 automated tests
- Local real-process deployment smoke
- Rollback and database-integrity verification

## Not yet completed

- Real public-cloud deployment
- Public HTTPS domain acceptance
- Windows PC powered-off tablet acceptance
- Production cutover
- Full multi-role implementation
- Complete Learning State / F0–F5 chain

## Status

PARTIALLY COMPLETED

## Security

- No Provider key committed
- No production database committed
- No private learning data committed
- Runtime secrets remain external to Git

## Release

Candidate tag: `cloud-hermes-core-v1-rc1`
```

## 3. Rules honored

- Draft only; never auto-merged.
- Base is the documented stable baseline, not a feature branch.
- No force-push; the branch is pushed with a normal (non-force) `git push -u`.

## 4. Block

PR creation requires the remote repo to exist and the integration branch to be pushed. Both are
blocked in this environment (PUSH-REPORT.md). After the user creates the private repo and
authenticates, the `gh pr create --draft ...` command in PUSH-REPORT.md opens it.
