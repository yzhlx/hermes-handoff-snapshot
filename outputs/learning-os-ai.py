"""Provider adapter and response contracts for Hermes Learning OS AI features."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


ERROR_TYPES = (
    "概念或知识点不理解", "公式、定理或定义记忆错误", "审题错误", "解题思路错误",
    "推理过程错误", "计算错误", "变形或符号错误", "方法选择错误", "盲目套公式",
    "题型识别错误", "粗心或注意力问题", "时间管理问题", "其他无法归类的原因",
)
REVIEW_PRIORITIES = ("high", "medium", "low")
DEFAULT_TIMEOUT_SECONDS = 30
MIN_TIMEOUT_SECONDS = 5
MAX_TIMEOUT_SECONDS = 120
HERMES_SYSTEM_INSTRUCTIONS = (
    "You are Hermes, a learning assistant. Use simplified Chinese when possible. "
    "Give actionable next steps, distinguish facts from inference, ask for missing "
    "evidence, do not claim that viewing an answer means mastery, and do not provide "
    "medical diagnoses or invent learning records."
)


class AIProviderError(RuntimeError):
    """A stable, secret-safe provider error suitable for the local API boundary."""

    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code = code
        self.status = status

    def payload(self) -> dict:
        return {"code": self.code, "error": str(self)}


def _load_credentials_module():
    import importlib.util

    path = Path(__file__).with_name("learning-os-credentials.py")
    spec = importlib.util.spec_from_file_location("learning_os_credentials", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _text(value: object, name: str, required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{name} is required")
    return value.strip()


def _texts(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must be a list of text")
    return [item.strip() for item in value]


def _timeout(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("AI timeout must be an integer")
    try:
        seconds = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("AI timeout must be an integer") from error
    if not MIN_TIMEOUT_SECONDS <= seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"AI timeout must be {MIN_TIMEOUT_SECONDS} to {MAX_TIMEOUT_SECONDS} seconds")
    return seconds


def normalize_provider_url(base_url: str, protocol: str) -> str:
    """Accept a provider root, /v1 root, or the exact endpoint without mixing protocols."""

    if protocol not in {"chat_completions", "responses"}:
        raise AIProviderError("AI_UNSUPPORTED_PROTOCOL", "Unsupported AI provider protocol.", 400)
    if not isinstance(base_url, str) or not base_url.strip():
        raise AIProviderError("AI_INVALID_BASE_URL", "Please provide an AI service URL.", 400)
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise AIProviderError("AI_INVALID_BASE_URL", "AI service URL must be a valid HTTPS URL without query parameters.", 400)

    endpoint = "chat/completions" if protocol == "chat_completions" else "responses"
    opposite = "responses" if protocol == "chat_completions" else "chat/completions"
    path = parsed.path.rstrip("/")
    if path.endswith(f"/{opposite}"):
        raise AIProviderError("AI_UNSUPPORTED_PROTOCOL", "The configured endpoint does not match the selected AI protocol.", 400)
    if protocol == "chat_completions" and path.endswith("/chat"):
        path = f"{path}/completions"
    if not path.endswith(f"/{endpoint}"):
        if not path or path.endswith("/v1"):
            path = f"{path}/" if path else "/v1/"
        else:
            path = f"{path}/"
        path = f"{path}{endpoint}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _extract_chat_content(response: object) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid Chat Completions response.") from error
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"text", "output_text"} and isinstance(item.get("text"), str):
                parts.append(item["text"].strip())
        return "\n".join(part for part in parts if part)
    raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid Chat Completions message.")


def _extract_responses_text(response: object) -> str:
    if isinstance(response, dict) and isinstance(response.get("output_text"), str):
        return response["output_text"].strip()
    try:
        output = response["output"]
    except (KeyError, TypeError) as error:
        raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid Responses response.") from error
    if not isinstance(output, list):
        raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid Responses output.")
    parts: list[str] = []
    for output_item in output:
        if not isinstance(output_item, dict) or not isinstance(output_item.get("content"), list):
            continue
        for content_item in output_item["content"]:
            if isinstance(content_item, dict) and content_item.get("type") == "output_text" and isinstance(content_item.get("text"), str):
                parts.append(content_item["text"].strip())
    return "\n".join(part for part in parts if part)


def _provider_error_from_http(status: int) -> AIProviderError:
    if status in {401, 403}:
        return AIProviderError("AI_AUTH_FAILED", "AI authentication failed. Check the API key.", 401)
    if status == 404:
        return AIProviderError("AI_MODEL_NOT_FOUND", "AI model or endpoint was not found. Check the model and URL.", 404)
    if status == 429:
        return AIProviderError("AI_RATE_LIMITED", "AI provider rate limit reached. Try again later.", 429)
    if 500 <= status <= 599:
        return AIProviderError("AI_PROVIDER_UNAVAILABLE", "AI provider is temporarily unavailable. Try again later.", 502)
    return AIProviderError("AI_PROVIDER_UNAVAILABLE", "AI provider rejected the request.", 502)


def validate_error_analysis(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("information_sufficient"), bool):
        raise ValueError("information_sufficient is required")
    sufficient = payload["information_sufficient"]
    questions = _texts(payload.get("questions", []), "questions")[:3]
    if not sufficient:
        return {
            "information_sufficient": False,
            "missing_information": _texts(payload.get("missing_information", []), "missing_information"),
            "questions": questions,
        }
    primary = _text(payload.get("primary_error_type"), "primary_error_type")
    secondary = _texts(payload.get("secondary_error_types", []), "secondary_error_types")
    if primary not in ERROR_TYPES or any(item not in ERROR_TYPES for item in secondary):
        raise ValueError("Unsupported error type")
    suggestion = _text(payload.get("improvement_suggestion"), "improvement_suggestion")
    if len(suggestion) > 30:
        raise ValueError("improvement_suggestion must be at most 30 characters")
    priority = _text(payload.get("review_priority"), "review_priority")
    if priority not in REVIEW_PRIORITIES:
        raise ValueError("Unsupported review priority")
    if not isinstance(payload.get("long_term_weakness"), bool):
        raise ValueError("long_term_weakness must be a boolean")
    return {
        "information_sufficient": True,
        "primary_error_type": primary,
        "secondary_error_types": secondary,
        "error_step": _text(payload.get("error_step"), "error_step"),
        "evidence": _texts(payload.get("evidence"), "evidence"),
        "thinking_difference": _text(payload.get("thinking_difference"), "thinking_difference"),
        "knowledge_points": _texts(payload.get("knowledge_points"), "knowledge_points"),
        "next_time_check": _texts(payload.get("next_time_check"), "next_time_check"),
        "improvement_suggestion": suggestion,
        "review_priority": priority,
        "long_term_weakness": payload["long_term_weakness"],
        "questions": questions,
    }


def _error_analysis_prompt(question: dict) -> str:
    return """You are a learning wrong-answer analysis assistant. Output JSON only. Do not guess when evidence is insufficient.
