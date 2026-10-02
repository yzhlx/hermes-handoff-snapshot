# UI 2.0 Decisions

## D-001 — Preserve the warm-paper notebook foundation

The existing warm beige palette, serif display voice, and restrained dark ink match Hermes' product constraints. UI 2.0 consolidates them into semantic tokens rather than introducing a new visual brand, external fonts, glass effects, gradients, or a component framework.

## D-002 — Mission is the homepage centre of gravity

The Today dashboard makes `Today's Mission` the first substantial work surface after the contextual greeting. Metrics become a quiet supporting strip. This improves next-action clarity without changing dashboard data or task selection semantics.

## D-003 — Source preview is separated from the installed package

The installed executable owns its embedded assets and the default ports. Source UI verification therefore uses a separate static host and deterministic browser route interception where required. No historical package is overwritten during design work.

## D-004 — No artificial product data

Empty, current-task, candidate-task, and AI-insight states use the existing dashboard response. Visual hierarchy must remain understandable when data is absent; test-only fixtures never enter the package.

## D-005 — Hermes AI uses a mentor desk, not chat bubbles

Conversation history is treated as saved learning threads, Hermes replies are styled as learning annotations, and the composer is a paper field with a clear label. Existing chat creation, persistence, message order, error preservation, and provider call sequence remain unchanged.

## D-006 — Browser fetch failures use local-service language

Raw browser fetch failures are not actionable. The frontend maps only transport-level failures to a local-service message and stable `LOCAL_SERVICE_UNAVAILABLE` code; HTTP API errors retain their original response message and code.

## D-007 — Week Planner is a planning sheet, not a board

The planner pairs one intentional task-entry sheet with the selected day's rhythm. It makes existing planner constraints visible without changing task limits, priority meanings, date filtering, storage, or task status semantics. A successful request resets only after API confirmation; a later list-refresh failure is shown as a refresh problem, never as a failed save.

## D-008 — Recognition width is a cap, not a target

Full regression exposed an existing frontend canvas inconsistency: a 1200px-wide handwritten region was enlarged to the 1600px provider cap, unnecessarily reducing each world-coordinate chunk and creating a fourth upload. The documented behavior is to scale only over-wide content down to the cap. The single scale expression now preserves narrower native content. This is a regression correction required for the full suite, not a new recognition feature, API change, or data-model change.

## D-009 - Browser regression follows the cap contract

The World Canvas browser regression still asserted that a 353 by 262 content region should be enlarged to roughly the provider maximum. That assertion contradicted D-008 and the Canvas model unit contract. It now asserts the exact native 353 by 262 output dimensions, proving that the browser integration preserves narrow content rather than regressing to unnecessary upscaling.
