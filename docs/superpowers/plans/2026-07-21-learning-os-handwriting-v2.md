# Learning OS Handwriting V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the handwriting prototype to the configured relay vision model, replace the broken white-overpaint eraser with real segment deletion, and add palm-safe canvas zoom and pan.

**Architecture:** Keep the existing static HTML on port 4173 and add a dependency-free Python proxy on port 4174. The browser owns drawing, erasing, view transforms, and confirmation; the proxy owns credentials, payload validation, and Responses API translation. Stored strokes remain normalized logical-page coordinates, independent of zoom and pan.

**Tech Stack:** Standalone HTML/CSS/JavaScript, Pointer Events, Python 3 standard library, Responses API, Python Playwright.

**Repository note:** This workspace is not a Git repository. Do not initialize Git and do not add fake commit steps.

---

## File Map

- Create `outputs/learning-os-api.py`: local credential-safe HTTP proxy and relay response parser.
- Create `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`: proxy unit tests and optional live smoke test.
- Modify `outputs/learning-os-ui-prototype.html`: eraser history, zoom/pan, palm rejection, proxy recognition UI.
- Modify `work/presentations/learning-os-ui/tmp/test_handwriting.py`: eraser, zoom, touch, and recognition interaction tests.
- Modify `work/presentations/learning-os-ui/tmp/test_handwriting_responsive.py`: toolbar and recognition-state layout checks.

### Task 1: Define And Test The Proxy Contract

**Files:**
- Create: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`
- Create: `outputs/learning-os-api.py`

- [ ] **Step 1: Write failing tests for request validation and model JSON extraction**

Create tests that load the hyphenated proxy module by path and exercise pure functions without using a real key:

```python
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "outputs" / "learning-os-api.py"


def load_module():
    spec = importlib.util.spec_from_file_location("learning_os_api", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProxyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def test_validate_recognition_request_accepts_png_and_strokes(self):
        payload = {
            "png_data_url": "data:image/png;base64,iVBORw0KGgo=",
            "stroke_json": {"schemaVersion": 1, "pages": []},
        }
        result = self.api.validate_recognition_request(payload)
        self.assertEqual(result["png_data_url"], payload["png_data_url"])

    def test_validate_recognition_request_rejects_non_png(self):
        with self.assertRaisesRegex(ValueError, "PNG"):
            self.api.validate_recognition_request({
                "png_data_url": "data:image/jpeg;base64,AA==",
                "stroke_json": {},
            })

    def test_extract_output_json_handles_code_fence(self):
        response = {
            "id": "resp_test",
            "output": [{
                "content": [{
                    "type": "output_text",
                    "text": "```json\n{\"sections\":[],\"critical_formulas\":[],\"diagram_notes\":[],\"uncertain\":[]}\n```",
                }],
            }],
        }
        parsed = self.api.extract_model_result(response)
        self.assertEqual(parsed["request_id"], "resp_test")
        self.assertEqual(parsed["sections"], [])

    def test_build_relay_payload_contains_image_not_strokes(self):
        result = self.api.build_relay_payload("data:image/png;base64,AA==")
        serialized = json.dumps(result)
        self.assertIn("input_image", serialized)
        self.assertNotIn("stroke_json", serialized)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the proxy tests and verify RED**

Run:

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_api.py' -v
```

Expected: FAIL because `outputs/learning-os-api.py` does not exist.

- [ ] **Step 3: Implement validation, payload construction, and response extraction**

Create `outputs/learning-os-api.py` with these public contracts:

```python
MAX_BODY_BYTES = 8 * 1024 * 1024
MODEL = os.environ.get("LEARNING_OS_VISION_MODEL", "gpt-5.6-luna")
RELAY_URL = os.environ.get(
    "LEARNING_OS_RELAY_URL",
    "https://www.cctq.ai/v1/responses",
)


def validate_recognition_request(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    png_data_url = payload.get("png_data_url")
    if not isinstance(png_data_url, str) or not png_data_url.startswith(
        "data:image/png;base64,"
    ):
        raise ValueError("A PNG data URL is required")
    encoded = png_data_url.split(",", 1)[1]
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("PNG Base64 is invalid") from exc
    if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Decoded payload is not a PNG")
    if len(decoded) > 5 * 1024 * 1024:
        raise ValueError("PNG exceeds the 5MB limit")
    if not isinstance(payload.get("stroke_json"), dict):
        raise ValueError("stroke_json must be an object")
    return {"png_data_url": png_data_url, "stroke_json": payload["stroke_json"]}


def build_relay_payload(png_data_url: str) -> dict:
    return {
        "model": MODEL,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": TRANSCRIPTION_PROMPT},
                {"type": "input_image", "image_url": png_data_url, "detail": "high"},
            ],
        }],
        "max_output_tokens": 5000,
    }


