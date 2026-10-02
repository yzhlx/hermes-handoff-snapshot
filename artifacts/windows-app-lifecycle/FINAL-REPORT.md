# FINAL REPORT — Hermes Learning OS graceful-exit defect

Branch: `fix/windows-app-graceful-exit`  ·  Worktree: `windows-app-graceful-exit`
Head: `a3f77bc`  ·  RED contract: `8130a23`
Status: **RESOLVED — Application lifecycle PASS (runtime-verified)**
Merge decision this round: **NOT auto-merged to `ui/hermes-ui-2-program`** (per authorization);
recommend merge after human review.

---

## 1. RED contract commit
`8130a23` — `test(lifecycle): define graceful shutdown contract`
First commit on the branch. Carried the defect docs (`artifacts/windows-app-lifecycle/*`) and the
failing exit test (`tests/test_windows_app_graceful_exit.py`, 1 FAIL + 1 ERROR from the absent
`request_shutdown` primitive). Branch marked RED / not merge-ready.

## 2. Implementation commit
`a3f77bc` — `fix(lifecycle): add user-accessible graceful shutdown`
Turned the RED test GREEN and added the user-facing exit entry. 7 files changed (+522 / −35).

## 3. Actual user exit entry adopted
UI 2.0 **settings page** → `APPLICATION / 退出应用` panel → button **`退出学习 OS`** →
confirm `<dialog>` (`#exitConfirmDialog`) → on confirm, `POST /api/v2/shutdown`.
The endpoint is loopback-only, **POST-only**, and **origin-checked** (foreign/missing `Origin`
→ `403`); it returns `200` *before* shutdown so the page shows "学习 OS 已退出，可以关闭此页面。".
No URL key, no external call. Closing the browser tab does **not** stop the background service.
This is the defect's actual closure (the internal primitive alone was, per the user's correction,
insufficient).

## 4. Modified files
- `outputs/learning-os-desktop.py` — `stop_event`, idempotent `request_shutdown()`,
  `shutdown_services()`, SIGINT/SIGTERM handlers, `main()` waits on `stop_event`.
- `outputs/learning-os-api.py` — `POST /api/v2/shutdown` handler (origin-checked, POST-only).
- `outputs/learning-os-app.html` — exit panel + confirm dialog.
- `outputs/learning-os-app.css` — `.danger` / exit dialog styles.
- `outputs/learning-os-app.js` — button → dialog → confirm → `request('/shutdown')` wiring.
- `tests/test_windows_app_graceful_exit.py` — 13-case suite (RED→GREEN).
- `tests/test_ui_2_exit_entry.py` — Playwright UI exit-entry test.

## 5. Test results
- `tests/test_windows_app_graceful_exit.py`: **13/13 PASS**.
- `tests/test_ui_2_exit_entry.py`: **1/1 PASS** (real browser click→confirm→self-exit).
- Handwriting regression `tests/test_ui_2_handwriting_entry.py`: **2/2 PASS**.
- Full suite (Launcher, API, Static, default Python, Canvas Model, Handwriting, Responsive
  Handwriting, `node --check` ×3 JS, `git diff --check`): **all PASS / clean**.
- No mock-only process verification; no lowered assertions; the RED test was kept and turned GREEN.

## 6. New candidate package path
`package-ui-2-graceful-exit-candidate/学习 OS/` (onedir, windowed) — built **without** overwriting
`package-ui-2-canvas-candidate`, any historical package, or the 13:06 migration handoff.

## 7. Candidate EXE SHA-256
`d80e7affb81a800ce92c97446a4b36f9da02dc2cbd6a6b01b59e461f4a7d32b4`  (size 2,483,509 bytes)

## 8. App self-exit via its own flow
**PASS.** Phase 8 launched the EXE and drove a real same-origin browser to click + confirm the
exit button. The EXE self-terminated on its own — **no `taskkill`, no precision-PID** — and a
`GET`/probe confirmed the process was gone (exit code 0).

## 9. 4173 / 4174 auto-released
**PASS.** After the user-confirmed exit, both loopback ports were no longer listening
(`port_is_listening` False) within the wait window.

