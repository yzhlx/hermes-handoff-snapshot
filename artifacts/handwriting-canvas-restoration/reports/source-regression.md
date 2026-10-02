# Source regression report

Status: PASS

Executed 2026-07-22 against a static server started from this worktree on port 52344. The server returned HTTP 200 and exact SHA-256 byte matches for the HTML, CSS, application JS, Canvas model, and new workspace JS.

- Core: 6 passed.
- Store: 8 passed.
- API: 51 passed; 2 intentional live-provider skips.
- Static host: 3 passed.
- Launcher units: 6 passed.
- Motion contract: passed.
- Canvas model: 10 passed, repeated three times.
- World Canvas, handwriting, responsive handwriting, UI 2.0 product, weekly plan, wrong-answer, timeline, Hermes AI, AI settings, learning state/statistics, and UI 2.0 visuals: passed.
- Formal root entry discovery: 2 passed, repeated three times.
- `node --check` passed for application JS, Canvas model, and workspace controller.
- `git diff --check` passed before source commit.

The pre-existing listener on port 52342 returned different bytes and was not stopped; it was not used for the source verification.
