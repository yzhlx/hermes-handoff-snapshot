# Learning OS MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Learning OS MVP with today planning, error-question management and review, AI analysis/chat, status records, and isolated AI configuration.

**Architecture:** Keep the loopback Python service and SQLite database, adding a focused domain store for planner, error-question, review, state, chat, and provider settings. Replace the prototype root with a responsive single-page application whose page modules call a versioned local API; preserve the existing handwriting prototype as a separate legacy artifact.

**Tech Stack:** Python 3.12 standard library, SQLite, Windows Credential Manager via `ctypes`, vanilla HTML/CSS/JavaScript, Playwright and `unittest`.

---

## File Structure

- Create: `outputs/learning-os-core.py` — SQLite schema, domain validation, scheduling, dashboard projections, import/export.
- Create: `outputs/learning-os-credentials.py` — Windows Credential Manager adapter and safe metadata API.
- Create: `outputs/learning-os-ai.py` — protocol adapters, provider settings, JSON contracts for error analysis and chat.
- Modify: `outputs/learning-os-api.py` — mount Learning OS v2 routes while retaining `/api/v1/handwriting/*` and evidence routes.
- Modify: `outputs/learning-os-static.py` — serve the v2 app at `/` with no cache.
- Create: `outputs/learning-os-app.html`, `outputs/learning-os-app.css`, `outputs/learning-os-app.js` — responsive product UI.
- Create: `work/presentations/learning-os-ui/tmp/test_learning_os_core.py` — domain and scheduling tests.
- Create: `work/presentations/learning-os-ui/tmp/test_learning_os_app.py` — Playwright MVP workflow tests.
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py` — v2 HTTP contracts and AI adapter tests.
- Create: `README.md` — startup, configuration, privacy, backup/export, and deployment instructions.

### Task 1: Local Domain Store

**Files:**
- Create: `outputs/learning-os-core.py`
- Test: `work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 1: Write failing tests for task CRUD and today selection**

```python
def test_today_projection_prefers_active_then_high_priority_due_task(self):
    store = LearningOSCore(Path(self.temporary.name))
    store.create_task({"title": "低", "study_date": "2026-07-21", "priority": "low"})
    high = store.create_task({"title": "高", "study_date": "2026-07-21", "priority": "high"})
    dashboard = store.today("2026-07-21", "09:00")
    self.assertEqual(dashboard["current_task"]["id"], high["id"])
```

- [ ] **Step 2: Run the focused test and verify it fails because `LearningOSCore` does not exist**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 3: Implement SQLite migrations and the task/today API**

```python
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, subject_id TEXT,
  study_date TEXT NOT NULL, start_time TEXT, estimated_minutes INTEGER,
  due_at TEXT, priority TEXT NOT NULL, status TEXT NOT NULL,
  needs_review INTEGER NOT NULL DEFAULT 0, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
```

Implement `create_task`, `update_task`, `transition_task`, `list_tasks`, and `today`. Accept only `high`, `medium`, `low`; preserve skipped and postponed tasks rather than deleting them.

- [ ] **Step 4: Run focused tests and verify they pass**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

### Task 2: Error Questions and Review Scheduling

**Files:**
- Modify: `outputs/learning-os-core.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 1: Write failing tests for error question fields, five-question selection, and review outcomes**

```python
def test_daily_review_selects_five_due_high_priority_unmastered_items(self):
    for priority in ("high", "high", "medium", "low", "low", "low"):
        store.create_error_question({"subject": "高等数学", "title": priority, "priority": priority})
    items = store.daily_review("2026-07-21")
    self.assertEqual(len(items), 5)
    self.assertEqual(items[0]["priority"], "high")
