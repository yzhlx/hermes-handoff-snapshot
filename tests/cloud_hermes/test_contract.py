"""Contract tests — frozen V1 API contract field presence + stable error codes (Track D)."""
import os
import unittest

from tests.cloud_hermes.helpers import make_app, start_server, Client


HEALTH_KEYS = {
    "status", "service", "version", "provider_configured", "database_available",
    "memory_available", "event_store_available", "execution_node_required",
}
CHAT_KEYS = {
    "reply", "conversation_id", "message_id", "hermes_run_id", "role_id",
    "memory_refs", "event_ids", "tool_calls", "warnings",
}
RUN_KEYS = {"hermes_run_id", "status", "role_id", "context_retrieval", "provider_call", "writeback", "tool_calls", "events"}


class TestContract(unittest.TestCase):
    def setUp(self):
        self.app, self.cfg, self.db = make_app()
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

    def test_health_fields_and_no_secrets(self):
        st, data = self.client.health()
        self.assertEqual(st, 200)
        self.assertEqual(set(data.keys()), HEALTH_KEYS)
        blob = str(data)
        self.assertNotIn(self.cfg.provider_api_key, blob)
        self.assertNotIn("sk-", blob.lower())

    def test_chat_response_fields(self):
        _, data = self.client.chat("hi", idempotency_key="idem-contract-1")
        self.assertEqual(set(data.keys()), CHAT_KEYS)
        self.assertTrue(data["hermes_run_id"].startswith("run_"))

    def test_run_summary_fields(self):
        _, data = self.client.chat("hi", idempotency_key="idem-contract-2")
        _, run = self.client.get_run(data["hermes_run_id"])
        self.assertEqual(set(run.keys()), RUN_KEYS)
        self.assertEqual(run["context_retrieval"]["performed"], True)

    def test_stable_error_codes(self):
        # unauth -> AUTH_REQUIRED
        anon = Client(self.base)
        st, data = anon.chat("hi")
        self.assertEqual(data["code"], "AUTH_REQUIRED")
        # not found run -> NOT_FOUND
        _, data = self.client.get_run("run_nonexistent")
        self.assertEqual(data["code"], "NOT_FOUND")
        # validation: empty message
        st, data = self.client.request("POST", "/api/hermes/v1/chat", {"message": "  "},
                                       headers={"Authorization": f"Bearer {self.client.token}"})
        self.assertEqual(data["code"], "VALIDATION_ERROR")

    def test_idempotency_no_double_provider_call(self):
        provider = self.app.service._provider
        self.client.chat("unique", idempotency_key="idem-nodouble")
        self.client.chat("unique", idempotency_key="idem-nodouble")
        # provider.complete must have been called exactly once
        self.assertEqual(len(provider.calls), 1)

    def test_client_cannot_forge_run_id(self):
        st, data = self.client.request("POST", "/api/hermes/v1/runs/run_forged",
                                       headers={"Authorization": f"Bearer {self.client.token}"})
        # the run_id is server-minted; a client-supplied one is just a lookup, not creation
        self.assertEqual(data["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
