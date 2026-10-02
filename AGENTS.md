# AGENTS.md — Hermes Learning OS

## 注意事项

- 每次改动完成后，都必须创建一个对应的 Git commit，以便后续追踪和回滚。
- 每次改动后，都必须编写或更新相关测试，并在交付给用户前，确保所有测试和验证全部通过。

> This file defines the standing rules for every AI coding agent working in this repository.
> It applies to Codex, sub-agents, review agents, QA agents, and any automated code-modification workflow.
> When a task-specific instruction conflicts with this file, the safer and narrower instruction wins.
> Never silently violate this file. Report conflicts before proceeding.

---

## 0. Quick Operating Rules

Before changing code:

1. Inspect the repository structure and existing documentation.
2. Identify the real application entry points, database path, test commands, and packaging flow.
3. Preserve existing architecture unless the task explicitly authorizes architectural change.
4. Back up production data before any migration or destructive test.
5. Use isolated test data and a temporary SQLite database.
6. Run the existing test suite before modifying behavior.
7. Make the smallest change that satisfies the request.
8. Verify the real application, not only isolated code.
9. Run tests again after the change.
10. Report actual results only.

Never:

- claim a command passed without executing it;
- test destructive operations against the user's production database;
- expose API keys, credentials, private learning data, or database copies;
- modify unrelated code “while here”;
- replace the framework merely for convenience;
- turn known limitations into fake completed features;
- delete tests or weaken assertions to make CI green.

---

# 1. Project Identity

## 1.1 Product name

**Hermes Learning OS**

## 1.2 Product category

Hermes is an:

> AI-native personal learning operating system.

It is not:

- a conventional LMS;
- an online course marketplace;
- a generic admin dashboard;
- a social learning platform;
- a medical or psychological diagnosis tool;
- a cloud-first multi-user SaaS product at the current stage.

## 1.3 Current deployment model

The current product is a local-first, single-user Windows application built around:

- a local web interface;
- a Python local service;
- a SQLite database;
- a packaged Windows application;
- local AI provider configuration;
- Windows Credential Manager for secret storage;
- responsive support for desktop, tablet, and mobile layouts.

The local service must remain bound to the local machine unless a task explicitly authorizes a networking change.

## 1.4 Product mission

Hermes helps the user:

- decide what to study next;
- record tasks and weekly plans;
- capture wrong answers and learning evidence;
- review mistakes;
- track learning state;
- converse with an AI learning assistant;
- turn activity into persistent learning records;
- progressively build a long-term learning system.

## 1.5 Core experience

The product should feel like:

> a calm, intelligent learning notebook with a daily rhythm timeline and a decision-oriented AI assistant.

---

# 2. Product Principles

All product and engineering decisions must follow these principles.

## 2.1 Learning outcomes over feature count

Do not add features merely because they are technically possible.

Every feature should help the user:

- recall;
- practice;
- reflect;
- plan;
- correct;
- persist evidence;
- reduce friction.

## 2.2 AI is a learning decision assistant

Hermes AI is not a generic customer-service chatbot.

It should:

- explain the user’s learning state;
- identify weak areas;
- suggest the next best action;
- analyze wrong answers;
- help plan review;
- ask for missing evidence;
- avoid pretending certainty when information is incomplete.

## 2.3 Do not guess when evidence is insufficient

AI analysis must distinguish:

- known facts;
- user-provided evidence;
- inferred conclusions;
- missing information;
- provider or model limitations.

When the answer cannot be grounded, request more information rather than fabricate a confident result.

## 2.4 Local-first trust

The user must understand where data is stored.

Prefer:

- local persistence;
- transparent configuration;
- recoverable files;
- explicit data flows;
- minimal external dependence.

## 2.5 Long-session usability

The interface may be used for hours.

Therefore:

- avoid visual noise;
- avoid high-saturation color systems;
- avoid unnecessary animation;
- preserve readable contrast;
- keep actions predictable;
- make keyboard and touch interaction practical.

## 2.6 Minimize user effort

Prefer:

