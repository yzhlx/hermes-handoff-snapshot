# Milestone 12 — Windows Candidate Package

## Status: BLOCKED

## PASS

- Built `package-ui-2-candidate/学习 OS/学习 OS.exe` with PyInstaller 6.21.0 in a new output, work, and spec directory.
- Candidate contains 94 files. Embedded `learning-os-app.css` SHA-256 exactly matches `outputs/learning-os-app.css`; the embedded canvas-model SHA-256 also matches its source.
- No SQLite database file is embedded in the candidate. A text-resource secret-pattern scan found no plaintext key pattern.
- Candidate EXE was launched by absolute path from `C:\` with an isolated `LOCALAPPDATA` root while a historical package owned the default ports. It exited with code 0 in 1395ms, recorded the existing-service state, and did not add or remove a listener.
- Candidate embedded static resources were served at port 52343 with HTTP 200. `test_learning_os_app.py` and `test_ui_2_program_visuals.py` both passed against those packaged assets. The owned temporary static-server port was released after the test.

- 2026-07-22 04:19 +08:00 recheck: embedded CSS and canvas-model SHA-256 values still match `outputs/`; exact extension filtering found 0 embedded SQLite files; a text-resource secret-pattern scan found 0 matches; `test_windows_launcher.py` passed all 6 tests in 0.257s.
- 2026-07-22 04:45 +08:00: the isolated launcher-unit suite passed again, 6 tests in 0.056s. It verifies the launcher implementation and does not replace candidate-owned fixed-port lifecycle evidence.

## BLOCKED

- Ports 4173 and 4174 are owned by PID 35932, historical `package-ai-fixed/学习 OS/学习 OS.exe`. This run did not stop it.
- Therefore a candidate-owned local API/static launch, isolated SQLite writes, page reload/restart persistence, candidate-owned shutdown, and default-port release cannot be verified safely.

## Reconfirmation

- At 2026-07-22 04:16 +08:00, `Get-NetTCPConnection -State Listen -LocalPort 4173,4174` again resolved both listeners to PID 35932. `Win32_Process.ExecutablePath` resolved that PID to the historical `package-ai-fixed` executable. No process was stopped because it predates the candidate verification and may be user-owned.
- At 2026-07-22 04:44 +08:00, the same read-only port and executable-path check again found PID 35932 owning both ports from the historical package. Candidate payload parity was also rechecked: embedded CSS, application JavaScript, and Canvas model all have SHA-256 values equal to their current source files. No service, package, database, or user data was changed.

## NOT COVERED

- Real Provider call with a user credential. The source test suite intentionally skips live-provider calls unless `LEARNING_OS_LIVE_TEST=1` is supplied.

## KNOWN LIMITATION

- The launcher lifecycle is not changed by UI 2.0. A current launcher process does not provide a newly implemented tray exit command.
- Temporary test browser data exists under `tmp/ui2-candidate-existing-service-localappdata/`; it was created by the EXE's browser-open action, not by SQLite or the candidate bundle, and was not removable under the current execution policy.

## Resume condition

Once 4173/4174 are free, launch the existing candidate with a fresh isolated `LOCALAPPDATA` root, use `EXE_QA_TEST_` records, and complete the blocked lifecycle/persistence matrix without rebuilding the candidate.
