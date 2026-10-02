from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import uuid


class AggregateIdentityError(ValueError):
    pass


class UnknownEventTypeError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_from_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "sequence": row["sequence"],
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "aggregate_type": row["aggregate_type"],
        "aggregate_id": row["aggregate_id"],
        "occurred_at": row["occurred_at"],
        "payload": json.loads(row["payload_json"]),
    }


class EventStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA recursive_triggers = ON")
        self._create_schema()

    def _create_schema(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              event_type TEXT NOT NULL,
              aggregate_type TEXT NOT NULL,
              aggregate_id TEXT NOT NULL,
              occurred_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_aggregate_sequence
            ON events(aggregate_type, aggregate_id, sequence);
            CREATE TRIGGER IF NOT EXISTS events_no_update
            BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete
            BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            """
        )

    def append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
        event_id: str | None = None,
        occurred_at: str | None = None,
    ) -> dict:
        if not all(isinstance(value, str) and value for value in (
            event_type,
            aggregate_type,
            aggregate_id,
        )):
            raise ValueError("Event type and aggregate identity are required")
        if not isinstance(payload, dict):
            raise ValueError("Event payload must be an object")
        event_id = event_id or str(uuid.uuid4())
        occurred_at = occurred_at or _utc_now()
        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = self.connection.execute(
                    """
                    INSERT INTO events (
                      event_id, event_type, aggregate_type, aggregate_id,
                      occurred_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        occurred_at,
                        payload_json,
                    ),
                )
                sequence = cursor.lastrowid
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
        return {
            "sequence": sequence,
            "event_id": event_id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "occurred_at": occurred_at,
            "payload": json.loads(payload_json),
        }

    def replay(self, aggregate_type: str, aggregate_id: str) -> list[dict]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT sequence, event_id, event_type, aggregate_type,
                       aggregate_id, occurred_at, payload_json
                FROM events
                WHERE aggregate_type = ? AND aggregate_id = ?
                ORDER BY sequence ASC
                """,
                (aggregate_type, aggregate_id),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def get_event(self, event_id: str) -> dict | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT sequence, event_id, event_type, aggregate_type,
                       aggregate_id, occurred_at, payload_json
                FROM events WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
        return _event_from_row(row)

    def find_evidence_by_submission_id(self, submission_id: str) -> dict | None:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT sequence, event_id, event_type, aggregate_type,
                       aggregate_id, occurred_at, payload_json
                FROM events
                WHERE event_type = 'EvidenceExtracted'
                ORDER BY sequence ASC
                """
            ).fetchall()
        for row in rows:
            event = _event_from_row(row)
            if event["payload"].get("submission_id") == submission_id:
                return event
        return None

    def list_evidence(
        self,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT sequence, event_id, event_type, aggregate_type,
                   aggregate_id, occurred_at, payload_json
            FROM events WHERE event_type = 'EvidenceExtracted'
        """
        params: list[str] = []
        if aggregate_type is not None:
            query += " AND aggregate_type = ?"
            params.append(aggregate_type)
        if aggregate_id is not None:
            query += " AND aggregate_id = ?"
            params.append(aggregate_id)
        query += " ORDER BY sequence DESC"
        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
        return [_event_from_row(row) for row in rows]

    def close(self):
        connection = getattr(self, "connection", None)
        if connection is not None:
            connection.close()
            self.connection = None


class ArtifactRepository:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_name(name: str):
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise ValueError("Artifact filename must be a plain filename")
        if name in {".", ".."}:
            raise ValueError("Artifact filename is invalid")

    @staticmethod
    def _write_file(path: Path, content: bytes):
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _file_record(path: Path) -> dict:
        content = path.read_bytes()
        return {
            "path": path.name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def write_evidence(
        self,
        evidence_id: str,
        handwriting: dict,
        pages: list[dict],
        transcript: str | None,
        typed_answer: str | None = None,
    ) -> dict:
        self._validate_name(evidence_id)
        target = self.root / evidence_id
        if target.exists():
            raise FileExistsError(f"Artifact {evidence_id} already exists")
        temporary = self.root / f".{evidence_id}.{uuid.uuid4().hex}.tmp"
        temporary.mkdir()
        try:
            handwriting_bytes = json.dumps(
                handwriting,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            self._write_file(temporary / "handwriting.json", handwriting_bytes)
            if transcript is not None:
                self._write_file(
                    temporary / "transcript.txt",
                    transcript.encode("utf-8"),
                )
            if typed_answer is not None:
                self._write_file(
                    temporary / "typed-answer.txt",
                    typed_answer.encode("utf-8"),
                )
            for page in pages:
                filename = page.get("filename")
                content = page.get("bytes")
                self._validate_name(filename)
                if not isinstance(content, bytes):
                    raise ValueError("Artifact page bytes are required")
                self._write_file(temporary / filename, content)

            files = [
                self._file_record(path)
                for path in sorted(temporary.iterdir(), key=lambda item: item.name)
            ]
            manifest = {
                "schema_version": 1,
                "evidence_id": evidence_id,
                "files": files,
            }
            self._write_file(
                temporary / "manifest.json",
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                ).encode("utf-8"),
            )
            os.replace(temporary, target)
            return manifest
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def verify_manifest(self, manifest: dict) -> bool:
        evidence_id = manifest.get("evidence_id")
        try:
            self._validate_name(evidence_id)
        except ValueError:
            return False
        directory = self.root / evidence_id
        if not directory.is_dir():
            return False
        for record in manifest.get("files", []):
            path = directory / record.get("path", "")
            if not path.is_file():
                return False
            content = path.read_bytes()
            if len(content) != record.get("bytes"):
                return False
            if hashlib.sha256(content).hexdigest() != record.get("sha256"):
                return False
        return True

    def read_manifest(self, evidence_id: str) -> dict:
        self._validate_name(evidence_id)
        return json.loads(
            (self.root / evidence_id / "manifest.json").read_text(encoding="utf-8")
        )

    def path_for(self, evidence_id: str, filename: str) -> Path:
        self._validate_name(evidence_id)
        self._validate_name(filename)
        return self.root / evidence_id / filename


def project_events(events: list[dict]) -> dict:
    state = {
        "aggregate_type": None,
        "aggregate_id": None,
        "evidence_ids": [],
        "latest_assessment": None,
        "assessment_history": [],
        "f_state": None,
        "assessment_status": None,
    }
    seen_event_ids: set[str] = set()
    for event in sorted(events, key=lambda item: item.get("sequence", 0)):
        event_id = event.get("event_id")
        if event_id is not None and event_id in seen_event_ids:
            continue
        if event_id is not None:
            seen_event_ids.add(event_id)
        identity = (event.get("aggregate_type"), event.get("aggregate_id"))
        if state["aggregate_type"] is None:
            state["aggregate_type"], state["aggregate_id"] = identity
        elif identity != (state["aggregate_type"], state["aggregate_id"]):
            raise AggregateIdentityError("Projection cannot mix aggregate identity")

        payload = event.get("payload") or {}
        event_type = event.get("event_type")
        if event_type == "EvidenceExtracted":
            evidence_id = payload.get("evidence_id")
            if evidence_id and evidence_id not in state["evidence_ids"]:
                state["evidence_ids"].append(evidence_id)
            state["assessment_status"] = "pending"
        elif event_type == "AssessmentRequested":
            state["assessment_status"] = "assessing"
        elif event_type == "AssessmentRecorded":
            assessment = dict(payload)
            state["latest_assessment"] = assessment
            state["assessment_history"].append(assessment)
            state["f_state"] = payload.get("f_state")
            state["assessment_status"] = "recorded"
        elif event_type == "AssessmentFailed":
            state["assessment_status"] = "failed"
        else:
            raise UnknownEventTypeError(f"Unknown event type: {event_type}")
    return state