- sensible defaults;
- fewer clicks;
- prefilled forms;
- resumable workflows;
- visible next actions;
- preserving partially entered content after errors.

## 2.7 Honest status

A feature is not complete until it is implemented, tested, and verified in the real application.

Use these status labels in reports:

- `PASS`
- `FAIL`
- `BLOCKED`
- `NOT COVERED`
- `KNOWN LIMITATION`
- `MANUAL USER ACCEPTANCE`

---

# 3. Current Functional Scope

The following capabilities are considered currently implemented unless repository inspection proves otherwise:

- Home dashboard
  - today’s tasks;
  - next task;
  - completion progress;
  - remaining tasks;
  - wrong-answer review count;
  - learning-state recommendations.
- Weekly planning
  - create task;
  - assign date;
  - priority;
  - estimated duration;
  - notes;
  - start current task.
- Wrong-answer notebook
  - question;
  - attempted solution;
  - correct answer;
  - explanation;
  - subject;
  - chapter;
  - priority.
- AI wrong-answer analysis.
- Image-based quick wrong-answer draft capture.
- Daily mathematics wrong-answer review.
- Learning-state recording.
- AI conversations and history.
- AI provider settings and connection test.
- Learning statistics.
- Responsive interface.
- Notebook + rhythm timeline visual direction.
- Windows packaged application.
- Automated tests covering core, API, storage, static service, handwriting/image intake, responsive behavior, home, and navigation.

Repository inspection is authoritative. Do not assume a feature exists merely because it is listed here.

---

# 4. Known Limitations

The following items are not to be reported as completed unless explicitly implemented and verified:

- PDF-to-image conversion pipeline;
- multi-page PDF visual recognition;
- durable local attachment library for wrong-answer files;
- one-click weekly-plan creation from image/PDF/text;
- complete edit and delete UI for tasks and wrong answers;
- data export;
- one-click data clearing;
- multi-device synchronization;
- account system;
- public online deployment;
- guaranteed vision compatibility with arbitrary API relay providers.

Treat these as `KNOWN LIMITATION`, not `FAIL`, unless the current UI falsely claims they are available.

---

# 5. Architecture Boundaries

## 5.1 Preserve current architecture

Unless explicitly authorized, do not replace or redesign:

- Python local service;
- SQLite persistence;
- Windows packaging model;
- local-only networking;
- Windows Credential Manager integration;
- existing AI provider abstraction;
- current static frontend approach or framework;
- current routing model.

## 5.2 UI-only tasks

A UI-only task must not modify:

- database schema;
- API contracts;
- secret storage;
- local service binding;
- AI protocol behavior;
- storage semantics;
- Windows packaging behavior.

Allowed changes for UI-only work:

- HTML structure;
- CSS;
- design tokens;
- frontend component organization;
- responsive layout;
- accessibility;
- non-breaking interaction refinements;
- presentation-only mock data in isolated prototypes.

## 5.3 Database changes

Any schema change requires:

1. explicit authorization;
2. migration plan;
3. backup plan;
4. forward migration;
5. rollback or recovery plan;
6. tests using a temporary database;
7. verification with existing data;
8. documentation update.

Never edit a production SQLite file manually.

## 5.4 API changes

API changes must be backward compatible unless explicitly approved.

For every changed endpoint, document:

- method;
- path;
- request schema;
- response schema;
- status codes;
- error cases;
- compatibility impact;
- tests.

## 5.5 Windows application packaging

Do not overwrite a known-good packaged build during experimentation.

Use a separate output directory for test builds.

Verify:

- startup from a path containing Chinese characters;
- startup from a different current working directory;
- local service connection;
- database path;
- close behavior;
- residual processes;
- port-conflict behavior.

---

# 6. Repository Discovery Workflow

At the start of every non-trivial task:

1. Locate the repository root.
2. Read this file fully.
3. Read relevant README and docs.
4. Inspect the directory tree.
5. Identify:
   - frontend entry;
   - Python service entry;
   - SQLite initialization;
   - configuration files;
   - test directories;
   - packaging scripts;
   - generated outputs.
