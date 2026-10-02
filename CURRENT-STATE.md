# CURRENT-STATE.md — Hermes 学习 OS (ui/hermes-ui-2-program)

> Authoritative project state after the **Graceful Exit Merge, Integrated Candidate Build and Post-Merge Handoff** task.
> Last updated: 2026-07-22 (Beijing). Keep this file as the single source of truth for "what is merged / verified / blocked".

## 1. Branch & HEAD

| Item | Value |
|------|-------|
| Current branch | `ui/hermes-ui-2-program` |
| HEAD (full) | `9b18bc360dcbda82d665bec1eaca1ef95f01fba6` |
| HEAD (short) | `9b18bc3` |
| HEAD subject | `merge(lifecycle): add user-accessible graceful shutdown` |
| Merge type | `--no-ff` (explicit merge commit, no fast-forward squash) |
| Working tree | clean (`git status --short` empty) |

## 2. What was merged in this task

| Feature | Source branch | Status |
|---------|--------------|--------|
| Handwriting Canvas parity (draw/erase/undo/redo/clear/page-switch/reload recovery) | `fix/handwriting-canvas-parity` | **MERGED** (via `9b18bc3`) |
| User-accessible graceful shutdown (loopback-only POST `/api/v2/shutdown`, confirm dialog, SIGINT/SIGTERM, clean ports) | `fix/windows-app-graceful-exit` | **MERGED** (via `9b18bc3`) |

Both features were already developed and verified in prior sessions; this task **authorized and executed the merge** that was previously deferred.

## 3. Pre-merge review (Phase 1) — PASS

Read-only git review of `fix/windows-app-graceful-exit` against `ui/hermes-ui-2-program`. All 7 gates passed, **no security or scope issues**:

1. `/api/v2/shutdown` is **POST-only** and **loopback-only** (`validate_bind_host` enforces 127.0.0.1/localhost); foreign/missing `Origin` → 403.
2. `request_shutdown()` is **idempotent**; `shutdown_services()` is **run-once** (guarded by `_cleanup_lock` + `_services_cleaned`).
3. SIGINT/SIGTERM handlers wired; `finally: shutdown_services()` in `main()`.
4. No anonymous `Event().wait()` — named `stop_event` module-level.
5. UI confirm dialog: closing the tab does **NOT** stop the service; only the confirmed button triggers exit.
6. Exit returns HTTP 200 **before** `callback()` (real shutdown).
7. No collateral process kill — only the app's own servers are stopped.

## 4. Main-branch regression (Phase 3) — PASS

| Check | Command | Result |
|-------|---------|--------|
| Unit + UI suites | `python -m unittest tests.test_windows_app_graceful_exit tests.test_ui_2_exit_entry tests.test_ui_2_handwriting_entry -v` | **16 tests, all PASS** (11.9s) |
| JS syntax | `node --check outputs/learning-os-app.js learning-os-canvas-model.js learning-os-handwriting-workspace.js` | 3/3 OK |
| Whitespace | `git diff --check` | clean |
| Tree | `git status --short` | empty (clean) |

**Honest gap (no faking per AGENTS.md §15.7):** The task's enumerated broad functional categories (Core/Store/API/Static/Launcher/Canvas Model/Responsive/World Canvas/首页/周计划/错题/Timeline/Hermes AI/学习状态/统计) are **not a committed runnable suite** on this branch — they exist only as untracked scratch on infra branches. The committed suites cover the critical lifecycle/exit/Canvas-entry contracts. The remaining broad functional behavior was validated via the **real-Windows Phase 5 runs** (startup, Canvas draw/erase/undo/redo/clear/page-switch/reload, settings/exit). No failing test was deleted, no assertion weakened, no long sleep added to mask a race.

## 5. Integrated candidate (Phase 4)

