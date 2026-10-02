# RELEASE-STATUS.md — Hermes 学习 OS (Integrated Candidate)

> Release readiness for the unified `ui/hermes-ui-2-program` candidate built in Phase 4.
> Per AGENTS.md §23.6 Release mode: clean build ✓ · full tests ✓ · package smoke test ✓ · version/report ✓ · no prod data in artifacts ✓.

## Release candidate

| Field | Value |
|-------|-------|
| Product | 学习 OS (Hermes UI 2 Program — integrated) |
| Candidate path | `package-ui-2-integrated-candidate/学习 OS/` |
| Launcher | `学习 OS.exe` (2,483,509 B) |
| EXE SHA-256 | `2262b0004c487ad67f4d2787dde0b11aa7e71f9727d6407c12da011074f00cf9` |
| Built from | `ui/hermes-ui-2-program` @ `9b18bc360dcbda82d665bec1eaca1ef95f01fba6` |
| Build | PyInstaller 6.21.0 onedir + windowed, Python 3.13.14 |
| Ports | static 4173, API 4174 (loopback) |

## Readiness checklist

- [x] Clean build (Phase 4) — reproducible, provenance recorded
- [x] Full committed tests (Phase 3) — 16/16 pass
- [x] Package smoke test (Phase 5) — real Windows run, A/B/C/D/E pass
- [x] Version / report — CURRENT-STATE / TASK-QUEUE / RELEASE-STATUS authored
- [x] No production data in artifacts — secret scan 0 real hits; handoff ZIP excludes SQLite/.env/keys/logs/profile/cache/old-zip

## Verification evidence

- Regression: `python -m unittest tests.test_windows_app_graceful_exit tests.test_ui_2_exit_entry tests.test_ui_2_handwriting_entry -v` → **16 tests OK**
- Windows run: startup OK, Canvas draw/erase/undo/redo/clear/page-switch/reload OK, normal exit rc 0 + ports released + no orphan, **Canvas draft recovered across restart**
- Exit security: POST-only + loopback + origin-checked `/api/v2/shutdown`; idempotent `request_shutdown()`; run-once `shutdown_services()`; SIGINT/SIGTERM wired; no anonymous wait; no collateral kill

## Manual user acceptance (required before public release)

1. **Real stylus (pen) input** on a physical digitizer — confirm a natural handwriting stroke is captured (automated `PointerEvent` plumbing passes; hardware sign-off is the user's).
2. General daily-driver smoke: open each page (今天的安排 / 周计划 / 错题 / 每日复习 / AI 对话 / 学习记录 / 设置), create/edit/delete a task, confirm data persists after restart.
3. Graceful exit via 设置 → 退出学习 OS → confirm; confirm ports 4173/4174 are free afterward and no orphan process remains.

## Known limitations

- Broad functional category suites (Core/Store/API/Static/Responsive/World Canvas/首页/周计划/错题/Timeline/Hermes AI/学习状态/统计) are not a committed runnable suite; validated via real-Windows runs + the 3 committed suites, not an exhaustive automated matrix.
- Single benign `GET /favicon.ico` 404 in server logs (browser auto-request; no favicon shipped). Non-blocking.
- `OSError: [WinError 10038]` in `test_ui_2_exit_entry` is a benign harness warning (select on non-socket in the port-wait helper); test passes.

## Release blockers

- **None.** The merged main branch + integrated candidate are releasable for internal/manual-acceptance distribution. The only gating item is the MANUAL stylus acceptance (a hardware sign-off, not a code defect).

## Not in this release (deferred)

- UI design upgrade (`ui/hermes-learning-journal-v2`) — next phase.
- Infrastructure features on `feat/hermes-ai-evals`, `feat/hermes-engineering-skills`, `feat/hermes-release-qa`, `chore/repository-foundation`, `rescue/mixed-work-20260722` — not merged.

## Pre-merge checkpoint

- `incoming/hermes-source-handoff-20260722-130603.zip` — PRE-MERGE CHECKPOINT only; do not overwrite/delete.