6. Find existing commands for:
   - install;
   - run;
   - lint;
   - formatting;
   - tests;
   - browser tests;
   - package/build.
7. Inspect current Git status.
8. Avoid modifying generated or packaged files unless required.

Do not stop after producing a plan. Continue into implementation unless a real blocker exists.

---

# 7. Design System

## 7.1 Visual direction

The dominant direction is:

> warm beige minimal learning notebook + daily rhythm timeline + Hermes AI learning assistant.

Visual references should be interpreted as principles, not copied pixel-for-pixel.

## 7.2 Product tone

The interface should feel:

- calm;
- warm;
- rational;
- precise;
- mature;
- trustworthy;
- personal;
- intelligent without being futuristic.

## 7.3 Avoid

Do not use:

- neon purple;
- cyberpunk visuals;
- black full-page backgrounds;
- large blue-purple gradients;
- excessive glassmorphism;
- oversized glowing AI orbs;
- childlike education illustrations;
- rainbow dashboards;
- colorful icon grids;
- heavy shadows;
- dense enterprise-admin layouts;
- course-marketplace aesthetics.

## 7.4 Default design tokens

Use shared variables rather than scattered hard-coded values.

```css
:root {
  --bg-canvas: #F2EEE6;
  --bg-sidebar: #E8E1D7;
  --bg-panel: #F8F5EF;
  --bg-card: #FCFAF6;
  --bg-card-muted: #EEE8DE;

  --text-primary: #24241F;
  --text-secondary: #706D65;
  --text-tertiary: #99948A;
  --text-inverse: #F8F5EE;

  --border-default: #DDD5C9;
  --border-subtle: rgba(68, 61, 50, 0.10);

  --accent-ink: #30312C;
  --accent-lime: #CBD58D;
  --accent-sage: #AAB79F;
  --accent-warm: #B59574;
  --accent-ai: #8C7663;

  --success: #7F9676;
  --warning: #BE9B5D;
  --danger: #AD756B;

  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 26px;

  --shadow-soft: 0 12px 35px rgba(70, 60, 46, 0.05);

  --transition-fast: 160ms ease;
  --transition-normal: 220ms ease;
}
```

Adjust only when needed for accessibility or consistency.

## 7.5 Typography

Prefer the project’s existing font stack.

If no stack exists:

```css
font-family:
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  "PingFang SC",
  "Microsoft YaHei",
  sans-serif;
```

Do not require network-hosted fonts.

## 7.6 Spacing and sizing

Use an 8px-based spacing system.

Recommended defaults:

- outer page margin: 24–32px;
- card gap: 16–20px;
- card padding: 20–24px;
- card radius: 18–22px;
- control height: 40–44px;
- border: 1px;
- animation: 160–240ms.

## 7.7 Hierarchy

Primary visual order on the home page:

1. Today’s core task;
2. Next action;
3. Daily rhythm timeline;
4. Learning recommendation;
5. Hermes AI insight;
6. Summary metrics.

Do not give all cards equal visual weight.

---

# 8. Main Layout Rules

## 8.1 Desktop

The home page may use four logical regions:

1. navigation sidebar;
2. daily timeline;
3. main workspace;
4. Hermes AI panel.

These regions should be separated by spacing, background shifts, and subtle borders rather than four heavy boxed cards.

## 8.2 Tablet

- sidebar may narrow;
- timeline may collapse;
- AI panel may become a drawer;
- touch targets must remain usable.

## 8.3 Mobile

- do not shrink the desktop four-column layout;
- use bottom navigation or a drawer;
- show core tasks first;
- render timeline as a vertical stream;
- show AI in a bottom sheet or dedicated view;
- prevent horizontal overflow;
- ensure forms and dialogs fit the viewport;
- keep the composer visible when the software keyboard appears.

## 8.4 Required viewport checks

For major UI changes verify:

- 1440×900
- 1366×768
- 1024×768
- 768×1024
- 390×844