def extract_model_result(response: dict) -> dict:
    chunks = [
        content["text"]
        for item in response.get("output", [])
        for content in item.get("content", [])
        if content.get("type") == "output_text" and content.get("text")
    ]
    text = "\n".join(chunks).strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    result = json.loads(text.strip())
    result["request_id"] = response.get("id")
    result["model"] = response.get("model", MODEL)
    result["confidence"] = None
    return result
```

Use this exact prompt so the proxy contract is deterministic:

```python
TRANSCRIPTION_PROMPT = """You are transcribing a handwritten study answer from one PNG image.
Return only one valid JSON object with exactly these top-level keys:
{
  "date": string or null,
  "sections": [{"title": string, "transcript": string}],
  "critical_formulas": [{"latex": string, "meaning": string}],
  "diagram_notes": [string],
  "uncertain": [string]
}

Preserve the writer's wording and mathematical notation. Transcribe subscripts,
superscripts, Greek letters, inequality strictness (< versus <=), integration
limits, regions of convergence, arrows, labels, and units exactly. Use LaTeX
for formulas. Do not solve the problem, correct the answer, infer missing text,
or guess unreadable marks. Put every ambiguity or unreadable span in uncertain.
Use empty arrays when a category is absent. Do not emit Markdown fences or any
text outside the JSON object."""
```

- [ ] **Step 4: Run the proxy tests and verify GREEN**

Run the command from Step 2.

Expected: four tests PASS.

### Task 2: Add The Local HTTP Proxy Without Exposing Credentials

**Files:**
- Modify: `outputs/learning-os-api.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Add failing tests for credential resolution and upstream errors**

Add tests with temporary files and injected mappings:

```python
def test_resolve_api_key_prefers_environment(self):
    key = self.api.resolve_api_key(
        environ={"LEARNING_OS_API_KEY": "env-key"},
        auth_path=Path("missing.json"),
    )
    self.assertEqual(key, "env-key")

def test_resolve_api_key_reads_codex_auth(self):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "auth.json"
        path.write_text('{"OPENAI_API_KEY":"stored-key"}', encoding="utf-8")
        key = self.api.resolve_api_key(environ={}, auth_path=path)
        self.assertEqual(key, "stored-key")

def test_normalize_upstream_error_hides_body(self):
    error = self.api.normalize_upstream_error(RuntimeError("secret upstream body"))
    self.assertEqual(error, "Vision service request failed")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because the three functions do not exist.

- [ ] **Step 3: Implement credential resolution, relay call, CORS, and routes**

Use `ThreadingHTTPServer` and `BaseHTTPRequestHandler`. Required behavior:

```python
ALLOWED_ORIGINS = {
    "http://127.0.0.1:4173",
    "http://localhost:4173",
}


def resolve_api_key(environ=os.environ, auth_path=Path.home() / ".codex" / "auth.json"):
    if environ.get("LEARNING_OS_API_KEY"):
        return environ["LEARNING_OS_API_KEY"]
    if auth_path.exists():
        data = json.loads(auth_path.read_text(encoding="utf-8"))
        if data.get("OPENAI_API_KEY"):
            return data["OPENAI_API_KEY"]
    raise RuntimeError("No server-side API credential is configured")


def call_relay(png_data_url: str) -> dict:
    request = urllib.request.Request(
        RELAY_URL,
        data=json.dumps(build_relay_payload(png_data_url)).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resolve_api_key()}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_upstream_error(_error: Exception) -> str:
    return "Vision service request failed"
```

The handler must provide `GET /health`, `OPTIONS`, and `POST /api/v1/handwriting/recognize`; reject other paths; enforce `Content-Length <= MAX_BODY_BYTES`; and return `{ "error": "..." }` without upstream bodies or credentials.

- [ ] **Step 4: Run all proxy tests and verify GREEN**

Expected: seven tests PASS.

### Task 3: Reproduce And Replace The White-Overpaint Eraser

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`
- Modify: `outputs/learning-os-ui-prototype.html:477-707`

- [ ] **Step 1: Add a failing Playwright eraser test**

Add an `erase_stroke` helper that dispatches pen pointer events after selecting `#eraserTool`. Draw one long stroke with at least nine points, erase across its middle, and assert:

