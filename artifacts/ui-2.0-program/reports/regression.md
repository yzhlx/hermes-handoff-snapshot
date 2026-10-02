# Milestone 11 — Full Regression

## Result: PASS

## Independent recheck, 2026-07-22 04:30 +08:00

The complete discovered source suite was rerun. The isolated suites passed with core 6, store 8, API 51 with 2 intentional external-provider skips, static host 3, launcher 6, motion contract, and Canvas 10 tests repeated 3 times. Real HTTP Playwright runs then passed for World Canvas, handwriting, responsive handwriting, product UI, planner, wrong-answer, timeline, Hermes AI, AI settings, learning state/statistics, and the visual suite repeated 3 times.

The source host at port 52342 returned HTTP 200. Its served CSS, application JS, and Canvas model SHA-256 values matched current `outputs/` assets before browser validation. Browser request routing remained deterministic for API write and provider scenarios; the only unmocked dashboard read was used to open the existing recall surface for the World Canvas test.

The recheck initially exposed a stale World Canvas assertion that still expected a 353 by 262 narrow region to be enlarged. The implementation, Canvas unit test, and D-008 all define the maximum as a cap. The browser assertion now verifies the exact native dimensions and passed after correction.

### Commands used for the independent recheck

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py work\presentations\learning-os-ui\tmp\test_learning_os_core.py
& $py work\presentations\learning-os-ui\tmp\test_learning_os_store.py
& $py work\presentations\learning-os-ui\tmp\test_learning_os_api.py
& $py work\presentations\learning-os-ui\tmp\test_static_server.py
& $py work\presentations\learning-os-ui\tmp\test_windows_launcher.py
& $py work\presentations\learning-os-ui\tmp\test_ui_motion_contract.py
node work\presentations\learning-os-ui\tmp\test_canvas_model.cjs  # repeated three times

$env:LEARNING_OS_URL = 'http://127.0.0.1:52342/learning-os-ui-prototype.html'
& $py work\presentations\learning-os-ui\tmp\test_world_canvas.py
& $py work\presentations\learning-os-ui\tmp\test_handwriting.py
& $py work\presentations\learning-os-ui\tmp\test_handwriting_responsive.py

$env:LEARNING_OS_URL = 'http://127.0.0.1:52342/'
$env:LEARNING_OS_TEST_URL = 'http://127.0.0.1:52342/'
& $py work\presentations\learning-os-ui\tmp\test_learning_os_app.py
& $py work\presentations\learning-os-ui\tmp\test_weekly_plan_submission.py
& $py work\presentations\learning-os-ui\tmp\test_wrong_answer_submission.py
& $py work\presentations\learning-os-ui\tmp\test_learning_timeline_ui.py
& $py work\presentations\learning-os-ui\tmp\test_hermes_ai_ui.py
& $py work\presentations\learning-os-ui\tmp\test_ai_settings_ui.py
& $py work\presentations\learning-os-ui\tmp\test_learning_state_statistics_ui.py
& $py work\presentations\learning-os-ui\tmp\test_ui_2_program_visuals.py  # repeated three times
```

The complete discovered test suite was run after the canvas-chunk correction. Core, store, API, static host, launcher unit, canvas, handwriting, responsive, product UI, planner, wrong-answer, Hermes AI, settings, learning state/statistics, motion, and visual suites passed.

The API suite reports 51 passing tests and two expected skips. Both skips are deliberate external-live-provider checks gated by `LEARNING_OS_LIVE_TEST=1`; no live credential was requested or used.

## Regression correction

`test_canvas_model.cjs` initially failed because a 1200px-wide image was being enlarged to a 1600px maximum width. The corrected cap preserves native width unless content is over-wide. The augmented regression test and the canvas model pass three consecutive runs; world-canvas and handwriting browser suites also pass.

Exact commands and classifications are maintained in `../TEST-MATRIX.md` and will be included in the final report after Milestone 12.

## NOT COVERED

No root lint, TypeScript, or type-check configuration exists in this vanilla HTML/CSS/JS and Python source root. The project’s executable verification gates are the discovered Python, Node, and Playwright suites listed in the matrix.
