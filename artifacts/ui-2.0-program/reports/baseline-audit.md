# Milestone 0 — Baseline Audit

## Method

On 2026-07-22, the already-running packaged application at `http://127.0.0.1:4173/` was inspected through its visible navigation without submitting any forms or sending AI messages. Screenshots are in `../screenshots/milestone-0/`. The source root was also inspected; it is a vanilla static HTML/CSS/JS frontend backed by the existing local API.

## Page inventory

| Page | Entry | Core user task | Baseline observation | Regression sensitivity |
| --- | --- | --- | --- | --- |
| Today | `今日` | identify and start the next learning action | Warm shell is established, but metric strip precedes Mission and weakens the next-action hierarchy | dashboard loading, task start, status dialog, AI prompt handoff |
| Weekly Planner | `周计划` | add a dated task and see today's tasks | Form is usable but visually reads as two equal administrative panels; empty list has little guidance | prior safe form reset, disabled submit, persistence, date filter |
| Wrong Answer Notebook | `错题专栏` | record evidence and review prior mistakes | Long form dominates; evidence and later AI analysis have no visual separation | required fields, quick-image dialog, provider failures, persistence |
| Daily Review | `每日复习` | complete up to five review outcomes | One-problem focus is structurally sound, but empty/completion feedback needs a deliberate visual state | maximum-five semantics, outcome persistence |
| Hermes AI | `AI 对话` | create/select a conversation and send a learning question | Existing message area is functional but generic; the empty state and composer lack a mentor/editorial role | conversation isolation, duplicate protection, provider failures, persisted user message |
| Learning Records | `学习记录` | interpret stored study records | Three equal data panels create low hierarchy; empty state is plain text | statistics data mappings, no invented trends |
| Settings | `设置` | safely configure and test AI provider | Clear field labels and non-secret key flow exist, but visual grouping and save/test status need stronger differentiation | credential redaction, protocol/provider fields, connection test |
| System surfaces | status dialog, notice, image quick entry | feedback and short workflows | Existing modal/toast treatment is functional but is not yet a unified component/state system | dialog focus/close, error visibility, no sensitive output |

## Cross-page visual and interaction audit

### Repeated patterns to unify

- Warm canvas, sidebar, serif headings, outlines, and dark primary buttons already provide a valid foundation.
- Page headings repeat both in the top context bar and the page body, creating excess vertical cost.
- Form controls, panels, list rows, and chat messages use closely related but not consistently tokenized spacing, radius, focus, and empty-state rules.
- Every content area is generally a bordered white panel, so primary work and supporting information compete equally.

### State coverage baseline

| State | Existing condition | UI 2.0 action |
| --- | --- | --- |
| Empty | Plain `暂无` / `还没有` text appears on several pages | retain honest data but establish one contextual empty-state pattern |
| Loading | no visible structural placeholder on page-level fetches | add a frontend-only skeleton/quiet loading treatment without changing endpoints |
| Error | `notice` displays an error message | standardize error contrast, language, and aria-live behavior |
| Success | save flows use notices and data refresh | preserve true success semantics; strengthen visible result instead of celebratory toast noise |
| Disabled / duplicate prevention | present in task and chat submit handling | preserve and give controls a shared disabled affordance |

### Accessibility baseline

- Semantic regions, button labels, form labels, dialog elements, and a focus style exist.
- The current focus ring and muted text require contrast and consistency review across all paper layers.
- Mobile converts sidebar navigation to a horizontal bottom strip; narrow-page overflow and touch target checks remain outstanding.
- Status is sometimes represented by a coloured dot plus text; UI 2.0 must retain text labels.

## Baseline risks

1. Do not regress the weekly planner's fixed submit/reset behavior; successful persistence must not become an apparent failure.
2. Do not change chat request order, saved-user-message behavior, provider error handling, or credential display.
3. Do not introduce mock data just to make empty screens visually dense.
4. The installed package is an immutable baseline during source UI work. Source preview must not be mistaken for a newly built package.

## Milestone 0 result

PASS with audit limitations: every accessible primary page was opened and captured, but no write workflow or external AI call was run because this milestone was deliberately read-only against the running package. Those behaviors are covered in later targeted and full regression milestones.
