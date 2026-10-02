# MEMORY-CONTRACT.md

## Entities (Track B)
- `memory_items(id, namespace, kind, content, confidence, source_message_ids, created_at,
  updated_at, status='active')`
- `memory_candidates(id, candidate_type, content, confidence, source_message_ids, role_id,
  status='pending', created_at, promoted_item_id)`

## Namespaces
- `user/shared` — shared user memory (teaching preferences, planning preferences, stable
  study habits, explicitly authorized info).
- `role/master`, `role/signal_teacher`, `role/graduate_senior`, `role/supportive_senior`,
  `role/ruthless_humiliator` — role-private memory. V1 schema supports the namespace; only
  `master` is wired in V1 (other personas are out of scope per §14).

## Rules
- A normal chat message is NEVER auto-written to `memory_items`.
- The model (via Run orchestrator) may only INSERT a `memory_candidates` row with
  `status='pending'`, carrying `candidate_type`, `content`, `confidence`,
  `source_message_ids`, `role_id`.
- Promotion to `memory_items` is an explicit step (`memory.promote_candidate`) requiring a
  rule/audit pass, and emits a `MemoryPromoted` event. Demotion emits `MemoryDemoted`.
- Retrieval returns only `status='active'` items in the requested namespace (+ `user/shared`
  always visible to all roles unless role-private override).
- Confidence is a float 0..1; used for ranking, never as a truth claim.

## Evidence required by acceptance
- A `MemoryRetrieved` summary in the Run (memory_count>0 when candidates were promoted and
  approved) with `source_message_ids` populated — proves retrieval is real, not claimed.

## Out of scope (§14)
Four full persona implementations, auto-promotion heuristics beyond a simple confidence
threshold rule, and bulk import of local history.
