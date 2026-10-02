# TARGET-CALL-CHAIN.md

Target call chain after Hermes Cloud Core V1 is integrated. Frozen with API-CONTRACT.md.

```
Windows Learning OS ─┐
Tablet web ──────────┼─(HTTPS Bearer token + Idempotency-Key)─> Cloud Hermes Gateway
Phone web ───────────┤        POST /api/hermes/v1/chat
Feishu entry ────────┘
                                |
                                v
                    [Auth] validate session/bearer token (Track A+D)
                                |
                                v
                    [Idempotency] check Idempotency-Key (Track B)
                                |
                                v
                    [Run] HermesRunCreated  (hermes_run_id minted server-side)
                                |
                                v
                    [Master] resolve role/profile (default role=master)
                                |
                                v
                    [Context] Memory retrieval (approved memory_items by namespace)
                                |                         (Track B)
                                v
                    [Provider] invoke configured provider (key from env/secret mgr)
                                |                         (Track A, abstraction)
                                v
                    [Validate] response non-empty, schema-valid
                                |
                                v
                    [Writeback] append events (RoleConversationCompleted, etc.)
                                |  submit MemoryCandidate (model cannot write memory directly)
                                |  write conversation + messages
                                v
                    [Run] HermesRunCompleted
                                |
                                v
                    HTTP 200 { reply, conversation_id, message_id, hermes_run_id,
                               role_id, memory_refs, event_ids, tool_calls, warnings }
```

## Offline-PC guarantees

- The Cloud Hermes service runs independently of the Windows PC. When the PC is off,
  tablet/phone still reach Cloud Hermes over HTTPS; AI chat, cloud sessions, cloud long-term
  memory, cloud history, cloud tasks, Hermes Run tracking, Event append, scheduled-task
  infra, and Provider calls all continue.
- Commands that need Obsidian/Anki/local files are enqueued into `execution_commands`
  with `status=pending` and do NOT block the chat response. They are claimed later by the
  Windows Execution Node when it reconnects (pull model; cloud never scans the LAN).

## No silent fallback

- If Hermes is unavailable in production -> respond `HERMES_UNAVAILABLE` (no client
  fallthrough to direct Provider).
- `AI_TRANSPORT=direct` is permitted ONLY in explicit development mode (default off, UI
  labelled "Direct Provider Development Mode"), never in production builds.
