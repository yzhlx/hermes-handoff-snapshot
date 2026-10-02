"""Security tests — injection, CSRF, rate limit, authz, secret hygiene, XSS static (Track D)."""
import os
import unittest

from tests.cloud_hermes.helpers import make_app, start_server, Client, REPO_ROOT


class TestSecurity(unittest.TestCase):
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

    def test_sql_injection_login_fails(self):
        evil = "' OR '1'='1"
        # wrong password with injected username must NOT authenticate
        st, data = self.client.request("POST", "/api/hermes/v1/auth/login",
                                        {"username": evil, "password": "Password123"})
        self.assertNotEqual(st, 200)
        self.assertNotEqual(data.get("code"), None)

    def test_rate_limiting_on_login(self):
        anon = Client(self.base)
        # 5 failures then a 6th must be rate-limited (429)
        last = None
        for _ in range(6):
            st, last = anon.request("POST", "/api/hermes/v1/auth/login",
                                    {"username": "admin", "password": "wrong"})
            if st == 429:
                break
        self.assertEqual(st, 429)
        self.assertEqual(last["code"], "RATE_LIMITED")

    def test_csrf_required_for_cookie_post(self):
        # Over plain HTTP the cookie jar drops `Secure` cookies, so we inject the session
        # cookie manually (in production HTTPS the browser sends it). This still validates
        # the server-side CSRF rule for cookie-authenticated state-changing requests.
        import json
        import urllib.request
        # raw login to capture the Set-Cookie session value
        req = urllib.request.Request(
            self.base + "/api/hermes/v1/auth/login",
            data=json.dumps({"username": "admin", "password": "Password123"}).encode(),
            method="POST", headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        set_cookie = resp.headers.get("Set-Cookie", "")
        session = set_cookie.split("session=", 1)[1].split(";", 1)[0]
        login_body = json.loads(resp.read().decode())
        csrf = login_body["csrf_token"]  # CSRF token from the SAME session that set the cookie
        cookie_client = Client(self.base)  # token=None -> cookie path only
        # cookie only, no CSRF -> 403
        st, _ = cookie_client.request("POST", "/api/hermes/v1/chat", {"message": "hi"},
                                      headers={"Cookie": "session=" + session})
        self.assertEqual(st, 403)
        # cookie + CSRF -> allowed
        st2, _ = cookie_client.request("POST", "/api/hermes/v1/chat", {"message": "hi"},
                                       headers={"Cookie": "session=" + session, "X-CSRF-Token": csrf})
        self.assertEqual(st2, 200)

    def test_unauthorized_access_rejected(self):
        anon = Client(self.base)
        for path in ["/api/hermes/v1/conversations", "/api/hermes/v1/tasks",
                     "/api/hermes/v1/runs/run_x", "/api/hermes/v1/execution-nodes"]:
            st, _ = anon.request("GET", path)
            self.assertEqual(st, 401, f"path {path} should require auth")

    def test_secret_not_in_health_or_responses(self):
        st, data = self.client.health()
        blob = str(data).lower()
        self.assertNotIn(self.cfg.provider_api_key.lower(), blob)
        self.assertNotIn("sk-", blob)
        # chat response must not contain provider key
        _, chat = self.client.chat("hi", idempotency_key="idem-sec-1")
        self.assertNotIn(self.cfg.provider_api_key, str(chat))

    def test_provider_key_only_in_env_not_persisted(self):
        # provider_api_key from config must never be written to the DB
        rows = self.app.db.query("SELECT sql FROM sqlite_master WHERE type='table'")
        schema_blob = " ".join(r["sql"] or "" for r in rows)
        self.assertNotIn(self.cfg.provider_api_key, schema_blob)
        # and not present in any row of any table
        for table in ["users", "sessions", "conversations", "messages", "hermes_runs", "tasks"]:
            for row in self.app.db.query(f"SELECT * FROM {table}"):
                self.assertNotIn(self.cfg.provider_api_key, str(dict(row)))

    def test_xss_escaping_in_web_client(self):
        # Static check: the web client must escape HTML before injecting messages.
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn("escapeHtml", js)
        self.assertIn("&lt;", js)  # real escaping, not innerHTML assignment of raw content

    def test_no_silent_fallback_flag_in_production(self):
        # In production config, direct transport is disallowed.
        from cloud_hermes.config import Config
        prod = Config(env="production", ai_transport="direct")
        self.assertFalse(prod.direct_transport_allowed())


if __name__ == "__main__":
    unittest.main()
