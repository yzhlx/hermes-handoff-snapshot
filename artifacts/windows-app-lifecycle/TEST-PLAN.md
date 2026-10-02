# Test plan — graceful exit

## RED → GREEN
File: `tests/test_windows_app_graceful_exit.py` (13 cases)

- `test_launcher_exposes_request_shutdown` — launcher exposes `request_shutdown` + named
  `stop_event`. **PASS**.
- `test_graceful_shutdown_releases_ports` — in-process servers, `request_shutdown()` frees
  4173/4174. **PASS**.
- `test_request_shutdown_idempotent` — calling it twice is safe. **PASS**.
- `test_stop_event_unblocks_main_wait` — `main()` waits on the named `stop_event`. **PASS**.
- `test_signal_handlers_request_exit` — SIGINT/SIGTERM wired to `request_shutdown()`. **PASS**.
- `test_no_anonymous_event_wait` — source uses `stop_event.wait()`, not `threading.Event().wait()`. **PASS**.
- `test_cleanup_runs_once` — idempotent cleanup (both servers closed once). **PASS**.
- `test_main_returns_zero_on_controlled_shutdown` — controlled shutdown → rc 0. **PASS**.
- `test_shutdown_endpoint_post_only` — `GET`≠200, `POST`→200 and releases ports. **PASS**.
- `test_shutdown_endpoint_rejects_foreign_origin` — foreign/missing `Origin`→403, ports stay. **PASS**.
- `test_exit_entry_exists_in_html` — `#exitAppButton`, `#exitStatus` present. **PASS**.
- `test_exit_confirm_dialog_exists` — `#exitConfirmDialog`, `#confirmExit`, `#cancelExit` + JS wiring. **PASS**.
- `test_canvas_draft_capability_intact` — Canvas draft storage key present, source mtime unchanged. **PASS**.

Run:
```powershell
python -m unittest tests.test_windows_app_graceful_exit -v
```
Expected: **OK (GREEN)** — 13 passed.

## UI exit-entry test (Playwright, real browser)
File: `tests/test_ui_2_exit_entry.py`
- Starts real static + API servers in-process, opens `http://127.0.0.1:4173/` in headless
  Chrome (channel=chrome), navigates to settings, clicks `#exitAppButton`, confirms
  `#confirmExit`, asserts `#exitStatus` shows `已退出`, and verifies both ports close. **PASS (1 test)**.

## Regression that must stay GREEN
- `tests/test_ui_2_handwriting_entry.py` (2 tests) — canvas workspace still intact. **PASS**.
- Source/package hash checks: 13 bundled resources match `outputs/` SHA-256 (Phase 7). **PASS**.

## Full suite run (all GREEN)
graceful-exit (13) · Launcher · API · Static · default Python · UI2 handwriting entry (2) ·
Playwright exit-entry (1) · Canvas Model · Handwriting · Responsive Handwriting · `node --check`
on 3 JS files · `git diff --check`. **PASS** (no mock-only process verification; no assertion
lowering; RED test retained-then-turned-GREEN).

## Real Windows runtime (Phase 8) — MANUAL/AUTOMATED
Launch candidate EXE with isolated `LOCALAPPDATA`, drive a real same-origin browser to click +
confirm the exit button, assert the EXE self-terminates (no taskkill/precision-PID), ports
released, no orphan; restart same dir; path with spaces + Chinese. **PASS (3 scenarios)**.
Precision-PID termination was used ONLY as a safety cleanup in a smoke-test exception path and
is **not** required for the normal exit.

## Manual acceptance (Windows, real hardware)
- Real stylus / pen-input Canvas drawing: **MANUAL USER ACCEPTANCE** (cannot automate).
