# Learning OS V3 Hybrid Canvas And Local Loop Design

**Status:** Implemented and verified locally

## Goal

Turn the current handwriting prototype into the primary Learning OS experience. The website owns the complete local workflow:

1. Present an active-recall question.
2. Let the learner answer on a hybrid self-growing canvas.
3. Transcribe handwriting with the configured relay model.
4. Require human review of the transcript.
5. Persist immutable Evidence in a local Event Store.
6. Evaluate the answer in the background.
7. Append an Assessment event and project the resulting Learning State.
8. Return the assessment to the same website without navigating away from the answer.

This phase remains local. It does not deploy to Hermes, take over the 21:00 workflow, connect Feishu, or modify the cloud project at `/home/ubuntu/learning-os`.

## Product Experience

The website is the primary client. Downloads are secondary backup and sharing actions.

During recall, the question remains in a compact top bar and the canvas occupies almost the entire workspace. A floating bottom toolbar keeps pen, eraser, pan, zoom, fit-content, and submit controls reachable on a tablet.

Submitting does not navigate to another page. The immutable answer snapshot is saved first. The website then shows a compact background-assessment status. When assessment finishes, a review drawer opens beside the original canvas on desktop and from the bottom on narrow tablet and phone layouts. The original handwriting remains visible for direct comparison.

The assessment drawer shows:

- current assessment status;
- correct, missing, and incorrect points;
- critical formula feedback;
- confirmed transcript;
- previous and resulting `f_state`;
- event and assessment identifiers;
- actions to answer again or return to the daily queue.

The UI may report success only after the local API returns a persisted `event_id`. A failed write keeps the answer and offers retry. A failed assessment preserves Evidence, appends a failure event, and offers retry without inventing Learning State.

## Hybrid Self-Growing Canvas

Each page is an independent world-coordinate canvas. Coordinates are logical CSS pixels and are not clamped to `0-1`.

The initial paper bounds are approximately one tablet viewport wide and 1.5 viewport heights tall. After a stroke is committed:

- if content is within 160 logical pixels of the bottom edge, grow downward by 600 pixels;
- if content is within 120 logical pixels of the left or right edge, grow that side by 400 pixels;
- growth happens only after pointer-up, so the paper never jumps during a stroke;
- existing stroke coordinates and the current view transform never change during growth.

The page may grow repeatedly in every direction, but its default behavior is vertical. This gives normal answers a long-paper feel while still supporting wide derivations and diagrams.

The view remains separate from content:

```json
{
  "zoom": 1.0,
  "panX": 0,
  "panY": 0
}
```

Zoom remains limited to 50%-300%. One finger pans, two fingers pinch, and touch never creates ink. Pen activity cancels existing touch gestures and blocks new touch gestures for 800ms. Large touch contact patches are ignored as palms.

The toolbar provides:

- pen;
- true segment eraser;
- mouse/trackpad pan mode;
- undo and redo;
- zoom controls;
- reset to the page origin at 100%;
- fit all content into the viewport;
- a secondary overflow menu for clear, page management, and exports.

Undo and redo restore both strokes and paper bounds. A clear operation resets bounds to the initial paper size. Page switching never changes world coordinates.

## Stroke Schema And Migration

New drafts and exports use schema version 2:

```json
{
  "schemaVersion": 2,
  "coordinateSpace": "world-css-px",
  "pages": [{
    "id": "page-id",
    "bounds": {"minX": 0, "minY": 0, "maxX": 1200, "maxY": 1800},
    "strokes": [{
      "id": "stroke-id",
      "tool": "draw",
      "color": "#172127",
      "baseWidth": 3.5,
      "points": [{"x": 120.5, "y": 88.25, "pressure": 0.61, "t": 1420}]
    }]
  }]
}
```

Schema v1 drafts are migrated once on load. Normalized coordinates are multiplied by the initial page width and height. The migrated draft is then saved as schema v2. Migration must preserve page order, stroke order, IDs, pressure, and timestamps.

View state is a UI preference and is not part of immutable Evidence.

## Export And Recognition

The primary flow never requires a download.

Secondary export actions include:

- export all content as a PNG cropped to the union of stroke bounds plus 80 pixels of padding;
- export the current viewport as a PNG;
- export schema v2 stroke JSON.

Export output is independent of viewport dimensions, current zoom, and pan.

Recognition uses content-aware image chunks. The browser renders immutable PNG chunks from world coordinates. Each chunk is at most 1600x1600 output pixels and overlaps its vertical neighbor by 120 logical pixels. Empty chunks are not sent. A request may contain at most 12 chunks and each decoded PNG must be no larger than 5MB.

The local proxy sends chunks sequentially to `gpt-5.6-luna`, preserving page and chunk order. It merges sections, formulas, diagrams, and uncertain spans while deduplicating overlap text. Model output remains untrusted text and is rendered with `textContent` only.

The recognition request captures the current content version and page ID. If either changes before all chunks return, the response is discarded. Every new result clears the transcript-confirmation checkbox.

## Local Persistence

