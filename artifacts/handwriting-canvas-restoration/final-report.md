# Hermes Handwriting Canvas Stabilization, Commit and Windows Package Verification

## PASS

1. Formal regression moved out of `tmp`: `tests/test_ui_2_handwriting_entry.py` is the only new test source; no duplicate remains in `tmp`.
2. Stable discovery command finds it automatically: 2 tests passed three consecutive times.
3. The formal root now has a real navigation entry, workspace DOM, Canvas model script, and workspace controller; it does not navigate to or depend on the prototype URL.
4. Source regression passed: core/storage/API/static/launcher/model/UI suites and JS syntax checks passed; live provider coverage is intentionally skipped.
5. Canvas restoration is committed as `2c84701fabbb764ad8e07da23c61d94d65c94d19`.
6. New candidate path: `package-ui-2-canvas-candidate/学习 OS/学习 OS.exe`.
7. Candidate contains the workspace JS and all checked source/package hashes match, including the new JS.
8. No SQLite schema or API contract was changed. Formal re-entry regression found no duplicate listeners. No key or user data was committed.
9. Windows runtime verification completed (see `reports/windows-runtime-verification.md`): candidate EXE launch, full interaction matrix, persistence/restart, 5/5 path matrix, and exact-PID port cleanup all PASS. The environment could not be left with a stray process because all termination used exact PID.

## RESOLVED (was BLOCKED)

1. The candidate EXE launch/close/restart, candidate-owned HTTP, Canvas actions, persistence, port release, orphan-process check, and path matrix were completed in a dedicated controlled Windows session. The only residual item is the absence of a normal controlled shutdown (KNOWN LIMITATION, tracked in `fix/windows-app-graceful-exit`), not a verification gap. No unknown process was stopped; ports were free before launch.

## NOT COVERED

- Real provider recognition with a user credential.
- EXE launch from original, space-containing, Chinese-containing, non-project, and `C:\Windows` paths.

## KNOWN LIMITATION

- Canvas draft persistence is browser-local; durable attachment storage remains outside this recovery.
- The launcher does not expose a normal controlled shutdown command.

## MANUAL USER ACCEPTANCE

See `reports/manual-device-acceptance.md` for stylus, touch, palm, pressure, orientation, long-session, and close/restart checks. No hardware capability is claimed as automated PASS.

## Merge recommendation

Recommended for merge. The Windows runtime verification is complete (PASS / KNOWN LIMITATION / MANUAL USER
ACCEPTANCE). Merge with:

```powershell
git checkout ui/hermes-ui-2-program
git merge --no-ff fix/handwriting-canvas-parity
```
