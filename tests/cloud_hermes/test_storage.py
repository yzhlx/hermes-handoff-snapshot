"""Storage tests — schema migration idempotency, tables, FK, event guards (Track D)."""
import os
import sqlite3
import unittest

from tests.cloud_hermes.helpers import make_app, REPO_ROOT


REQUIRED_TABLES = [
    "users", "sessions", "login_attempts", "devices", "conversations", "messages",
    "hermes_runs", "memory_items", "memory_candidates", "events", "tool_runs", "tasks",
    "execution_nodes", "execution_commands", "idempotency_records", "schema_migrations",
]


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.app, self.cfg, self.db = make_app()

    def tearDown(self):
        try:
            self.app.stop()
        except Exception:
            pass
        try:
            if os.path.exists(self.db):
                os.remove(self.db)
        except Exception:
            pass

    def test_all_tables_exist(self):
        rows = self.app.db.query("SELECT name FROM sqlite_master WHERE type='table'")
        names = {r["name"] for r in rows}
        for t in REQUIRED_TABLES:
            self.assertIn(t, names, f"missing table {t}")

    def test_migration_idempotent(self):
        v1 = self.app.db.schema_version()
        self.assertGreaterEqual(v1, 1)
        # re-applying must be a no-op and not raise
        applied = self.app.db.apply_migrations()
        self.assertEqual(applied, 0)
        self.assertEqual(self.app.db.schema_version(), v1)

    def test_foreign_keys_enforced(self):
        # messages require a valid conversation; FK on should reject orphan
        with self.assertRaises(sqlite3.IntegrityError):
            self.app.db.execute(
                "INSERT INTO messages(id, conversation_id, role, content, created_at) VALUES(?,?,?,?,?)",
                ("msg_x", "conv_does_not_exist", "user", "hi", "2026-01-01T00:00:00Z"),
            )

    def test_event_triggers_block_dml(self):
        self.app.events.append("TaskCreated", "task", "t1", {"x": 1})
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.app.db.execute("UPDATE events SET event_type='Z' WHERE event_id IS NOT NULL")
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.app.db.execute("DELETE FROM events")

    def test_parameterized_store_of_hostile_content(self):
        # SQL/HTML in content must be stored verbatim (parameterized) and retrievable,
        # proving no injection at the data layer.
        evil = "'); DROP TABLE users; -- <script>alert(1)</script>"
        self.app.memory.add_shared_memory("user_preference", evil, 0.9)
        items = self.app.memory.retrieve("master")
        self.assertEqual(items[0]["content"], evil)


if __name__ == "__main__":
    unittest.main()
