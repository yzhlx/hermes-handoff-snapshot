# Learning OS V3 Hybrid Canvas And Local Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bounded handwriting page with a predictable self-growing world canvas and complete the local website workflow from immutable Evidence persistence through AI Assessment and Learning State projection.

**Architecture:** Extract deterministic canvas rules into a browser/Node-compatible JavaScript module and keep rendering and pointer orchestration in the existing HTML. Extend the loopback Python service with a focused append-only SQLite/artifact module, explicit Evidence APIs, and one background assessment worker. The browser polls persisted submission state and renders assessment feedback in-place beside the immutable answer.

**Tech Stack:** Standalone HTML/CSS/JavaScript, Pointer Events, Node built-in test runner, Python 3 standard library, SQLite, Responses API, Python Playwright.

**Repository note:** This workspace is not a Git repository. Do not initialize Git and do not add fake commit steps. Use file-scope auditing and fresh test output as the completion evidence.

---

## File Map

- Create `outputs/learning-os-canvas-model.js`: schema v2 world coordinates, migration, growth, content bounds, fit view, and recognition chunk planning.
- Create `outputs/learning-os-store.py`: append-only SQLite events, immutable artifact writes, Evidence queries, and deterministic projection.
- Modify `outputs/learning-os-ui-prototype.html`: full-height hybrid canvas, schema v2 rendering, overflow menu, submission states, polling, and assessment drawer.
- Modify `outputs/learning-os-api.py`: multi-chunk recognition, Evidence routes, assessment jobs, artifact delivery, and strict local security.
- Create `work/presentations/learning-os-ui/tmp/test_canvas_model.cjs`: deterministic canvas model tests.
- Create `work/presentations/learning-os-ui/tmp/test_learning_os_store.py`: SQLite, artifact, idempotency, and projection tests.
- Modify `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`: Evidence HTTP routes, chunk recognition, assessment success/failure/retry tests.
- Modify `work/presentations/learning-os-ui/tmp/test_handwriting.py`: world-coordinate drawing, growth, fit view, exports, stale recognition, submit, polling, and result drawer tests.
- Modify `work/presentations/learning-os-ui/tmp/test_handwriting_responsive.py`: full-screen canvas and responsive drawer assertions.
- Create runtime-only `data/` on first API start. Tests must use temporary directories and must not write fixtures into this directory.

## Checkpoint A: Hybrid Self-Growing Canvas

### Task 1: Define The Schema V2 Canvas Model

**Files:**
- Create: `outputs/learning-os-canvas-model.js`
- Create: `work/presentations/learning-os-ui/tmp/test_canvas_model.cjs`

- [ ] **Step 1: Write failing Node tests for creation, migration, content bounds, growth, fit view, and chunks**

Create `test_canvas_model.cjs` with these exact behavior cases:

```javascript
const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../../../../outputs/learning-os-canvas-model.js');

const stroke = points => ({
  id: 'stroke-1', tool: 'draw', color: '#172127', baseWidth: 4, points,
});

test('creates a world-coordinate page', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'page-1' });
  assert.deepEqual(page.bounds, { minX: 0, minY: 0, maxX: 1000, maxY: 1200 });
  assert.deepEqual(page.strokes, []);
});

test('migrates schema v1 without changing stroke metadata', () => {
  const draft = { schemaVersion: 1, pages: [{ id: 'p', strokes: [{
    id: 's', tool: 'draw', color: '#000', baseWidth: 3,
    points: [{ x: .25, y: .5, pressure: .7, t: 12 }],
  }] }] };
  const migrated = model.migrateDraft(draft, { width: 1200, height: 1800 });
  assert.equal(migrated.schemaVersion, 2);
  assert.deepEqual(migrated.pages[0].strokes[0].points[0], {
    x: 300, y: 900, pressure: .7, t: 12,
  });
});

test('grows only the approached edges after a committed stroke', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  const next = model.growForStroke(page, stroke([
    { x: 40, y: 1100, pressure: .5, t: 1 },
    { x: 15, y: 1180, pressure: .5, t: 2 },
  ]));
  assert.deepEqual(next.bounds, { minX: -400, minY: 0, maxX: 1000, maxY: 1800 });
  assert.deepEqual(page.bounds, { minX: 0, minY: 0, maxX: 1000, maxY: 1200 });
});

test('fits all content with padding without mutating the page', () => {
  const page = model.createPage({ width: 1000, height: 800, id: 'p' });
  page.strokes = [stroke([{ x: 100, y: 200 }, { x: 900, y: 1000 }])];
  const view = model.fitContentView(page, { width: 800, height: 600 }, 80);
  assert.ok(view.zoom >= .5 && view.zoom <= 3);
  assert.ok(Number.isFinite(view.panX));
  assert.ok(Number.isFinite(view.panY));
});

test('plans ordered overlapping recognition chunks', () => {
  const chunks = model.planRecognitionChunks(
    { minX: 0, minY: 0, maxX: 1200, maxY: 3600 },
    { maxWidth: 1600, maxHeight: 1600, overlap: 120, maxChunks: 12 },
  );
  assert.equal(chunks.length, 3);
  assert.equal(chunks[0].index, 0);
  assert.equal(chunks[1].minY, chunks[0].maxY - 120);
  assert.equal(chunks[2].index, 2);
});
```

