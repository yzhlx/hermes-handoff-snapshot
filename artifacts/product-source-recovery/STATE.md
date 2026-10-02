# Hermes Authoritative Product Source Recovery — State

## PASS — source recovery complete

- Authoritative source selected: `C:\Users\user\Documents\Codex\2026-07-21\https-chatgpt-com-share-6a5e4b81-db84\outputs\`.
- Restored branch: `ui/hermes-ui-2-program`, based on `chore/repository-foundation` commit `4302200`.
- Restored worktree: `F:\Users\user\Documents\learning os-worktrees\hermes-ui-2-program`.
- The selected source is not an EXE extraction: the candidate PyInstaller spec explicitly bundles that `outputs\` directory.
- `package-ui-2-candidate` exactly matches the selected source for all eleven checked core static/Python files.
- Recovered source tests passed; live-provider tests remain intentionally skipped.

## KNOWN LIMITATION — handwriting P0 reproduced

The UI 2.0 product page does not mount the handwriting canvas. The complete handwriting implementation remains in `outputs/learning-os-ui-prototype.html`; the current model file remains present but has no UI entry. This is a known parity regression for the follow-up branch, not a source-recovery failure.
