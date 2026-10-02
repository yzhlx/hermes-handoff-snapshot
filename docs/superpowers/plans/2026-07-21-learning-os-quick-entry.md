# Learning OS Quick Entry Implementation Plan

> **For agentic workers:** Execute task-by-task with tests before production changes.

**Goal:** Let a learner convert plan text/photos and error-question photos into editable previews, then save them locally with one confirmation.

**Architecture:** Store uploads as files beneath the local data directory and store only attachment metadata in SQLite. The AI gateway receives temporary data URLs for selected images and returns strict JSON drafts; the browser lets the learner edit the draft before it creates tasks or an error question.

**Tech Stack:** Python standard library, SQLite, existing OpenAI-compatible AI gateway, vanilla HTML/CSS/JavaScript, unittest and Playwright.

### Task 1: Local Attachments and Quick-Entry Draft Contracts

**Files:**
- Modify: `outputs/learning-os-core.py`
- Modify: `outputs/learning-os-api.py`
- Test: `work/presentations/learning-os-ui/tmp/test_learning_os_core.py`
- Test: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] Write failing tests that a PNG attachment is saved outside SQLite and that an error question lists its attachment metadata.
- [ ] Implement attachment metadata, filename sanitization, MIME/size validation, and loopback JSON upload routes.
- [ ] Run focused core/API tests.

### Task 2: AI Photo Extraction

**Files:**
- Modify: `outputs/learning-os-ai.py`
- Modify: `outputs/learning-os-api.py`
- Test: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] Write failing tests for strict weekly-task and error-question extraction JSON.
- [ ] Implement chat-completions and responses image payload adapters plus draft validation.
- [ ] Add routes that return drafts without persisting tasks or error questions.
- [ ] Run focused AI/API tests.

### Task 3: Confirmed Quick-Entry UI

**Files:**
- Modify: `outputs/learning-os-app.html`
- Modify: `outputs/learning-os-app.js`
- Modify: `outputs/learning-os-app.css`
- Test: `work/presentations/learning-os-ui/tmp/test_learning_os_app.py`

- [ ] Write failing Playwright checks for the plan quick-entry and error-question photo controls.
- [ ] Implement selected-file preview, AI draft display, editable fields, and explicit confirm-save commands.
- [ ] Run desktop and mobile browser checks.
