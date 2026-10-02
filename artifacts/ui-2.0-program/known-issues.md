# Known Issues and Limits

## P0 — Handwriting Canvas Feature Parity Regression

The user has confirmed that the UI 2.0 handwriting canvas is materially reduced compared with the previously usable implementation. This is a release blocker, independent of the currently passing canvas-model, handwriting, and responsive tests: those tests do not demonstrate historical feature completeness.

Final UI 2.0 candidate-package acceptance is paused until a dedicated handwriting-canvas recovery branch restores the missing behavior, documents the previous-versus-current parity assessment, and adds focused regression coverage. The candidate must not be marked `COMPLETE` or released based on the current test results.

## BLOCKED

- PID 35932 from historical `package-ai-fixed/学习 OS/学习 OS.exe` owns both 4173 and 4174. It was not created by this run and was not stopped. This blocks candidate-owned startup, persistence/restart, own-service shutdown, and default-port release verification.

A recovery check at 2026-07-22 04:16 +08:00 reconfirmed the same process and port ownership. A user-approved empty-port maintenance window is required before the final candidate package test can proceed.

A further read-only recovery check at 2026-07-22 04:44 +08:00 found the same condition. Candidate asset parity remains intact, but parity cannot prove the candidate-owned lifecycle or persistence chain.

## KNOWN LIMITATION

- The source root is not a Git repository. Source milestone commits cannot be created; the unrelated Git worktree at `F:\Users\user\Documents\learning os` is deliberately not used for source commits.
- The separate source host at port 52342 is not in the local API CORS allow-list. It intentionally renders the local-service error state outside intercepted browser tests; no CORS/API behavior changed for this UI program.
- Two API tests intentionally skip real external Provider calls unless `LEARNING_OS_LIVE_TEST=1` is set. No credential was requested or read.
- The existing launcher has no new UI 2.0 lifecycle feature. It was not redesigned in this UI-only program.
- The isolated temporary QA root `tmp/ui2-candidate-existing-service-localappdata/` was created only for the candidate existing-service check. It contains no candidate SQLite database and passed a secret-pattern scan, but cleanup was blocked by the execution policy after it also received a browser temporary profile. It is outside `artifacts/` and must not be packaged or committed.

## NO CURRENT SOURCE TEST FAILURE

The prior canvas-model regression was corrected: `maxWidth` now caps only over-wide recognition content, avoiding an unnecessary upscale and a fourth overlapping chunk.
