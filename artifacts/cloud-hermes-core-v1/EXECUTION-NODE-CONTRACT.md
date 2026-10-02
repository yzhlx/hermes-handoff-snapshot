# EXECUTION-NODE-CONTRACT.md

## Purpose
Local Windows PC acts as an OPTIONAL Execution Node. Commands needing Obsidian/Anki/local
files are queued; the chat response does not wait for them.

## Entities (Track B)
- `execution_nodes(id, device_id, last_seen, status, capabilities_json)`
- `execution_commands(id, device_id, command_type, payload_json, status, idempotency_key,
  lease_token, lease_expires_at, retry_count, result_json, created_at, completed_at)`

## Lifecycle
```
(pc online)  node registers/heartbeats -> status=online
client/run   enqueues command -> status=pending
node         claims (lease) -> status=claimed -> running
node         completes/fails -> completed/failed (+ result_json)
(pc offline) commands stay pending; cloud chat unaffected
```

## Rules
- `command_id` unique (UUID); `idempotency_key` dedupes re-enqueues.
- Lease: `lease_token` + `lease_expires_at` (e.g. 5 min). Only the lease holder may progress
  the command; expired lease can be re-claimed (no duplicate execution because status is the
  guard and writes are atomic).
- `retry_count` capped (default 3); permanent failure after cap.
- Result回传 via `POST /api/hermes/v1/execution-nodes/{device_id}/commands/{id}/result`
  (authenticated node).
- Cloud chat MUST NOT depend on a command completing; a pending command yields a
  `LOCAL_EXECUTION_PENDING` warning in the chat response, not a failure.

## Acceptance
- Local node offline -> `GET /execution-nodes` returns `{status:"offline", cloud_chat_available:true}`.
- Node claims same command twice (simulated) -> second claim is a no-op (no re-execution).
- Pending command does not block a chat response (verified in integration test).
