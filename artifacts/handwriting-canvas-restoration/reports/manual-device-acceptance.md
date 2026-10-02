# Manual device acceptance

Status: MANUAL USER ACCEPTANCE

Use the new candidate package with a non-sensitive `EXE_QA_TEST_` marker and an isolated test profile. Confirm:

- pen writing and fast continuous strokes;
- palm rejection while writing;
- pressure response, if supported by the hardware/browser;
- pen eraser end, if supported;
- touch pan and pinch zoom;
- tablet landscape and portrait toolbar access;
- long writing session without missed or duplicated strokes;
- eraser, undo, redo, clear confirmation, page changes, and exports;
- local draft save, close, refresh, restart, and restoration;
- candidate EXE close releases 4173/4174 and leaves no orphan process.

No physical stylus or touch hardware was used in this task, so the hardware-specific items above remain MANUAL USER ACCEPTANCE and are not reported as automated PASS.

Separately, the runtime verification (`reports/windows-runtime-verification.md`) confirmed the lifecycle items that do not require hardware: candidate EXE close releases 4173/4174 and leaves no orphan process (verified via exact-PID termination, since the Launcher has no normal exit control), plus local draft save/close/refresh/restart restoration. Those specific items are recorded as PASS in that report.