```python
before = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
before_points = sum(len(s["points"]) for s in before["pages"][0]["strokes"])

page.locator("#eraserTool").click()
erase_stroke(page, [{"x": 145, "y": 110}, {"x": 155, "y": 110}])
erased = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
erased_points = sum(len(s["points"]) for s in erased["pages"][0]["strokes"])

assert erased_points < before_points
assert all(s["tool"] == "draw" for s in erased["pages"][0]["strokes"])

page.locator("#undoStroke").click()
restored = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert restored["pages"][0]["strokes"] == before["pages"][0]["strokes"]

page.locator("#redoStroke").click()
redone = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert redone["pages"][0]["strokes"] == erased["pages"][0]["strokes"]
```

- [ ] **Step 2: Run Playwright and verify RED**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'work\presentations\learning-os-ui\tmp\test_handwriting.py'
```

Expected: FAIL because the current eraser adds a white `tool=eraser` stroke instead of deleting points.

- [ ] **Step 3: Implement snapshot history and segment erasing**

Change each page to:

```javascript
{
  id: crypto.randomUUID(),
  strokes: [],
  undoStack: [],
  redoStack: []
}
```

Use these contracts:

```javascript
const cloneStrokes = strokes => JSON.parse(JSON.stringify(strokes));

function commitHistory(page, before, after) {
  if (JSON.stringify(before) === JSON.stringify(after)) return;
  page.undoStack.push({ before, after });
  page.redoStack = [];
}

function eraseAt(point, radiusPx = 18) {
  const rect = canvas.getBoundingClientRect();
  const radiusX = radiusPx / (rect.width * handwritingState.view.zoom);
  const radiusY = radiusPx / (rect.height * handwritingState.view.zoom);
  currentPage().strokes = currentPage().strokes.flatMap(stroke => {
    const fragments = [];
    let fragment = [];
    for (const candidate of stroke.points) {
      const distance = Math.hypot(
        (candidate.x - point.x) / radiusX,
        (candidate.y - point.y) / radiusY,
      );
      if (distance <= 1) {
        if (fragment.length >= 2) fragments.push(fragment);
        fragment = [];
      } else {
        fragment.push(candidate);
      }
    }
    if (fragment.length >= 2) fragments.push(fragment);
    return fragments.map(points => ({ ...stroke, id: crypto.randomUUID(), points }));
  });
}
```

At eraser pointerdown, capture `gesture.before`; call `eraseAt` during down/move; at pointerup commit one history entry. Drawing and clear-page also commit before/after snapshots. Undo assigns the last `before`; redo assigns its `after`.

- [ ] **Step 4: Run Playwright and verify GREEN**

Expected: eraser, undo, redo, existing draw, export, persistence, and Evidence tests PASS.

### Task 4: Add Zoom, Pan, And Palm Rejection

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`
- Modify: `outputs/learning-os-ui-prototype.html:145-244,354-373,477-681`

- [ ] **Step 1: Add failing zoom and touch tests**

Add assertions for `#zoomIn`, `#zoomOut`, `#zoomLevel`, `#resetView`, and `#panTool`:

```python
page.locator("#zoomIn").click()
expect(page.locator("#zoomLevel")).to_have_text("125%")
zoomed = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert zoomed["view"]["zoom"] == 1.25

page.locator("#resetView").click()
expect(page.locator("#zoomLevel")).to_have_text("100%")

before_touch = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
dispatch_pointer(page, "pointerdown", pointer_type="touch", x=100, y=100, width=70, height=70)
dispatch_pointer(page, "pointermove", pointer_type="touch", x=160, y=160, width=70, height=70)
dispatch_pointer(page, "pointerup", pointer_type="touch", x=160, y=160, width=70, height=70)
after_touch = page.evaluate("window.__learningOSHandwriting.debugSnapshot()")
assert after_touch["pages"] == before_touch["pages"]
assert after_touch["view"] == before_touch["view"]
```

Draw after zooming and assert the stored point is inverse-transformed into the logical page rather than using raw viewport coordinates.

- [ ] **Step 2: Run Playwright and verify RED**

Expected: FAIL because zoom controls and `view` state do not exist and touch currently creates ink.

- [ ] **Step 3: Add stable toolbar controls and view state**

Add controls with fixed dimensions:

```html
<button class="icon-button tool-button" id="panTool" type="button" aria-pressed="false" title="移动">移动</button>
<button class="icon-button" id="zoomOut" type="button" aria-label="缩小" title="缩小">−</button>
<span class="zoom-level" id="zoomLevel">100%</span>
<button class="icon-button" id="zoomIn" type="button" aria-label="放大" title="放大">＋</button>
<button class="icon-button tool-button" id="resetView" type="button" title="复位视图">复位</button>
```

Add state and transform helpers:

