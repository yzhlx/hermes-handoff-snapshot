# ACCEPTANCE-CRITERIA.md

All of the following must hold before announcing "Hermes Cloud Core V1 已接入".

## Main call chain
- [ ] Production Learning OS no longer calls Provider directly (cloud mode default on).
- [ ] Every AI request passes through Cloud Hermes.
- [ ] Every response carries a real `hermes_run_id`.
- [ ] Logs trace the whole chain via correlation id.
- [ ] Cloud Hermes down -> client fails clearly (no silent Provider fallback).
- [ ] No silent Provider fallback in production.

## Long-term memory
- [ ] Real Memory Retrieval runs before the model call.
- [ ] New sessions can read approved memory.
- [ ] Normal chat history is NOT auto long-term memory.
- [ ] Model submits only Memory Candidate (with source/confidence/status).
- [ ] Memory write is auditable.

## Event Store
- [ ] Each chat appends >=1 session event.
- [ ] Business events append-only (UPDATE/DELETE blocked by trigger).
- [ ] event_id unique.
- [ ] correlation_id points to the Hermes Run.
- [ ] Duplicate request -> no duplicate events.
- [ ] Events survive service restart.

## Cloud-independent operation (real test, PC off)
- [ ] Tablet on mobile network logs in, creates conversation, reads a memory, completes a
      chat, creates a cloud task, queries a Run, creates a local-exec command (pending).
- [ ] Local-exec command stays `pending` while PC is off; does not block chat.

## Security
- [ ] Provider key only in cloud (env/secret mgr).
- [ ] No key in frontend bundle, no key in logs.
- [ ] HTTPS, auth enforced, unauthorized rejected.
- [ ] Local service not public; DB not public.
- [ ] Tests use a test DB, never production.
- [ ] No private data in test artifacts.

## Compatibility & rollback
- [ ] Windows non-AI features intact.
- [ ] Tasks / wrong-answers / Canvas / exit logic unbroken.
- [ ] Old stable build still launches.
- [ ] Migration verifiable.
- [ ] Executable rollback exists; rollback keeps new cloud data; does not overwrite local DB.

## Honesty guard
The following are NOT acceptable as completion evidence (per task §17): system prompt
mentions Hermes; a class named `HermesGateway`; UI says "Hermes 正在思考"; the model says
"我检索了记忆"; a design doc mentions Event Store; mock tests standing in for real deploy;
tablet-access-while-PC-on standing in for PC-off test.
