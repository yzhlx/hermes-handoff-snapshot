# Candidate package verification

Candidate: `package-ui-2-canvas-candidate/学习 OS/学习 OS.exe`

## PASS

- Built from commit `2c84701fabbb764ad8e07da23c61d94d65c94d19` using Python 3.12.13 and PyInstaller 6.21.0.
- Build command used a new dist directory and external F: work/spec directories; no historical package directory was overwritten.
- Candidate contains 85 files and includes the full `outputs/` asset set.
- Source/package SHA-256 matched for `learning-os-app.html`, `learning-os-app.css`, `learning-os-app.js`, `learning-os-canvas-model.js`, `learning-os-handwriting-workspace.js`, `learning-os-static.py`, `learning-os-desktop.py`, and `learning-os-api.py`.
- The workspace JS is present in `_internal/` and therefore cannot produce a package-only 404 from an omitted asset.
- Exact extension scan found 0 packaged `.db`, `.sqlite`, or `.sqlite3` data files.
- Text-resource scan found no credential value. Its sole pattern hit was the source identifier `payload.clear_api_key`, not a secret.
- Ports 4173 and 4174 were read-only checked free before planned EXE smoke.

## BLOCKED

The real EXE lifecycle test was not started because the windowless launcher has no normal close path and the environment rejected a script that would terminate even the known candidate process after testing. Starting it would risk leaving an orphan that occupies 4173/4174. Thus candidate-owned HTTP, Pointer interaction, refresh/restart persistence, close, port release, same-data-root restart, and path-matrix EXE launch are not covered.

## Build correction record

Two argument-stage attempts failed before packaging: an empty `--add-data` destination and a C:-spec/F:-source cross-volume path. Neither produced a candidate directory. The successful Windows form was `--add-data "<outputs>;."` with work/spec directories on F:.
