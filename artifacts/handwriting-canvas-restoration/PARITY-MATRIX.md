# Parity matrix

| Reference behavior | UI 2.0 integration | Status |
| --- | --- | --- |
| Full Canvas controller | `learning-os-handwriting-workspace.js` | PASS |
| Canvas data model | existing `learning-os-canvas-model.js` loaded before controller | PASS |
| Product entry | generated `[data-action="recall"]` navigation button | PASS |
| DOM mount and controls | UI 2.0 root modal markup | PASS |
| Pointer/eraser/history/clear | controller and formal root test | PASS |
| Desktop/tablet/mobile layout | UI 2.0 CSS plus responsive legacy regression | PASS |
| Static delivery | no-store JS HTTP 200 test and source/package hashes | PASS |
| Packaged executable start/close/restart | start/restart/persistence/port-release PASS; normal exit absent (KNOWN LIMITATION, tracked in `fix/windows-app-graceful-exit`) | KNOWN LIMITATION |
| Colour picker control | not present in preserved reference or restored UI | NOT APPLICABLE |
