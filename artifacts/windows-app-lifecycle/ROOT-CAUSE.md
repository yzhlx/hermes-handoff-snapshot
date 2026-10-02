# Root cause — no graceful exit

## Symptom
Launching the packaged "学习 OS" EXE left a process that could not be shut down through any
in-app control. Verification had to use an exact-PID kill.

## Mechanism
In `outputs/learning-os-desktop.py`, the old `main()`:
1. Started the API server (`ThreadingHTTPServer` on `127.0.0.1:4174`) and the static server
   (`create_server` on `127.0.0.1:4173`) as daemon threads.
2. Blocked the main thread with an anonymous `threading.Event().wait()`.
3. The `finally` block closed the servers, but it only ran when `main()` returned or raised —
   which never happened during normal operation.

There was no `stop_event`, no `request_shutdown()`, no signal handler, and **no user-facing exit
control** (no tray, no window, no button). Because the app is browser-UI driven, the only
user-visible interaction surface was the web UI — and it had no "exit" affordance at all.

## Why the original fix was insufficient (and what the final fix adds)
A module-level `stop_event` + `request_shutdown()` + SIGINT/SIGTERM handlers are a correct
*internal* shutdown primitive, but by themselves they do **not** close the defect "there is no
user-accessible normal exit entry". A user still could not discover or operate an exit. The
defect is fully closed only when a user can find and click a real exit control.

## Implemented fix (shipped in `a3f77bc`)
### Internal primitive (`outputs/learning-os-desktop.py`)
- Module-level `stop_event = threading.Event()`, `_cleanup_lock`, `_services_cleaned` flag.
- `shutdown_services()`: idempotent; closes `static_server` and `api_server` (`shutdown()` +
  `server_close()`, and `api_server.service.close()`); never raises.
- `request_shutdown()`: sets `stop_event`, calls `shutdown_services()`; idempotent; does **not**
  call `os._exit()` and does **not** kill any other process by name or PID.
- `_install_signal_handlers()`: registers SIGINT/SIGTERM → `request_shutdown()` (guarded; fails
  silently if not in main thread).
- `main()` waits on `stop_event.wait()` (named event, not anonymous), tracks both servers on
  module globals, and the `finally` block calls `shutdown_services()` exactly once.

### User-accessible exit entry (the actual defect closure)
- **Settings page button** (`outputs/learning-os-app.html` / `.js`): a `退出学习 OS` button in a
  new `APPLICATION / 退出应用` panel, with a confirm `<dialog>` (`#exitConfirmDialog`) requiring
  explicit confirmation before any shutdown is requested.
- **Loopback-only controlled endpoint** (`outputs/learning-os-api.py`): `POST /api/v2/shutdown`
  — POST-only, origin-checked (foreign or missing `Origin` → `403`), responds `200` *before*
  calling `request_shutdown()`, so the page can show "学习 OS 已退出，可以关闭此页面。".
  No URL-embedded key, no external call.
- Closing the browser tab does **not** stop the background service; only the confirmed button
  does. This satisfies the requirement that a user can discover and actively operate a normal
  exit.

### Constraint compliance
- No `os._exit()`; no `taskkill`; no process-name/PID kill.
- Clear shutdown order: API + static `shutdown()` → `server_close()` → release 4173/4174.
- No orphan threads; state is saved before exit (SQLite via the service; no schema change).