---

# 9. Page-Specific Rules

## 9.1 Home

Must preserve:

- today’s tasks;
- next task;
- completion progress;
- remaining tasks;
- wrong-answer review count;
- learning-state recommendation.

The primary action should be obvious.

Do not fill the home page with charts.

## 9.2 Daily rhythm timeline

The timeline represents the user’s learning day, not a generic task list.

Use:

- thin vertical line;
- small nodes;
- compact time labels;
- clear current-task state;
- muted future items;
- completed state with text/icon, not color alone.

## 9.3 Weekly plan

- preserve date-based navigation;
- keep task creation lightweight;
- use muted priority indicators;
- use the current day as a visual anchor;
- do not imitate a corporate project-management board.

## 9.4 Wrong-answer notebook

Information hierarchy:

1. question;
2. user attempt;
3. correct answer;
4. explanation;
5. metadata.

AI analysis should look like a learning insight, not a chatbot response.

## 9.5 Daily review

- focus on one problem at a time;
- show progress;
- make result buttons touch-friendly;
- support:
  - mastered;
  - partially mastered;
  - still cannot solve;
  - careless;
  - skipped.
- persist results reliably.

## 9.6 Learning-state recording

- use low-stimulation controls;
- avoid medical framing;
- do not diagnose;
- preserve partially completed form data where practical;
- dialogs must remain closable.

## 9.7 AI conversation

- support new conversation;
- persist history;
- keep long messages readable;
- prevent cross-thread message contamination;
- preserve user messages on provider failure;
- never expose secrets.

## 9.8 AI settings

Clearly separate:

- base URL;
- protocol/provider type;
- model;
- secret;
- connection test.

Never display the full stored secret after saving.

## 9.9 Statistics

Statistics must produce actionable interpretation.

Avoid excessive charts.

Check for:

- `NaN`;
- `undefined`;
- negative counts;
- mismatched totals;
- stale values after new records.

---

# 10. Frontend Engineering

## 10.1 Reuse the current stack

Do not replace the frontend stack unless authorized.

Do not install a large framework solely to improve one page.

## 10.2 Component structure

Avoid monolithic files when the existing stack supports modularization.

Separate:

- data access;
- state;
- rendering;
- shared styles;
- dialogs;
- reusable controls.

## 10.3 CSS

- prefer shared variables;
- avoid duplicated declarations;
- avoid `!important` unless documented;
- keep selectors predictable;
- do not create page-specific color systems;
- preserve reduced-motion support.

## 10.4 JavaScript and TypeScript

- avoid `any` where TypeScript is used;
- handle null/undefined explicitly;
- validate external data;
- prevent duplicate submissions;
- restore button state after failures;
- preserve user input on recoverable errors.

## 10.5 Accessibility

All interactive UI must include:

- semantic elements where possible;
- keyboard operation;
- visible `focus-visible`;
- appropriate labels;
- `aria-label` for icon-only controls;
- sufficient contrast;
- status text beyond color;
- reduced-motion behavior;
- dialog focus management.

---

# 11. Python Service Rules

## 11.1 Local binding

The service must continue to listen only on the intended local interface unless explicitly changed.

## 11.2 Input validation

Validate:

- required fields;
- data types;
- string length;
- enumerations;
- dates;
- file types;
- file size;
- identifiers.

## 11.3 Error handling

Return clear, stable errors.

Do not expose:

- stack traces to normal users;
- filesystem secrets;
- API keys;
- credential-manager values;
- internal absolute paths unless necessary for debugging logs.

## 11.4 Logging

Logs should include enough context to diagnose failures but must redact:

- API keys;
- tokens;
- user private content where unnecessary;
- credential values.

## 11.5 File handling

- sanitize filenames;
- avoid path traversal;
- use dedicated storage directories;
- verify file types;
- do not assume file extension equals actual type;
- avoid overwriting user files.

---

# 12. SQLite Rules

## 12.1 Test isolation

Automated tests must use a temporary database.

Do not point tests to the user’s production database.

