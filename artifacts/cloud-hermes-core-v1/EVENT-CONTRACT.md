# EVENT-CONTRACT.md

## Store (Track B) — append-only
`events` table columns (reuses learning-os-store EventStore philosophy + V1 fields):

```
sequence        INTEGER PK AUTOINCREMENT
event_id        TEXT UNIQUE NOT NULL
event_type      TEXT NOT NULL
aggregate_type  TEXT NOT NULL
aggregate_id    TEXT NOT NULL
occurred_at     TEXT NOT NULL
recorded_at     TEXT NOT NULL
actor           TEXT
source          TEXT
idempotency_key TEXT
causation_id    TEXT
correlation_id  TEXT          -- points to hermes_run_id
payload_version INTEGER
payload_json    TEXT NOT NULL
artifact_refs   TEXT          -- JSON array
metadata_json   TEXT
```

Triggers `events_no_update` / `events_no_delete` ABORT on UPDATE/DELETE (verified by
`tests/test_storage.py`). Corrections append a compensating/superseding event.

## Event types (minimum V1)
- `HermesRunStarted`
- `ContextRetrieved`
- `ProviderInvocationCompleted`
- `RoleConversationCompleted`   (>=1 per chat)
- `MemoryCandidateCreated`
- `MemoryPromoted`
- `TaskCreated`
- `ExecutionCommandQueued`
- `ExecutionCommandCompleted`

## Identity rules
- `event_id` = server-minted UUID; unique.
- `correlation_id` = the `hermes_run_id` that produced the event.
- `idempotency_key` = client idempotency key when the event is the result of an idempotent
  write; reused events share the key so duplicate requests cannot double-append.
- `payload` is a JSON object; never contains secrets or raw system prompts.

## Acceptance proof
- A chat appends >=1 event; duplicate Idempotency-Key yields the SAME event set (no new
  events). Events survive a service restart (persisted in SQLite/WAL).
