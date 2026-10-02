"""Integration tests — full chain, real memory retrieval, persistence across restart,
offline command does not block chat (Track D)."""
import os
import tempfile
import unittest

from tests.cloud_hermes.helpers import make_app, start_server, Client


class TestIntegration(unittest.TestCase):
    def setUp(self):
        # use a FILE db so we can test restart persistence
        self.db = tempfile.mktemp(suffix=".db")
        self.app, self.cfg, _ = make_app(db_path=self.db)
        self.srv, self.port = start_server(self.app)
        self.base = f"http://127.0.0.1:{self.port}"
        self.client = Client(self.base)
        self.client.login("admin", "Password123")

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

    def test_real_memory_retrieval_in_new_session(self):
        # Seed an approved shared memory, then a brand-new chat must retrieve it.
        self.app.memory.add_shared_memory("user_preference", "用户喜欢用费曼学习法讲错题", 0.9)
        _, data = self.client.chat("帮我复习错题", idempotency_key="idem-mem-1")
        self.assertGreaterEqual(len(data["memory_refs"]), 1)
        # And the run summary confirms retrieval performed with memory_count>0
        _, run = self.client.get_run(data["hermes_run_id"])
        self.assertEqual(run["context_retrieval"]["memory_count"], 1)

    def test_events_survive_restart(self):
        _, data = self.client.chat("persist me", idempotency_key="idem-persist-1")
        rid = data["hermes_run_id"]
        before = self.app.events.count()
        self.assertGreaterEqual(before, 1)
        # Simulate restart: stop server + build a NEW app on the SAME db file.
        self.srv.shutdown()
        self.app.stop()
        app2, _, _ = make_app(db_path=self.db, admin_token="INIT123")
        # events + run must still exist
        self.assertGreaterEqual(app2.events.count(), before)
        run = app2.db.get_run(rid)
        self.assertIsNotNone(run)
        self.assertEqual(run["status"], "completed")
        app2.stop()

    def test_offline_command_does_not_block_chat(self):
        dev = "dev_offline_int"
        # enqueue a local command (node offline)
        st, cmd = self.client.request(
            "POST", f"/api/hermes/v1/execution-nodes/{dev}/commands",
            {"command_type": "local_exec", "payload": {"action": "open_obsidian"}},
            headers={"Authorization": f"Bearer {self.client.token}", "Idempotency-Key": "idem-cmd-1"},
        )
        self.assertEqual(st, 201)
        self.assertEqual(cmd["status"], "pending")
        # chat must still succeed and not wait for the command
        _, chat = self.client.chat("继续学习", idempotency_key="idem-cmd-chat")
        self.assertIn("hermes_run_id", chat)

    def test_local_command_claim_and_complete(self):
        dev = "dev_claim_int"
        self.client.request(
            "POST", f"/api/hermes/v1/execution-nodes/{dev}/commands",
            {"command_type": "local_exec", "payload": {"action": "x"}},
            headers={"Authorization": f"Bearer {self.client.token}", "Idempotency-Key": "idem-claim-1"},
        )
        # node claims
        st, claimed = self.client.request("GET", f"/api/hermes/v1/execution-nodes/{dev}/commands",
                                          headers={"Authorization": f"Bearer {self.client.token}"})
        self.assertEqual(st, 200)
        self.assertEqual(len(claimed["items"]), 1)
        cid = claimed["items"][0]["id"]
        token = claimed["items"][0]["lease_token"]
        # node completes
        st, res = self.client.request("POST", f"/api/hermes/v1/execution-nodes/{dev}/commands/{cid}/result",
                                      {"lease_token": token, "result": {"ok": True}},
                                      headers={"Authorization": f"Bearer {self.client.token}"})
        self.assertEqual(st, 200)
        self.assertTrue(res["ok"])


if __name__ == "__main__":
    unittest.main()
