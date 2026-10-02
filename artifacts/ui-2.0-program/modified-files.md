# Modified Files

## Product frontend

- `outputs/learning-os-app.html` — semantic UI 2.0 structure for the home, planner, notebook, AI, records, and settings surfaces.
- `outputs/learning-os-app.css` — shared warm-paper tokens, typography, controls, responsive rules, keyboard focus, reduced motion, and quiet interaction feedback.
- `outputs/learning-os-app.js` — presentation/state rendering only; existing routes and API contracts are retained.
- `outputs/learning-os-canvas-model.js` — corrected one scale cap so narrow recognition content is not upscaled.

## Regression coverage

- `work/presentations/learning-os-ui/tmp/test_learning_os_api.py` — fixed-date fixture alignment from the prior UI work.
- `work/presentations/learning-os-ui/tmp/test_learning_os_app.py` — source-host deterministic UI regression support.
- `work/presentations/learning-os-ui/tmp/test_weekly_plan_submission.py` — source-host deterministic planner regression support.
- `work/presentations/learning-os-ui/tmp/test_ui_motion_contract.py` — quiet busy feedback contract.
- `work/presentations/learning-os-ui/tmp/test_ui_2_program_visuals.py` — visual/responsive evidence capture.
- `work/presentations/learning-os-ui/tmp/test_canvas_model.cjs` — asserts native-width preservation for non-overwide recognition content.

- `work/presentations/learning-os-ui/tmp/test_world_canvas.py` - corrected the stale browser assertion so it verifies native narrow-content dimensions under the existing provider-cap contract.

## Generated candidate

- `package-ui-2-candidate/学习 OS/` — new PyInstaller candidate only; it contains 94 files and has not replaced any historical package.
- `tmp/pyinstaller-work-ui-2-candidate/` and `tmp/pyinstaller-spec-ui-2-candidate/` — build intermediates only.

## Design and recovery records

- `.hallmark/preflight.json` and `.hallmark/log.json` — source design-system continuity records.
- `artifacts/ui-2.0-program/` — program, status, decision, test, screenshot, and report records.

- `artifacts/ui-2.0-program/{STATE.md,CURRENT-TASK.md,TEST-MATRIX.md,reports/windows-package.md,known-issues.md,final-report.md}`: recovery-check records for the confirmed historical port owner and fresh non-invasive candidate-integrity evidence.
- `artifacts/ui-2.0-program/reports/recovery-port-check-2026-07-22-0444.md`: current-run, read-only port-owner and candidate-payload-parity evidence.

No Python service, API contract, SQLite schema, credential storage, Provider/Gateway behavior, launcher source, or historical package was changed.
