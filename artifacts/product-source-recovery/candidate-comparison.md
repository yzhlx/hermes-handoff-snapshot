# Candidate comparison

## Authoritative candidate: `outputs/`

Evidence order, not timestamp alone:

1. It contains the complete product composition: static application, local API/static services, SQLite store/core, AI adapter, credential boundary, desktop launcher, Canvas model, and legacy canvas source.
2. The UI 2.0 PyInstaller spec uses `outputs/learning-os-desktop.py` as its entry and includes the entire absolute `outputs/` directory as data.
3. Every checked file in the UI 2.0 candidate equals the corresponding current `outputs/` SHA-256: HTML, CSS, app JS, canvas-model JS, API, AI, core, store, static host, launcher, and credential module. `package-source-hashes.csv` records the 11 source/package hash pairs.
4. The restored test tree imports and serves this source root directly.

## Package comparison

| Package | UI static files | Canvas model | API/core/store/static/launcher/credentials | Result |
|---|---|---|---|---|
| `package-ui-2-candidate` | exact match | exact match | exact match | Full checked-source match; this package was generated from the selected source. |
| `package-ai-fixed-v2` | differs | differs | API/core/store/static/launcher/credentials match | Older UI payload with a compatible later AI/service layer. |
| `package-ai-fixed` | differs | differs | API/core/store/static/launcher/credentials mostly match; AI differs | Older package, correlation only. |

## Answers

- The source directory generating the latest UI 2.0 candidate is `outputs/`.
- Package static resources are an exact checked match with `outputs/`.
- The Python service is also an exact checked match with the UI 2.0 candidate, so this is a full match rather than a static-only inference.
- No checked core source file is newer than, or absent from, the UI 2.0 candidate.
- No checked UI 2.0 candidate source file was missing from `outputs/`.
