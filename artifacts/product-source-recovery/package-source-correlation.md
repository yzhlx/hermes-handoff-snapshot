# Package/source correlation

## Build evidence

`tmp/pyinstaller-spec-ui-2-candidate/学习 OS.spec` (SHA-256 `864E711B98D368DB042AFE69407A426C4D4A8C10D0873E4317ED512517561BA0`) records:

- entry: `outputs/learning-os-desktop.py`;
- data directory: the complete historical absolute `outputs/` directory;
- output package: `package-ui-2-candidate/学习 OS/`.

This establishes build-input provenance without treating package contents as source.

## SHA-256 result

The following source/package pairs are exact matches in `package-ui-2-candidate/学习 OS/_internal/`:

- `learning-os-app.html`, `learning-os-app.css`, `learning-os-app.js`, `learning-os-canvas-model.js`;
- `learning-os-api.py`, `learning-os-ai.py`, `learning-os-core.py`, `learning-os-store.py`;
- `learning-os-static.py`, `learning-os-desktop.py`, `learning-os-credentials.py`.

The complete, independently recomputable 11-file source/package hash receipt is committed as `package-source-hashes.csv`. It records both SHA-256 inputs and a `MATCH` status for every row; the package itself remains excluded as a build product.

## Package limitations

- The candidate package is a build product and was not copied into Git.
- Candidate-owned packaged lifecycle/persistence was historically blocked by an unrelated process on ports 4173/4174. This recovery verified the restored source services, not a replacement EXE build.
