# Hermes AI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use systematic debugging and test-driven development task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair only the verified Hermes AI provider integration defect and produce an independently packaged, evidence-backed Windows build.

**Architecture:** Preserve the Python local API, SQLite configuration/persistence, Windows Credential Manager, and static frontend. Audit the existing adapter boundary first; route connection testing, chat, and wrong-answer analysis through the same validated provider behavior without changing unrelated product behavior.

**Tech Stack:** Python 3.12 standard library HTTP server/SQLite/ctypes, static HTML/CSS/JavaScript, Playwright, PyInstaller.

---

### Task 1: Establish a safe, reproducible baseline

**Files:**
- Create: `artifacts/qa/ai-integration/current-ai-call-chain.md`
- Create: `artifacts/qa/ai-integration/baseline-reproduction.md`
- Create: `artifacts/qa/ai-integration/commands.log`
- Inspect: `outputs/learning-os-ai.py`, `outputs/learning-os-api.py`, `outputs/learning-os-core.py`, `outputs/learning-os-store.py`, `outputs/learning-os-credentials.py`, `outputs/learning-os-app.js`, `outputs/learning-os-app.html`

- [ ] Start source services with an isolated data directory and run the existing suite.
- [ ] Record the settings-to-provider-to-SQLite call graph from actual code.
- [ ] Reproduce unconfigured, malformed-provider, empty-response, and normal mocked requests in source and `package-fixed-v2`, without reading a real credential.

### Task 2: Write deterministic failing regression tests

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] Add one focused test for each demonstrated adapter failure, including request URL/path, protocol payload, response extraction, normalized status/error, persistence, and secret redaction.
- [ ] Run the new test against the pre-fix source and save its failure evidence.

### Task 3: Implement the smallest adapter and UI correction

**Files:**
- Modify: `outputs/learning-os-ai.py`
- Modify only if required by the proven call path: `outputs/learning-os-api.py`, `outputs/learning-os-app.js`, `outputs/learning-os-app.html`

- [ ] Apply a single focused fix at the traced root cause.
- [ ] Keep credentials out of SQLite, frontend responses, logs, screenshots, and reports.
- [ ] Keep user chat messages persisted before a provider failure and retain retryable UI state.

### Task 4: Verify source behavior, package, and evidence

**Files:**
- Create: `artifacts/qa/ai-integration/*.md`
- Create: `package-ai-fixed/学习 OS/` via the existing packaging flow

- [ ] Run all new adapter tests three times and the relevant existing suite.
- [ ] Run a controlled real-provider smoke test only if an existing usable configuration is available; otherwise report `BLOCKED`.
- [ ] Build only `package-ai-fixed/学习 OS/` and run isolated package startup, persistence, and no-secret checks.
- [ ] Write the required PASS/FAIL/BLOCKED/NOT COVERED/KNOWN LIMITATION final report.
