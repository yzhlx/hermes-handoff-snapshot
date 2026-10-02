# UI 2.0 Test Matrix

| Area | Command / evidence | Result |
| --- | --- | --- |
| Handwriting Canvas feature parity | User-confirmed comparison with prior usable functionality; current automated canvas tests do not establish full historical parity | P0 BLOCKED — recovery branch and parity-focused coverage required before release acceptance resumes |
| Core domain | `test_learning_os_core.py` | PASS – 6 tests |
| Local storage | `test_learning_os_store.py` | PASS — 8 tests |
| Local API and provider failure paths | `test_learning_os_api.py` | PASS — 51 tests; 2 intentional live-provider skips |
| Static host | `test_static_server.py` | PASS — 3 tests |
| Launcher units | `test_windows_launcher.py` | PASS — 6 tests |
| Canvas chunk planner | `test_canvas_model.cjs` | PASS — 10 tests × 3 runs |
| World canvas | `test_world_canvas.py` | PASS |
| Handwriting intake | `test_handwriting.py` | PASS |
| Handwriting responsive | `test_handwriting_responsive.py` | PASS |
| Product navigation / focus / five viewports | `test_learning_os_app.py` against source host 52342 | PASS |
| Weekly Planner submit/reset | `test_weekly_plan_submission.py` against source host 52342 | PASS |
| Wrong-answer evidence flows | `test_wrong_answer_submission.py` against source host 52342 | PASS |
| Timeline semantics | `test_learning_timeline_ui.py` against source host 52342 | PASS |
| Hermes AI conversation states | `test_hermes_ai_ui.py` against source host 52342 | PASS |
| AI settings and redaction state | `test_ai_settings_ui.py` against source host 52342 | PASS |
| Learning state / statistics | `test_learning_state_statistics_ui.py` against source host 52342 | PASS |
| Motion contract | `test_ui_motion_contract.py` | PASS |
| UI 2.0 screenshot / responsive suite | `test_ui_2_program_visuals.py` against source host 52342 | PASS × 3 |
| Candidate build | PyInstaller separate output | PASS |
| Candidate asset parity | SHA-256 of embedded CSS and canvas model | PASS |
| Candidate existing-service behavior | EXE from `C:\`, isolated app root | PASS — exit 0, no duplicate listener |
| Candidate embedded static UI | HTTP 200 + product and visual browser tests at 52343 | PASS |
| Recovery integrity recheck | SHA-256 asset parity, exact SQLite-extension scan, secret-pattern scan, and launcher units at 2026-07-22 04:19 +08:00; launcher unit rerun at 04:45 +08:00 | PASS: assets match, 0 SQLite files, 0 text-resource matches, launcher 6/6 in 0.056s |
| Candidate empty-port startup/persistence/restart/exit | Requires candidate ownership of 4173/4174 | BLOCKED — historical package owns both ports |

## Independent source recheck, 2026-07-22 04:30 +08:00

- Isolated source suites: PASS - core 6, store 8, API 51 with 2 intentional external-provider skips, static host 3, launcher 6, motion contract, and Canvas 10 repeated 3 times.
- Real HTTP browser suites at source host 52342: PASS - World Canvas, handwriting, responsive handwriting, product UI, weekly planner, wrong-answer, timeline, Hermes AI, AI settings, learning state/statistics, and visual evidence repeated 3 times.
- Source-host asset parity: PASS - HTTP 200 and CSS, app JS, and Canvas-model SHA-256 values matched `outputs/`.
- Test correction: the stale World Canvas narrow-content assertion failed before correction, then passed after being aligned with the existing provider-cap contract.

`LEARNING_OS_TEST_URL` / `LEARNING_OS_URL` pointed only browser UI tests to separate source or candidate static hosts. Their Playwright routes supplied deterministic test-only API responses and did not modify the running package, local settings, or SQLite.