## 10. Orphan processes
**None.** After self-exit, no process held 4173/4174 and no leftover app process remained.
(Precision-PID termination was used ONLY as a smoke-test safety cleanup and is not required for
the normal exit.)

## 11. Canvas persistence maintained
**PASS (source) / MANUAL USER ACCEPTANCE (live stylus).** The exit change does not touch the
Canvas; `test_canvas_draft_capability_intact` confirms the draft-storage capability and source
are intact, and the Canvas page loads normally. Real pen-input drawing cannot be automated and
remains **MANUAL USER ACCEPTANCE**.

## 12. Still need precision-PID cleanup?
**No.** The normal exit path self-terminates cleanly. Precision-PID was used only once, in a
smoke-test exception branch, and is documented as a safety net — not a dependency.

## 13. Branch / worktree status
`fix/windows-app-graceful-exit` @ `a3f77bc`, working tree **clean** (`git status --short`
empty; `git diff --check` clean). Two commits on the branch:
`8130a23` (RED contract) → `a3f77bc` (implementation).

## 14. Merge recommendation to `ui/hermes-ui-2-program`
**Do NOT auto-merge this round** (explicit authorization). After human review of this report and
the manual Canvas-stylus acceptance, **recommend merging** `fix/windows-app-graceful-exit` into
`ui/hermes-ui-2-program` via `--no-ff` (the branch is a clean, tested, runtime-verified closure
of the "no normal exit" defect, and does not alter the Canvas/schema/network-binding behavior).

## 15. Items still needing manual acceptance
- **Real stylus / pen-input drawing** on the handwriting Canvas (headless automation cannot
  replicate pen input). The draft-storage source is verified intact; only live pen interaction
  is deferred to the user.
- Optional: final human UX sign-off of the exit-confirm dialog copy in a production-like
  environment (the mechanism and runtime self-exit are already verified).

---

## Build provenance (Phase 7)
- **Branch / commit:** `fix/windows-app-graceful-exit` @ `a3f77bc`.
- **Build command:**
  `pyinstaller --noconfirm --onedir --windowed --name "学习 OS" --add-data "<worktree>/outputs;." --distpath "<worktree>/package-ui-2-graceful-exit-candidate" <worktree>/outputs/learning-os-desktop.py`
  (work/spec on F: to avoid the cross-volume failure seen in earlier attempts).
- **Python:** 3.13.14 (managed runtime; reference canvas-candidate used 3.12.13 — the app is
  pure stdlib so behavior is equivalent; recorded for honesty).
- **PyInstaller:** 6.21.0 (matches the reference canvas-candidate exactly).
- **Build time:** 2026-07-22 14:52:34 +0800.
- **Layout:** onedir — `学习 OS.exe` + `_internal/` (matches the reference package shape).
- **Canvas workspace JS:** present (`learning-os-handwriting-workspace.js` in `_internal/`).
- **In-package resource hash check:** 13 key bundled files (html/css/js/py) SHA-256 **all MATCH**
  source `outputs/`.
- **Secret scan:** 0 plaintext-key pattern hits across bundled text resources.
- **File count:** 85 (matches reference).

## Phase 8 runtime evidence (3 scenarios, all PASS)
| Scenario | ports up | entry found | confirm dialog | self-exit | ports released | orphan | rc |
|---|---|---|---|---|---|---|---|
| isolated canonical path | ✓ | ✓ | ✓ | ✓ | ✓ | none | 0 |
| restart same isolated dir | ✓ | ✓ | ✓ | ✓ | ✓ | none | 0 |
| path with spaces + Chinese | ✓ | ✓ | ✓ | ✓ | ✓ | none | 0 |

Status text observed after confirm: **"学习 OS 已退出，可以关闭此页面。"**

## Status-label summary
- Application lifecycle (self-exit): **PASS**
- Port release / no orphan: **PASS**
- User-discoverable exit entry: **PASS**
- Automated test suite: **PASS**
- Candidate build + hash check + secret scan: **PASS**
- Real stylus Canvas drawing: **MANUAL USER ACCEPTANCE**
- Auto-merge to `ui/hermes-ui-2-program`: **NOT THIS ROUND** (recommend after review)
