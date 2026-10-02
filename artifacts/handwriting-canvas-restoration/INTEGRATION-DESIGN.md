# Integration design

`learning-os-app.html` owns the UI 2.0 workspace markup and loads scripts in this order:

1. `learning-os-app.js` creates the product navigation entry;
2. `learning-os-canvas-model.js` exposes the existing model;
3. `learning-os-handwriting-workspace.js` binds the already-present Canvas DOM once.

The controller is an IIFE loaded after its DOM. It persists only local Canvas drafts in browser localStorage, retains the existing Evidence/recognition endpoints, and does not change schema, API, credentials, network binding, or packaging architecture. PyInstaller receives the whole `outputs/` directory as data, so the new static asset is included without a separate manifest edit.