For insufficient evidence output:
{"information_sufficient":false,"missing_information":["..."],"questions":["..."]}
For sufficient evidence output:
{"information_sufficient":true,"primary_error_type":"...","secondary_error_types":["..."],"error_step":"...","evidence":["..."],"thinking_difference":"...","knowledge_points":["..."],"next_time_check":["..."],"improvement_suggestion":"under 30 chars","review_priority":"high|medium|low","long_term_weakness":true,"questions":[]}
Only use these error types: %s. Use the supplied data as evidence and never fabricate it. Data: %s""" % (
        "、".join(ERROR_TYPES), json.dumps(question, ensure_ascii=False),
    )


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return stripped.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    return stripped


class AIGateway:
    def __init__(self, core, credentials=None, request_json=None):
        self.core = core
        self.credentials = credentials or _load_credentials_module().WindowsCredentialStore()
        self.request_json = request_json or self._post_json

    def settings(self) -> dict:
        result = dict(self.core.get_ai_settings())
        result.update(self.credentials.status())
        return result

    def configure(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("AI settings must be an object")
        metadata = {key: value for key, value in payload.items() if key not in {"api_key", "clear_api_key"}}
        clear_secret = payload.get("clear_api_key", False)
        if not isinstance(clear_secret, bool):
            raise ValueError("clear_api_key must be a boolean")
        secret = payload.get("api_key")
        if clear_secret and secret:
            raise ValueError("Provide a new API key or clear the key, not both")
        # Validate the persistent configuration before changing an external credential.
        self.core.validate_ai_settings(metadata)
        if clear_secret:
            self.credentials.delete_secret()
        elif secret is not None:
            self.credentials.set_secret(secret)
        self.core.update_ai_settings(metadata)
        return self.settings()

    def validate_config(self) -> tuple[dict, str, int]:
        settings = self.core.get_ai_settings()
        if not settings.get("base_url") or not settings.get("model"):
            raise AIProviderError("AI_NOT_CONFIGURED", "AI is not configured. Save the provider URL and model first.", 400)
        secret = self.credentials.get_secret()
        if not secret:
            raise AIProviderError("AI_KEY_MISSING", "AI API key is missing. Save an API key in Settings.", 400)
        try:
            timeout_seconds = _timeout(settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        except ValueError as error:
            raise AIProviderError("AI_NOT_CONFIGURED", str(error), 400) from error
        return settings, secret, timeout_seconds

    @staticmethod
    def _post_json(url: str, headers: dict, payload: dict, timeout_seconds: int) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raise _provider_error_from_http(error.code) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise AIProviderError("AI_TIMEOUT", "AI provider timed out or could not be reached.", 504) from error
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned a non-JSON response.") from error
        if not isinstance(result, dict):
            raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid JSON response.")
        return result

    def _request(self, protocol: str, base_url: str, headers: dict, payload: dict, timeout_seconds: int) -> dict:
        url = normalize_provider_url(base_url, protocol)
        try:
            return self.request_json(url, headers, payload, timeout_seconds)
        except AIProviderError:
            raise
        except TimeoutError as error:
            raise AIProviderError("AI_TIMEOUT", "AI provider timed out or could not be reached.", 504) from error
        except urllib.error.HTTPError as error:
            raise _provider_error_from_http(error.code) from error
        except (urllib.error.URLError, OSError) as error:
            raise AIProviderError("AI_PROVIDER_UNAVAILABLE", "AI provider is unavailable. Check the service URL.") from error
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
            raise AIProviderError("AI_INVALID_RESPONSE", "AI provider returned an invalid response.") from error

    def generate_text(self, messages: list[dict], max_tokens: int = 1200) -> str:
        settings, secret, timeout_seconds = self.validate_config()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {secret}"}
        protocol = settings["protocol"]
        if protocol == "chat_completions":
            response = self._request(
                protocol, settings["base_url"], headers,
                {"model": settings["model"], "messages": messages, "max_tokens": max_tokens}, timeout_seconds,
            )
            content = _extract_chat_content(response)
        elif protocol == "responses":
            instructions = next((item["content"] for item in messages if item.get("role") == "system" and isinstance(item.get("content"), str)), HERMES_SYSTEM_INSTRUCTIONS)
            input_messages = [item for item in messages if item.get("role") != "system"]
            response = self._request(
                protocol, settings["base_url"], headers,
                {"model": settings["model"], "instructions": instructions, "input": input_messages, "max_output_tokens": max_tokens}, timeout_seconds,
            )
            content = _extract_responses_text(response)
        else:
            raise AIProviderError("AI_UNSUPPORTED_PROTOCOL", "Unsupported AI provider protocol.", 400)
        if not content:
            raise AIProviderError("AI_EMPTY_RESPONSE", "AI provider returned an empty response.")
        return content

    def test_connection(self) -> str:
        return self.answer_chat([{"role": "user", "content": "Reply with exactly: connection successful."}], max_tokens=20)

    def analyze_error_question(self, question: dict) -> dict:
        evidence_fields = ("problem_text", "work_text", "correct_answer", "explanation")
        if not isinstance(question, dict) or not any(isinstance(question.get(field), str) and question[field].strip() for field in evidence_fields):
            return {
                "information_sufficient": False,
                "missing_information": ["题目、作答过程、正确答案或解析"],
                "questions": ["请补充原题或你的作答过程，再分析错误原因。"],
            }
        raw = self.generate_text([{"role": "user", "content": _error_analysis_prompt(question)}])
        try:
            return validate_error_analysis(json.loads(_strip_json_fence(raw)))
        except json.JSONDecodeError as error:
            raise AIProviderError("AI_INVALID_RESPONSE", "AI analysis did not return valid JSON.") from error
        except ValueError as error:
            raise AIProviderError("AI_INVALID_RESPONSE", "AI analysis did not match the expected learning-analysis format.") from error

    def answer_chat(self, messages: list[dict], max_tokens: int = 1200) -> str:
        context = [{"role": "system", "content": HERMES_SYSTEM_INSTRUCTIONS}]
        context.extend(
            {"role": item["role"], "content": item["content"]}
            for item in messages[-12:]
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str) and item["content"].strip()
        )
        return self.generate_text(context, max_tokens)

    def extract_error_question(self, images: list[str]) -> dict:
        if not isinstance(images, list) or not images or len(images) > 6:
            raise ValueError("Please upload 1 to 6 images")
        settings, secret, timeout_seconds = self.validate_config()
        if settings["protocol"] != "chat_completions":
            raise AIProviderError("AI_VISION_UNSUPPORTED", "Image quick entry currently requires Chat Completions.", 400)
        prompt = "Recognize these wrong-answer images. Return JSON only with title, problem_text, work_text, correct_answer, explanation, subject, and chapter. Leave unreadable fields blank; never guess."
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": image, "detail": "high"}}
            for image in images
        ]
        response = self._request(
            "chat_completions", settings["base_url"],
            {"Content-Type": "application/json", "Authorization": f"Bearer {secret}"},
            {"model": settings["model"], "messages": [{"role": "user", "content": content}], "max_tokens": 1800}, timeout_seconds,
        )
        try:
            draft = json.loads(_strip_json_fence(_extract_chat_content(response)))
        except (json.JSONDecodeError, AIProviderError) as error:
            raise AIProviderError("AI_INVALID_RESPONSE", "AI did not return a usable wrong-answer draft.") from error
        if not isinstance(draft, dict):
            raise AIProviderError("AI_INVALID_RESPONSE", "AI did not return a usable wrong-answer draft.")
        return {key: str(draft.get(key, "") or "") for key in ("title", "problem_text", "work_text", "correct_answer", "explanation", "subject", "chapter")}
