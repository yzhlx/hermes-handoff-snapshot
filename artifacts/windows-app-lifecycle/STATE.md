# Windows app graceful-exit — defect state

Status: **RESOLVED — Application lifecycle PASS** (runtime-verified on Windows)
Branch: `fix/windows-app-graceful-exit`
Worktree: `windows-app-graceful-exit`
Source of truth: `outputs/learning-os-desktop.py`
Head commit: `a3f77bc` (`fix(lifecycle): add user-accessible graceful shutdown`)
RED contract commit: `8130a23` (`test(lifecycle): define graceful shutdown contract`)

> ## RESOLVED — READY FOR MERGE REVIEW
> The branch now carries the full fix (internal shutdown primitive **plus** a user-discoverable,
> user-operable exit entry in the UI 2.0 settings page) and a **passing** test suite. The
> candidate EXE was built and verified in a real Windows runtime (Phase 8): it self-exits
> through the in-app exit button with **no taskkill / no precision-PID**, releases ports
> `4173`/`4174`, and leaves no orphan. **Do not auto-merge into `ui/hermes-ui-2-program`
> this round** (per authorization); recommend merge after human review of this report.

## What is verified
- Internal shutdown primitive: module-level `stop_event`, idempotent `request_shutdown()`, and
  SIGINT/SIGTERM handlers in `outputs/learning-os-desktop.py` (Phase 3).
- **User exit entry (the defect's actual fix):** UI 2.0 settings page button `退出学习 OS`
  → confirm dialog → `POST /api/v2/shutdown` (loopback-only, same-origin/origin-checked,
  POST-only). Closing the browser tab does **not** stop the background service. (Phase 4)
- Automated tests GREEN: 13 backend cases (`tests/test_windows_app_graceful_exit.py`) + 1
  Playwright UI test (`tests/test_ui_2_exit_entry.py`). Existing handwriting regression
  (`tests/test_ui_2_handwriting_entry.py`, 2 tests) stays GREEN. (Phase 5)
- Candidate package built (`package-ui-2-graceful-exit-candidate/学习 OS/`, onedir, windowed)
  with all 13 bundled resources matching source `outputs/` SHA-256, Canvas workspace JS
  present, 0 secret-pattern hits. (Phase 7)
- Real Windows runtime: launched with an isolated `LOCALAPPDATA`, driven by a real same-origin
  headless Chrome to click + confirm the exit button — the EXE self-terminated (rc 0),
  released both ports, no orphan; restart with the same dir recovered; a path containing
  spaces + Chinese also exited correctly. (Phase 8)

## What was broken (root cause, now fixed)
- `main()` blocked on an anonymous `threading.Event().wait()` and exposed no stop primitive,
  no signal handler, and no in-app exit control. The only way to stop the app was an
  exact-PID kill. See `ROOT-CAUSE.md`.

## Scope of this branch
- Diagnose and fix the graceful-exit gap, including the **user-accessible** exit entry.
- Do NOT put this fix on `fix/handwriting-canvas-parity`.
- Do NOT start colour-picker development here.

## Manual user acceptance (real-hardware only)
- Real stylus / pen-input drawing on the handwriting Canvas cannot be automated; the Canvas
  draft-storage capability source is unchanged (verified by `test_canvas_draft_capability_intact`)
  and the app loads the Canvas page normally. Treat live pen interaction as MANUAL USER
  ACCEPTANCE.