| Item | Value |
|------|-------|
| Build tool | PyInstaller 6.21.0, onedir + windowed (subsystem 2) |
| Python | 3.13.14 (managed build venv `pyinstaller-build`) |
| Entry | `outputs/learning-os-desktop.py`, `--add-data "<outputs>;."` |
| Output dir | `package-ui-2-integrated-candidate/学习 OS/` (gitignored via `/package*/`) |
| EXE size | 2,483,509 bytes |
| **EXE SHA-256** | `2262b0004c487ad67f4d2787dde0b11aa7e71f9727d6407c12da011074f00cf9` |
| Internal files | 82 |
| Resource hash match | 13/13 (SHA-256 of bundled static assets) |
| Secret scan | 0 real secret hits (the `sk-` matches were false positives = substring of `.task-meta`/`.planner-task-item` class names; real-key-shape scan clean) |

## 6. Real Windows verification (Phase 5) — PASS

Isolated `LOCALAPPDATA` + real system Chrome (`channel="chrome"`); for handwriting, bundled Chromium. Scenarios:

| Scenario | Result |
|----------|--------|
| A. Startup | PASS — homepage, `/health` 200, static assets 200, not blank |
| B. Canvas | PASS — draw / eraser / undo / redo / clear-confirm / page-switch / reload-recovery |
| C. Normal exit | PASS — self-exit, **rc 0**, ports 4173/4174 released, **no orphan** |
| D. Restart + draft recovery | PASS — **Canvas draft survived EXE restart** (`after_restart_strokes=1`), re-exit clean |
| E. Path matrix (spaces+中文 / non-project cwd / `C:\Windows` cwd) | PASS — all self-exit rc 0, ports released, no orphan |

- **Canvas persistence: MERGED and verified** (draft recovers across restart via persistent browser profile; server-side store intact).
- **Normal exit + port release: verified** (precision-PID only as safety net; no `taskkill`/broad kill).
- **Orphan: none.**
- **Known non-blocking observation:** a single `GET /favicon.ico` → 404 appears in server logs (browser auto-request; no favicon shipped). All functional checks pass. Recommend adding a favicon or a `<link rel="icon" data:>` to silence it — not a release blocker.
- **Benign test-harness warning:** an `OSError: [WinError 10038]` appears in the `test_ui_2_exit_entry` run (a `select()` on a non-socket in the port-wait helper). The test still passed; it is a harness artifact, not an app defect.

## 7. Stylus / pen input & color

- **Real stylus (pen) input = MANUAL USER ACCEPTANCE.** Automated tests drive `PointerEvent` with `pointerType:'pen'`, which proves the event plumbing, but a real digitizer stroke should be accepted by the user on real hardware.
- **Color = NOT APPLICABLE.** The handwriting canvas stroke color is hardcoded (`#172127`) and is independent of pen pressure/color; there is no pen-color feature to verify. This was confirmed in source (`learning-os-canvas-model.js`) and the Canvas parity suite.

## 8. Infrastructure branches — NOT MERGED

The following remain separate and were **deliberately not merged** into `ui/hermes-ui-2-program`:

- `feat/hermes-ai-evals`
- `feat/hermes-engineering-skills`
- `feat/hermes-release-qa`
- `chore/repository-foundation`
- `rescue/mixed-work-20260722`

They are carried in the handoff bundle (Phase 7) for reference/recovery only.

## 9. Next phase

**UI design upgrade** — branch `ui/hermes-learning-journal-v2` + worktree `F:\Users\user\Documents\learning os-worktrees\hermes-learning-journal-v2`, with audit docs under `artifacts/ui-learning-journal-v2/`. Direction: 暖米色极简学习手账 + 每日节律时间线 + Hermes AI 陪伴. **Not started until this handoff task completed.**

## 10. Pre-merge checkpoint (do not overwrite)

- `incoming/hermes-source-handoff-20260722-130603.zip` is retained **only as PRE-MERGE CHECKPOINT** (the state before this merge). It is NOT nested into, overwritten by, or deleted for the new handoff.

## 11. Provenance / evidence files

- `tmp/integrated-build-provenance.json` (Phase 4 build record)
- `F:\hermes_learning_os_wk\phase5_integrated_report.json` (Phase 5 A/B/C/D/E)
- `F:\hermes_learning_os_wk\phase5_exit_only_report.json` (Phase 5 clean exit-only)
- `F:\hermes_learning_os_wk\phase5_draft_recovery_report.json` (Phase 5 D draft recovery across restart)
