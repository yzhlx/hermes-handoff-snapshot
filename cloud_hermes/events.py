"""Cloud Hermes Core — append-only Event Store (Track B owns).

OWNER: Track B. Business events are append-only. UPDATE/DELETE are blocked by DB triggers.
Corrections append a compensating/superseding event. event_id is unique; correlation_id
points to the producing Hermes Run.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .db import CloudDatabase, _utc_now


class EventStore:
    def __init__(self, db: CloudDatabase):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                actor TEXT,
                source TEXT,
                idempotency_key TEXT,
                causation_id TEXT,
                correlation_id TEXT,
                payload_version INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT NOT NULL,
                artifact_refs_json TEXT,
                metadata_json TEXT
            );
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_agg ON events(aggregate_type, aggregate_id, sequence)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_corr ON events(correlation_id)"
        )
        # Append-only guards: abort on UPDATE/DELETE.
        self.db.execute(
            "CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events "
            "BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;"
        )
        self.db.execute(
            "CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events "
            "BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;"
        )

    def append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
        *,
        event_id: str | None = None,
        actor: str | None = None,
        source: str | None = None,
        idempotency_key: str | None = None,
        causation_id: str | None = None,
        correlation_id: str | None = None,
        payload_version: int = 1,
        artifact_refs: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        if not all(isinstance(v, str) and v for v in (event_type, aggregate_type, aggregate_id)):
            raise ValueError("event_type, aggregate_type and aggregate_id are required")
        if not isinstance(payload, dict):
            raise ValueError("event payload must be an object")
        eid = event_id or f"evt_{uuid.uuid4().hex}"
        occurred = _utc_now()
        recorded = occurred
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.db.execute(
            """
            INSERT INTO events (
                event_id, event_type, aggregate_type, aggregate_id, occurred_at, recorded_at,
                actor, source, idempotency_key, causation_id, correlation_id, payload_version,
                payload_json, artifact_refs_json, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                eid, event_type, aggregate_type, aggregate_id, occurred, recorded,
                actor, source, idempotency_key, causation_id, correlation_id, payload_version,
                payload_json,
                json.dumps(artifact_refs or [], ensure_ascii=False) if artifact_refs else None,
                json.dumps(metadata or {}, ensure_ascii=False) if metadata else None,
            ),
        )
        return {
            "event_id": eid,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "occurred_at": occurred,
            "recorded_at": recorded,
            "actor": actor,
            "source": source,
            "idempotency_key": idempotency_key,
            "causation_id": causation_id,
            "correlation_id": correlation_id,
            "payload_version": payload_version,
            "payload": payload,
            "artifact_refs": artifact_refs or [],
            "metadata": metadata or {},
        }

    def get(self, event_id: str) -> dict | None:
        row = self.db.query_one("SELECT * FROM events WHERE event_id=?", (event_id,))
        return self._row_to_dict(row) if row else None

    def list_by_correlation(self, correlation_id: str) -> list[dict]:
        rows = self.db.query(
            "SELECT * FROM events WHERE correlation_id=? ORDER BY sequence ASC", (correlation_id,)
        )
        return [self._row_to_dict(r) for r in rows]

    def list_by_aggregate(self, aggregate_type: str, aggregate_id: str) -> list[dict]:
        rows = self.db.query(
            "SELECT * FROM events WHERE aggregate_type=? AND aggregate_id=? ORDER BY sequence ASC",
            (aggregate_type, aggregate_id),
        )
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
        artifact_refs = json.loads(row["artifact_refs_json"]) if row.get("artifact_refs_json") else []
        metadata = json.loads(row["metadata_json"]) if row.get("metadata_json") else {}
        return {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "aggregate_type": row["aggregate_type"],
            "aggregate_id": row["aggregate_id"],
            "occurred_at": row["occurred_at"],
            "recorded_at": row["recorded_at"],
            "actor": row.get("actor"),
            "source": row.get("source"),
            "idempotency_key": row.get("idempotency_key"),
            "causation_id": row.get("causation_id"),
            "correlation_id": row.get("correlation_id"),
            "payload_version": row.get("payload_version", 1),
            "payload": payload,
            "artifact_refs": artifact_refs,
            "metadata": metadata,
        }

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM events")
        return int(row["c"]) if row else 0
