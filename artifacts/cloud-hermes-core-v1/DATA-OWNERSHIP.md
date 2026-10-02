# DATA-OWNERSHIP.md

Single-writer ownership. A file/subsystem has exactly one Track owner. Cross-Track edits are
forbidden; changes are requested via review report + failing test.

## Track A (Cloud Hermes Gateway / Runtime) — owner
- `cloud_hermes/app.py` (HTTP routing + handlers)
- `cloud_hermes/run_orchestrator.py`
- `cloud_hermes/context.py`
- `cloud_hermes/provider.py`
- `cloud_hermes/errors.py`
- `cloud_hermes/main.py` (service start/stop, structured logging)

## Track B (Cloud Memory / Event / Persistence) — owner
- `cloud_hermes/db.py` (schema + migrations + repositories)
- `cloud_hermes/events.py` (append-only event store)
- `cloud_hermes/memory.py`
- `cloud_hermes/execution_node.py`

## Track C (Learning OS Client / Web) — owner
- `cloud_hermes/client/learning_os_cloud_client.py` (Windows local-API adapter)
- patched `outputs/learning-os-api.py` (cloud mode switch, old provider retained)
- `web/index.html`, `web/app.js`, `web/style.css` (deployable static tablet/web UI)

## Track D (Security / Deployment / QA) — owner
- `cloud_hermes/auth.py`
- `tests/` (all suites), `nginx.conf`, `Dockerfile`, `docker-compose.yml`,
  `deploy/`, `scripts/rollback.sh`, `SECURITY-REVIEW.md`

## Shared (read-only reference)
- `cloud_hermes/config.py` — environment contract; any Track may read, only Track D changes
  the secret-handling policy.

## Database tables -> owner
| Table | Owner | Notes |
|-------|-------|-------|
| users / sessions /login_attempts | D+A | auth |
| devices | C+B | device identity |
| conversations / messages | B | persistence |
| hermes_runs | A+B | run lifecycle |
| memory_items / memory_candidates | B | memory |
| events | B | append-only |
| tool_runs | A+B | tool calls |
| tasks | B | minimal CRUD |
| execution_nodes / execution_commands | B | queue |
| idempotency_records | A+B | idempotency |

## Hard rules
- No Track may write another Track's owned file.
- Test Agent (D) may ADD `tests/` and failing tests, but never silently modify production code.
- All merges happen only in `integration/cloud-hermes-core-v1`.
- No development directly on the stable baseline branch.
