# API-CONTRACT.md  (FROZEN — V1)

Frozen in Phase 0. Changing any field requires re-running Phase 0 sign-off.

All endpoints are under base `/api/hermes/v1`. All request/response bodies are JSON
(`Content-Type: application/json`). Auth: `Authorization: Bearer <user-session-token>`
(also accepts session cookie for browser SSO). Idempotent writes carry
`Idempotency-Key: <client-generated-uuid>`.

## Health

`GET /api/hermes/v1/health` (no auth)

```json
{
  "status": "ok",
  "service": "hermes-cloud-core",
  "version": "1",
  "provider_configured": true,
  "database_available": true,
  "memory_available": true,
  "event_store_available": true,
  "execution_node_required": false
}
```

MUST NOT return: secrets, internal file paths, DB connection strings, private learning data.

## Chat

`POST /api/hermes/v1/chat`
Headers: `Authorization: Bearer <token>`, `Idempotency-Key: <uuid>`

Request:
```json
{
  "conversation_id": "conv_optional",
  "role_id": "master",
  "message": "用户消息",
  "artifact_refs": [],
  "client": { "type": "web", "device_id": "opaque-device-id", "client_version": "v1" }
}
```

Response (200):
```json
{
  "reply": "模型最终回复",
  "conversation_id": "conv_xxx",
  "message_id": "msg_xxx",
  "hermes_run_id": "run_xxx",
  "role_id": "master",
  "memory_refs": [],
  "event_ids": ["evt_xxx"],
  "tool_calls": [],
  "warnings": []
}
```

Rules:
- `hermes_run_id` REQUIRED (server-minted; client may not forge it).
- `conversation_id` REQUIRED in response (server creates if absent).
- At least one session event (RoleConversationCompleted) is appended.
- Duplicate `Idempotency-Key` MUST NOT re-call Provider nor re-write a task.
- Error responses carry a stable `code` (see AUTH-CONTRACT error table); raw stack never
  returned to normal users.

## Run query

`GET /api/hermes/v1/runs/{hermes_run_id}` (auth)

Safe summary only:
```json
{
  "hermes_run_id": "run_xxx",
  "status": "completed",
  "role_id": "master",
  "context_retrieval": { "performed": true, "memory_count": 3 },
  "provider_call": { "performed": true, "provider_name": "configured-provider", "model": "configured-model" },
  "writeback": { "event_count": 2, "memory_candidate_count": 1 },
  "tool_calls": []
}
```

MUST NOT return full system prompt, secrets, or unnecessary private data.

## Conversations

`GET /api/hermes/v1/conversations` -> `{ "items": [ {conversation summary} ] }`
`GET /api/hermes/v1/conversations/{conversation_id}` -> full conversation + messages

## Tasks

`GET /api/hermes/v1/tasks` -> list
`POST /api/hermes/v1/tasks` (Idempotency-Key) -> create `{title, description, status}`

V1 = minimal safe cloud task CRUD (no full Kanban).

## Execution nodes

`GET /api/hermes/v1/execution-nodes`

When local node offline:
```json
{ "status": "offline", "cloud_chat_available": true }
```

## Auth endpoints (Track D)

`POST /api/hermes/v1/auth/login` `{username, password}` -> sets session cookie + returns
`{access_token}` (bearer). `POST /api/hermes/v1/auth/logout`. `GET /api/hermes/v1/auth/me`.
One-time admin init via `ADMIN_INIT_TOKEN` env (sets admin password on first boot).

## Stable error codes (used across all responses)

`HERMES_UNAVAILABLE, AUTH_REQUIRED, AUTH_EXPIRED, AUTH_INVALID, PROVIDER_UNAVAILABLE,
PROVIDER_TIMEOUT, PROVIDER_INVALID_RESPONSE, MEMORY_UNAVAILABLE, WRITEBACK_FAILED,
RATE_LIMITED, REQUEST_TIMEOUT, INVALID_RESPONSE, LOCAL_EXECUTION_PENDING, VALIDATION_ERROR,
CONFLICT, NOT_FOUND, INTERNAL_ERROR`. Never collapse all errors to a single generic message.
