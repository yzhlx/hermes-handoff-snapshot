# PHASE-0-AUDIT.md — Hermes Cloud Core V1

> Phase 0 is serial and was executed by the total-coordination agent before any product
> code was modified. This document records what was actually verified in the repository,
> not assumptions.

## 0.1 Repository governance check (actual commands run)

Run from `agent-governance-sync-v1/` (the canonical Learning OS repo containing the
`outputs/` product code and the authoritative governance files):

| Command | Result |
|---------|--------|
| `git rev-parse --show-toplevel` | `F:/Users/user/Documents/learning os-worktrees/agent-governance-sync-v1` |
| `git branch --show-current` | `chore/agent-governance-sync-v1` |
| `git rev-parse --short HEAD` | `b7f6989` |
| `git status --short` | clean (no uncommitted changes on the baseline) |
| `git log --oneline -12` | product branch tip sequence below |
| `git worktree list --porcelain` | 20 registered worktrees (this task added `cloud-hermes-core-v1`) |

### Baseline resolution (important)

- `CURRENT-STATE.md` declares the authoritative stable HEAD as **`9b18bc3`**
  (`merge(lifecycle): add user-accessible graceful shutdown`).
- The actual tip of the stable product branch `ui/hermes-ui-2-program` is **`058e0a8`**
  (`merge(agent): establish shared worktree instructions`).
- Verified ancestry: `9b18bc3` IS an ancestor of `058e0a8` (`git merge-base --is-ancestor`
  returned ANCESTOR_OK). `058e0a8` is therefore strictly newer and already contains the
  documented stable merge.
- Decision: this round branches from **`058e0a8`** — the real latest stable HEAD of the
  product branch — which subsumes `9b18bc3`. This satisfies "branch from the real latest
  HEAD" and avoids blindly hardcoding the older `9b18bc3` constant. The governance file was
  stale relative to the actual branch tip (the agent-instructions merge landed after the
  state file was written).

### Governance files read (real content)

- `AGENTS.md` (33 KB) — agent governance, no-faking rule §15.7, worktree instructions.
- `CURRENT-STATE.md` — stable HEAD `9b18bc3`, graceful-exit + canvas merged, EXE verified.
- `TASK-QUEUE.md` — current task list.
- `RELEASE-STATUS.md` — release gating.
- `learning-domain-event-model-v1/` — Learning Domain Event Model (event shapes reused).
- `learning-os-store.py` `EventStore` — already append-only with a trigger that aborts on
  UPDATE/DELETE. The cloud event store reuses this exact philosophy and extends the fields
  to the V1 contract (correlation_id, causation_id, idempotency_key, actor, source,
  payload_version, artifact_refs, metadata).

## 0.2 Current call chain (verified in source)

```
learning-os-app.js  (API = http://127.0.0.1:4174/api/v2)
   └─ POST /api/v2/chats/{id}/messages   {role:"user", content}
learning-os-api.py  (BaseHTTPRequestHandler)
   └─ service.ai.answer_chat(list_chat_messages(chat_id))
learning-os-ai.py  AIGateway.answer_chat()
   └─ generate_text(messages, max_tokens)
        └─ _request(protocol, base_url, headers{Authorization: Bearer <local-cred-key>}, payload)
             └─ urllib POST -> Provider (e.g. deepkey.top / cctq.ai) /v1/chat/completions
learning-os-store.py  chat_messages (SQLite, local)
```

Evidence:
- `learning-os-app.js:1` `const API = 'http://127.0.0.1:4174/api/v2';`
- `learning-os-app.js:293` chat form posts to `/chats/${id}/messages`.
- `learning-os-api.py:1093-1112` chat handler calls `service.ai.answer_chat(...)` then
  `core.add_chat_message(chat_id, {role:"assistant", content: answer})`.
- `learning-os-ai.py:208-363` `AIGateway` reads the key from
  `WindowsCredentialStore` (local Windows credential manager) and calls the provider
  directly. `HERMES_SYSTEM_INSTRUCTIONS` is only a system-prompt string (line 21-26).

### What is NOT in the current chain (confirmed)

No Hermes Gateway, no Hermes Runtime, no Profile resolution, no Memory retrieval, no Skill
router, no Tool Router, no Event Store writeback, no Master, no Critic, no Execution Node,
and no `hermes_run_id`. Hermes currently appears only as: `HERMES_SYSTEM_INSTRUCTIONS`
string, UI copy ("Hermes 正在整理"), and the product name. This matches the task's premise
exactly. Therefore this task establishes the **first real cloud Hermes main call chain**.

## 0.3 Cloud runtime inventory (Phase 0 §5.2)

Mandated checks (`systemctl`, `docker`, `ss`, `ps`, `crontab`, port scan, nginx/caddy) were
attempted from this environment. Results, honestly recorded:

| Check | Result |
|-------|--------|
| `systemctl list-units` | not applicable — this is a Windows 10/11 workstation, no systemd |
| `docker ps` / `docker compose ls` | Docker Desktop present? — no running Hermes/learning container found; no cloud runtime |
| `ss -lntp` | N/A on Windows; local listeners are the Windows Python Learning OS service on 127.0.0.1:4173/4174 only |
| `ps aux` | only local Learning OS Python processes; no `hermes`/`gateway`/`feishu` cloud process |
| `crontab -l` | N/A (Windows Task Scheduler, not cron); no Hermes cron |
| Keyword scan (`hermes`,`gateway`,`master`,`profile`,`memory`,`skill`,`mcp`,`feishu`,`provider`,`deepkey`) | only matched the **local** `learning-os-ai.py` / `learning-os-app.js` (UI copy + local provider). No cloud Hermes service, no Feishu bot entry, no cloud memory/skill/MCP. |

**Conclusion:** No reusable cloud Hermes Runtime exists in any accessible environment. Per
Phase 0 §5.2, when the "so-called cloud Hermes is only another direct-provider chat shell"
(or absent), we implement the **minimum runnable Cloud Hermes Core** from scratch. That is
what this task does. SSH/cloud-host access is unavailable from this machine, so the actual
public-cloud deployment is tracked as `BLOCKED_CLOUD_ACCESS` (see FINAL-REPORT.md) while the
service, containerization, deployment scripts, and full local integration tests are real.

## 0.4 Frozen V1 API contract

See `API-CONTRACT.md`. Frozen and MUST NOT change without re-running Phase 0 sign-off.

## 0.5 Ownership & worktrees

See `WORKTREE-OWNERSHIP.md` and `DATA-OWNERSHIP.md`. Created branches (all from `058e0a8`):
`feat/cloud-hermes-gateway-v1`, `feat/cloud-hermes-memory-events-v1`,
`feat/learning-os-cloud-hermes-client-v1`, `test/cloud-hermes-security-qa-v1`,
`integration/cloud-hermes-core-v1` (working worktree at
`F:/Users/user/Documents/learning os-worktrees/cloud-hermes-core-v1`).

## 0.6 Honesty notes

- No claim is made that a cloud Hermes already existed. It did not.
- No claim is made that the public-cloud deployment succeeded. It is BLOCKED here; the
  local deployment smoke + rollback smoke are real and are documented separately.
- Mock Provider is used for deterministic tests; the real Provider is behind an env-var
  abstraction and only smoke-tested with explicit credentials (marked UNEXECUTED here
  because no key is available in this environment).
