# Known issues and limitations

- KNOWN LIMITATION: recognition uses the existing local provider path; no live provider credential was read or used. Two API live-provider tests remain intentionally skipped.
- KNOWN LIMITATION: the Canvas draft is local browser storage; durable attachment-library work is outside this UI recovery.
- KNOWN LIMITATION: the Launcher exposes no normal controlled shutdown (main thread blocks on `threading.Event().wait()`, no tray/exit control). Windows runtime verification confirmed start/restart/persistence/port-release via exact-PID termination; see `reports/windows-runtime-verification.md`. A proper graceful-exit fix is tracked separately in `fix/windows-app-graceful-exit`, not on this branch.
- MANUAL USER ACCEPTANCE: stylus, touch, palm, pressure and pen-eraser hardware behavior require a real device.