```

- [ ] **Step 2: Run the test and verify it fails for missing review methods**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 3: Implement error-question, attachment metadata, analysis, and review tables**

```python
CREATE TABLE IF NOT EXISTS error_questions (
  id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, chapter TEXT, title TEXT,
  problem_text TEXT, work_text TEXT, reasoning_text TEXT, correct_answer TEXT,
  explanation TEXT, notes TEXT, tags_json TEXT NOT NULL, difficulty TEXT,
  priority TEXT NOT NULL, mastery TEXT NOT NULL, next_review_date TEXT,
  review_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
```

Implement attachment metadata without embedding files in SQLite, multi-select error types, `record_review`, and interval rules: mastered `+14d`, partial `+4d`, cannot `+1d`, careless `+3d`, skip `+1d`. Select at most five items ordered by overdue days, priority, mastery, and last failed time.

- [ ] **Step 4: Run focused tests and verify they pass**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

### Task 3: Status, Conversations, Data Controls, and Credential Boundary

**Files:**
- Modify: `outputs/learning-os-core.py`
- Create: `outputs/learning-os-credentials.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 1: Write failing tests for non-medical status advice, linked chat messages, and export redaction**

```python
def test_high_pressure_low_energy_advice_is_non_medical(self):
    record = store.record_status({"mood": 2, "energy": 1, "stress": 5, "fatigued": True})
    self.assertEqual(record["advice"]["level"], "long_rest")
    self.assertNotIn("诊断", record["advice"]["message"])
```

- [ ] **Step 2: Run the tests and verify missing methods fail**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

- [ ] **Step 3: Implement status records, conversations/messages, and JSON export/delete operations**

Implement deterministic non-medical advice rules, optional `link_type`/`link_id` for messages, searchable text query, whole-library export that excludes credentials, and soft/object deletion endpoints. Implement Credential Manager wrapper with `CredWriteW`, `CredReadW`, `CredDeleteW`; expose only `is_configured` and a four-character suffix to callers.

- [ ] **Step 4: Run focused tests and verify they pass**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_core.py`

### Task 4: AI Gateway and Error Analysis Contract

**Files:**
- Create: `outputs/learning-os-ai.py`
- Modify: `outputs/learning-os-api.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Write failing tests for provider protocol selection and information-insufficient analysis**

```python
def test_validate_error_analysis_requires_at_most_three_questions_when_insufficient(self):
    result = validate_error_analysis({"information_sufficient": False, "questions": ["a", "b", "c"]})
    self.assertFalse(result["information_sufficient"])
```

- [ ] **Step 2: Run the test and verify the AI module is unavailable**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 3: Implement `responses` and `chat_completions` adapters**

Create provider configuration metadata in SQLite, resolve the secret through `learning-os-credentials.py`, build only current/linked context, validate error-analysis keys and type values, and return safe timeout/upstream messages. Add `/api/v2/settings/ai`, `/api/v2/settings/ai/test`, `/api/v2/error-questions/{id}/analyze`, and `/api/v2/chats/{id}/messages` routes.

- [ ] **Step 4: Run API tests and verify they pass**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

### Task 5: v2 HTTP Resources

**Files:**
- Modify: `outputs/learning-os-api.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Write failing HTTP tests for dashboard, tasks, error questions, reviews, status, chats, and export**

```python
def test_dashboard_returns_empty_local_first_state(self):
    with urllib.request.urlopen(self.base_url + "/api/v2/dashboard?date=2026-07-21") as response:
        body = json.loads(response.read())
    self.assertIsNone(body["current_task"])
    self.assertEqual(body["review"]["target_count"], 5)
```

- [ ] **Step 2: Run HTTP tests and verify routes return 404 before implementation**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 3: Mount v2 routes against a shared `LearningOSCore` instance**

Support GET/POST/PATCH for tasks and error questions; POST review/status/chat actions; GET dashboard, daily review, statistics, export; DELETE object and library routes. Validate origin, request size, JSON types, and attachment filenames. Keep existing v1 handwriting/evidence contract unchanged.

- [ ] **Step 4: Run API suite and verify v1 and v2 contracts pass**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

### Task 6: Responsive Product UI

**Files:**
- Create: `outputs/learning-os-app.html`
- Create: `outputs/learning-os-app.css`
- Create: `outputs/learning-os-app.js`
- Modify: `outputs/learning-os-static.py`
- Create: `work/presentations/learning-os-ui/tmp/test_learning_os_app.py`

- [ ] **Step 1: Write Playwright tests for the empty local-first dashboard and each primary navigation route**

```python
def test_mobile_navigation_exposes_today_plan_errors_review_chat_and_settings(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(URL)
    expect(page.get_by_role("navigation")).to_contain_text("今日")
    page.get_by_role("button", name="错题专栏").click()
    expect(page.get_by_role("heading", name="错题专栏")).to_be_visible()
```

- [ ] **Step 2: Run the browser test and verify v2 root does not yet exist**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_app.py`

- [ ] **Step 3: Implement the fixed-navigation app and shared API client**

Implement only confirmed Chinese pages: concise Today execution dashboard, weekly tasks, error question list/editor/detail/analysis, daily review runner, chat sidebar/history, status dialog, records statistics, and settings. Use real empty states rather than sample learning records. Add desktop sidebar, tablet collapse, mobile bottom navigation, form labels, accessible buttons, loading/error states, and narrow layouts without overlap.

- [ ] **Step 4: Serve v2 app at `/` and preserve legacy prototype at its direct filename**

Change static routing only after `learning-os-app.html` exists; use no-cache headers for HTML/JS/CSS. Keep `/learning-os-ui-prototype.html` working for the prior handwriting workflow.

- [ ] **Step 5: Run browser and static tests at desktop, tablet, and mobile sizes**

Run: `python work/presentations/learning-os-ui/tmp/test_learning_os_app.py`

### Task 7: Documentation, Example Data, and Full Verification

**Files:**
- Create: `README.md`
- Create: `examples/learning-os-example.json`
- Modify: `work/presentations/learning-os-ui/tmp/test_static_server.py`

- [ ] **Step 1: Write a failing static-server test asserting the root exposes the product UI**

```python
def test_root_serves_v2_product_app(self):
    with urllib.request.urlopen(f"{self.base_url}/") as response:
        body = response.read().decode("utf-8")
    self.assertIn("错题专栏", body)
    self.assertIn("learning-os-app.js", body)
```

- [ ] **Step 2: Run the static test and verify it fails before routing change**

Run: `python work/presentations/learning-os-ui/tmp/test_static_server.py`

- [ ] **Step 3: Add operator documentation and anonymous example data**

Document local startup, the two ports, SQLite/asset locations, Windows Credential Manager configuration, provider protocol fields, backup/export/delete actions, deployment limits for a loopback-only app, and responsive test commands. Example data must use generic subjects/tasks and contain no personal learning record.

- [ ] **Step 4: Run the complete verification suite**

Run:

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py work\presentations\learning-os-ui\tmp\test_learning_os_core.py
& $py work\presentations\learning-os-ui\tmp\test_learning_os_api.py
& $py work\presentations\learning-os-ui\tmp\test_static_server.py
& $py work\presentations\learning-os-ui\tmp\test_handwriting.py
& $py work\presentations\learning-os-ui\tmp\test_world_canvas.py
& $py work\presentations\learning-os-ui\tmp\test_learning_os_app.py
```

Expected: all tests pass; explicitly skipped live-provider tests remain skipped unless configured.

## Plan Review

The tasks cover confirmed pages, local-first storage, error analysis, review scheduling, plans, state, chat, isolated AI configuration, export/delete, responsive UI, and documentation. API v1 handwriting/evidence remains covered by the existing test suite. No credential is written to the repository or included in examples.
