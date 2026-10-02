# Hermes Learning OS UI 2.0 Program

## Long-term objective

Evolve the existing local-first Hermes Learning OS from a functional MVP into a calm, durable desktop learning system. The work is visual and interaction-focused: it preserves all existing learning data meanings, SQLite schema, API contracts, provider behavior, credential boundaries, and Windows launcher behavior.

## Milestones

0. Baseline audit and risk inventory
1. Design System Foundation
2. Home experience and Today's Mission
3. Hermes AI experience
4. Learning Rhythm / Timeline
5. Weekly Planner
6. Wrong Answer Notebook
7. Learning State and Statistics
8. Settings and system surfaces
9. Motion and interaction polish
10. Responsive and accessibility validation
11. Full regression
12. Isolated Windows candidate package

## Non-negotiable boundaries

- Frontend HTML, CSS, and presentation-only JavaScript are the primary change surface.
- No SQLite schema, API contract, learning-state computation, AI gateway behavior, credential handling, Event Store, or launcher behavior changes without a separately documented necessity and regression test.
- Existing packages are evidence and must not be overwritten.
- Production learning data is never used for destructive testing or copied into artifacts.
- Each milestone requires a real rendered check, relevant automated checks, an updated program state, and explicit limitations.

## Acceptance bar

The end state has one shared warm-paper design language, one clear primary action per screen, usable states for loading/empty/error/success, keyboard-visible focus, reduced-motion support, responsive layouts without horizontal overflow, real regression evidence, and an isolated candidate package only after the full suite is green.