- [ ] **Step 2: Run the Node tests and verify RED**

Run:

```powershell
& 'F:\software\Nodejs\node.exe' --test 'work\presentations\learning-os-ui\tmp\test_canvas_model.cjs'
```

Expected: FAIL because `outputs/learning-os-canvas-model.js` does not exist.

- [ ] **Step 3: Implement the pure model contracts**

Create a UMD module so Node can `require()` it and the page receives `window.LearningOSCanvasModel`. Export exactly:

```javascript
{
  SCHEMA_VERSION: 2,
  createPage,
  migrateDraft,
  strokeBounds,
  contentBounds,
  growForStroke,
  fitContentView,
  planRecognitionChunks,
  snapshotPage,
  restorePageSnapshot,
}
```

Use these constants and rules:

```javascript
const INITIAL_HEIGHT_FACTOR = 1.5;
const BOTTOM_THRESHOLD = 160;
const SIDE_THRESHOLD = 120;
const VERTICAL_GROWTH = 600;
const HORIZONTAL_GROWTH = 400;
const MIN_ZOOM = .5;
const MAX_ZOOM = 3;
```

`growForStroke` must clone `bounds`, inspect only the committed stroke's bounds, grow each approached edge once, and return a new page object. `snapshotPage` must include both cloned strokes and cloned bounds. `restorePageSnapshot` must restore both without sharing arrays with history entries.

`contentBounds(page, padding = 0)` must return the union of all draw-stroke points expanded by half the stroke width and padding. For an empty page it must return a clone of `page.bounds`.

`planRecognitionChunks` must first scale an over-wide content area to `maxWidth`, then create vertical world-coordinate chunks whose rendered output does not exceed `maxHeight`. It must throw `RangeError('Recognition requires more than 12 chunks')` instead of truncating content.

- [ ] **Step 4: Run Node tests and verify GREEN**

Expected: all five model tests PASS.

### Task 2: Integrate World Coordinates And Bounds History

**Files:**
- Modify: `outputs/learning-os-ui-prototype.html:145-168,354-397,490-1152`
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`

- [ ] **Step 1: Add failing Playwright assertions for schema v2 and growth timing**

Add a helper that draws near the initial bottom and assert:

```python
initial = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert initial["schemaVersion"] == 2
initial_bounds = initial["pages"][0]["bounds"]

dispatch_pointer(page, "pointerdown", pointer_type="pen", x=200, y=canvas_height - 30, pointer_id=70)
during = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert during["pages"][0]["bounds"] == initial_bounds
dispatch_pointer(page, "pointerup", pointer_type="pen", x=240, y=canvas_height - 10, pointer_id=70)
after = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert after["pages"][0]["bounds"]["maxY"] == initial_bounds["maxY"] + 600

page.locator("#undoStroke").click()
undone = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert undone["pages"][0]["bounds"] == initial_bounds
page.locator("#redoStroke").click()
redone = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert redone["pages"][0]["bounds"] == after["pages"][0]["bounds"]
```

Also seed a schema v1 draft before navigation and assert the loaded point is migrated to world pixels and localStorage is rewritten with `schemaVersion: 2`.

- [ ] **Step 2: Run Playwright and verify RED**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'work\presentations\learning-os-ui\tmp\test_handwriting.py'
```