## 12.2 Transactions

Use transactions for multi-step changes that must be atomic.

## 12.3 Persistence validation

For any write workflow test:

1. perform UI or API action;
2. verify API response;
3. verify database row;
4. reload page;
5. restart service if applicable;
6. verify data still exists.

## 12.4 Time and dates

Date-sensitive tests must use a controlled clock or fixed test date.

Avoid tests that break around midnight.

## 12.5 Data integrity

Check:

- duplicate insertion;
- foreign-key consistency if used;
- ordering;
- Unicode;
- long text;
- empty values;
- restart persistence.

---

# 13. AI Integration Rules

## 13.1 Provider abstraction

Do not hard-code a single provider unless the architecture already requires it.

## 13.2 Testing

Automated tests should default to a deterministic mock provider.

Live provider calls are optional smoke tests and must be reported separately.

## 13.3 Failure handling

Test:

- missing configuration;
- invalid URL;
- invalid secret;
- timeout;
- empty response;
- malformed JSON;
- unsupported image input;
- provider returning text instead of expected structure;
- repeated clicks;
- cancellation or page navigation.

## 13.4 Vision capability

Do not assume every OpenAI-compatible relay supports image or PDF input.

The UI must report actual provider capability honestly.

## 13.5 Secret handling

Secrets must not be:

- stored in SQLite plaintext;
- stored in localStorage;
- committed to Git;
- printed in logs;
- shown in screenshots;
- included in test fixtures.

---

# 14. Image and PDF Intake

## 14.1 Images

For image quick-entry tests, use fixed non-private fixtures.

Verify:

- supported type;
- unsupported type;
- large image;
- provider unavailable;
- draft generation;
- editable draft;
- save;
- preservation of form content after failure.

## 14.2 PDF

Until the complete pipeline exists, only test current real behavior.

The UI must not imply that PDF recognition completed when only upload selection succeeded.

Known incomplete stages may include:

- PDF rendering to images;
- page-by-page vision;
- result merging;
- attachment persistence.

---

# 15. Testing Strategy

## 15.1 Required layers

Use the layers available in the repository:

- unit tests;
- API tests;
- storage tests;
- browser/end-to-end tests;
- packaging smoke tests;
- responsive checks.

## 15.2 Baseline first

Before code changes:

1. run existing tests;
2. record exact commands;
3. preserve failure output;
4. inspect skipped tests;
5. confirm the test database is isolated.

## 15.3 Critical end-to-end chain

For persisted user workflows, verify:

> UI action → API request → SQLite write → page reload → application/service restart → data remains correct.

## 15.4 Test data

Use obvious prefixes:

- `E2E_TEST_`
- `QA_TEST_`

Clean up only data created by the current test run.

## 15.5 Determinism

Tests must:

- be independent;
- avoid order dependence;
- use fixed clocks for date logic;
- use mocks for AI;
- avoid arbitrary sleep;
- wait for actual conditions;
- produce useful failure messages.

## 15.6 Repetition

Run newly added critical tests at least three times when checking for flakiness.

## 15.7 Do not cheat

Never:

- remove a failing test to pass;
- weaken assertions;
- catch all exceptions and continue;
- mark a failing path as skipped without justification;
- validate only HTTP 200;
- use production data.

---

# 16. Required Functional Regression Coverage

## 16.1 Home

Verify:

- empty state;
- one task;
- multiple tasks;
- all completed;
- progress count;
- remaining count;
- next-task selection;
- review count;
- refresh;
- restart persistence.

## 16.2 Weekly plan

Verify:

- create task;
- date assignment;
- priority;
- estimated duration;
- notes;
- date filtering;
- start task;
- home consistency;
- invalid title;
- long notes;
- refresh;
- restart.

## 16.3 Wrong-answer notebook

Verify:

- complete record;
- optional empty fields;
- required validation;
- Unicode/formulas;
- long text;
- metadata;
- list display;
- statistics integration;
- refresh;
- restart.

## 16.4 AI wrong-answer analysis

Verify:

