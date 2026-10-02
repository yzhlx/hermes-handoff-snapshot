# Candidate locations

| Rank | Classification | Location | Evidence | Decision |
|---|---|---|---|---|
| A | Authoritative product source | `C:\Users\user\Documents\Codex\2026-07-21\https-chatgpt-com-share-6a5e4b81-db84\outputs\` | Unpacked HTML/CSS/JS, Python services, launcher, canvas model, legacy canvas source; build spec references it; candidate hashes match it. | Restored. |
| B | Complete historical source within same source root | `outputs/learning-os-ui-prototype.html` | Contains complete Canvas UI and is served by the static host; handwriting tests target it. | Restored as the parity baseline, not mounted by UI 2.0. |
| C | Partial output/evidence | `work/presentations/learning-os-ui/tmp/` | Source tests, Canvas model test, and isolated test helpers; includes unrelated presentation helper files. | Restored only test source files. |
| D | Build products | `package-ui-2-candidate/`, `package-ai-fixed-v2/`, `package-ai-fixed/` | PyInstaller outputs used only for correlation. | Not restored as source. |
| E | Reports/fixtures | `artifacts/ui-2.0-program/`, `artifacts/qa/`, screenshots | Useful provenance and regression evidence; not executable product source. | Only Markdown UI 2.0 program records restored. |
| F | Unrelated repository/worktree material | `F:\Users\user\Documents\learning os*` infrastructure branches | Repository rescue/foundation/evals/skills/release QA work. | Not merged or modified. |

The selected directory is not a Git repository. The recovery branch therefore records this as source recovery, rather than asserting historical Git provenance.
