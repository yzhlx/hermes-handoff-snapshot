# Hermes Authoritative Product Source Recovery — Final report

## PASS

1. Candidates found: authoritative `outputs/`, legacy Canvas source in that root, source tests under `work/presentations/learning-os-ui/tmp`, and historical packages for correlation.
2. Authoritative source: `C:\Users\user\Documents\Codex\2026-07-21\https-chatgpt-com-share-6a5e4b81-db84\outputs\`.
3. Evidence: build spec references `outputs/`; eleven UI 2.0 package/source hashes match; source services and regression tests run from the restored copy.
4. Latest UI 2.0 candidate package source: `outputs/`.
5. Static hashes: exact match for HTML, CSS, app JS, and Canvas-model JS.
6. Python service correlation: exact checked match for API, AI, core, store, static, launcher, and credentials.
7. Most complete handwriting Canvas: `outputs/learning-os-ui-prototype.html`.
8. Current UI 2.0 Canvas omission: no Canvas mount, no Canvas-model script include, and no Canvas controls on `learning-os-app.html`.
9. External backup: `C:\Users\user\Documents\Codex\source-recovery-backups\hermes-authoritative-20260722-100257` (65 files, SHA-256 manifest verified).
10. UI branch: created as `ui/hermes-ui-2-program`.
11. Source recovery commit: `f8143da917d17c2b61c57a7acf20dd30beb49456` (`chore(product): recover authoritative Hermes UI 2.0 source`).
12. UI worktree: `F:\Users\user\Documents\learning os-worktrees\hermes-ui-2-program`.
13. Tests: Python unit/API/static/launcher 74 passed with 2 intentional live-provider skips; Canvas model 10 passed; 11 Playwright/UI regression scripts plus the `test_ui_motion_contract.py` UI contract script passed (12 executable UI/Canvas regression scripts total); source static/API both returned HTTP 200.
14. Sensitive data: none found or copied; no credential-manager value was read.

## KNOWN LIMITATION

The recovered UI 2.0 state faithfully reproduces the user-confirmed P0 Canvas parity regression. Passing legacy Canvas tests do not establish UI 2.0 Canvas availability.

## Next step

Create `fix/handwriting-canvas-parity` from the source-recovery commit only after the recovery branch is clean. Use the preserved prototype as the behavioral reference and add UI 2.0 entry-point coverage before making any Canvas change.
