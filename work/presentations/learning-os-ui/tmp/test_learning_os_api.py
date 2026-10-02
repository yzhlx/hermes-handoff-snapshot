import base64
import http.client
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "outputs" / "learning-os-api.py"
AI_MODULE_PATH = ROOT / "outputs" / "learning-os-ai.py"
CREDENTIALS_MODULE_PATH = ROOT / "outputs" / "learning-os-credentials.py"


def load_module():
    spec = importlib.util.spec_from_file_location("learning_os_api", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ai_module():
    spec = importlib.util.spec_from_file_location("learning_os_ai", AI_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_credentials_module():
    spec = importlib.util.spec_from_file_location("learning_os_credentials", CREDENTIALS_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AiAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = load_ai_module()

    def test_validate_error_analysis_limits_questions_when_information_is_insufficient(self):
        result = self.ai.validate_error_analysis(
            {
                "information_sufficient": False,
                "missing_information": ["缺少作答过程"],
                "questions": ["第一问", "第二问", "第三问", "第四问"],
            }
        )
        self.assertFalse(result["information_sufficient"])
        self.assertEqual(result["questions"], ["第一问", "第二问", "第三问"])

    def test_validate_error_analysis_requires_supported_error_types_and_short_advice(self):
        result = self.ai.validate_error_analysis(
            {
                "information_sufficient": True,
                "primary_error_type": "推理过程错误",
                "secondary_error_types": ["计算错误"],
                "error_step": "代入极限公式时",
                "evidence": ["把 x^2 误写为 x"],
                "thinking_difference": "应先检查定义域再化简",
                "knowledge_points": ["极限运算"],
                "next_time_check": ["逐项核对指数"],
                "improvement_suggestion": "化简后逐项核对指数",
                "review_priority": "high",
                "long_term_weakness": True,
                "questions": [],
            }
        )
        self.assertEqual(result["primary_error_type"], "推理过程错误")
        self.assertTrue(result["long_term_weakness"])


class AiGatewayProviderContractTests(unittest.TestCase):
    class _Core:
        def __init__(self, settings):
            self.settings = dict(settings)

        def get_ai_settings(self):
            return dict(self.settings)

        def update_ai_settings(self, payload):
            self.settings.update(payload)
            return self.get_ai_settings()

    class _Credentials:
        def __init__(self, secret="AI_TEST_SECRET_1234"):
            self.secret = secret

        def get_secret(self):
            return self.secret

        def set_secret(self, secret):
            self.secret = secret

        def delete_secret(self):
            self.secret = None

        def status(self):
            return {"is_configured": bool(self.secret), "key_suffix": self.secret[-4:] if self.secret else None}

    def setUp(self):
        self.ai = load_ai_module()

    def test_chat_completions_normalizes_provider_root_and_content_array(self):
        calls = []

        def request_json(url, headers, payload, timeout_seconds):
            calls.append((url, headers, payload, timeout_seconds))
            return {"choices": [{"message": {"content": [{"type": "text", "text": "connected"}]}}]}

        gateway = self.ai.AIGateway(
            self._Core({"base_url": "https://provider.example/v1/", "protocol": "chat_completions", "model": "test-model", "timeout_seconds": 17}),
            credentials=self._Credentials(),
            request_json=request_json,
        )

        self.assertEqual(gateway.answer_chat([{"role": "user", "content": "ping"}]), "connected")
        self.assertEqual(calls[0][0], "https://provider.example/v1/chat/completions")
        self.assertEqual(calls[0][3], 17)
        self.assertEqual(calls[0][2]["model"], "test-model")

    def test_chat_completions_normalizes_a_partial_chat_path_without_duplication(self):
        calls = []

        def request_json(url, _headers, _payload, _timeout_seconds):
            calls.append(url)
            return {"choices": [{"message": {"content": "connected"}}]}

        gateway = self.ai.AIGateway(
            self._Core({"base_url": "https://provider.example/v1/chat", "protocol": "chat_completions", "model": "test-model", "timeout_seconds": 30}),
            credentials=self._Credentials(), request_json=request_json,
        )

        self.assertEqual(gateway.test_connection(), "connected")
        self.assertEqual(calls, ["https://provider.example/v1/chat/completions"])

    def test_responses_uses_instructions_and_normalizes_root_url(self):
        calls = []

        def request_json(url, _headers, payload, _timeout_seconds):
            calls.append((url, payload))
            return {"output": [{"content": [{"type": "output_text", "text": "PONG"}]}]}

        gateway = self.ai.AIGateway(
            self._Core({"base_url": "https://provider.example", "protocol": "responses", "model": "test-model", "timeout_seconds": 9}),
            credentials=self._Credentials(),
            request_json=request_json,
        )

        self.assertEqual(gateway.answer_chat([{"role": "user", "content": "ping"}]), "PONG")
        self.assertEqual(calls[0][0], "https://provider.example/v1/responses")
        self.assertTrue(calls[0][1]["instructions"].startswith("You are Hermes, a learning assistant."))
        self.assertEqual(calls[0][1]["input"], [{"role": "user", "content": "ping"}])

    def test_provider_failures_are_stable_and_do_not_expose_the_secret(self):
        def request_json(_url, _headers, _payload, _timeout_seconds):
            raise urllib.error.HTTPError("https://provider.example", 401, "unauthorized", {}, None)

        gateway = self.ai.AIGateway(
            self._Core({"base_url": "https://provider.example", "protocol": "chat_completions", "model": "test-model", "timeout_seconds": 30}),
            credentials=self._Credentials("AI_TEST_SECRET_1234"),
            request_json=request_json,
        )
        with self.assertRaises(self.ai.AIProviderError) as raised:
            gateway.test_connection()
        self.assertEqual(raised.exception.code, "AI_AUTH_FAILED")
        self.assertEqual(raised.exception.status, 401)
        self.assertNotIn("AI_TEST_SECRET_1234", str(raised.exception))

    def test_empty_and_malformed_provider_responses_are_not_treated_as_success(self):
        for response, expected_code in [
            ({"choices": [{"message": {"content": ""}}]}, "AI_EMPTY_RESPONSE"),
            ({"choices": []}, "AI_INVALID_RESPONSE"),
        ]:
            gateway = self.ai.AIGateway(
                self._Core({"base_url": "https://provider.example", "protocol": "chat_completions", "model": "test-model", "timeout_seconds": 30}),
                credentials=self._Credentials(),
                request_json=lambda *_args, response=response: response,
            )
            with self.assertRaises(self.ai.AIProviderError) as raised:
                gateway.answer_chat([{"role": "user", "content": "ping"}])
            self.assertEqual(raised.exception.code, expected_code)

    def test_wrong_answer_analysis_uses_the_adapter_when_evidence_exists_and_asks_when_it_does_not(self):
        calls = []
        valid_analysis = {
            "information_sufficient": True,
            "primary_error_type": self.ai.ERROR_TYPES[0],
            "secondary_error_types": [],
            "error_step": "substitution",
            "evidence": ["the sign was omitted"],
            "thinking_difference": "check the sign before simplifying",
            "knowledge_points": ["sign rules"],
            "next_time_check": ["check each sign"],
            "improvement_suggestion": "check every sign",
            "review_priority": "medium",
            "long_term_weakness": False,
            "questions": [],
        }

        def request_json(_url, _headers, payload, _timeout_seconds):
            calls.append(payload)
            return {"choices": [{"message": {"content": json.dumps(valid_analysis)}}]}

        gateway = self.ai.AIGateway(
            self._Core({"base_url": "https://provider.example", "protocol": "chat_completions", "model": "test-model", "timeout_seconds": 30}),
            credentials=self._Credentials(), request_json=request_json,
        )
        result = gateway.analyze_error_question({"problem_text": "x + 1 = 0", "work_text": "x = 1"})
        self.assertTrue(result["information_sufficient"])
        self.assertEqual(len(calls), 1)
        insufficient = gateway.analyze_error_question({"subject": "math"})
        self.assertFalse(insufficient["information_sufficient"])
        self.assertTrue(insufficient["questions"])
        self.assertEqual(len(calls), 1)


@unittest.skipUnless(os.name == "nt", "Windows Credential Manager is Windows-only")
class CredentialStoreTests(unittest.TestCase):
    def test_missing_credential_reports_unconfigured_status(self):
        credentials = load_credentials_module()
        store = credentials.WindowsCredentialStore("LearningOS.Test.Missing.Credential")
        self.assertEqual(store.status(), {"is_configured": False, "key_suffix": None})

    def test_test_credential_can_be_saved_updated_and_deleted_without_exposure(self):
        credentials = load_credentials_module()
        target = f"LearningOS.Test.AI.{uuid.uuid4()}"
        store = credentials.WindowsCredentialStore(target)
        try:
            store.set_secret("QA_TEST_SECRET_1111")
            self.assertEqual(store.status(), {"is_configured": True, "key_suffix": "1111"})
            store.set_secret("QA_TEST_SECRET_2222")
            self.assertEqual(store.status(), {"is_configured": True, "key_suffix": "2222"})
        finally:
            store.delete_secret()
        self.assertEqual(store.status(), {"is_configured": False, "key_suffix": None})


class ProxyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def test_validate_recognition_request_accepts_png_and_strokes(self):
        payload = {
            "png_data_url": "data:image/png;base64,iVBORw0KGgo=",
            "stroke_json": {"schemaVersion": 1, "pages": []},
        }
        result = self.api.validate_recognition_request(payload)
        self.assertEqual(result["png_data_url"], payload["png_data_url"])
        self.assertEqual(len(result["chunks"]), 1)

    def test_validate_recognition_request_accepts_ordered_chunks(self):
        png = "data:image/png;base64,iVBORw0KGgo="
        result = self.api.validate_recognition_request(
            {
                "chunks": [
                    {"page_id": "page-2", "index": 1, "png_data_url": png},
                    {"page_id": "page-1", "index": 0, "png_data_url": png},
                ],
                "stroke_json": {"schemaVersion": 2, "pages": []},
            }
        )
        self.assertEqual(
            [(item["page_id"], item["index"]) for item in result["chunks"]],
            [("page-2", 1), ("page-1", 0)],
        )

    def test_recognize_chunks_calls_relay_in_order_and_deduplicates_overlap(self):
        calls = []
        responses = iter(
            [
                {
                    "id": "resp-1",
                    "model": "gpt-5.6-luna",
                    "output": [{"content": [{"type": "output_text", "text": json.dumps({
                        "date": None,
                        "sections": [{"title": "正文", "transcript": "ROC 是收敛域，右边信号"}],
                        "critical_formulas": [{"latex": "X(s)", "meaning": "变换"}],
                        "diagram_notes": [],
                        "uncertain": [],
                    }, ensure_ascii=False)}]}],
                },
                {
                    "id": "resp-2",
                    "model": "gpt-5.6-luna",
                    "output": [{"content": [{"type": "output_text", "text": json.dumps({
                        "date": None,
                        "sections": [{"title": "正文", "transcript": "右边信号对应右半平面。"}],
                        "critical_formulas": [{"latex": "X(s)", "meaning": "变换"}],
                        "diagram_notes": ["s 平面"],
                        "uncertain": ["边界开闭待确认"],
                    }, ensure_ascii=False)}]}],
                },
            ]
        )

        def relay(image):
            calls.append(image)
            return next(responses)

        chunks = [
            {"page_id": "p", "index": 0, "png_data_url": "first"},
            {"page_id": "p", "index": 1, "png_data_url": "second"},
        ]
        result = self.api.recognize_chunks({"chunks": chunks}, relay=relay)
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(len(result["sections"]), 1)
        self.assertEqual(
            result["sections"][0]["transcript"],
            "ROC 是收敛域，右边信号对应右半平面。",
        )
        self.assertEqual(len(result["critical_formulas"]), 1)
        self.assertEqual(result["diagram_notes"], ["s 平面"])
        self.assertEqual(result["uncertain"], ["边界开闭待确认"])

    def test_recognition_overlap_is_not_deduplicated_across_pages(self):
        responses = iter(
            [
                {"id": "p1", "output": [{"content": [{"type": "output_text", "text": json.dumps({
                    "date": None,
                    "sections": [{"title": "正文", "transcript": "第一页 XYZ"}],
                    "critical_formulas": [], "diagram_notes": [], "uncertain": [],
                }, ensure_ascii=False)}]}]},
                {"id": "p2", "output": [{"content": [{"type": "output_text", "text": json.dumps({
                    "date": None,
                    "sections": [{"title": "正文", "transcript": "XYZ 第二页"}],
                    "critical_formulas": [], "diagram_notes": [], "uncertain": [],
                }, ensure_ascii=False)}]}]},
            ]
        )
        result = self.api.recognize_chunks(
            {"chunks": [
                {"page_id": "page-1", "index": 0, "png_data_url": "one"},
                {"page_id": "page-2", "index": 0, "png_data_url": "two"},
            ]},
            relay=lambda _image: next(responses),
        )
        self.assertEqual(
            [section["transcript"] for section in result["sections"]],
            ["第一页 XYZ", "XYZ 第二页"],
        )

    def test_validate_recognition_request_rejects_non_png(self):
        with self.assertRaisesRegex(ValueError, "PNG"):
            self.api.validate_recognition_request(
                {
                    "png_data_url": "data:image/jpeg;base64,AA==",
                    "stroke_json": {},
                }
            )

    def test_extract_output_json_handles_code_fence(self):
        response = {
            "id": "resp_test",
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                "```json\n"
                                '{"sections":[],"critical_formulas":[],'
                                '"diagram_notes":[],"uncertain":[]}\n'
                                "```"
                            ),
                        }
                    ]
                }
            ],
        }
        parsed = self.api.extract_model_result(response)
        self.assertEqual(parsed["request_id"], "resp_test")
        self.assertEqual(parsed["sections"], [])

    def test_build_relay_payload_contains_image_not_strokes(self):
        result = self.api.build_relay_payload("data:image/png;base64,AA==")
        serialized = json.dumps(result)
        self.assertIn("input_image", serialized)
        self.assertNotIn("stroke_json", serialized)

    def test_chat_completion_payload_uses_openai_compatible_image_url(self):
        original_protocol = self.api.RELAY_PROTOCOL
        self.api.RELAY_PROTOCOL = "chat_completions"
        try:
            result = self.api.build_relay_payload("data:image/png;base64,AA==")
        finally:
            self.api.RELAY_PROTOCOL = original_protocol
        content = result["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(content[1]["image_url"]["url"], "data:image/png;base64,AA==")

    def test_chat_completion_response_converts_to_output_text(self):
        normalized = self.api.normalize_chat_completion_response(
            {
                "id": "chat_test",
                "model": "gemini-2.5-flash",
                "choices": [{"message": {"content": "{\"sections\":[]}"}}],
            }
        )
        self.assertEqual(normalized["id"], "chat_test")
        self.assertEqual(normalized["model"], "gemini-2.5-flash")
        self.assertEqual(normalized["output"][0]["content"][0]["text"], "{\"sections\":[]}")

    def test_resolve_api_key_prefers_environment(self):
        key = self.api.resolve_api_key(
            environ={"LEARNING_OS_API_KEY": "env-key"},
            auth_path=Path("missing.json"),
        )
        self.assertEqual(key, "env-key")

    def test_resolve_api_key_reads_codex_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"
            path.write_text('{"OPENAI_API_KEY":"stored-key"}', encoding="utf-8")
            key = self.api.resolve_api_key(environ={}, auth_path=path)
        self.assertEqual(key, "stored-key")

    def test_normalize_upstream_error_hides_body(self):
        error = self.api.normalize_upstream_error(
            RuntimeError("secret upstream body")
        )
        self.assertEqual(error, "Vision service request failed")

    def test_upstream_timeout_is_reported_without_exposing_details(self):
        error = self.api.normalize_upstream_error(
            TimeoutError("secret upstream body")
        )
        self.assertEqual(error, "Vision service timed out; try again later")

    def test_upstream_http_status_is_safe_and_actionable(self):
        error = self.api.normalize_upstream_error(
            urllib.error.HTTPError("https://relay.test", 502, "Bad Gateway", {}, None)
        )
        self.assertEqual(error, "Vision service unavailable (upstream HTTP 502)")

    def test_relay_deadline_returns_without_waiting_for_blocked_upstream(self):
        started = threading.Event()
        release = threading.Event()

        def blocked():
            started.set()
            release.wait(1)

        try:
            with self.assertRaises(TimeoutError):
                self.api.call_with_deadline(blocked, timeout_seconds=0.01)
            self.assertTrue(started.is_set())
        finally:
            release.set()

    def test_validate_bind_host_rejects_non_loopback(self):
        self.assertEqual(self.api.validate_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(self.api.validate_bind_host("localhost"), "localhost")
        with self.assertRaisesRegex(ValueError, "loopback"):
            self.api.validate_bind_host("0.0.0.0")

    @unittest.skipUnless(
        os.environ.get("LEARNING_OS_LIVE_TEST") == "1",
        "set LEARNING_OS_LIVE_TEST=1 to call the configured relay",
    )
    def test_live_relay_recognizes_reference_handwriting(self):
        png = (ROOT / "outputs" / "recap-page-1-160dpi.png").read_bytes()
        data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        result = self.api.extract_model_result(self.api.call_relay(data_url))
        self.assertIn("sections", result)
        self.assertIn("critical_formulas", result)
        formulas = " ".join(
            item.get("latex", "") for item in result["critical_formulas"]
        ).replace(" ", "")
        self.assertIn("X(s)", formulas)
        self.assertIn("s+", formulas)


class ProxyHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def setUp(self):
        self.original_call_relay = self.api.call_relay
        self.api.call_relay = lambda _image: {
            "id": "resp_http_test",
            "model": "gpt-5.6-luna",
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "date": None,
                                    "sections": [],
                                    "critical_formulas": [],
                                    "diagram_notes": [],
                                    "uncertain": [],
                                }
                            ),
                        }
                    ]
                }
            ],
        }
        self.server = self.api.ThreadingHTTPServer(
            ("127.0.0.1", 0), self.api.LearningOSHandler
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.api.call_relay = self.original_call_relay

    @staticmethod
    def _valid_body():
        return json.dumps(
            {
                "png_data_url": "data:image/png;base64,iVBORw0KGgo=",
                "stroke_json": {"schemaVersion": 1, "pages": []},
            }
        ).encode("utf-8")

    def test_options_allows_only_local_ui_origin(self):
        request = urllib.request.Request(
            self.base_url + "/api/v1/handwriting/recognize",
            headers={"Origin": "http://127.0.0.1:4173"},
            method="OPTIONS",
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(
                response.headers["Access-Control-Allow-Origin"],
                "http://127.0.0.1:4173",
            )

    def test_options_allows_local_ui_origin_for_v2_requests(self):
        request = urllib.request.Request(
            self.base_url + "/api/v2/dashboard?date=2026-07-21",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "GET",
            },
            method="OPTIONS",
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(
                response.headers["Access-Control-Allow-Origin"],
                "http://127.0.0.1:4173",
            )
            self.assertIn("GET", response.headers["Access-Control-Allow-Methods"])

    def test_post_rejects_untrusted_origin(self):
        request = urllib.request.Request(
            self.base_url + "/api/v1/handwriting/recognize",
            data=self._valid_body(),
            headers={
                "Content-Type": "application/json",
                "Origin": "https://example.test",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)
        self.assertEqual(context.exception.code, 403)

    def test_post_returns_structured_result_and_cors(self):
        request = urllib.request.Request(
            self.base_url + "/api/v1/handwriting/recognize",
            data=self._valid_body(),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:4173",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(result["request_id"], "resp_http_test")
            self.assertEqual(
                response.headers["Access-Control-Allow-Origin"],
                "http://127.0.0.1:4173",
            )

    def test_post_rejects_oversized_body_without_reading_it(self):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2
        )
        connection.putrequest("POST", "/api/v1/handwriting/recognize")
        connection.putheader("Origin", "http://127.0.0.1:4173")
        connection.putheader("Content-Length", str(self.api.MAX_BODY_BYTES + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        connection.close()

    def test_upstream_error_body_is_not_exposed(self):
        def fail(_image):
            raise RuntimeError("secret upstream response")

        self.api.call_relay = fail
        request = urllib.request.Request(
            self.base_url + "/api/v1/handwriting/recognize",
            data=self._valid_body(),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:4173",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)
        body = context.exception.read().decode("utf-8")
        self.assertEqual(context.exception.code, 502)
        self.assertIn("Vision service request failed", body)
        self.assertNotIn("secret upstream response", body)

    def test_upstream_timeout_returns_gateway_timeout(self):
        def fail(_image):
            raise TimeoutError("secret upstream body")

        self.api.call_relay = fail
        request = urllib.request.Request(
            self.base_url + "/api/v1/handwriting/recognize",
            data=self._valid_body(),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:4173",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)
        body = json.loads(context.exception.read().decode("utf-8"))
        self.assertEqual(context.exception.code, 504)
        self.assertEqual(body["error"], "Vision service timed out; try again later")


class LearningOSV2HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.service = self.api.LearningOSService(
            Path(self.temporary.name), auto_assess=False
        )
        self.server = self.api.ThreadingHTTPServer(
            ("127.0.0.1", 0), self.api.LearningOSHandler
        )
        self.server.service = self.service
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.temporary.cleanup()

    def _request(self, method, path, payload=None):
        request = urllib.request.Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:4173",
            },
            method=method,
        )
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_dashboard_returns_empty_local_first_state(self):
        status, body = self._request("GET", "/api/v2/dashboard?date=2026-07-21")
        self.assertEqual(status, 200)
        self.assertIsNone(body["current_task"])
        self.assertEqual(body["review"]["target_count"], 5)

    def test_task_and_error_question_resources_feed_dashboard_and_review(self):
        status, task = self._request(
            "POST", "/api/v2/tasks",
            {"title": "复习极限", "study_date": "2026-07-21", "priority": "high"},
        )
        self.assertEqual(status, 201)
        status, question = self._request(
            "POST", "/api/v2/error-questions",
            {"subject": "高等数学", "title": "极限错题", "priority": "high", "next_review_date": "2026-07-21"},
        )
        self.assertEqual(status, 201)
        _, dashboard = self._request("GET", "/api/v2/dashboard?date=2026-07-21")
        self.assertEqual(dashboard["current_task"]["id"], task["id"])
        self.assertEqual(dashboard["review"]["items"][0]["id"], question["id"])

    def test_ai_analysis_and_chat_reply_are_saved_through_v2_routes(self):
        class FakeAI:
            def analyze_error_question(self, question):
                return {
                    "information_sufficient": True,
                    "primary_error_type": "计算错误",
                    "secondary_error_types": [],
                    "error_step": "化简步骤",
                    "evidence": [question["work_text"]],
                    "thinking_difference": "应逐项检查",
                    "knowledge_points": ["极限"],
                    "next_time_check": ["核对符号"],
                    "improvement_suggestion": "逐项核对符号",
                    "review_priority": "medium",
                    "long_term_weakness": False,
                    "questions": [],
                }

            def answer_chat(self, messages):
                return "请先写出已知条件。"

        self.service.ai = FakeAI()
        _, question = self._request(
            "POST", "/api/v2/error-questions",
            {"subject": "高等数学", "title": "极限", "work_text": "把负号漏掉"},
        )
        status, analysis = self._request("POST", f"/api/v2/error-questions/{question['id']}/analyze", {})
        self.assertEqual(status, 201)
        self.assertEqual(analysis["primary_error_type"], "计算错误")
        _, chat = self._request("POST", "/api/v2/chats", {"title": "学习咨询"})
        status, reply = self._request("POST", f"/api/v2/chats/{chat['id']}/messages", {"role": "user", "content": "怎么开始？"})
        self.assertEqual(status, 201)
        self.assertEqual(reply["assistant"]["content"], "请先写出已知条件。")


    def test_chat_user_message_survives_a_provider_failure_with_a_stable_error(self):
        class FailingAI:
            def answer_chat(self, _messages):
                raise self.api.AI_MODULE.AIProviderError(
                    "AI_TIMEOUT", "AI provider timed out or could not be reached.", 504
                )

        failing_ai = FailingAI()
        failing_ai.api = self.api
        self.service.ai = failing_ai
        _, chat = self._request("POST", "/api/v2/chats", {"title": "QA_TEST_PROVIDER_FAILURE"})
        request = urllib.request.Request(
            f"{self.base_url}/api/v2/chats/{chat['id']}/messages",
            data=json.dumps({"role": "user", "content": "QA_TEST_KEEP_ME"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:4173"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request)
        self.assertEqual(raised.exception.code, 504)
        body = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(body["code"], "AI_TIMEOUT")
        self.assertNotIn("AI_TEST_SECRET", json.dumps(body))
        messages = self.service.core.list_chat_messages(chat["id"])
        self.assertEqual([(message["role"], message["content"]) for message in messages], [("user", "QA_TEST_KEEP_ME")])


class EvidenceHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.service = self.api.LearningOSService(
            Path(self.temporary.name),
            auto_assess=False,
        )
        self.server = self.api.ThreadingHTTPServer(
            ("127.0.0.1", 0), self.api.LearningOSHandler
        )
        self.server.service = self.service
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.temporary.cleanup()

    @staticmethod
    def _png_data_url():
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    def _evidence_payload(self, submission_id="submission-1"):
        return {
            "submission_id": submission_id,
            "aggregate": {"type": "knowledge-point", "id": "laplace-roc"},
            "question": "解释拉普拉斯变换的 ROC。",
            "transcript": "ROC 为收敛域。",
            "transcript_confirmed": True,
            "handwriting": {
                "schemaVersion": 2,
                "coordinateSpace": "world-css-px",
                "pages": [],
            },
            "images": [
                {
                    "page_id": "page-1",
                    "index": 0,
                    "png_data_url": self._png_data_url(),
                }
            ],
        }

    def _request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:4173",
            },
            method=method,
        )
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_submit_is_persisted_and_idempotent(self):
        status, created = self._request(
            "POST", "/api/v1/evidence", self._evidence_payload()
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["status"], "assessing")
        self.assertEqual(created["artifact_integrity"], "verified")
        self.assertRegex(created["event_id"], r"^[0-9a-f-]{36}$")

        repeat_status, repeated = self._request(
            "POST", "/api/v1/evidence", self._evidence_payload()
        )
        self.assertEqual(repeat_status, 200)
        self.assertEqual(repeated["event_id"], created["event_id"])
        self.assertEqual(repeated["evidence_id"], created["evidence_id"])

    def test_detail_list_timeline_and_projection(self):
        _, created = self._request(
            "POST", "/api/v1/evidence", self._evidence_payload()
        )
        _, detail = self._request(
            "GET", f"/api/v1/evidence/{created['evidence_id']}"
        )
        self.assertEqual(detail["evidence_id"], created["evidence_id"])
        self.assertEqual(detail["status"], "assessing")
        self.assertNotIn("png_data_url", json.dumps(detail))

        _, listing = self._request(
            "GET",
            "/api/v1/evidence?aggregate_type=knowledge-point&aggregate_id=laplace-roc",
        )
        self.assertEqual(len(listing["items"]), 1)

        _, timeline = self._request(
            "GET",
            "/api/v1/timeline?aggregate_type=knowledge-point&aggregate_id=laplace-roc",
        )
        self.assertEqual(
            [event["event_type"] for event in timeline["events"]],
            ["EvidenceExtracted", "AssessmentRequested"],
        )

        _, projection = self._request(
            "GET",
            "/api/v1/projection?aggregate_type=knowledge-point&aggregate_id=laplace-roc",
        )
        self.assertEqual(projection["assessment_status"], "assessing")

    def test_rejects_unconfirmed_transcript_and_missing_images(self):
        unconfirmed = self._evidence_payload("submission-2")
        unconfirmed["transcript_confirmed"] = False
        with self.assertRaises(urllib.error.HTTPError) as context:
            self._request("POST", "/api/v1/evidence", unconfirmed)
        self.assertEqual(context.exception.code, 400)

        missing = self._evidence_payload("submission-3")
        missing["images"] = []
        with self.assertRaises(urllib.error.HTTPError) as context:
            self._request("POST", "/api/v1/evidence", missing)
        self.assertEqual(context.exception.code, 400)

    def test_rejects_empty_answer_without_ink_or_text(self):
        payload = self._evidence_payload("submission-empty")
        payload["transcript"] = None
        payload["transcript_confirmed"] = False
        payload["handwriting"]["pages"] = [{"id": "page-1", "strokes": []}]
        with self.assertRaises(urllib.error.HTTPError) as context:
            self._request("POST", "/api/v1/evidence", payload)
        self.assertEqual(context.exception.code, 400)

    def test_unknown_evidence_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            self._request("GET", "/api/v1/evidence/missing")
        self.assertEqual(context.exception.code, 404)


class ImmediateExecutor:
    def submit(self, function, *args, **kwargs):
        result = function(*args, **kwargs)

        class CompletedFuture:
            def result(self):
                return result

        return CompletedFuture()


class AssessmentServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _valid_assessment():
        return {
            "summary": "核心结论正确",
            "correct_points": ["写出了 ROC 边界"],
            "missing_points": ["未讨论双边信号"],
            "incorrect_points": [],
            "formula_feedback": ["X(s) 正确"],
            "f_state": "F3",
            "recommended_action": "补充双边信号后再答一次",
            "uncertain": [],
        }

    @staticmethod
    def _payload():
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        return {
            "submission_id": "assessment-submission",
            "aggregate": {"type": "knowledge-point", "id": "laplace-roc"},
            "question": "解释拉普拉斯变换的 ROC。",
            "transcript": "ROC 为收敛域。",
            "transcript_confirmed": True,
            "handwriting": {
                "schemaVersion": 2,
                "coordinateSpace": "world-css-px",
                "pages": [],
            },
            "images": [{
                "page_id": "page-1",
                "index": 0,
                "png_data_url": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
            }],
        }

    def _service(self, relay):
        return self.api.LearningOSService(
            Path(self.temporary.name),
            relay=relay,
            executor=ImmediateExecutor(),
            auto_assess=True,
        )

    def test_valid_assessment_is_appended_and_projected(self):
        service = self._service(lambda _request: self._valid_assessment())
        try:
            _, created = service.submit_evidence(self._payload())
            detail = service.get_evidence(created["evidence_id"])
            self.assertEqual(detail["status"], "recorded")
            self.assertEqual(detail["assessment"]["f_state"], "F3")
            projection = service.projection("knowledge-point", "laplace-roc")
            self.assertEqual(projection["f_state"], "F3")
            self.assertEqual(projection["assessment_status"], "recorded")
        finally:
            service.close()

    def test_typed_only_answer_is_persisted_and_assessed(self):
        captured = {}

        def relay(request):
            captured.update(request)
            return self._valid_assessment()

        payload = self._payload()
        payload["transcript"] = None
        payload["transcript_confirmed"] = False
        payload["typed_answer"] = "ROC 是拉普拉斯变换的收敛域。"
        service = self._service(relay)
        try:
            _, created = service.submit_evidence(payload)
            detail = service.get_evidence(created["evidence_id"])
            self.assertEqual(detail["typed_answer"], payload["typed_answer"])
            self.assertEqual(captured["transcript"], payload["typed_answer"])
            self.assertEqual(captured["answer_source"], "typed_answer")
            paths = {
                record["path"]
                for record in detail["artifact_files"]
            }
            self.assertIn("typed-answer.txt", paths)
            timeline = service.timeline("knowledge-point", "laplace-roc")["events"]
            evidence = next(
                event for event in timeline
                if event["event_type"] == "EvidenceExtracted"
            )
            self.assertEqual(
                evidence["payload"]["typed_answer"], payload["typed_answer"]
            )
        finally:
            service.close()

    def test_invalid_output_appends_sanitized_failure(self):
        service = self._service(lambda _request: {"summary": "missing fields"})
        try:
            _, created = service.submit_evidence(self._payload())
            detail = service.get_evidence(created["evidence_id"])
            self.assertEqual(detail["status"], "failed")
            self.assertEqual(detail["failure"]["category"], "invalid_output")
            self.assertNotIn("missing fields", json.dumps(detail))
        finally:
            service.close()

    def test_upstream_error_is_sanitized_and_retry_appends_events(self):
        def fail(_request):
            raise RuntimeError("secret upstream response")

        service = self._service(fail)
        try:
            _, created = service.submit_evidence(self._payload())
            evidence_id = created["evidence_id"]
            failed = service.get_evidence(evidence_id)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["failure"]["category"], "upstream_error")
            self.assertNotIn("secret upstream response", json.dumps(failed))

            service.relay = lambda _request: self._valid_assessment()
            retry = service.retry_assessment(evidence_id)
            self.assertEqual(retry["status"], "recorded")
            timeline = service.timeline("knowledge-point", "laplace-roc")["events"]
            kinds = [event["event_type"] for event in timeline]
            self.assertEqual(kinds.count("AssessmentRequested"), 2)
            self.assertEqual(kinds.count("AssessmentFailed"), 1)
            self.assertEqual(kinds.count("AssessmentRecorded"), 1)
        finally:
            service.close()

    def test_concurrent_duplicate_submission_creates_one_evidence(self):
        service = self.api.LearningOSService(
            Path(self.temporary.name),
            auto_assess=False,
        )
        original_write = service.artifacts.write_evidence
        first_write_started = threading.Event()

        def slow_write(*args, **kwargs):
            first_write_started.set()
            time.sleep(0.15)
            return original_write(*args, **kwargs)

        service.artifacts.write_evidence = slow_write
        results = []
        errors = []

        def submit():
            try:
                results.append(service.submit_evidence(self._payload()))
            except Exception as error:
                errors.append(error)

        first = threading.Thread(target=submit)
        second = threading.Thread(target=submit)
        try:
            first.start()
            self.assertTrue(first_write_started.wait(timeout=2))
            second.start()
            first.join(timeout=3)
            second.join(timeout=3)
            self.assertFalse(errors)
            self.assertEqual(len(results), 2)
            self.assertEqual({status for status, _ in results}, {200, 201})
            self.assertEqual(
                len({result["evidence_id"] for _, result in results}), 1
            )
            self.assertEqual(len(service.store.list_evidence()), 1)
        finally:
            service.close()

    def test_running_assessment_cannot_be_retried(self):
        service = self.api.LearningOSService(
            Path(self.temporary.name),
            auto_assess=False,
        )
        try:
            _, created = service.submit_evidence(self._payload())
            evidence_id = created["evidence_id"]
            with service._jobs_lock:
                service._jobs[evidence_id] = object()
            with self.assertRaisesRegex(ValueError, "already running"):
                service.retry_assessment(evidence_id)
            timeline = service.timeline("knowledge-point", "laplace-roc")["events"]
            self.assertEqual(
                [event["event_type"] for event in timeline].count("AssessmentRequested"),
                1,
            )
        finally:
            service.close()

    def test_new_assessment_request_clears_prior_failure_in_detail(self):
        service = self.api.LearningOSService(
            Path(self.temporary.name),
            auto_assess=False,
        )
        try:
            _, created = service.submit_evidence(self._payload())
            evidence_id = created["evidence_id"]
            service.store.append(
                "AssessmentFailed",
                "knowledge-point",
                "laplace-roc",
                {
                    "failure_id": "failure-1",
                    "evidence_id": evidence_id,
                    "category": "upstream_error",
                    "retryable": True,
                },
            )
            service.store.append(
                "AssessmentRequested",
                "knowledge-point",
                "laplace-roc",
                {"evidence_id": evidence_id, "job_id": "job-2"},
            )
            detail = service.get_evidence(evidence_id)
            self.assertEqual(detail["status"], "assessing")
            self.assertIsNone(detail["failure"])
            self.assertIsNone(detail["assessment"])
        finally:
            service.close()

    @unittest.skipUnless(
        os.environ.get("LEARNING_OS_LIVE_TEST") == "1",
        "set LEARNING_OS_LIVE_TEST=1 to call the configured relay",
    )
    def test_live_assessment_persists_and_projects_state(self):
        payload = self._payload()
        png = (ROOT / "outputs" / "recap-page-1-160dpi.png").read_bytes()
        payload["submission_id"] = "live-assessment-submission"
        payload["images"] = [{
            "page_id": "page-1",
            "index": 0,
            "png_data_url": (
                "data:image/png;base64," + base64.b64encode(png).decode("ascii")
            ),
        }]
        service = self.api.LearningOSService(
            Path(self.temporary.name),
            executor=ImmediateExecutor(),
            auto_assess=True,
        )
        try:
            status, created = service.submit_evidence(payload)
            self.assertEqual(status, 201)
            detail = service.get_evidence(created["evidence_id"])
            self.assertEqual(detail["status"], "recorded")
            self.assertEqual(
                set(detail["assessment"]) - {
                    "assessment_id", "evidence_id", "model", "request_id"
                },
                {
                    "summary",
                    "correct_points",
                    "missing_points",
                    "incorrect_points",
                    "formula_feedback",
                    "f_state",
                    "recommended_action",
                    "uncertain",
                },
            )
            projection = service.projection("knowledge-point", "laplace-roc")
            self.assertEqual(projection["assessment_status"], "recorded")
            self.assertRegex(projection["f_state"], r"^F[0-5]$")
            kinds = [
                event["event_type"]
                for event in service.timeline("knowledge-point", "laplace-roc")["events"]
            ]
            self.assertIn("EvidenceExtracted", kinds)
            self.assertIn("AssessmentRecorded", kinds)
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
