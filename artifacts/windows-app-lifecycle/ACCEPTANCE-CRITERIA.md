# Acceptance criteria — graceful exit

The fix is accepted when ALL of the following hold. Status reflects the state at
commit `a3f77bc` + Phase 7/8 verification.

1. **Controlled stop primitive exists.** `outputs/learning-os-desktop.py` exposes a
   `request_shutdown()` that cleanly stops both servers and releases ports `4173`/`4174`
   without an external process kill. — **PASS** (unit test `test_launcher_exposes_request_shutdown`,
   `test_graceful_shutdown_releases_ports`, `test_request_shutdown_idempotent`).

2. **Signal handling.** `SIGINT` and `SIGTERM` each trigger the same clean shutdown path. —
   **PASS** (`test_signal_handlers_request_exit` mocks `signal.signal` and asserts handlers call
   `request_shutdown()`; verified in implementation).

3. **Port release + no orphan.** After a graceful shutdown, `4173`/`4174` are free and no orphan
   process remains. — **PASS** (backend test `test_shutdown_endpoint_rejects_foreign_origin`
   confirms ports stay until a valid request; Phase 8 confirms real release + no orphan).

4. **No UX/behaviour regression.** App still starts, serves the workspace, opens the browser as
   before; handwriting canvas regression (`tests/test_ui_2_handwriting_entry.py`) still passes. —
   **PASS** (2/2 tests green; `test_canvas_draft_capability_intact` confirms draft storage intact).

5. **Automated coverage GREEN.** `tests/test_windows_app_graceful_exit.py` (13 cases) passes. —
   **PASS** (was RED at `8130a23`, now GREEN). Plus `tests/test_ui_2_exit_entry.py` (Playwright
   UI test: discover + confirm + self-exit) passes.

6. **No secrets / no user-data leak.** Shutdown path writes/exposes no credentials or user data. —
   **PASS** (Phase 7 text-resource secret scan: 0 hits; endpoint returns only a status message).

7. **User-discoverable, user-operable exit entry exists (the actual defect closure).** A user can
   find and actively trigger a normal exit from the in-app UI, independent of the internal
   primitive. — **PASS** (UI 2.0 settings page `退出学习 OS` button → confirm dialog →
   `POST /api/v2/shutdown`; verified end-to-end in Phase 8 with a real browser: the EXE
   self-terminated via the button, no taskkill/precision-PID).

8. **Runtime self-exit (real Windows).** The packaged EXE self-exits via the user entry without
   taskkill/PID kill, releases both ports, and leaves no orphan; restart with the same data root
   recovers; a path containing spaces + Chinese also exits. — **PASS** (Phase 8, 3 scenarios).

## Status labels used
PASS · FAIL · BLOCKED · NOT COVERED · KNOWN LIMITATION · MANUAL USER ACCEPTANCE

## Manual user acceptance (not automatable)
- **Real stylus / pen-input drawing** on the handwriting Canvas: CANNOT be automated headlessly.
  The Canvas draft-storage source is unchanged and the page loads normally — treat live pen
  interaction as **MANUAL USER ACCEPTANCE**.