Expected: FAIL because pages have no `bounds`, debug schema is absent, and stored points are normalized.

- [ ] **Step 3: Load the model module and migrate page state**

Add before the existing inline application script:

```html
<script src="learning-os-canvas-model.js"></script>
```

Bind:

```javascript
const CanvasModel = window.LearningOSCanvasModel;
const makePage = () => CanvasModel.createPage({
  width: Math.max(900, canvas?.getBoundingClientRect().width || 900),
  height: Math.max(700, canvas?.getBoundingClientRect().height || 700),
});
```

Replace normalized point conversion with world conversion:

```javascript
function pointFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  const view = handwritingState.view;
  return {
    x: (event.clientX - rect.left - view.panX) / view.zoom,
    y: (event.clientY - rect.top - view.panY) / view.zoom,
    pressure: Number((event.pressure > 0 ? event.pressure : .5).toFixed(3)),
    t: Math.round(performance.now()),
  };
}
```

Change history entries to `{ before: snapshotPage(page), after: snapshotPage(page) }`. After committing a draw stroke, call `growForStroke` before recording the `after` snapshot. Undo, redo, and clear must restore both `strokes` and `bounds`.

- [ ] **Step 4: Render world coordinates and repeating paper**

Render the viewport in this order:

```javascript
context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
context.fillStyle = '#e8ece9';
context.fillRect(0, 0, rect.width, rect.height);
context.save();
context.translate(view.panX, view.panY);
context.scale(view.zoom, view.zoom);
drawWorldPaper(context, page.bounds);
page.strokes.forEach(stroke => drawWorldStroke(context, stroke));
context.restore();
```

`drawWorldPaper` must fill the current bounds and draw horizontal rules every 42 world pixels and a red margin at `bounds.minX + 58`. `drawWorldStroke` must use point coordinates directly without multiplying by viewport dimensions.

- [ ] **Step 5: Run model and Playwright tests and verify GREEN**

Expected: model tests PASS and all existing drawing, eraser, palm, draft, export, and Evidence tests remain green after assertion updates for schema v2.

### Task 3: Fit Content, Stable Exports, And Recognition Chunks

**Files:**
- Modify: `outputs/learning-os-ui-prototype.html:145-168,354-397,1136-1261`
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting_responsive.py`

- [ ] **Step 1: Add failing tests for fit-content and viewport-independent full export**

Add `#fitContent` and assert it places every content-bound corner inside the canvas viewport. Render full-content PNG at 1024px and 760px browser widths and assert the data URLs are byte-identical. Assert `renderCurrentViewDataUrl()` changes after pan while `renderFullContentDataUrl()` does not.

Add chunk assertions through the debug API:

```python
chunks = page.evaluate("window.__learningOSHandwriting.planCurrentRecognitionChunks()")
assert chunks
assert [chunk["index"] for chunk in chunks] == list(range(len(chunks)))
assert all(chunk["png_data_url"].startswith("data:image/png;base64,") for chunk in chunks)
```

- [ ] **Step 2: Run Playwright and verify RED**

Expected: FAIL because fit-content, world crop export, current-view export, and chunk rendering do not exist.

- [ ] **Step 3: Implement fit and the secondary overflow menu**

Add stable controls:

```html
<button class="icon-button" id="fitContent" type="button" title="适应内容" aria-label="适应内容">⌖</button>
<button class="icon-button" id="moreCanvasActions" type="button" title="更多" aria-label="更多">⋯</button>
<div class="canvas-menu" id="canvasMenu" hidden>
  <button id="clearPage" type="button">清空本页</button>
  <button id="exportFullPng" type="button">导出全部 PNG</button>
  <button id="exportViewPng" type="button">导出当前视图</button>
  <button id="exportJson" type="button">导出笔迹 JSON</button>
</div>
```

Move existing clear/export commands into this menu. Keep page navigation in the top bar. The floating bottom toolbar must remain one row at 768px and may use icons with tooltips at 375px.

- [ ] **Step 4: Implement deterministic render targets**

Use three functions with distinct contracts:

```javascript
function renderWorldRegion(page, region, outputWidth, outputHeight) {
  const exportCanvas = document.createElement('canvas');
  exportCanvas.width = Math.max(1, Math.ceil(outputWidth));
  exportCanvas.height = Math.max(1, Math.ceil(outputHeight));
  const context = exportCanvas.getContext('2d');
  const scaleX = exportCanvas.width / (region.maxX - region.minX);
  const scaleY = exportCanvas.height / (region.maxY - region.minY);
  context.scale(scaleX, scaleY);
  context.translate(-region.minX, -region.minY);
  drawWorldPaper(context, page.bounds);
  page.strokes.forEach(stroke => drawWorldStroke(context, stroke));
  return exportCanvas;
}

function renderFullContentDataUrl(page, padding = 80) {
  const region = CanvasModel.contentBounds(page, padding);
  const worldWidth = Math.max(1, region.maxX - region.minX);
  const worldHeight = Math.max(1, region.maxY - region.minY);
  const outputWidth = Math.min(1600, Math.ceil(worldWidth));
  const outputHeight = Math.ceil(worldHeight * outputWidth / worldWidth);
  return renderWorldRegion(page, region, outputWidth, outputHeight)
    .toDataURL('image/png');
}

function renderCurrentViewDataUrl(page) {
  const rect = canvas.getBoundingClientRect();
  const view = handwritingState.view;
  const region = {
    minX: -view.panX / view.zoom,
    minY: -view.panY / view.zoom,
    maxX: (rect.width - view.panX) / view.zoom,
    maxY: (rect.height - view.panY) / view.zoom,
  };
  return renderWorldRegion(page, region, rect.width, rect.height)
    .toDataURL('image/png');
}
```

`renderWorldRegion` maps a world rectangle to a fresh offscreen canvas. `renderFullContentDataUrl` derives its region only from `CanvasModel.contentBounds(page, padding)`. `renderCurrentViewDataUrl` derives its region by inverse-transforming the viewport corners. Neither function reads display DPR.

`planCurrentRecognitionChunks` must call `CanvasModel.planRecognitionChunks`, render every region, and return ordered objects with `page_id`, `index`, `minY`, `maxY`, and `png_data_url`.

- [ ] **Step 5: Run canvas, Playwright, and responsive tests and verify GREEN**

Expected: all Checkpoint A tests PASS with no page errors or horizontal overflow.

## Checkpoint B: Website Evidence And Assessment Loop

### Task 4: Build The Append-Only Store And Immutable Artifact Repository

**Files:**
- Create: `outputs/learning-os-store.py`
- Create: `work/presentations/learning-os-ui/tmp/test_learning_os_store.py`

- [ ] **Step 1: Write failing store tests**

Test these public contracts:

```python
EventStore(db_path, artifact_root)
EventStore.append(event_type, aggregate_type, aggregate_id, payload, event_id=None)
EventStore.replay(aggregate_type, aggregate_id)
EventStore.get_event(event_id)
EventStore.find_evidence_by_submission_id(submission_id)
ArtifactRepository.write_evidence(evidence_id, handwriting, pages, transcript)
ArtifactRepository.verify_manifest(manifest)
project_events(events)
```

Required cases:

- append and ordered replay survive close/reopen;
- direct SQL update and delete are rejected by triggers;
- artifact bytes and JSON are atomically written and SHA-256 verified;
- reusing `submission_id` returns the original Evidence event;
- `AssessmentRecorded` projects feedback and current `f_state`;
- `AssessmentFailed` preserves Evidence and reports retryability;
- mixed aggregate identity raises `AggregateIdentityError`.

