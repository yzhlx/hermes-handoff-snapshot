# Learning OS Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current generic dashboard treatment with an intentional, responsive Learning OS interface that keeps today's next action visually primary and makes every modal reliably closable.

**Architecture:** Keep the existing Python API, SQLite models, and page identifiers unchanged. First create three static HTML design directions in `design-demos/` using the current empty-state content; after the user selects a direction, apply its token system and layout rules to the production HTML/CSS, then standardize dialog lifecycle behavior in the existing JavaScript.

**Tech Stack:** Native HTML, CSS, and browser JavaScript; Python standard-library tests; Playwright browser checks.

---

### Task 1: Deliver comparable visual directions

**Files:**
- Create: `design-demos/learning-os-execution-desk.html`
- Create: `design-demos/learning-os-study-notebook.html`
- Create: `design-demos/learning-os-rhythm-calendar.html`

- [ ] **Step 1: Build the three desktop-first, responsive HTML directions**

Each file must use actual product terms (`今日`, `周计划`, `错题专栏`, `每日复习`, `AI 对话`, `记录状态`) and clear empty states (`今天尚未安排任务`, `状态尚未记录`), not fabricated progress metrics. It must include a one-line assumptions comment, a visible “记录状态” button, and a narrow-screen media query.

- [ ] **Step 2: Screenshot all three directions at 1440x900 and 375x667**

Run: `npx playwright screenshot --viewport-size=1440,900 file:///.../design-demos/<file>.html <file>-desktop.png`

Expected: six screenshots, each readable at its intended viewport with no horizontal overflow.

- [ ] **Step 3: Inspect the screenshots and select no production direction yet**

Verify that the three directions differ in hierarchy and layout, not merely color. Present the three desktop screenshots to the user and wait for a choice or a requested mix.

### Task 2: Reproduce and fix the status-dialog close failure

**Files:**
- Modify: `work/presentations/learning-os-ui/tmp/test_learning_os_app.py`
- Modify: `outputs/learning-os-app.html`
- Modify: `outputs/learning-os-app.js`
- Modify: `outputs/learning-os-app.css`

- [ ] **Step 1: Write a failing browser regression test**

Add a test which loads the app, opens `#statusDialog` with `#statusButton`, clicks an explicit close control, and asserts `document.querySelector('#statusDialog').open is False`.

- [ ] **Step 2: Run the test and verify the failure**

Run: `C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe work\presentations\learning-os-ui\tmp\test_learning_os_app.py`

Expected: FAIL because the current close button submits `#statusForm`, whose submit handler calls `preventDefault()`.

- [ ] **Step 3: Make dialog close controls explicit**

Replace the status close button with `<button id="closeStatusDialog" type="button">关闭</button>`, attach a click listener that calls `#statusDialog.close()`, and retain the existing form submit handler only for saving. Add shared dialog CSS so close controls stay visible at mobile widths.

- [ ] **Step 4: Verify the regression test passes**

Run the same command. Expected: PASS.

### Task 3: Apply the selected visual system without changing behavior

**Files:**
- Modify: `outputs/learning-os-app.html`
- Modify: `outputs/learning-os-app.css`
- Modify: `outputs/learning-os-app.js`

- [ ] **Step 1: Preserve selectors and page identifiers used by the current script**

Before changing markup, list all `#id`, `[data-page]`, and `[data-view]` selectors referenced by `learning-os-app.js`. Keep each one or update its JavaScript reference in the same change.

- [ ] **Step 2: Apply the selected tokens and page hierarchy**

Use the chosen direction’s typography, spacing, navigation, controls, dialogs, and responsive rules. The Today page must show the current task first, then the next tasks and status; secondary metrics must not compete with the current task.

- [ ] **Step 3: Test page navigation and dialog behavior**

Extend the app browser test to open each navigation page, open and close the status dialog, and open and close quick error entry. Expected: no page errors and all dialogs can close without submitting data.

### Task 4: Verify and package only after the visual work is accepted

**Files:**
- Modify if required: `outputs/learning-os-desktop.py`
- Regenerate: `package/学习 OS/`

- [ ] **Step 1: Run the complete existing regression suite**

Run the core, API, static-server, handwriting, world-canvas, and Learning OS app tests using the bundled Python runtime.

- [ ] **Step 2: Build the local Windows package**

Run the existing PyInstaller/package command from the project documentation, then launch the generated executable once to confirm it opens the local app.

- [ ] **Step 3: Report only verified results**

Summarize the selected visual direction, fixed dialog behavior, responsive viewport checks, and the package location.