- sufficient information;
- insufficient information;
- no fabricated certainty;
- provider unconfigured;
- invalid provider;
- timeout;
- malformed response;
- duplicate submission prevention;
- original content preservation.

## 16.5 Image quick entry

Verify:

- select image;
- valid format;
- invalid format;
- large image;
- draft fill;
- edit draft;
- save;
- unsupported provider;
- failure recovery;
- multiple upload state.

## 16.6 Daily review

Verify:

- maximum five;
- fewer than five;
- no questions;
- no unintended duplication;
- each result category;
- progress update;
- completion;
- statistics;
- restart persistence.

## 16.7 Learning state

Verify:

- all fields;
- reasonable empty handling;
- non-medical advice;
- home update;
- persistence;
- close button;
- Escape;
- overlay behavior;
- repeat open/close;
- body scroll restoration.

## 16.8 AI conversation

Verify:

- create conversation;
- send;
- save;
- history;
- switch;
- refresh;
- restart;
- empty message;
- provider failure;
- message preservation;
- no cross-thread mixing;
- secret redaction.

## 16.9 AI settings

Verify:

- URL;
- protocol;
- model;
- secret flow;
- connection success;
- failure;
- timeout;
- redisplay of non-secret values;
- no full-secret display;
- no plaintext SQLite/localStorage secret;
- log redaction.

## 16.10 Statistics

Verify:

- by subject;
- by chapter;
- by error type;
- totals;
- empty data;
- one record;
- multiple subjects;
- update after new data;
- refresh;
- restart;
- invalid numerical display.

## 16.11 Responsive UI

Verify all required viewports.

Check:

- no unintended horizontal scroll;
- usable navigation;
- visible controls;
- dialog fit;
- readable timeline;
- touch targets;
- AI composer visibility;
- no text clipping;
- no button overlap.

## 16.12 Windows package

Verify:

- start;
- correct page;
- local service;
- SQLite;
- close;
- repeat start;
- Chinese path;
- different working directory;
- correct data directory;
- service missing;
- port conflict.

---

# 17. Bug-Fix Workflow

For every defect:

1. Record reproduction steps.
2. Assign severity:
   - Critical;
   - High;
   - Medium;
   - Low.
3. Record expected behavior.
4. Record actual behavior.
5. Save evidence.
6. Identify likely files.
7. Add a failing regression test when practical.
8. Confirm the test fails before the fix.
9. Apply the smallest fix.
10. Confirm the new test passes.
11. Run the full relevant regression suite.
12. Report any remaining risk.

Do not fix unrelated issues in the same change.

---

# 18. Change Scope and Refactoring

## 18.1 Smallest viable change

Prefer a focused patch over a broad rewrite.

## 18.2 Refactoring authorization

Refactoring is allowed only when:

- it is needed for the requested change;
- behavior is preserved;
- tests exist;
- the scope is explained;
- unrelated modules remain untouched.

## 18.3 Generated files

Do not manually edit generated output when source files exist.

If the packaged HTML is generated, modify its source and rebuild.

If the repository uses the output file as the source of truth, document that before editing.

---

# 19. Git and Commit Rules

## 19.1 Working tree

Before changes:

- inspect `git status`;
- do not overwrite unrelated user changes;
- do not reset or clean without permission.

## 19.2 Commit messages

Use conventional, descriptive messages where commits are requested:

- `feat(ui): refine daily timeline`
- `fix(storage): preserve review status after restart`
- `test(e2e): cover wrong-answer creation`
- `docs: document local AI configuration`
- `refactor(frontend): extract shared dialog styles`

Avoid:

- `fix`
- `update`
- `misc`
- `changes`

## 19.3 Secrets and artifacts

Never commit:

- secrets;
- production database;
- credential exports;
- user learning data;
- temporary screenshots containing private content;
- build caches;
- test temp files.

---

# 20. Documentation Rules

Update documentation when changing:

- setup;
- commands;
- database;
- API;
- packaging;
- configuration;
- known limitations;
- user-visible workflows.

