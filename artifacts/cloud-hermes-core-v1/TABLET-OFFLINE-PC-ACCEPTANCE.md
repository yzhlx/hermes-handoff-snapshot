# Tablet-Offline / PC-Off Acceptance — Hermes Cloud Core V1

**Honesty rule (from task):** cloud capabilities may only be claimed when the **PC (cloud host)
is actually ON and reachable**. A tablet session that is merely *connected to the local app
while the PC is on* must never be presented as "PC off / cloud unavailable". If the PC is off,
the client must explicitly state cloud is unavailable; it may offer a clearly-labeled **local**
fallback but must not impersonate cloud results.

**Date:** 2026-07-22.

---

## 1. Two Operating Modes (contract, enforced in code)

| Mode | Trigger | Cloud Hermes behavior | Client obligation |
|---|---|---|---|
| **PC ON (cloud reachable)** | `HERMES_CLOUD_MODE=cloud` and host responds | Real `hermes_run_id`, real events, real memory retrieval | Show "本轮依据" (run/memory/events) from the cloud response |
| **PC OFF (cloud unreachable)** | host does not respond / `HERMES_CLOUD_MODE=off` | Cloud calls fail fast | Show "云端不可用"; do NOT fake a run id; optional **local** mode must be labeled |

## 2. What Was Realized & Verified (PC-ON path)

- `web/index.html` + `web/app.js` + `web/style.css`: responsive tablet/web UI served
  **same-origin** from the cloud service at `GET /web` (`app.py`), so no cross-origin token leak.
- Login modal → `POST /auth/login` → stores bearer token in `sessionStorage` (**not**
  `localStorage`), satisfying the "no token in localStorage" boundary.
- "本轮依据" panel renders the **real** `hermes_run_id`, `memory_refs`, and `event_ids` returned
  by the cloud — proven by `api-results/run.json` and the smoke (events:
  `HermesRunStarted, ContextRetrieved, RoleConversationCompleted, ProviderInvocationCompleted`).
- `execution-nodes` endpoint lets a tablet **enqueue a local command**; the node reports
  `status: offline, cloud_chat_available: true` when no execution node is connected, and chat
  is never blocked by that (verified in smoke: chat returned 200 with execution node offline).
- Distinct error codes (`AUTH_REQUIRED`, `AUTH_INVALID`, `RATE_LIMITED`, `VALIDATION_ERROR`,
  `CONFLICT`, `INTERNAL_ERROR`) are surfaced to the UI so the tablet can show the right message
  instead of a generic failure.

## 3. PC-OFF Acceptance Criteria (must hold before calling this DONE)

1. **No cloud impersonation:** when the cloud host is unreachable, the client MUST NOT display a
   `hermes_run_id`, memory refs, or events that did not come from the cloud.
2. **Explicit state:** UI shows an unambiguous "云端不可用 / Cloud unavailable" state (not a
   silent retry that looks like success).
3. **No silent fallback:** if a local fallback answers, the response is clearly labeled "本地模式
   (local)" and is never attributed to Hermes Cloud.
4. **Local command queue:** a command enqueued while PC-off is stored and flushed when the cloud
   (or its execution node) reconnects — not lost, not double-executed (lease-based queue).
5. **Token hygiene:** the bearer token is never written to `localStorage` and is cleared on tab
   close (sessionStorage).

## 4. Manual Test Plan (PC-OFF) — NOT auto-executed here

> A physical tablet / second browser was not available in this sandbox, so the PC-OFF path is
> accepted at the **contract + code** level and ships with this manual plan. It is NOT claimed as
> executed.

1. Start the cloud service; from a browser set `HERMES_CLOUD_MODE=cloud` and log in → confirm
   "本轮依据" shows a real run id (PC-ON evidence already captured in `api-results/`).
2. Stop the cloud service (simulate PC off). Reload the tablet UI and send a message → expect
   "云端不可用" and **no** run id shown.
3. With cloud off, enqueue a local command via `POST /execution-nodes` → expect it queued,
   `status: pending`.
4. Restart the cloud service → expect the queued command to be claimed once (lease prevents
   double execution) and completed.
5. Confirm `sessionStorage` has the token and `localStorage` does not (DevTools → Application).

## 5. Evidence Files

- `api-results/chat.json`, `run.json`, `execution-nodes.json` — PC-ON real payloads.
- `logs/deploy-smoke.log` — full PC-ON endpoint exercise.
- `web/app.js` — token-in-sessionStorage, "本轮依据" rendering, explicit error handling.
