# Windows candidate package runtime verification

Status: Canvas runtime PASS · Persistence/restart PASS · Path matrix 5/5 PASS · Exact-PID port cleanup PASS · Normal exit KNOWN LIMITATION · Color selector NOT COVERED (NOT APPLICABLE) · Hardware pen MANUAL USER ACCEPTANCE

This is the slimmed verification record for the candidate package built from source commit `626e8f1`
(`fix/handwriting-canvas-parity`). Raw evidence (scripts, JSON reports, screenshots, process records) is
retained at `C:\Users\user\Documents\Codex\hermes-canvas-runtime-qa\20260722-125734\` and is intentionally
**not** committed to the branch.

## Scope and boundaries

- Verification target: `package-ui-2-canvas-candidate/学习 OS/学习 OS.exe`.
- No source was modified, no package was rebuilt, the Launcher was not modified, and no branch was merged.
- The real user `AppData\Local\Learning OS` store was left untouched (verified by mtime: 07-21 / 07-22 unchanged).
- Test tag: `CANVAS_QA_20260722-125734_FH2IYU`; isolated `LOCALAPPDATA` and isolated browser profile used.
- No bulk process killing by name. All termination used exact PID via `Stop-Process -Force`.

## Port gate

- `STATIC_PORT=4173`, `API_PORT=4174`, `HOST=127.0.0.1`.
- Ports were free before launch (no unknown occupant). After launch both ports were confirmed LISTENING by PID.
- Exact-PID termination released both ports; re-launch bound them again. No orphan process remained (single-process model).

## Interaction matrix (Playwright + system Chrome, headless)

| Check | Result | Note |
| --- | --- | --- |
| Pointer pen strokes | PASS | real pointer draw via mouse confirmed |
| Color switch | NOT COVERED | no DOM color control; `startStroke` hardcodes `#172127` |
| Line width | PASS | `strokeSize` slider drives width |
| Clear with confirm | PASS | `confirmClear` guard present |
| Undo / redo | PASS | `undoStroke` / `redoStroke` |
| Eraser | PASS | `eraserTool` |
| Page switch, no duplicate binding | PASS | re-entry guard verified |
| Reload recovery | PASS | localStorage draft key `learning-os-handwriting-draft-v1` |
| Console fatal errors | PASS | only benign `favicon.ico` 404 |
| Security scan | PASS | 0 plaintext-key hits in served JS / API |

## Path matrix (5/5 PASS)

Original dir, space-containing path, Chinese-containing path, non-project cwd, and `C:\Windows` cwd all
launched, served, and cleaned up correctly.

## Persistence and restart

- Draft persists only in browser localStorage (no server-side draft sync). This is an honest architecture
  disclosure, not a defect.
- Close + restart of the EXE restored the workspace and released ports (verified via exact-PID termination).

## Application lifecycle

- KNOWN LIMITATION: the Launcher main thread blocks on `threading.Event().wait()` and exposes no tray / exit
  control, so there is no normal controlled shutdown path. Verification therefore used exact-PID termination.
  This is a product defect tracked separately in `fix/windows-app-graceful-exit` (Phase 3), **not** on this branch.

## Color capability decision

- NOT APPLICABLE. `FEATURE-INVENTORY.md` states the preserved reference has no separate colour-picker control
  and the restored product uses the reference default ink colour. The old prototype/reference also lacks color
  selection. No open parity gap is recorded; color selection is **not** implemented in this phase.

## Precise status statement

核心书写工作区和关键编辑能力已恢复并通过候选包运行验证；经核对 FEATURE-INVENTORY 与旧参考实现，
颜色切换不属于历史正式能力（旧参考实现亦无独立颜色控件），当前候选 UI 不提供颜色控件，记为 NOT APPLICABLE。

## Merge recommendation

The blocked EXE matrix is now completed. This branch is recommended for merge into `ui/hermes-ui-2-program`:

```powershell
git checkout ui/hermes-ui-2-program
git merge --no-ff fix/handwriting-canvas-parity
```
