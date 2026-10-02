# TASK-QUEUE.md — Hermes 学习 OS

> Status of tracked work as of 2026-07-22 (after Graceful Exit Merge + Integrated Candidate Handoff).

## Legend
`[DONE]` completed & verified · `[IN-PROGRESS]` active · `[BLOCKED]` cannot proceed · `[TODO]` pending · `[MANUAL]` needs human acceptance

## Lifecycle / exit

- [DONE] User-accessible graceful shutdown (`fix/windows-app-graceful-exit`) — merged via `9b18bc3`
- [DONE] Pre-merge security & scope review (Phase 1) — 7/7 gates pass
- [DONE] Main-branch regression (Phase 3) — 16 tests pass, node --check clean, tree clean
- [DONE] Integrated candidate build (Phase 4) — PyInstaller 6.21.0, EXE SHA `2262b000…f00cf9`
- [DONE] Real Windows verification (Phase 5) — A/B/C/D/E pass, draft recovery across restart confirmed
- [MANUAL] Real stylus (pen) input acceptance on physical digitizer — automated plumbing OK, user sign-off needed

## Canvas

- [DONE] Handwriting Canvas parity (`fix/handwriting-canvas-parity`) — merged via `9b18bc3`
- [DONE] Canvas persistence across EXE restart — verified (draft recovered)
- [DONE] Color = NOT APPLICABLE — stroke color hardcoded `#172127`, no pen-color feature

## Handoff / release

- [DONE] Authoritative status docs (CURRENT-STATE / TASK-QUEUE / RELEASE-STATUS) — this task
- [DONE] Post-graceful-exit git bundle + candidate ZIP + manifest (Phase 7)
- [DONE] UI design branch + worktree + audit docs (`ui/hermes-learning-journal-v2`) (Phase 8)
- [TODO] UI design implementation (暖米色极简学习手账 + 每日节律时间线 + Hermes AI 陪伴) — next phase, not started
- [TODO] Add favicon (or data-URI `<link rel="icon">`) to silence benign `/favicon.ico` 404

## Future learning-data integrations

- [TODO][LATER] Maimemo（墨墨背单词）read-only vocabulary integration — not part of the current UI implementation phase.
  - Add a `Maimemo Adapter` using the official authorized API; first inspect and preserve the raw response fields before defining stable mappings.
  - Store raw synchronization snapshots as artifacts/events and build a separate `Vocabulary State / Vocabulary Weakness Projection`.
  - Let Hermes compute an explainable high-risk / stubborn-word ranking from the available review and memory data; do not attempt to reproduce Maimemo's proprietary scheduling algorithm.
  - Add a lightweight homepage card named `今日顽固词`, showing one word at a time with pronunciation, revealable meaning/example, risk reason, and previous/next controls.
  - Add a full English-module page named `词汇薄弱点`, grouping words into `需抢救`, `正在恢复`, and `已稳定`.
  - Later option: show a low-frequency one-word micro-review during Pomodoro breaks, without turning rest periods into mandatory study sessions.
  - Responsibility boundary: Maimemo remains responsible for formal vocabulary learning, review scheduling, and memory planning; Hermes handles aggregation, display, reading-context association, explanation, and review summaries.
  - Keep vocabulary state separate from the general knowledge-point `F0–F5` model.
  - Phase 1 is read-only. Do not automatically add words, trigger early reviews, modify Maimemo plans, or build a replacement flashcard scheduler.
  - Acceptance prerequisite: confirm the real API fields available to the user's authorized account and define deduplication, sync cadence, error handling, and token-security rules.

## Infrastructure (NOT merged, carried in bundle for reference)

- [TODO] `feat/hermes-ai-evals`
- [TODO] `feat/hermes-engineering-skills`
- [TODO] `feat/hermes-release-qa`
- [TODO] `chore/repository-foundation`
- [TODO] `rescue/mixed-work-20260722`

## Blockers

- **None for release of the merged main branch + integrated candidate.** The only open item is MANUAL stylus acceptance (a hardware sign-off, not a code blocker).
