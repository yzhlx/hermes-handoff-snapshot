"""Cloud Hermes Core — Memory store (Track B owns).

OWNER: Track B. Implements the MEMORY-CONTRACT:
- Normal chat is NEVER auto long-term memory.
- The model may only submit a `memory_candidates` row (status=pending) with source/confidence.
- Promotion to `memory_items` is an explicit step, emitting a `MemoryPromoted` event.
- Retrieval returns only active items in the requested namespace (+ shared user memory).
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .db import CloudDatabase, _utc_now
from .events import EventStore


# Namespaces
NS_SHARED = "user/shared"
ROLE_NS_PREFIX = "role/"


def normalize_role_namespace(role_id: str) -> str:
    return f"{ROLE_NS_PREFIX}{role_id}"


class MemoryStore:
    def __init__(self, db: CloudDatabase, events: EventStore):
        self.db = db
        self.events = events

    # ---- retrieval (real, before the model call) ----
    def retrieve(self, role_id: str, limit: int = 10) -> list[dict]:
        """Return active memory items visible to the role: shared user memory + role-private."""
        role_ns = normalize_role_namespace(role_id)
        rows = self.db.query(
            "SELECT id, namespace, kind, content, confidence, source_message_ids_json, created_at "
            "FROM memory_items WHERE status='active' AND (namespace=? OR namespace=?) "
            "ORDER BY confidence DESC, created_at DESC LIMIT ?",
            (NS_SHARED, role_ns, limit),
        )
        return [
            {
                "id": r["id"],
                "namespace": r["namespace"],
                "kind": r["kind"],
                "content": r["content"],
                "confidence": r["confidence"],
                "source_message_ids": json.loads(r["source_message_ids_json"]) if r["source_message_ids_json"] else [],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def retrieve_contents(self, role_id: str, limit: int = 10) -> list[str]:
        return [m["content"] for m in self.retrieve(role_id, limit)]

    # ---- candidate submission (model cannot write memory directly) ----
    def submit_candidate(
        self,
        candidate_type: str,
        content: str,
        confidence: float,
        source_message_ids: list[str],
        role_id: str,
        *,
        correlation_id: str | None = None,
        actor: str | None = None,
    ) -> str:
        cid = f"mcand_{uuid.uuid4().hex}"
        self.db.execute(
            "INSERT INTO memory_candidates(id, candidate_type, content, confidence, source_message_ids_json, role_id, status, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid, candidate_type, content, confidence,
             json.dumps(source_message_ids or [], ensure_ascii=False), role_id, "pending", _utc_now()),
        )
        self.events.append(
            "MemoryCandidateCreated",
            "memory_candidate", cid,
            {
                "candidate_type": candidate_type,
                "content": content,
                "confidence": confidence,
                "source_message_ids": source_message_ids,
                "role_id": role_id,
                "status": "pending",
            },
            actor=actor or "system", source="memory_store", correlation_id=correlation_id,
            causation_id=correlation_id,
        )
        return cid

    # ---- explicit promotion (rule/audit) ----
    def promote_candidate(self, candidate_id: str, *, reason: str = "auto-confidence-threshold", min_confidence: float = 0.6) -> str | None:
        cand = self.db.query_one("SELECT * FROM memory_candidates WHERE id=?", (candidate_id,))
        if not cand or cand["status"] != "pending":
            return None
        if cand["confidence"] < min_confidence:
            return None  # not promoted; remains pending for human review
        item_id = f"mem_{uuid.uuid4().hex}"
        now = _utc_now()
        self.db.execute(
            "INSERT INTO memory_items(id, namespace, kind, content, confidence, source_message_ids_json, created_at, updated_at, status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (item_id, normalize_role_namespace(cand["role_id"]), cand["candidate_type"], cand["content"],
             cand["confidence"], cand["source_message_ids_json"], now, now, "active"),
        )
        self.db.execute(
            "UPDATE memory_candidates SET status='promoted', promoted_item_id=?, reason=? WHERE id=?",
            (item_id, reason, candidate_id),
        )
        self.events.append(
            "MemoryPromoted",
            "memory_item", item_id,
            {
                "candidate_id": candidate_id,
                "namespace": normalize_role_namespace(cand["role_id"]),
                "kind": cand["candidate_type"],
                "content": cand["content"],
                "confidence": cand["confidence"],
                "source_message_ids": json.loads(cand["source_message_ids_json"]) if cand["source_message_ids_json"] else [],
                "reason": reason,
            },
            actor="system", source="memory_store", correlation_id=cand["id"],
        )
        return item_id

    def list_candidates(self, status: str | None = "pending") -> list[dict]:
        if status:
            rows = self.db.query(
                "SELECT * FROM memory_candidates WHERE status=? ORDER BY created_at DESC", (status,)
            )
        else:
            rows = self.db.query("SELECT * FROM memory_candidates ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def add_shared_memory(self, kind: str, content: str, confidence: float = 0.9, source_message_ids: list[str] | None = None) -> str:
        """Direct, audited insert of approved shared user memory (e.g., explicit user authorization)."""
        item_id = f"mem_{uuid.uuid4().hex}"
        now = _utc_now()
        self.db.execute(
            "INSERT INTO memory_items(id, namespace, kind, content, confidence, source_message_ids_json, created_at, updated_at, status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (item_id, NS_SHARED, kind, content, confidence,
             json.dumps(source_message_ids or [], ensure_ascii=False), now, now, "active"),
        )
        self.events.append(
            "MemoryPromoted", "memory_item", item_id,
            {"namespace": NS_SHARED, "kind": kind, "content": content, "confidence": confidence,
             "source_message_ids": source_message_ids or [], "reason": "explicit-authorization"},
            actor="user", source="memory_store",
        )
        return item_id
