"""Cloud Hermes Core — database schema, migrations, repositories (Track B owns).

OWNER: Track B (Cloud Memory / Event / Persistence). Exposes a thread-safe connection and
generic helpers; domain stores (events/memory/execution_node) build on top of this.

All SQL uses parameterized statements (?) — no string interpolation of user input — to
prevent SQL injection (acceptance criterion 16).
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from pathlib import Path


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Ordered, idempotent migration steps. V1 = single migration creating all entities.
MIGRATIONS: list[tuple[str, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL,
            admin_initialized INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            device_id TEXT,
            csrf_token TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ip TEXT,
            attempted_at TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_login_attempts_key ON login_attempts(username, ip, attempted_at);

        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            user_id TEXT,
            client_type TEXT,
            client_version TEXT,
            last_seen TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            role_id TEXT NOT NULL DEFAULT 'master',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            hermes_run_id TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS hermes_runs (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            user_id TEXT,
            role_id TEXT NOT NULL,
            status TEXT NOT NULL,
            context_retrieval_performed INTEGER NOT NULL DEFAULT 0,
            memory_count INTEGER NOT NULL DEFAULT 0,
            provider_performed INTEGER NOT NULL DEFAULT 0,
            provider_name TEXT,
            provider_model TEXT,
            event_count INTEGER NOT NULL DEFAULT 0,
            memory_candidate_count INTEGER NOT NULL DEFAULT 0,
            tool_calls_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            correlation_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_conv ON hermes_runs(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_runs_user ON hermes_runs(user_id);

        CREATE TABLE IF NOT EXISTS memory_items (
            id TEXT PRIMARY KEY,
            namespace TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            source_message_ids_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE INDEX IF NOT EXISTS idx_memory_ns ON memory_items(namespace, status);

        CREATE TABLE IF NOT EXISTS memory_candidates (
            id TEXT PRIMARY KEY,
            candidate_type TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            source_message_ids_json TEXT,
            role_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            promoted_item_id TEXT,
            reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cand_status ON memory_candidates(status);

        CREATE TABLE IF NOT EXISTS tool_runs (
            id TEXT PRIMARY KEY,
            hermes_run_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT,
            output_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hermes_run_id) REFERENCES hermes_runs(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);

        CREATE TABLE IF NOT EXISTS execution_nodes (
            device_id TEXT PRIMARY KEY,
            user_id TEXT,
            status TEXT NOT NULL DEFAULT 'offline',
            capabilities_json TEXT,
            last_seen TEXT,
            registered_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS execution_commands (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            idempotency_key TEXT,
            lease_token TEXT,
            lease_expires_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            result_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_exec_status ON execution_commands(status, device_id);
        CREATE INDEX IF NOT EXISTS idx_exec_idem ON execution_commands(idempotency_key);

        CREATE TABLE IF NOT EXISTS idempotency_records (
            key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """,
    ),
]