```javascript
view: { zoom: 1, panX: 0, panY: 0 },
touches: new Map(),
lastPenAt: 0,

function clampView() {
  const rect = canvas.getBoundingClientRect();
  const view = handwritingState.view;
  const scaledWidth = rect.width * view.zoom;
  const scaledHeight = rect.height * view.zoom;
  const minPanX = Math.min(0, rect.width - scaledWidth);
  const minPanY = Math.min(0, rect.height - scaledHeight);
  view.panX = scaledWidth <= rect.width
    ? (rect.width - scaledWidth) / 2
    : Math.min(0, Math.max(minPanX, view.panX));
  view.panY = scaledHeight <= rect.height
    ? (rect.height - scaledHeight) / 2
    : Math.min(0, Math.max(minPanY, view.panY));
}

function setZoom(nextZoom, focalX, focalY) {
  const view = handwritingState.view;
  const zoom = Math.min(3, Math.max(.5, nextZoom));
  const ratio = zoom / view.zoom;
  view.panX = focalX - (focalX - view.panX) * ratio;
  view.panY = focalY - (focalY - view.panY) * ratio;
  view.zoom = zoom;
  clampView();
  updateViewControls();
  renderCanvas();
}

function pointFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  const view = handwritingState.view;
  return {
    x: ((event.clientX - rect.left - view.panX) / view.zoom) / rect.width,
    y: ((event.clientY - rect.top - view.panY) / view.zoom) / rect.height,
    pressure: Number((event.pressure > 0 ? event.pressure : .5).toFixed(3)),
    t: Math.round(performance.now()),
  };
}
```

In `renderCanvas`, clear the viewport, then apply `translate(panX, panY)` and `scale(zoom, zoom)` before drawing the paper and strokes. Keep `renderPageDataUrl` untransformed.

- [ ] **Step 4: Implement pointer classification and palm rejection**

Use these rules in pointer handlers:

```javascript
const PEN_GUARD_MS = 800;
const PALM_SIZE_PX = 35;

function isLikelyPalm(event) {
  return event.pointerType === 'touch' &&
    (event.width >= PALM_SIZE_PX || event.height >= PALM_SIZE_PX);
}

function touchAllowed(event) {
  return !isLikelyPalm(event) &&
    !handwritingState.penPointerId &&
    Date.now() - handwritingState.lastPenAt >= PEN_GUARD_MS;
}
```

Pen updates `lastPenAt` on down/move/up. Touch never calls drawing or erasing. One allowed touch pans; two allowed touches pinch around their midpoint. Mouse pans only in `pan` mode. Reset returns `{ zoom: 1, panX: 0, panY: 0 }`.

- [ ] **Step 5: Run Playwright and verify GREEN**

Expected: zoom, inverse drawing coordinates, reset, pan, palm rejection, eraser, and all previous tests PASS.

### Task 5: Connect The Recognition UI To The Proxy

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting.py`
- Modify: `outputs/learning-os-ui-prototype.html:184-205,403-424,768-771`

- [ ] **Step 1: Add a failing mocked recognition test**

Before navigating, intercept the proxy URL:

```python
page.route(
    "http://127.0.0.1:4174/api/v1/handwriting/recognize",
    lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "request_id": "resp_test",
            "model": "gpt-5.6-luna",
            "confidence": None,
            "sections": [{"title": "信号", "transcript": "ROC 为收敛域。"}],
            "critical_formulas": [{"latex": "X(s)=1/(s+3)", "meaning": "拉氏变换"}],
            "diagram_notes": ["门函数图"],
            "uncertain": ["积分下限需确认"],
        }),
    ),
)
```

Draw one stroke, click recognition, and assert the button enters a running state, the transcript becomes editable, service status names the model, formulas and uncertain items render, and the confirmation checkbox remains unchecked.

- [ ] **Step 2: Run Playwright and verify RED**

Expected: FAIL because the button currently only reveals the disconnected placeholder.

- [ ] **Step 3: Implement the recognition request and review rendering**

Add stable IDs for service state, metrics, formulas, diagrams, and uncertainties. Replace the click handler with:

```javascript
const RECOGNITION_URL = 'http://127.0.0.1:4174/api/v1/handwriting/recognize';

