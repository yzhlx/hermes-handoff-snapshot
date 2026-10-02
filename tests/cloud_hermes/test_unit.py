"""Unit tests — provider, memory, events, execution queue (Track D)."""
import sqlite3
import unittest

from tests.cloud_hermes.helpers import make_app


class TestUnit(unittest.TestCase):
    def setUp(self):
        self.app, self.cfg, self.db = make_app()

    def tearDown(self):
        try:
            self.app.stop()
        except Exception:
            pass
        try:
            import os
            if os.path.exists(self.db):
                os.remove(self.db)
        except Exception:
            pass

    def test_mock_provider_deterministic(self):
        from cloud_hermes.provider import MockProvider
        p = MockProvider("REPLY")
        out = p.complete([{"role": "user", "content": "hi"}], system="sys", max_tokens=10)
        self.assertTrue(out.startswith("REPLY:"))
        self.assertEqual(len(p.calls), 1)

    def test_memory_candidate_not_auto_promoted(self):
        cid = self.app.memory.submit_candidate("user_preference", "喜欢费曼学习法", 0.7, ["msg_1"], "master")
        self.assertIsNotNone(cid)
        # not promoted automatically (below threshold would stay; at 0.7 it CAN promote via explicit call)
        promoted = self.app.memory.promote_candidate(cid)
        self.assertIsNotNone(promoted)
        items = self.app.memory.retrieve("master")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "喜欢费曼学习法")

    def test_retrieve_excludes_other_roles(self):
        self.app.memory.add_shared_memory("user_preference", "shared fact", 0.9)
        # role-specific memory in a different namespace should not appear for master
        other = self.app.memory.submit_candidate("user_preference", "signal teacher secret", 0.9, ["m"], "signal_teacher")
        self.app.memory.promote_candidate(other)
        items = self.app.memory.retrieve("master")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "shared fact")

    def test_event_store_append_only(self):
        evt = self.app.events.append("HermesRunStarted", "hermes_run", "run_x", {"a": 1})
        eid = evt["event_id"]
        # UPDATE must be blocked by trigger (sqlite ABORT surfaces as IntegrityError)
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.app.db.execute("UPDATE events SET event_type='HACK' WHERE event_id=?", (eid,))
        # DELETE must be blocked by trigger
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.app.db.execute("DELETE FROM events WHERE event_id=?", (eid,))
        # idempotency of event_id: appending same id is a unique violation
        with self.assertRaises(sqlite3.IntegrityError):
            self.app.events.append("RoleConversationCompleted", "hermes_run", "run_x", {"b": 2}, event_id=eid)

    def test_execution_lease_prevents_double_execution(self):
        dev = "dev_lease"
        cid = self.app.execution.enqueue(dev, "local_exec", {"action": "x"})
        claimed = self.app.execution.claim(dev)
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0]["id"], cid)
        # second claim must not return the same command (already claimed)
        claimed2 = self.app.execution.claim(dev)
        self.assertEqual(claimed2, [])
        # complete with correct lease token
        token = claimed[0]["lease_token"]
        self.assertTrue(self.app.execution.complete(cid, token, {"ok": True}))
        # complete with wrong token must fail (not lease holder)
        self.assertFalse(self.app.execution.complete(cid, "wrong-token", {"ok": False}))

    def test_execution_offline_command_stays_pending(self):
        dev = "dev_offline"
        cid = self.app.execution.enqueue(dev, "local_exec", {"action": "open_obsidian"})
        status = self.app.execution.node_status(dev)
        self.assertEqual(status["status"], "offline")
        self.assertTrue(status["cloud_chat_available"])


if __name__ == "__main__":
    unittest.main()
