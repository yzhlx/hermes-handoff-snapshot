# Hermes UI 2.0 Program State

## Overall Status

BLOCKED

## Current Milestone

Milestone 12 – isolated Windows candidate package and lifecycle verification (suspended pending P0 handwriting-canvas feature-parity recovery).

## Completed Milestones

- Milestone 0 — baseline audit and page inventory.
- Milestone 1 — shared warm-paper design system and component-state foundation.
- Milestone 2 — Mission-first home experience.
- Milestone 3 — Hermes AI mentor-desk experience.
- Milestone 4 — Learning Rhythm timeline.
- Milestone 5 — Weekly Planner.
- Milestone 6 — Wrong Answer Notebook.
- Milestone 7 — Learning State and learning-record statistics surfaces.
- Milestone 8 — Settings and system surfaces.
- Milestone 9 — restrained motion contract.
- Milestone 10 — responsive and accessibility validation.
- Milestone 11 — complete source regression after the canvas chunking correction.
- Milestone 12 build, embedded-asset, existing-service, and static-asset UI checks.

## Active Work

- **P0 release blocker:** the user has confirmed that the UI 2.0 handwriting canvas is materially reduced compared with the previously usable version. Existing canvas-model, handwriting, and responsive tests do not establish historical feature parity and must not be used to downgrade this finding.
- Final candidate-package release acceptance is paused. Do not promote this program or the candidate to COMPLETE and do not resume package lifecycle verification until the handwriting-canvas recovery branch supplies a documented parity assessment and focused regression evidence.

- Candidate built at `package-ui-2-candidate/学习 OS/学习 OS.exe`.
- Candidate CSS and canvas-model hashes exactly match `outputs/`.
- Candidate EXE safely handled an already-running service from `C:\`: exit code 0 in 1395ms; the prior 4173/4174 owner remained unchanged.
- Candidate embedded static assets served HTTP 200 from a temporary port and passed product UI and visual browser regression.

Recovery check, 2026-07-22 04:16 +08:00: both default ports remain owned by historical PID 35932. Its executable path resolves to the historical `package-ai-fixed` package, not to the UI 2.0 candidate. This program did not create or stop that process.

## Next Actions

1. Close the historical `package-ai-fixed/学习 OS/学习 OS.exe` process that owns ports 4173/4174, or explicitly authorize a safe maintenance window to stop it.
2. Resume with a new isolated `LOCALAPPDATA` root and `EXE_QA_TEST_` records.
3. Verify candidate-owned startup, SQLite writes, reload/restart persistence, self-owned shutdown, 4173/4174 release, Chinese/space path, and log redaction.
4. Update this state to COMPLETE only if those real package checks pass.

## Tests Last Run

2026-07-22, source root, bundled Python/Node runtimes:

- `test_learning_os_core.py`: PASS — 6 tests.
- `test_learning_os_store.py`: PASS — 8 tests.
- `test_learning_os_api.py`: PASS — 51 tests, 2 intentional live-provider skips.
- `test_static_server.py`: PASS — 3 tests.
- `test_windows_launcher.py`: PASS — 6 tests.
- `test_canvas_model.cjs`: PASS — 10 tests, repeated 3 times.
- `test_world_canvas.py`, `test_handwriting.py`, and `test_handwriting_responsive.py`: PASS.
- Product, planner, wrong-answer, timeline, Hermes AI, AI settings, and learning-state/statistics browser regressions: PASS.
- `test_ui_motion_contract.py`: PASS.
- `test_ui_2_program_visuals.py`: PASS, repeated 3 times.
- Candidate embedded static assets: HTTP 200; `test_learning_os_app.py` and `test_ui_2_program_visuals.py`: PASS.

## Fresh Full Source Regression

- 2026-07-22 04:30 +08:00: core 6, store 8, API 51 with 2 intentional live-provider skips, static host 3, launcher 6, motion contract, and Canvas 10 tests repeated 3 times all passed using isolated test data paths.
- 2026-07-22 04:30 +08:00: World Canvas, handwriting, responsive handwriting, product UI, planner, wrong-answer, timeline, Hermes AI, AI settings, learning-state/statistics, and visual browser suites passed against the current source host at 52342; the visual suite was repeated 3 times.
- The source host returned HTTP 200 and its CSS, application JS, and Canvas-model SHA-256 values matched the current `outputs/` files before the browser run.
- A stale World Canvas assertion was corrected after it demonstrably failed against the documented cap behavior. The corrected integration test then passed against the real source host.

## Fresh Candidate Integrity Recheck

- 2026-07-22 04:19 +08:00: candidate resource parity recheck PASS; exact extension scan found 0 embedded SQLite files; text-resource secret-pattern scan found 0 matches.
- 2026-07-22 04:19 +08:00: `test_windows_launcher.py` PASS, 6 tests in 0.257s.
- 2026-07-22 04:45 +08:00: `test_windows_launcher.py` rerun PASS, 6 tests in 0.056s. This isolated launcher-unit result does not substitute for the blocked candidate-owned lifecycle chain.

## Recovery Check

- 2026-07-22 04:35 +08:00: candidate recovery precondition remains BLOCKED. `Get-NetTCPConnection` resolved both 4173 and 4174 listeners to historical PID 35932.
- 2026-07-22 04:44 +08:00: the same read-only port check again resolved both default listeners to historical PID 35932 under `package-ai-fixed/学习 OS/学习 OS.exe`. The candidate executable exists and its embedded CSS, app JavaScript, and Canvas-model hashes still exactly match `outputs/`; no package, process, service, database, or user data was changed.

## Known Failures

P0 – Handwriting Canvas Feature Parity Regression. User-confirmed material feature reduction relative to the prior usable canvas; current automated tests pass but do not prove historical feature completeness. Package-owned lifecycle/persistence testing is also blocked by the pre-existing 4173/4174 process.

## Decisions Needed From User

Authorize an empty-port verification window only if the historical package may be closed. Do not stop it automatically.

## Last Updated

2026-07-22 Asia/Shanghai – P0 handwriting-canvas parity blocker recorded; final candidate-package release acceptance paused.