async function recognizeCurrentAnswer() {
  const button = document.getElementById('recognizeAnswer');
  setRecognitionState('running');
  try {
    const response = await fetch(RECOGNITION_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        png_data_url: renderPageDataUrl(currentPage(), 1600, 1200),
        stroke_json: exportPayload(),
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Recognition failed');
    const transcript = result.sections
      .map(section => `## ${section.title}\n${section.transcript}`)
      .join('\n\n');
    recognizedText.value = transcript;
    renderRecognitionDetails(result);
    transcriptConfirmed.checked = false;
    setRecognitionState('success', result.model);
  } catch (error) {
    setRecognitionState('error', error.message);
  } finally {
    button.disabled = false;
  }
}
```

Implement detail rendering with DOM nodes and `textContent`, never `innerHTML`, for model strings:

```javascript
function replaceList(containerId, items, formatItem) {
  const container = document.getElementById(containerId);
  container.replaceChildren();
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    const empty = document.createElement('li');
    empty.textContent = '无';
    container.append(empty);
    return;
  }
  values.forEach(item => {
    const row = document.createElement('li');
    row.textContent = formatItem(item);
    container.append(row);
  });
}

function renderRecognitionDetails(result) {
  document.getElementById('recognitionRequestId').textContent = result.request_id || '—';
  document.getElementById('recognitionModel').textContent = result.model || '—';
  document.getElementById('recognitionConfidence').textContent = '—';
  replaceList(
    'recognitionFormulas',
    result.critical_formulas,
    item => `${item.latex || '—'}${item.meaning ? ` · ${item.meaning}` : ''}`,
  );
  replaceList('recognitionDiagrams', result.diagram_notes, item => String(item));
  replaceList('recognitionUncertain', result.uncertain, item => String(item));
  document.getElementById('recognitionResult').classList.add('visible');
}
```

The result panel must expose those six stable IDs plus `recognizedText` and `transcriptConfirmed`. Display `—` for confidence because the model does not supply a calibrated numeric value. Keep all model output unconfirmed until the checkbox is checked.

- [ ] **Step 4: Run Playwright and verify GREEN**

Expected: recognition, confirmation, Evidence, eraser, zoom, and all legacy checks PASS with no page errors.

### Task 6: Verify Proxy, Live Relay, And Responsive Layout

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_handwriting_responsive.py`
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_api.py`

- [ ] **Step 1: Add responsive toolbar assertions**

For 1440x900, 768x1024, and 375x667, assert `#zoomLevel`, `#panTool`, and `#recognizeAnswer` are inside the viewport, canvas dimensions remain at least 300x300, and no document horizontal overflow appears.

- [ ] **Step 2: Add an opt-in live smoke test**

When `LEARNING_OS_LIVE_TEST=1`, load `outputs/recap-page-1-160dpi.png`, call `call_relay`, and assert the extracted result contains `sections`, `critical_formulas`, and at least one formula containing `s+3`. Skip this test otherwise.

- [ ] **Step 3: Start the local proxy on an unused port**

Run hidden on port 4174:

```powershell
$proxyArgs = @{
  WindowStyle = 'Hidden'
  FilePath = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  ArgumentList = @('outputs\learning-os-api.py', '--port', '4174')
  WorkingDirectory = 'C:\Users\user\Documents\Codex\2026-07-21\https-chatgpt-com-share-6a5e4b81-db84'
}
Start-Process @proxyArgs
```

Verify:

```powershell
Invoke-RestMethod 'http://127.0.0.1:4174/health'
```

Expected: `{ "status": "ok", "model": "gpt-5.6-luna" }`.

- [ ] **Step 4: Run the full test suite**

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_api.py' -v
& $py 'work\presentations\learning-os-ui\tmp\test_handwriting.py'
& $py 'work\presentations\learning-os-ui\tmp\test_handwriting_responsive.py'
```

Expected: all proxy tests PASS, `handwriting Playwright checks: OK`, and `responsive handwriting checks: OK`.

- [ ] **Step 5: Run the Huashu visual verifier**

```powershell
$verifyArgs = @(
  'C:\Users\user\.codex\skills\huashu-design\scripts\verify.py'
  'outputs\learning-os-ui-prototype.html'
  '--viewports', '1440x900,768x1024,375x667'
  '--output', 'work\presentations\learning-os-ui\tmp\verify-handwriting-v2'
)
& $py @verifyArgs
```

Expected: screenshots for all viewports, no JavaScript errors, and a clean console.

- [ ] **Step 6: Perform the real relay smoke test once**

```powershell
$env:LEARNING_OS_LIVE_TEST='1'
& $py -m unittest 'work\presentations\learning-os-ui\tmp\test_learning_os_api.py' -v
Remove-Item Env:LEARNING_OS_LIVE_TEST
```

Expected: the live test completes through `https://www.cctq.ai/v1/responses` without printing the API key.

- [ ] **Step 7: Inspect desktop, tablet, and phone screenshots**

Confirm that toolbar controls do not wrap into isolated rows, recognition details do not overlap the submit action, and the canvas remains the dominant surface on tablet and phone.
