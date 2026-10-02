# Learning OS Handwriting V2 Design

## Goal

Upgrade the existing handwriting prototype so it can call the configured relay vision model, erase real stroke segments, and support tablet-safe zoom and pan without corrupting stored evidence.

## Scope

- Connect `POST /api/v1/handwriting/recognize` to the configured Responses API through a local server-side proxy.
- Keep API credentials outside browser code and exported artifacts.
- Replace white overpainting with destructive segment erasing that supports undo and redo.
- Add 50%-300% canvas zoom, reset, pan, mouse controls, and touch gestures.
- Add application-level palm rejection.
- Preserve current multipage, PNG export, stroke JSON export, text fallback, and Evidence confirmation behavior.

Not in scope: remote Hermes deployment, formula-specific OCR, automatic Assessment, or automatic Learning State changes.

## Architecture

The static HTML remains the UI served on port 4173. A small local Python proxy listens on port 4174, accepts only the local UI origin, validates the PNG payload, and calls the configured relay at `https://www.cctq.ai/v1/responses`. For the local prototype it may read the existing Codex API key without printing it; production deployment must receive the key through a server-side environment variable.

The browser sends a rendered page PNG and the stroke JSON. The proxy sends only the PNG and a constrained transcription prompt to the vision model. It returns structured sections, LaTeX formulas, diagram notes, and uncertain items. The original PNG and stroke JSON remain authoritative Evidence artifacts.

## Pointer And Palm Behavior

- `pointerType=pen` writes or erases according to the selected tool.
- Mouse writes or erases in those modes; a dedicated move tool pans the view.
- Touch never creates ink.
- A single touch pans only when no pen pointer is active and no pen event has occurred in the previous 800ms.
- Two touches pinch-zoom only when no pen pointer is active.
- Touch contacts with a large reported contact patch are ignored as likely palms.
- `touch-action: none` prevents browser scrolling while interacting with the canvas.

This cannot override defective device drivers that report a stylus as ordinary touch, but it prevents palm marks on devices that correctly expose Pointer Events.

## Eraser

The current white-stroke eraser is removed. During an erase gesture, points near the eraser path are deleted and surviving stroke fragments are split into independent strokes. One erase gesture is one history operation. Undo restores the exact pre-erase stroke snapshot; redo restores the erased snapshot.

Clear-page and drawing operations use the same snapshot history model so undo/redo behavior remains deterministic.

## Zoom And Pan

The view transform contains `zoom`, `panX`, and `panY`. Zoom is clamped to 0.5-3.0 and is centered on the gesture midpoint or viewport center. Pointer coordinates are inverse-transformed before being normalized and stored, so drawing at any zoom level produces stable page coordinates.

The toolbar provides zoom out, current percentage, zoom in, move, and reset controls. Export renders the logical page at a fixed resolution with no view transform, so zoom and pan never alter PNG or stroke JSON evidence.

## Recognition States

- Idle: model connection available but no request has started.
- Running: button disabled and progress text visible.
- Success: editable transcript, formulas, diagram notes, and uncertain items are shown for confirmation.
- Failure: the original page remains intact and a concise retryable error is shown.

Model output never changes Learning State directly. Submission still creates `EvidenceExtracted` with `pending_assessment`.

## Security And Limits

- No credential is embedded in HTML, local storage, downloads, logs, or test fixtures.
- Only PNG data URLs are accepted by the proxy.
- Payload size is bounded before decoding and before forwarding.
- CORS is restricted to the local prototype origins.
- Relay errors are normalized; upstream response bodies and credentials are not forwarded verbatim.

## Verification

- Playwright proves erasing removes only touched stroke segments and that undo/redo restores both states.
- Playwright proves zoom controls, reset, inverse coordinate mapping, move mode, and palm/touch rules.
- Playwright mocks a successful recognition response and verifies confirmation UI and Evidence submission.
- Python tests cover proxy validation, response extraction, error normalization, and credential handling without real secrets.
- One explicit real-image smoke test verifies the configured relay accepts the same handwritten PNG.
- Desktop, tablet, and phone screenshots are checked for clipping and overlap.

## Acceptance Criteria

- A stylus can write while a resting palm produces neither ink nor unexpected panning.
- The eraser visibly removes stroke segments and remains correct after redraw, zoom, export, undo, and redo.
- Users can zoom from 50% to 300%, pan, reset, and continue writing accurately.
- Recognition returns editable structured text through the relay without exposing credentials.
- Raw PNG and stroke JSON are retained, and no unconfirmed model output changes formal state.
