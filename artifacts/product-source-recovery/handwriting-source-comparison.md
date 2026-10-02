# Handwriting source comparison

## Most complete baseline

`outputs/learning-os-ui-prototype.html` is the most complete recoverable handwriting Canvas source. It has the Canvas UI, Pointer Events, pen/eraser/pan controls, undo/redo, clear, zoom/reset, persistence, recognition, and responsive controls. The static host intentionally still serves it.

## UI 2.0 result

`outputs/learning-os-app.html` contains no Canvas element and includes only `learning-os-app.js`. It does not include `learning-os-canvas-model.js` or any handwriting UI control. The current canvas model preserves data-model support for world coordinates, pan, undo/redo snapshots, recognition chunking, and saved timestamps, but it is headless because the UI entry is absent.

## Test parity finding

- `test_handwriting.py`, `test_handwriting_responsive.py`, and `test_world_canvas.py` all target `http://127.0.0.1:4173/learning-os-ui-prototype.html`.
- They pass against the recovered source, but they do not exercise the UI 2.0 page.
- Therefore the tests were not deleted, but their target stayed on the legacy canvas while UI 2.0 lost its canvas mount. This is an entry/UI integration regression, not proof that all Canvas implementation was deleted.

## Follow-up reference

Use `learning-os-ui-prototype.html` as the functional reference for `fix/handwriting-canvas-parity`. Do not copy it wholesale into UI 2.0; first map required interactions and preserve the UI 2.0 visual and API contracts.
