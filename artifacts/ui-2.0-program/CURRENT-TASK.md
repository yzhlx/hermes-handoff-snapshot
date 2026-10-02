# Current Task

## Goal

Complete the candidate-owned Windows lifecycle and persistence checks without touching a historical package process.

## P0 Release Hold

The user has confirmed a material handwriting-canvas feature-parity regression in UI 2.0. Do not continue this candidate-package acceptance task, start the candidate, or publish a final release conclusion until the dedicated handwriting-canvas recovery branch restores the missing behavior and supplies a documented parity assessment with focused regression coverage. Existing passing canvas tests are insufficient evidence of historical functional completeness.

## Blocker

Ports 4173 and 4174 are both owned by PID 35932, `package-ai-fixed/学习 OS/学习 OS.exe`, created before this run. The candidate safely detects it and exits, but cannot start its own API/static service or isolated SQLite while it exists.

At 2026-07-22 04:35 +08:00, the process command line was rechecked and identified as the historical package executable rather than the candidate. No termination or service manipulation was performed.

At 2026-07-22 04:44 +08:00, a fresh read-only listener check confirmed that 4173 and 4174 are still owned by the same historical executable. A candidate payload parity check also passed for `learning-os-app.css`, `learning-os-app.js`, and `learning-os-canvas-model.js`. The candidate, historical package, database, and running service were left untouched.

At 2026-07-22 04:45 +08:00, the isolated source launcher-unit suite passed again: 6 tests in 0.056s. It verifies launcher logic only and does not replace candidate-owned service, persistence, restart, shutdown, or port-release evidence.

The source regression baseline was independently rerun at 2026-07-22 04:30 +08:00 and is green. The only remaining program gate is candidate-owned package verification; the test-only Canvas assertion correction does not change the candidate payload and does not require a rebuild.

## Files in scope after unblock

- `package-ui-2-candidate/学习 OS/` — already built; do not rebuild or overwrite.
- New isolated `LOCALAPPDATA` test root and `EXE_QA_TEST_` records only.
- `artifacts/ui-2.0-program/reports/windows-package.md` and final program records.

## Acceptance after unblock

- Candidate owns 4173/4174, serves HTTP 200, writes isolated SQLite data, survives restart, and releases its own ports on exit.
- Historical package directories and user data remain untouched.

## Exact recovery instruction

Read `F:\Users\user\Documents\learning os\AGENTS.md`, then this program's `PROGRAM.md`, `STATE.md`, `CURRENT-TASK.md`, `DECISIONS.md`, `TEST-MATRIX.md`, and `reports/windows-package.md`. Verify the historical port owner is gone before launching the already-built candidate with a new isolated `LOCALAPPDATA` root. Do not repeat UI redesign or overwrite `package-ui-2-candidate/`.