Documentation must distinguish:

- implemented;
- experimental;
- planned;
- known limitation.

---

# 21. Definition of Done

A task is complete only when all applicable items are satisfied.

## 21.1 Implementation

- requested behavior exists;
- change scope is controlled;
- no unrelated functionality is removed;
- errors are handled;
- user data is preserved.

## 21.2 Verification

- baseline was recorded;
- relevant tests pass;
- new behavior is covered;
- real application was exercised;
- persistence was checked when relevant;
- responsive layouts were checked for UI work;
- package was checked when packaging was affected.

## 21.3 Quality

- no secret leakage;
- no production database misuse;
- no silent errors;
- no false completion claims;
- accessibility preserved;
- known limitations remain honest.

## 21.4 Report

The final report must include:

1. actual work completed;
2. files modified;
3. commands executed;
4. test results;
5. manual verification;
6. screenshots/log locations where applicable;
7. failures or blockers;
8. known limitations;
9. remaining risks.

---

# 22. Required Final Response Format

For implementation tasks, return:

## Completed

A concise description of actual changes.

## Files changed

List files and purpose.

## Verification

Include exact commands and actual results.

## Manual checks

Describe real application checks.

## Known limitations

Do not hide them.

## Risks / next step

Only the most relevant next action.

Do not say:

- “everything should work”;
- “all tests passed” without counts and commands;
- “implemented” when only scaffolding exists;
- “verified” when only source code was inspected.

---

# 23. Task Modes

Every task should be interpreted as one of these modes.

## 23.1 Audit mode

- inspect;
- test;
- report;
- do not change business behavior unless needed to make tests runnable.

## 23.2 UI mode

- preserve API and database;
- verify responsive behavior;
- use real browser rendering;
- produce screenshots where tooling exists.

## 23.3 Bug-fix mode

- reproduce;
- failing test;
- minimal fix;
- regression test.

## 23.4 Feature mode

- confirm scope;
- preserve architecture;
- implement;
- test;
- document.

## 23.5 Architecture mode

- no implementation until boundaries, migration, risks, and rollback are documented;
- architecture changes require explicit approval.

## 23.6 Release mode

- clean build;
- full tests;
- package smoke test;
- version/report;
- no production data in artifacts.

---

# 24. Hermes-Specific Product Constraints

## 24.1 Planner constraints

Where the product generates or highlights study tasks:

- core tasks ≤ 2;
- candidate tasks ≤ 3;
- preserve buffer time;
- reduce difficulty after repeated failure;
- reduce new work when wrong-answer density is high;
- use low-resistance tasks when fatigue is high.

Do not silently change these rules.

## 24.2 Mastery language

Do not equate “viewed the answer” with mastery.

Review result labels must preserve their actual meaning.

## 24.3 Non-medical guidance

Learning-state advice must remain non-medical and non-diagnostic.

Use language such as:

- “consider reducing task difficulty”;
- “take a short break”;
- “start with a low-resistance review.”

Do not diagnose disorders or health conditions.

## 24.4 Evidence-first AI

When analyzing a wrong answer, prefer:

- the question;
- the user’s attempted process;
- the correct answer;
- the explanation;
- subject/chapter;
- previous similar mistakes.

If these are missing, say what is needed.

---

# 25. Security Checklist

Before completion, check:

- [ ] local server binding remains local;
- [ ] no secret in logs;
- [ ] no secret in frontend storage;
- [ ] no production DB in tests;
- [ ] no path traversal in uploads;
- [ ] no unsafe file overwrite;
- [ ] no private data in screenshots;
- [ ] no debug endpoint exposing internals;
- [ ] no raw stack trace shown to normal users;
- [ ] credential-manager integration preserved.

---

# 26. UI Review Checklist

For major visual changes:

- [ ] warm beige notebook direction is obvious;
- [ ] not a generic SaaS dashboard;
- [ ] today’s task is the first visual priority;
- [ ] daily timeline reads as a rhythm, not a card list;
- [ ] Hermes AI looks like a learning assistant, not support chat;
- [ ] spacing and typography are consistent;
- [ ] cards are not overused;
- [ ] shadows are subtle;
- [ ] icons are consistent and restrained;
- [ ] keyboard focus is visible;
- [ ] reduced motion is respected;
- [ ] all required viewports checked;
- [ ] dialogs remain closable;
- [ ] no horizontal overflow;
- [ ] no text clipping;
- [ ] screenshots reflect the real application.

---

# 27. QA Artifact Layout

When a task requires a QA report, use a dedicated directory such as:

```text
artifacts/qa/
├── test-matrix.md
├── regression-report.md
├── commands.log
├── automated-tests.log
├── screenshots/
├── api-results/
├── database-checks/
└── known-limitations.md
```

Never include:

- API keys;
- Windows credential contents;
- user private learning data;
- production database copies.

---

# 28. Agent Collaboration

When multiple agents are used:

- assign one clear owner per file or subsystem;
- do not let agents make overlapping edits without coordination;
- separate implementation and review roles;
- require the reviewer to inspect actual diffs and test results;
- merge only after integration tests;
- the coordinating agent owns the final truthfulness of the report.

Suggested roles:

- Implementation Agent;
- Test Agent;
- UI Review Agent;
- Security Review Agent;
- Integration Agent.

Sub-agents must follow this file.

---

# 29. Escalation Conditions

Stop and ask for clarification or approval when:

- the task requires deleting user data;
- a migration may be irreversible;
- the production database cannot be isolated;
- an architectural change is required;
- a secret-handling change is required;
- the Windows package would be overwritten;
- existing user changes would be lost;
- the requested behavior conflicts with known product principles;
- the repository entry point cannot be identified reliably.

Do not ask for confirmation for routine, reversible, clearly scoped work.

---

# 30. Final Standing Instruction

Build Hermes as a durable learning system, not as a sequence of demos.

Prefer:

- evidence over assumptions;
- minimal changes over rewrites;
- verified behavior over plausible code;
- honest limitations over false completion;
- calm product quality over visual novelty;
- persistent learning value over feature volume.

---

# 31. Parallel Worktree Governance

This repository runs parallel feature development using Git worktrees. The standing rules below apply to every worktree and every agent. They describe responsibilities and boundaries; they do not hard-code a temporary commit as a permanent rule.

## 31.1 Authoritative state

- Git commits and the status documents in each worktree root are the authoritative source of project state.
- Conversation summaries, chat logs, or external notes are not authoritative.
- The stable integration baseline is the `ui/hermes-ui-2-program` branch.

## 31.2 Isolation model

- Each task uses its own branch and its own worktree.
- Do not develop directly in `ui/hermes-ui-2-program`; it is the stable integration baseline, not a task worktree.
- Do not modify the `rescue/mixed-work-20260722` worktree or branch.
- Do not auto-merge task branches. Merges into the stable baseline are coordinated explicitly.
- Do not overwrite historical candidate packages, Git bundles, or migration packages.

## 31.3 Testing discipline

- Tests must never use the user's real production database; use an isolated temporary database (see §12.1).
- Do not invoke a real AI provider without separate explicit authorization; use deterministic mocks by default (see §13.2).

## 31.4 Branch boundaries

- Feature branches must not modify `ui/hermes-learning-journal-v2`.
- UI branches must not unilaterally change the database schema, API contracts, or business rules (see §5.2).

## 31.5 Honest reporting

- Do not mark any check `PASS` unless it was actually executed.
- Use the status labels defined in §2.7: `PASS`, `FAIL`, `BLOCKED`, `NOT COVERED`, `KNOWN LIMITATION`, `MANUAL USER ACCEPTANCE`.
- Every task must produce a `HANDOFF.md` at its worktree root.

## 31.6 Pre-change confirmation

Before modifying any worktree, confirm:

```
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git status --short
```

## 31.7 Missing governance file

If the current worktree root does not contain an `AGENTS.md`, stop all formal development and report. Do not invent or copy a second authoritative state file.
