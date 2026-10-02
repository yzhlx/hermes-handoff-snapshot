# Recovery plan and branch boundary

## Completed source recovery

1. Select `outputs/` using build-input and SHA-256 evidence.
2. Create an external, timestamped, read-only backup before Git writes.
3. Create `ui/hermes-ui-2-program` from `chore/repository-foundation` in an independent worktree.
4. Restore product source, test source, product documentation, and UI 2.0 program Markdown evidence only.
5. Exclude packages, caches, logs, databases, screenshots, credentials, and user data.
6. Verify source services and recoverable test suites.

## Explicitly deferred

- Do not merge `feat/hermes-ai-evals`, `feat/hermes-engineering-skills`, or `feat/hermes-release-qa`.
- Do not modify `rescue/mixed-work-20260722`.
- Do not rebuild or replace `package-ui-2-candidate`.
- Do not fix Canvas parity in this branch.

## Next branch

After the source-recovery commit is present and this worktree is clean, create `fix/handwriting-canvas-parity` from that recovery commit in its own worktree. Its first task is a failing UI 2.0 page-level Canvas-entry regression test, followed by a minimal integration from the preserved legacy baseline.