class CloudDatabase:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.apply_migrations()

    # ---- migration ----
    def apply_migrations(self) -> int:
        with self._lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row["version"]
                for row in self.conn.execute("SELECT version FROM schema_migrations")
            }
            done = 0
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
                self.conn.executescript(sql)
                self.conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, _utc_now()),
                )
                applied.add(version)
                done += 1
            return done

    def schema_version(self) -> int:
        row = self.conn.execute(
            "SELECT MAX(version) AS v FROM schema_migrations"
        ).fetchone()
        return int(row["v"] or 0)

    # ---- generic helpers (parameterized) ----
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.execute(sql, params)

    def executemany(self, sql: str, seq: list[tuple]) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.executemany(sql, seq)

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    # ---- repositories ----
    def upsert_device(self, device_id: str, user_id: str | None, client_type: str, client_version: str) -> None:
        self.execute(
            """INSERT INTO devices(device_id, user_id, client_type, client_version, last_seen)
               VALUES(?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                 user_id=excluded.user_id, client_type=excluded.client_type,
                 client_version=excluded.client_version, last_seen=excluded.last_seen""",
            (device_id, user_id, client_type, client_version, _utc_now()),
        )

    def create_conversation(self, user_id: str, title: str | None, role_id: str, forced_id: str | None = None) -> str:
        cid = forced_id or f"conv_{uuid.uuid4().hex}"
        now = _utc_now()
        self.execute(
            "INSERT INTO conversations(id, user_id, title, role_id, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (cid, user_id, title or "新对话", role_id, now, now),
        )
        return cid

    def get_conversation(self, conv_id: str) -> dict | None:
        return self.query_one("SELECT * FROM conversations WHERE id=?", (conv_id,))

    def list_conversations(self, user_id: str) -> list[dict]:
        return self.query(
            "SELECT id, user_id, title, role_id, created_at, updated_at FROM conversations WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        )

    def touch_conversation(self, conv_id: str) -> None:
        self.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_utc_now(), conv_id))

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        hermes_run_id: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        mid = f"msg_{uuid.uuid4().hex}"
        import json
        self.execute(
            "INSERT INTO messages(id, conversation_id, role, content, hermes_run_id, created_at, metadata_json) VALUES(?,?,?,?,?,?,?)",
            (mid, conversation_id, role, content, hermes_run_id, _utc_now(),
             json.dumps(metadata or {}, ensure_ascii=False) if metadata else None),
        )
        self.touch_conversation(conversation_id)
        return mid

    def list_messages(self, conversation_id: str) -> list[dict]:
        return self.query(
            "SELECT id, conversation_id, role, content, hermes_run_id, created_at FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
            (conversation_id,),
        )

    def create_run(self, conversation_id: str | None, user_id: str | None, role_id: str, correlation_id: str | None = None) -> str:
        rid = f"run_{uuid.uuid4().hex}"
        self.execute(
            "INSERT INTO hermes_runs(id, conversation_id, user_id, role_id, status, created_at, correlation_id) VALUES(?,?,?,?,?,?,?)",
            (rid, conversation_id, user_id, role_id, "started", _utc_now(), correlation_id or rid),
        )
        return rid

    def update_run(self, run_id: str, **fields) -> None:
        allowed = {
            "status", "context_retrieval_performed", "memory_count", "provider_performed",
            "provider_name", "provider_model", "event_count", "memory_candidate_count",
            "tool_calls_json", "completed_at", "conversation_id", "correlation_id",
        }
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets)
        self.execute(f"UPDATE hermes_runs SET {cols} WHERE id=?", tuple(sets.values()) + (run_id,))

    def get_run(self, run_id: str) -> dict | None:
        return self.query_one("SELECT * FROM hermes_runs WHERE id=?", (run_id,))

    def create_task(self, user_id: str, title: str, description: str | None, status: str = "open") -> str:
        tid = f"task_{uuid.uuid4().hex}"
        now = _utc_now()
        self.execute(
            "INSERT INTO tasks(id, user_id, title, description, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
            (tid, user_id, title, description, status, now, now),
        )
        return tid

    def list_tasks(self, user_id: str) -> list[dict]:
        return self.query(
            "SELECT id, user_id, title, description, status, created_at, updated_at FROM tasks WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        )

    def get_task(self, task_id: str) -> dict | None:
        return self.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))

    def record_idempotency(self, key: str, response: dict) -> None:
        import json
        self.execute(
            "INSERT INTO idempotency_records(key, response_json, created_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET response_json=excluded.response_json, created_at=excluded.created_at",
            (key, json.dumps(response, ensure_ascii=False), _utc_now()),
        )

    def get_idempotency(self, key: str) -> dict | None:
        row = self.query_one("SELECT response_json FROM idempotency_records WHERE key=?", (key,))
        if not row:
            return None
        import json
        return json.loads(row["response_json"])
