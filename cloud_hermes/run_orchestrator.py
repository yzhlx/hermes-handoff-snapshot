"""Cloud Hermes Core — Run Orchestrator / Service (Track A owns).

OWNER: Track A (Gateway/Runtime). Implements the mandated call chain:

  HTTP request -> Authentication (done in app) -> Idempotency check
    -> Hermes Run created -> Role/Profile resolved -> Context retrieval requested
    -> Provider invoked -> Response validated -> Event/writeback requested
    -> Hermes Run completed -> API response

Every step is observable (events + run fields). No silent fallback to a direct provider in
production. hermes_run_id is server-minted and never forged by the client.
"""
from __future__ import annotations

import time

from .auth import AuthService
from .context import ContextBuilder
from .db import CloudDatabase
from .errors import HermesError, hermes_unavailable, status_for, validation_error
from .events import EventStore
from .execution_node import ExecutionQueue
from .memory import MemoryStore
from .provider import build_provider


# Heuristic: an explicit, durable preference request becomes a memory CANDIDATE (not memory).
_REMEMBER_MARKERS = ("请记住", "记住这个", "记住：", "记住:")


class HermesService:
    def __init__(
        self,
        db: CloudDatabase,
        events: EventStore,
        memory: MemoryStore,
        execution: ExecutionQueue,
        auth: AuthService,
        config,
        provider=None,
    ):
        self.db = db
        self.events = events
        self.memory = memory
        self.execution = execution
        self.auth = auth
        self.config = config
        self._provider = provider  # injected for tests; else built lazily

    # ---- provider ----
    def provider(self):
        if self._provider is not None:
            return self._provider
        return build_provider(self.config)

    # ---- health ----
    def health(self) -> dict:
        provider_ok = bool(self._provider is not None) or self.config.provider_configured() or self.config.mock_provider
        try:
            db_ok = self.db.schema_version() >= 1
        except Exception:
            db_ok = False
        try:
            mem_ok = self.memory.retrieve("master", 1) is not None
        except Exception:
            mem_ok = False
        try:
            ev_ok = self.events.count() >= 0
        except Exception:
            ev_ok = False
        return {
            "status": "ok",
            "service": "hermes-cloud-core",
            "version": "1",
            "provider_configured": provider_ok,
            "database_available": db_ok,
            "memory_available": mem_ok,
            "event_store_available": ev_ok,
            "execution_node_required": False,
        }

    # ---- the call chain ----
    def chat(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        role_id: str,
        message: str,
        client: dict | None,
        idempotency_key: str | None,
        device_id: str | None,
    ) -> dict:
        # 1) Idempotency check — duplicate key returns the stored response, no provider re-call.
        if idempotency_key:
            cached = self.db.get_idempotency(idempotency_key)
            if cached:
                return cached

        # 2) Validate
        if not message or not isinstance(message, str) or not message.strip():
            raise validation_error("message is required")
        role_id = role_id or "master"
        if len(message) > 20000:
            raise validation_error("message too long (max 20000 chars)")

        # 3) Conversation (create if absent; a client may supply its own id to mirror a
        #    local conversation into the cloud — cloud creates it if it does not exist).
        if conversation_id:
            conv = self.db.get_conversation(conversation_id)
            if conv and conv["user_id"] != user_id:
                raise HermesError("NOT_FOUND", "Conversation not found.", status_for("NOT_FOUND"))
            if not conv:
                conversation_id = self.db.create_conversation(user_id, None, role_id, forced_id=conversation_id)
        else:
            conversation_id = self.db.create_conversation(user_id, None, role_id)

        # 4) Hermes Run created (server-minted id; client cannot forge)
        run_id = self.db.create_run(conversation_id, user_id, role_id)
        correlation_id = run_id
        self.events.append(
            "HermesRunStarted", "hermes_run", run_id,
            {"conversation_id": conversation_id, "role_id": role_id, "user_id": user_id},
            actor=user_id, source="run_orchestrator", correlation_id=correlation_id, causation_id=correlation_id,
        )

        # Persist the user message (so source_message_ids can reference it)
        user_msg_id = self.db.add_message(conversation_id, "user", message, hermes_run_id=run_id)

        # 5) Context retrieval (REAL memory retrieval, before provider call)
        ctx = ContextBuilder(self.memory).build(role_id, message)
        self.db.update_run(run_id, context_retrieval_performed=1, memory_count=ctx["memory_count"])
        self.events.append(
            "ContextRetrieved", "hermes_run", run_id,
            {"role_id": ctx["role_id"], "memory_count": ctx["memory_count"],
             "memory_ids": [m["id"] for m in ctx["memory"]]},
            actor=user_id, source="context_builder", correlation_id=correlation_id, causation_id=run_id,
        )

        # 6) Provider invocation (no silent fallback)
        provider = self.provider()
        self.db.update_run(run_id, provider_performed=1, provider_name=provider.name, provider_model=provider.model)
        try:
            reply = provider.complete(
                [{"role": "user", "content": message}],
                system=ctx["system"],
                max_tokens=1200,
            )
        except HermesError as e:
            self.db.update_run(run_id, status="failed")
            # Do NOT store idempotency on failure -> client may retry with same key.
            raise

        # 7) Validate response
        if not reply or not reply.strip():
            self.db.update_run(run_id, status="failed")
            raise HermesError("PROVIDER_INVALID_RESPONSE", "Provider returned an empty response.", status_for("PROVIDER_INVALID_RESPONSE"))

        # 8) Writeback — persist assistant message + events + optional memory candidate
        assistant_msg_id = self.db.add_message(conversation_id, "assistant", reply, hermes_run_id=run_id)

        event_ids: list[str] = []
        evt = self.events.append(
            "RoleConversationCompleted", "hermes_run", run_id,
            {"conversation_id": conversation_id, "role_id": ctx["role_id"],
             "user_message_id": user_msg_id, "assistant_message_id": assistant_msg_id,
             "reply_len": len(reply)},
            actor=user_id, source="run_orchestrator", correlation_id=correlation_id, causation_id=run_id,
        )
        event_ids.append(evt["event_id"])

        # Memory candidate: only via explicit durable-preference intent (never auto from chat).
        memory_candidate_id = None
        if any(marker in message for marker in _REMEMBER_MARKERS) and len(message) <= 200:
            memory_candidate_id = self.memory.submit_candidate(
                candidate_type="user_preference",
                content=message,
                confidence=0.7,
                source_message_ids=[user_msg_id],
                role_id=ctx["role_id"],
                correlation_id=correlation_id,
                actor=user_id,
            )
            self.db.update_run(run_id, memory_candidate_count=1)

        # 9) Run completed
        self.db.update_run(run_id, status="completed", completed_at=self._now(), event_count=len(event_ids))
        self.events.append(
            "ProviderInvocationCompleted", "hermes_run", run_id,
            {"provider_name": provider.name, "provider_model": provider.model, "ok": True},
            actor=user_id, source="run_orchestrator", correlation_id=correlation_id, causation_id=run_id,
        )

        response = {
            "reply": reply,
            "conversation_id": conversation_id,
            "message_id": assistant_msg_id,
            "hermes_run_id": run_id,
            "role_id": ctx["role_id"],
            "memory_refs": [m["id"] for m in ctx["memory"]],
            "event_ids": event_ids,
            "tool_calls": [],
            "warnings": [],
        }
        # Store idempotency ONLY on success.
        if idempotency_key:
            self.db.record_idempotency(idempotency_key, response)
        return response

    # ---- run summary (safe) ----
    def get_run(self, run_id: str) -> dict:
        run = self.db.get_run(run_id)
        if not run:
            raise HermesError("NOT_FOUND", "Run not found.", status_for("NOT_FOUND"))
        events = self.events.list_by_correlation(run_id)
        return {
            "hermes_run_id": run["id"],
            "status": run["status"],
            "role_id": run["role_id"],
            "context_retrieval": {
                "performed": bool(run["context_retrieval_performed"]),
                "memory_count": run["memory_count"],
            },
            "provider_call": {
                "performed": bool(run["provider_performed"]),
                "provider_name": run["provider_name"],
                "model": run["provider_model"],
            },
            "writeback": {
                "event_count": run["event_count"],
                "memory_candidate_count": run["memory_candidate_count"],
            },
            "tool_calls": [],
            "events": [e["event_type"] for e in events],
        }

    # ---- conversations ----
    def list_conversations(self, user_id: str) -> dict:
        return {"items": self.db.list_conversations(user_id)}

    def get_conversation(self, user_id: str, conversation_id: str) -> dict:
        conv = self.db.get_conversation(conversation_id)
        if not conv or conv["user_id"] != user_id:
            raise HermesError("NOT_FOUND", "Conversation not found.", status_for("NOT_FOUND"))
        return {"conversation": conv, "messages": self.db.list_messages(conversation_id)}

    # ---- tasks ----
    def list_tasks(self, user_id: str) -> dict:
        return {"items": self.db.list_tasks(user_id)}

    def create_task(self, user_id: str, title: str, description: str | None, idempotency_key: str | None = None) -> dict:
        if idempotency_key:
            cached = self.db.get_idempotency(f"task:{idempotency_key}")
            if cached:
                return cached
        if not title or not isinstance(title, str) or not title.strip():
            raise validation_error("title is required")
        task_id = self.db.create_task(user_id, title.strip(), description)
        self.events.append(
            "TaskCreated", "task", task_id, {"title": title, "description": description, "status": "open"},
            actor=user_id, source="run_orchestrator", correlation_id=task_id, idempotency_key=idempotency_key,
        )
        result = {"id": task_id, "title": title.strip(), "description": description, "status": "open"}
        if idempotency_key:
            self.db.record_idempotency(f"task:{idempotency_key}", result)
        return result

    # ---- execution nodes ----
    def execution_nodes_status(self, device_id: str | None = None) -> dict:
        return self.execution.node_status(device_id)

    def enqueue_local_command(self, device_id: str, command_type: str, payload: dict, idempotency_key: str | None, user_id: str) -> dict:
        cmd_id = self.execution.enqueue(
            device_id, command_type, payload, idempotency_key=idempotency_key,
            correlation_id=idempotency_key, actor=user_id,
        )
        return {"command_id": cmd_id, "status": "pending", "device_id": device_id}

    def claim_commands(self, device_id: str, user_id: str) -> list[dict]:
        return self.execution.claim(device_id)

    def complete_command(self, command_id: str, lease_token: str, result: dict | None, failed: bool) -> bool:
        return self.execution.complete(command_id, lease_token, result, failed)

    @staticmethod
    def _now() -> str:
        from .db import _utc_now
        return _utc_now()