- [ ] **Step 2: Run store tests and verify RED**

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_store.py' -v
```

Expected: FAIL because `learning-os-store.py` does not exist.

- [ ] **Step 3: Implement immutable events and artifacts**

Use SQLite tables:

```sql
CREATE TABLE events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX events_aggregate_sequence
ON events(aggregate_type, aggregate_id, sequence);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
```

Write artifacts to a sibling temporary directory, fsync each file, write `manifest.json` last, then atomically rename the directory to `<artifact_root>/<evidence_id>`. The manifest must contain relative paths, byte lengths, and SHA-256 hashes. Reject path traversal and existing target directories.

Projection returns JSON-ready state containing aggregate identity, Evidence IDs, latest assessment, assessment history, `f_state`, and latest assessment status.

- [ ] **Step 4: Run store tests and verify GREEN**

Expected: all store tests PASS.

### Task 5: Add Evidence HTTP APIs And Idempotent Submission

**Files:**
- Modify: `outputs/learning-os-api.py:1-230`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Add failing HTTP tests**

Start the handler on an ephemeral port with a temporary `EventStore`. POST a valid body containing `submission_id`, aggregate identity, question, confirmed transcript, schema v2 handwriting, and PNG chunks. Assert:

```python
self.assertEqual(response.status, 201)
self.assertRegex(result["event_id"], r"^[0-9a-f-]{36}$")
self.assertEqual(result["status"], "pending_assessment")
self.assertEqual(result["artifact_integrity"], "verified")
```

Repeat the same POST and assert status 200 with the same `event_id`. Add GET list/detail, timeline, and projection cases. Assert unknown IDs return 404, unconfirmed non-empty transcripts return 400, missing chunks return 400, and artifact failures append no event.

- [ ] **Step 2: Run API tests and verify RED**

Expected: FAIL because the routes return 404.

- [ ] **Step 3: Add dependency-injected service state and routes**

Create `LearningOSService` with `store`, `artifact_repository`, `relay`, and `executor`. Attach one service instance to `ThreadingHTTPServer`. Route handlers must call service methods rather than module globals.

Implement:

```text
POST /api/v1/evidence
GET  /api/v1/evidence
GET  /api/v1/evidence/<id>
GET  /api/v1/timeline
GET  /api/v1/projection
```

On submission:

1. validate the body and confirmed transcript rule;
2. return the existing event if `submission_id` already exists;
3. write and verify immutable artifacts;
4. append `EvidenceExtracted`;
5. append `AssessmentRequested`;
6. enqueue the assessment job;
7. return persisted IDs.

Do not return data URLs from list/detail routes. Return artifact metadata and a loopback artifact endpoint only when the UI needs a rendered image.

- [ ] **Step 4: Run store and API tests and verify GREEN**

Expected: store tests and all HTTP tests PASS.

### Task 6: Implement Structured Background Assessment And Retry

**Files:**
- Modify: `outputs/learning-os-api.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Add failing assessment job tests**

Inject a fake relay that returns valid assessment JSON and assert `AssessmentRecorded` is appended with the Evidence ID and `f_state`. Inject malformed JSON and a raised upstream error and assert `AssessmentFailed` is appended with only a sanitized category. Retry must append a second `AssessmentRequested` with a new job ID and must not alter prior events.

- [ ] **Step 2: Run API tests and verify RED**

Expected: FAIL because assessment jobs and retry are absent.

- [ ] **Step 3: Add the exact assessment contract**

The assessment prompt must demand JSON with exactly:

```json
{
  "summary": "string",
  "correct_points": ["string"],
  "missing_points": ["string"],
  "incorrect_points": ["string"],
  "formula_feedback": ["string"],
  "f_state": "F0|F1|F2|F3|F4|F5",
  "recommended_action": "string",
  "uncertain": ["string"]
}
```

Validate every field and reject additional top-level keys. The worker must load and verify the immutable artifact manifest before calling the relay. Append `AssessmentRecorded` only after validation. Map timeout, malformed output, missing artifacts, hash mismatch, and upstream errors to stable sanitized categories.

Add:

```text
POST /api/v1/evidence/<id>/assessment/retry
```

Only Evidence whose latest assessment status is failed or pending after restart may be retried. One running in-memory job per Evidence ID is allowed.

- [ ] **Step 4: Run API and store tests and verify GREEN**

Expected: valid assessment, failure, retry, and restart projection tests PASS.

### Task 7: Replace Demo Submission With The Website-Centered Loop

