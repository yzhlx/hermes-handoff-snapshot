# MIGRATION-PLAN.md

## Principle
The local `chat_messages` SQLite is NOT long-term memory. V1 migration is staged and
explicit; it never auto-uploads private history.

## Stages
1. **New cloud conversations write to cloud immediately.** Once Cloud Hermes mode is enabled
   on the client, every new chat is persisted in the cloud DB (conversations/messages/
   hermes_runs/events). No migration of old data required for this to work.
2. **Windows local history stays read-only.** Existing local `chat_messages` remain
   accessible via the local API in non-cloud mode and are never overwritten.
3. **Optional one-time history import tool (NOT in V1).** A future `tools/import_local_history.py`
   will require explicit user authorization, backup-first, and supports failure rollback.
   It is stubbed (interface only) in V1 to avoid scope creep.
4. **No automatic upload of private history.** Default behavior uploads nothing; the user
   must opt in.
5. **Migration must be explicitly authorized** and **backed up before** and **rollbackable
   after**.

## Schema migration (Track B)
- `cloud_hermes/db.py` uses an explicit `schema_migrations` table with ordered, idempotent
  upgrade steps. `apply_migrations()` is run on startup and is safe to re-run (each step is
  guarded by a version check).
- Initial schema version = 1 (all V1 entities in DATA-OWNERSHIP.md).
- Down migrations are NOT auto-applied; rollback uses the backup + `ROLLBACK-PLAN.md`.

## Data semantics guard
- A normal chat message is NEVER auto-promoted to `memory_items`.
- The model may only submit `memory_candidates` (status=pending) with source message ids and
  confidence. Promotion to `memory_items` requires an explicit rule/audit step
  (`memory.promote_candidate`), recorded as a `MemoryPromoted` event.

## Verification
- `tests/test_storage.py` asserts the migrated schema has all required tables and that a
  second `apply_migrations()` is a no-op (idempotent).
- `database-checks/` holds the post-migration `sqlite_master` dump for the integration DB.