The local Python service on port `4174` becomes both the credential-safe vision proxy and the local Learning OS API. It binds only to loopback.

SQLite stores append-only events. Large immutable artifacts are stored outside SQLite under:

```text
data/artifacts/<evidence_id>/
  handwriting.json
  page-001.png
  page-002.png
  transcript.txt
```

Events reference artifact paths and SHA-256 hashes. Artifact files are written through a temporary file and atomic rename before the Evidence event is appended. Existing artifacts are never overwritten.

The local Event Store rejects SQL `UPDATE` and `DELETE` through triggers, matching the cloud architecture's append-only rule.

## Events And Projection

The minimum local event sequence is:

```text
EvidenceExtracted
AssessmentRequested
AssessmentRecorded | AssessmentFailed
```

`EvidenceExtracted` contains identifiers, artifact hashes, question context, confirmed transcript metadata, and creation time. It does not contain mutable Learning State.

`AssessmentRequested` records the assessment job and source Evidence ID.

`AssessmentRecorded` contains structured feedback, the assessed `f_state`, model metadata, and the Evidence ID. The reducer projects the current Learning State from events. It does not silently merge different aggregates.

`AssessmentFailed` records a sanitized error category and retryability. It does not expose credentials or upstream response bodies.

Assessment results are never produced by browser code and never update state without an appended `AssessmentRecorded` event.

## Assessment Workflow

After Evidence persistence, the API starts one local background assessment job. The job receives:

- question and expected learning objective;
- confirmed transcript;
- immutable handwriting image chunks;
- current projected state for context only.

The model must return strict JSON containing:

- `summary`;
- `correct_points`;
- `missing_points`;
- `incorrect_points`;
- `formula_feedback`;
- `f_state`;
- `recommended_action`;
- `uncertain`.

The API validates this structure before appending `AssessmentRecorded`. Invalid model output appends `AssessmentFailed` instead.

The website polls the submission resource every two seconds while the drawer is open. Polling stops on recorded assessment, recorded failure, modal close, or a five-minute client timeout. Closing the page does not cancel the server job. Refreshing the website reloads the persisted Evidence and current assessment status.

## API Contract

The local service exposes:

```text
GET  /health
POST /api/v1/handwriting/recognize
POST /api/v1/evidence
GET  /api/v1/evidence?aggregate_type=<type>&aggregate_id=<id>
GET  /api/v1/evidence/<evidence_id>
POST /api/v1/evidence/<evidence_id>/assessment/retry
GET  /api/v1/timeline?aggregate_type=<type>&aggregate_id=<id>
GET  /api/v1/projection?aggregate_type=<type>&aggregate_id=<id>
```

`POST /api/v1/evidence` is idempotent through a client-generated submission ID. Repeated requests with the same ID return the original persisted Evidence instead of appending duplicates.

All mutation routes require the allowed local UI Origin. Request size limits, strict JSON parsing, generic upstream errors, and credential isolation from V2 remain mandatory.

## Recovery And Failure States

- Draft saving continues locally during writing.
- A failed Evidence upload leaves the draft untouched and offers retry.
- A pending Evidence survives service restart. It remains pending until assessment is retried.
- Assessment retry appends a new `AssessmentRequested` event; it never edits the failed event.
- Missing or hash-mismatched artifacts make Evidence readable as metadata but block assessment and display an explicit integrity failure.
- Empty canvases cannot be recognized or submitted as handwritten Evidence.
- Stale recognition responses never replace newer canvas content. Assessment results are appended only for their immutable source Evidence ID.

## Verification

Automated tests must cover:

- schema v1 to v2 migration;
- growth at bottom, left, and right thresholds;
- no growth during an active stroke;
- undo and redo of strokes and page bounds;
- fit-content and reset-view behavior;
- pen, touch pan, pinch, palm rejection, and the 800ms guard;
- sparse-stroke and sparse-eraser-path handling;
- viewport-independent full-content PNG output;
- current-view PNG output;
- recognition chunk ordering, overlap, deduplication, and stale-response rejection;
- artifact atomicity and SHA-256 verification;
- append-only SQLite triggers;
- idempotent Evidence submission;
- assessment success, invalid output, failure, and retry events;
- projection after process restart;
- CORS, body limits, loopback binding, and error sanitization;
- desktop 1440x900, tablet 768x1024, and phone 375x667 layouts;
- no JavaScript errors, horizontal overflow, control overlap, or blank canvas output.

A live relay smoke test remains opt-in. It may verify transport and structured output, but it must not treat model transcription accuracy as deterministic. Human confirmation remains mandatory.

## Out Of Scope

- Hermes Runtime or Gateway changes;
- 21:00 workflow takeover;
- Feishu delivery or chat interaction;
- Anki or Kanban integration;
- cloud deployment;
- historical cloud-data migration;
- mastery, fatigue, next-review, or F0-F5 calculation policy beyond recording the assessed `f_state`;
- multi-user authentication;
- collaborative editing;
- an infinite-canvas minimap.
- dynamic question generation or review scheduling; V3 continues using the seeded recall question.
