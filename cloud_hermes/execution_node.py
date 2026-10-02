"""Cloud Hermes Core — Execution Node queue (Track B owns).

OWNER: Track B. Local Windows PC is an OPTIONAL Execution Node. Commands needing Obsidian/
Anki/local files are queued. The chat response does NOT wait for them. Lease-based claim
prevents double execution.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .db import CloudDatabase, _utc_now
from .events import EventStore


LEASE_SECONDS = 300
MAX_RETRIES = 3


class ExecutionQueue:
    def __init__(self, db: CloudDatabase, events: EventStore):
        self.db = db
        self.events = events

    def register_node(self, device_id: str, user_id: str | None, capabilities: list[str] | None = None) -> None:
        self.db.execute(
            """INSERT INTO execution_nodes(device_id, user_id, status, capabilities_json, last_seen, registered_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                 user_id=excluded.user_id, status='online',
                 capabilities_json=excluded.capabilities_json, last_seen=excluded.last_seen""",
            (device_id, user_id, "online", json.dumps(capabilities or [], ensure_ascii=False), _utc_now(), _utc_now()),
        )

    def heartbeat(self, device_id: str) -> None:
        self.db.execute(
            "UPDATE execution_nodes SET status='online', last_seen=? WHERE device_id=?",
            (_utc_now(), device_id),
        )

    def set_node_offline(self, device_id: str) -> None:
        self.db.execute("UPDATE execution_nodes SET status='offline', last_seen=? WHERE device_id=?", (_utc_now(), device_id))

    def node_status(self, device_id: str | None = None) -> dict:
        if device_id:
            row = self.db.query_one("SELECT * FROM execution_nodes WHERE device_id=?", (device_id,))
            if row and row["status"] == "online":
                return {"status": "online", "cloud_chat_available": True}
            return {"status": "offline", "cloud_chat_available": True}
        # aggregate
        online = self.db.query_one(
            "SELECT COUNT(*) AS c FROM execution_nodes WHERE status='online'"
        )
        if online and online["c"] > 0:
            return {"status": "online", "cloud_chat_available": True, "online_nodes": online["c"]}
        return {"status": "offline", "cloud_chat_available": True}

    def enqueue(
        self,
        device_id: str,
        command_type: str,
        payload: dict,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
    ) -> str:
        # Idempotency: same key -> return existing command id, do not duplicate.
        if idempotency_key:
            existing = self.db.query_one(
                "SELECT id FROM execution_commands WHERE idempotency_key=?", (idempotency_key,)
            )
            if existing:
                return existing["id"]
        cid = f"exec_{uuid.uuid4().hex}"
        self.db.execute(
            "INSERT INTO execution_commands(id, device_id, command_type, payload_json, status, idempotency_key, retry_count, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid, device_id, command_type, json.dumps(payload, ensure_ascii=False), "pending", idempotency_key, 0, _utc_now()),
        )
        self.events.append(
            "ExecutionCommandQueued", "execution_command", cid,
            {"device_id": device_id, "command_type": command_type, "idempotency_key": idempotency_key,
             "status": "pending", "payload": payload},
            actor=actor or "system", source="execution_queue", correlation_id=correlation_id,
            idempotency_key=idempotency_key, causation_id=correlation_id,
        )
        return cid

    def claim(self, device_id: str, limit: int = 5) -> list[dict]:
        """Atomically claim pending commands for this device via lease. Idempotent claim."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        lease_expires = (now + timedelta(seconds=LEASE_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        lease_token = uuid.uuid4().hex
        claimed = []
        # Claim one at a time to keep the lease atomic under the write lock.
        for _ in range(limit):
            row = self.db.query_one(
                "SELECT id FROM execution_commands "
                "WHERE device_id=? AND status='pending' "
                "AND (lease_expires_at IS NULL OR lease_expires_at <= ?) "
                "ORDER BY created_at ASC LIMIT 1",
                (device_id, now.strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
            if not row:
                break
            cur = self.db.execute(
                "UPDATE execution_commands SET status='claimed', lease_token=?, lease_expires_at=?, retry_count=retry_count+1 "
                "WHERE id=? AND status='pending'",
                (lease_token, lease_expires, row["id"]),
            )
            if cur.rowcount == 1:
                claimed.append(row["id"])
        # Return full command dicts for claimed ids
        result = []
        for cid in claimed:
            r = self.db.query_one("SELECT * FROM execution_commands WHERE id=?", (cid,))
            result.append(self._row_to_dict(r))
        return result

    def complete(self, command_id: str, lease_token: str, result: dict | None = None, failed: bool = False) -> bool:
        r = self.db.query_one("SELECT * FROM execution_commands WHERE id=?", (command_id,))
        if not r:
            return False
        if r["lease_token"] != lease_token:
            return False  # not the lease holder -> no execution
        new_status = "failed" if failed else "completed"
        if failed and r["retry_count"] < MAX_RETRIES:
            # allow a later re-claim by clearing lease; still mark failed attempt
            self.db.execute(
                "UPDATE execution_commands SET status='pending', lease_token=NULL, lease_expires_at=NULL, result_json=? WHERE id=? AND lease_token=?",
                (json.dumps(result or {}, ensure_ascii=False), command_id, lease_token),
            )
        else:
            self.db.execute(
                "UPDATE execution_commands SET status=?, result_json=?, completed_at=? WHERE id=? AND lease_token=?",
                (new_status, json.dumps(result or {}, ensure_ascii=False), _utc_now(), command_id, lease_token),
            )
        self.events.append(
            "ExecutionCommandCompleted", "execution_command", command_id,
            {"status": new_status, "result": result or {}},
            actor="execution_node", source="execution_queue", correlation_id=r["idempotency_key"],
        )
        return True

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        return {
            "id": row["id"],
            "device_id": row["device_id"],
            "command_type": row["command_type"],
            "payload": json.loads(row["payload_json"]) if row.get("payload_json") else {},
            "status": row["status"],
            "idempotency_key": row.get("idempotency_key"),
            "lease_token": row.get("lease_token"),
            "lease_expires_at": row.get("lease_expires_at"),
            "retry_count": row["retry_count"],
            "result": json.loads(row["result_json"]) if row.get("result_json") else None,
            "created_at": row["created_at"],
            "completed_at": row.get("completed_at"),
        }
