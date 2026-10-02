"""API tests — real HTTP through app.py (Track D)."""
import os
import unittest

from tests.cloud_hermes.helpers import make_app, start_server, Client


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app, self.cfg, self.db = make_app()
        self.srv, self.port = start_server(self.app)
        self.base = f"http://127.0.0.1:{self.port}"
        self.client = Client(self.base)
        st, data = self.client.login("admin", "Password123")
        self.assertEqual(st, 200)
        self.token = data["access_token"]

    def tearDown(self):
        try:
            self.srv.shutdown()
        except Exception:
            pass
        try:
            self.app.stop()
        except Exception:
            pass
        try:
            if os.path.exists(self.db):
                os.remove(self.db)
        except Exception:
            pass

    def test_health_public(self):
        st, data = self.client.health()
        self.assertEqual(st, 200)
        self.assertEqual(data["service"], "hermes-cloud-core")

    def test_unauthenticated_chat_rejected(self):
        anon = Client(self.base)
        st, _ = anon.chat("hi")
        self.assertEqual(st, 401)

    def test_login_logout_me(self):
        st, data = self.client.request("GET", "/api/hermes/v1/auth/me", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(st, 200)
        uid = self.app.db.query_one("SELECT id FROM users WHERE username=?", ("admin",))["id"]
        self.assertEqual(data["user_id"], uid)
        st, _ = self.client.request("POST", "/api/hermes/v1/auth/logout")
        self.assertEqual(st, 200)
        # token now revoked
        st, _ = self.client.chat("hi")
        self.assertEqual(st, 401)

    def test_chat_returns_run_and_events(self):
        st, data = self.client.chat("hello", idempotency_key="idem-api-1")
        self.assertEqual(st, 200)
        self.assertIn("hermes_run_id", data)
        self.assertIn("conversation_id", data)
        self.assertIn("message_id", data)
        self.assertTrue(len(data["event_ids"]) >= 1)
        self.assertIn("reply", data)

    def test_run_query_safe_summary(self):
        _, data = self.client.chat("hello", idempotency_key="idem-api-2")
        rid = data["hermes_run_id"]
        st, run = self.client.get_run(rid)
        self.assertEqual(st, 200)
        self.assertEqual(run["status"], "completed")
        self.assertIn("context_retrieval", run)
        self.assertIn("provider_call", run)
        self.assertIn("writeback", run)

    def test_conversations_and_messages(self):
        _, data = self.client.chat("hello", idempotency_key="idem-api-3")
        conv = data["conversation_id"]
        st, listing = self.client.request("GET", "/api/hermes/v1/conversations")
        self.assertEqual(st, 200)
        self.assertTrue(any(c["id"] == conv for c in listing["items"]))
        st, full = self.client.request("GET", f"/api/hermes/v1/conversations/{conv}")
        self.assertEqual(st, 200)
        self.assertGreaterEqual(len(full["messages"]), 2)

    def test_tasks_crud(self):
        st, task = self.client.request("POST", "/api/hermes/v1/tasks",
                                        {"title": "周计划"}, headers={"Idempotency-Key": "idem-task-api"})
        self.assertEqual(st, 201)
        self.assertIn("id", task)
        st, listing = self.client.request("GET", "/api/hermes/v1/tasks")
        self.assertEqual(st, 200)
        self.assertTrue(any(t["id"] == task["id"] for t in listing["items"]))

    def test_execution_nodes_offline(self):
        st, data = self.client.request("GET", "/api/hermes/v1/execution-nodes")
        self.assertEqual(st, 200)
        self.assertEqual(data["cloud_chat_available"], True)

    def test_duplicate_idempotency_same_run(self):
        _, a = self.client.chat("repeat", idempotency_key="idem-dup")
        _, b = self.client.chat("repeat", idempotency_key="idem-dup")
        self.assertEqual(a["hermes_run_id"], b["hermes_run_id"])


if __name__ == "__main__":
    unittest.main()
