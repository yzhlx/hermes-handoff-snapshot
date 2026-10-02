# Candidate Recovery Port Check — 2026-07-22 04:44 +08:00

## Scope

Read-only recovery verification only. No package, process, local service, SQLite database, credential, or user data was changed.

## Port-owner command

```powershell
Get-NetTCPConnection -State Listen -LocalPort 4173,4174
Get-CimInstance Win32_Process -Filter "ProcessId=<listener PID>"
```

## Actual result

| Port | Status | PID | Executable |
| --- | --- | --- | --- |
| 4173 | LISTEN | 35932 | historical `package-ai-fixed/学习 OS/学习 OS.exe` |
| 4174 | LISTEN | 35932 | historical `package-ai-fixed/学习 OS/学习 OS.exe` |

The candidate cannot safely own its fixed API/static ports while that pre-existing process remains running. It was not terminated because it may be user-owned.

## Candidate payload parity command

```powershell
Get-FileHash outputs/learning-os-app.css -Algorithm SHA256
Get-FileHash package-ui-2-candidate/学习 OS/_internal/learning-os-app.css -Algorithm SHA256
Get-FileHash outputs/learning-os-app.js -Algorithm SHA256
Get-FileHash package-ui-2-candidate/学习 OS/_internal/learning-os-app.js -Algorithm SHA256
Get-FileHash outputs/learning-os-canvas-model.js -Algorithm SHA256
Get-FileHash package-ui-2-candidate/学习 OS/_internal/learning-os-canvas-model.js -Algorithm SHA256
```

## Actual result

All three source/package pairs matched exactly:

- `learning-os-app.css`: PASS
- `learning-os-app.js`: PASS
- `learning-os-canvas-model.js`: PASS

## Launcher-unit regression

```powershell
& $py work/presentations/learning-os-ui/tmp/test_windows_launcher.py
```

Actual result at 2026-07-22 04:45 +08:00: `Ran 6 tests in 0.056s` — `OK`.

This is a source-level isolated unit suite and does not exercise the candidate package's blocked fixed-port lifecycle.

## Outcome

`BLOCKED` for candidate-owned startup, isolated SQLite write, reload/restart persistence, normal shutdown, and port release. `PASS` only for the non-invasive port-owner identification and candidate asset-currency checks.