**Files:**
- Modify: `outputs/learning-os-ui-prototype.html:403-451,1164-1349`
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`

- [ ] **Step 1: Add a failing mocked end-to-end browser test**

Mock Evidence POST to return `event_id`, `evidence_id`, and pending status. Mock two detail polls: first pending, then recorded with structured feedback. Assert:

- submit shows saving and disables duplicate submission;
- the canvas draft remains until the 201 response;
- status changes to evaluating without closing the workspace;
- the assessment drawer opens in place;
- original handwriting remains visible;
- feedback lists use `textContent`;
- `F2 -> F3`, event ID, and assessment ID render;
- answer-again clears only after confirmation;
- retry appears for a failed assessment response.

- [ ] **Step 2: Run Playwright and verify RED**

Expected: FAIL because submission still writes `learning-os-last-evidence-demo` and closes the modal.

- [ ] **Step 3: Implement save, poll, and drawer states**

Use one explicit state machine:

```javascript
const SubmissionState = Object.freeze({
  DRAFT: 'draft',
  SAVING: 'saving',
  ASSESSING: 'assessing',
  RECORDED: 'recorded',
  FAILED: 'failed',
});
```

Create a client-generated UUID once per submission attempt and reuse it on retry after network failure. POST immutable page chunks and schema v2 handwriting. Poll detail every two seconds, stop on terminal state or after five minutes, and resume polling from persisted `activeEvidenceId` after reload.

The assessment drawer must be a right-side sibling of the canvas on desktop and a bottom sheet below 920px. It must not be a card nested inside the canvas. Keep the canvas mounted and visible while the drawer is open.

- [ ] **Step 4: Replace primary export actions**

Remove visible export buttons from the answer footer. Keep them only in the canvas overflow menu. Replace the old footer with persisted draft/submission status and immutable Evidence ID when available.

- [ ] **Step 5: Run Playwright and verify GREEN**

Expected: mocked full workflow, old recognition behavior, palm rejection, growth, and exports PASS with no page errors.

### Task 8: Full Integration, Live Relay, And Visual Verification

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting_responsive.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`
- Update: `docs/superpowers/specs/2026-07-21-learning-os-v3-hybrid-canvas-local-loop-design.md` status only after verification

- [ ] **Step 1: Add final responsive assertions**

At 1440x900, 768x1024, and 375x667 assert:

- the writing canvas uses at least 60% of the visible workspace before the drawer opens;
- the floating toolbar is fully inside the viewport;
- opening the drawer leaves at least 300px visible canvas width on desktop;
- tablet/phone drawer is below or overlays from the bottom without horizontal overflow;
- feedback text and actions do not overlap;
- no page or canvas is blank after drawing.

- [ ] **Step 2: Start the updated services**

Keep static UI on 4173. Restart only the verified Learning OS proxy process on 4174 so it loads the new service/store code. Confirm:

```powershell
Invoke-RestMethod 'http://127.0.0.1:4174/health'
```

Expected health includes `status`, `model`, `store`, and `artifact_root`, without credentials.

- [ ] **Step 3: Run all deterministic tests**

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& 'F:\software\Nodejs\node.exe' --test 'work\presentations\learning-os-ui\tmp\test_canvas_model.cjs'
& $py -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_store.py' -v
& $py -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_api.py' -v
& $py 'work\presentations\learning-os-ui\tmp\test_handwriting.py'
& $py 'work\presentations\learning-os-ui\tmp\test_handwriting_responsive.py'
& $py -m compileall -q outputs work\presentations\learning-os-ui\tmp
```

Expected: every deterministic test passes; the live relay test remains skipped unless explicitly enabled.

- [ ] **Step 4: Run one real transcription and one real assessment**

Set `LEARNING_OS_LIVE_TEST=1` and run only opt-in live tests. Assert transport success, required JSON keys, persisted Evidence, appended Assessment event, and projected `f_state`. Do not assert exact transcription wording and do not print model output or credentials.

- [ ] **Step 5: Run the Huashu visual verifier**

```powershell
$env:PYTHONIOENCODING='utf-8'
& $py 'C:\Users\user\.codex\skills\huashu-design\scripts\verify.py' `
  'outputs\learning-os-ui-prototype.html' `
  --viewports '1440x900,768x1024,375x667' `
  --output 'work\presentations\learning-os-ui\tmp\verify-v3-final'
```

Expected: screenshots at all viewports, no JavaScript errors, and a clean console.

- [ ] **Step 6: Inspect screenshots and run credential/file-scope audits**

Inspect recall, evaluating, recorded, and failed states at desktop/tablet/phone sizes. Verify no literal API key exists anywhere under `outputs`, `work`, or `docs`. Confirm no files outside this workspace and runtime `data/` were modified.

- [ ] **Step 7: Mark the design status implemented only after fresh evidence**

Change the design status from `Approved design, implementation not started` to `Implemented and verified locally` only after Steps 3-6 pass. Report real test counts, skipped live tests, live request latency, modified files, service URLs, and remaining out-of-scope integrations.
