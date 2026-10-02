import argparse
import base64
import binascii
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse
import uuid


MAX_BODY_BYTES = 24 * 1024 * 1024
RELAY_TIMEOUT_SECONDS = 20
MODEL = os.environ.get("LEARNING_OS_VISION_MODEL", "gpt-5.6-luna")
RELAY_URL = os.environ.get(
    "LEARNING_OS_RELAY_URL",
    "https://www.cctq.ai/v1/responses",
)
RELAY_PROTOCOL = os.environ.get("LEARNING_OS_RELAY_PROTOCOL", "responses")
ALLOWED_ORIGINS = {
    "http://127.0.0.1:4173",
    "http://localhost:4173",
}


def _load_store_module():
    path = Path(__file__).with_name("learning-os-store.py")
    spec = importlib.util.spec_from_file_location("learning_os_store", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_core_module():
    path = Path(__file__).with_name("learning-os-core.py")
    spec = importlib.util.spec_from_file_location("learning_os_core", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_ai_module():
    path = Path(__file__).with_name("learning-os-ai.py")
    spec = importlib.util.spec_from_file_location("learning_os_ai", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STORE_MODULE = _load_store_module()
CORE_MODULE = _load_core_module()
AI_MODULE = _load_ai_module()

# Cloud Hermes bridge (Track C). Imported defensively so a missing module never breaks the
# local-only path; the local provider code remains intact for rollback.
try:
    from learning_os_cloud_bridge import CloudBridge, CloudChatError
    _CLOUD_BRIDGE = CloudBridge()
except Exception:  # pragma: no cover - bridge optional in local-only mode
    CloudBridge = None
    CloudChatError = Exception
    _CLOUD_BRIDGE = None

TRANSCRIPTION_PROMPT = """You are transcribing a handwritten study answer from one PNG image.
Return only one valid JSON object with exactly these top-level keys:
{
  "date": string or null,
  "sections": [{"title": string, "transcript": string}],
  "critical_formulas": [{"latex": string, "meaning": string}],
  "diagram_notes": [string],
  "uncertain": [string]
}

Preserve the writer's wording and mathematical notation. Transcribe subscripts,
superscripts, Greek letters, inequality strictness (< versus <=), integration
limits, regions of convergence, arrows, labels, and units exactly. Use LaTeX
for formulas. Do not solve the problem, correct the answer, infer missing text,
or guess unreadable marks. Put every ambiguity or unreadable span in uncertain.
Use empty arrays when a category is absent. Do not emit Markdown fences or any
text outside the JSON object."""

ASSESSMENT_PROMPT = """Evaluate one active-recall answer against its question.
Return only one valid JSON object with exactly these top-level keys:
{
  "summary": string,
  "correct_points": [string],
  "missing_points": [string],
  "incorrect_points": [string],
  "formula_feedback": [string],
  "f_state": "F0" | "F1" | "F2" | "F3" | "F4" | "F5",
  "recommended_action": string,
  "uncertain": [string]
}

Assess only evidence visible in the submitted answer text and handwriting images.
Do not invent missing work. Put ambiguous handwriting or grading uncertainty in
uncertain. Do not emit Markdown fences or text outside the JSON object."""

ASSESSMENT_KEYS = {
    "summary",
    "correct_points",
    "missing_points",
    "incorrect_points",
    "formula_feedback",
    "f_state",
    "recommended_action",
    "uncertain",
}


def validate_recognition_request(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    if not isinstance(payload.get("stroke_json"), dict):
        raise ValueError("stroke_json must be an object")
    chunks = payload.get("chunks")
    if chunks is None:
        chunks = [{
            "page_id": "page",
            "index": 0,
            "png_data_url": payload.get("png_data_url"),
        }]
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("At least one PNG chunk is required")
    if len(chunks) > 12:
        raise ValueError("No more than 12 PNG chunks are allowed")
    validated_chunks = []
    for position, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise ValueError("Each PNG chunk must be an object")
        png_data_url = chunk.get("png_data_url")
        _decode_png_data_url(png_data_url)
        try:
            index = int(chunk.get("index", position))
        except (TypeError, ValueError) as exc:
            raise ValueError("Chunk index must be an integer") from exc
        validated_chunks.append({
            "page_id": str(chunk.get("page_id") or "page"),
            "index": index,
            "png_data_url": png_data_url,
        })
    return {
        "png_data_url": validated_chunks[0]["png_data_url"],
        "chunks": validated_chunks,
        "stroke_json": payload["stroke_json"],
    }


def build_relay_payload(png_data_url: str) -> dict:
    content = [
        {"type": "input_text", "text": TRANSCRIPTION_PROMPT},
        {
            "type": "input_image",
            "image_url": png_data_url,
            "detail": "high",
        },
    ]
    if RELAY_PROTOCOL == "chat_completions":
        return build_chat_completion_payload(content)
    return {
        "model": MODEL,
        "input": [{"role": "user", "content": content}],
        "max_output_tokens": 5000,
    }


def build_chat_completion_payload(content: list[dict]) -> dict:
    chat_content = []
    for item in content:
        if item["type"] == "input_text":
            chat_content.append({"type": "text", "text": item["text"]})
        elif item["type"] == "input_image":
            chat_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": item["image_url"],
                        "detail": item.get("detail", "high"),
                    },
                }
            )
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": chat_content}],
        "max_tokens": 5000,
    }


def normalize_chat_completion_response(response: dict) -> dict:
    try:
        content = response["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as exc:
        raise ValueError("Chat completion response has no message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Chat completion message content is invalid")
    return {
        "id": response.get("id"),
        "model": response.get("model", MODEL),
        "output": [{"content": [{"type": "output_text", "text": content}]}],
    }


def extract_model_result(response: dict) -> dict:
    chunks = [
        content["text"]
        for item in response.get("output", [])
        for content in item.get("content", [])
        if content.get("type") == "output_text" and content.get("text")
    ]
    text = "\n".join(chunks).strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    result = json.loads(text.strip())
    result["request_id"] = response.get("id")
    result["model"] = response.get("model", MODEL)
    result["confidence"] = None
    return result


def _merge_overlap(left: str, right: str) -> str:
    if not left:
        return right
    if not right or right in left:
        return left
    maximum = min(len(left), len(right))
    for size in range(maximum, 2, -1):
        if left[-size:] == right[:size]:
            return left + right[size:]
    return left + ("\n" if not left.endswith("\n") else "") + right


def _append_unique(target: list, values: object):
    if not isinstance(values, list):
        return
    seen = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in target}
    for item in values:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            target.append(item)
            seen.add(key)


def recognize_chunks(request_data: dict, relay=None) -> dict:
    relay = relay or call_relay
    merged = {
        "date": None,
        "sections": [],
        "critical_formulas": [],
        "diagram_notes": [],
        "uncertain": [],
        "request_id": None,
        "model": MODEL,
        "confidence": None,
    }
    previous_page_id = None
    for chunk in request_data["chunks"]:
        result = extract_model_result(relay(chunk["png_data_url"]))
        if merged["request_id"] is None:
            merged["request_id"] = result.get("request_id")
        merged["model"] = result.get("model") or merged["model"]
        merged["date"] = merged["date"] or result.get("date")
        for section in result.get("sections", []):
            if not isinstance(section, dict):
                continue
            title = str(section.get("title") or "")
            transcript = str(section.get("transcript") or "")
            if (
                merged["sections"]
                and previous_page_id == chunk.get("page_id")
                and merged["sections"][-1]["title"] == title
            ):
                merged["sections"][-1]["transcript"] = _merge_overlap(
                    merged["sections"][-1]["transcript"], transcript
                )
            else:
                merged["sections"].append({"title": title, "transcript": transcript})
        _append_unique(merged["critical_formulas"], result.get("critical_formulas"))
        _append_unique(merged["diagram_notes"], result.get("diagram_notes"))
        _append_unique(merged["uncertain"], result.get("uncertain"))
        previous_page_id = chunk.get("page_id")
    return merged


def resolve_api_key(
    environ=os.environ,
    auth_path=Path.home() / ".codex" / "auth.json",
):
    if environ.get("LEARNING_OS_API_KEY"):
        return environ["LEARNING_OS_API_KEY"]
    if auth_path.exists():
        data = json.loads(auth_path.read_text(encoding="utf-8"))
        if data.get("OPENAI_API_KEY"):
            return data["OPENAI_API_KEY"]
    raise RuntimeError("No server-side API credential is configured")


def post_relay(payload: dict, user_agent: str) -> dict:
    request = urllib.request.Request(
        RELAY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resolve_api_key()}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=RELAY_TIMEOUT_SECONDS) as response:
        upstream = json.loads(response.read().decode("utf-8"))
    if RELAY_PROTOCOL == "chat_completions":
        return normalize_chat_completion_response(upstream)
    return upstream


def call_relay(png_data_url: str) -> dict:
    return post_relay(build_relay_payload(png_data_url), "LearningOS/2.0")


def call_with_deadline(operation, timeout_seconds: float = RELAY_TIMEOUT_SECONDS):
    result = {}
    completed = threading.Event()

    def run():
        try:
            result["value"] = operation()
        except Exception as error:
            result["error"] = error
        finally:
            completed.set()

    threading.Thread(target=run, daemon=True).start()
    if not completed.wait(timeout_seconds):
        raise TimeoutError("Vision service deadline exceeded")
    if "error" in result:
        raise result["error"]
    return result["value"]


def build_assessment_relay_payload(request_data: dict) -> dict:
    answer_label = (
        "Typed answer"
        if request_data.get("answer_source") == "typed_answer"
        else "Confirmed transcript"
    )
    content = [
        {
            "type": "input_text",
            "text": (
                f"{ASSESSMENT_PROMPT}\n\n"
                f"Question:\n{request_data['question']}\n\n"
                f"{answer_label}:\n{request_data.get('transcript') or '[none]'}"
            ),
        }
    ]
    content.extend(
        {
            "type": "input_image",
            "image_url": image_url,
            "detail": "high",
        }
        for image_url in request_data["image_data_urls"]
    )
    if RELAY_PROTOCOL == "chat_completions":
        return build_chat_completion_payload(content)
    return {"model": MODEL, "input": [{"role": "user", "content": content}], "max_output_tokens": 5000}


def call_assessment_relay(request_data: dict) -> dict:
    result = extract_model_result(
        post_relay(build_assessment_relay_payload(request_data), "LearningOS/3.0")
    )
    result.pop("confidence", None)
    return result


def validate_assessment_result(result: object) -> dict:
    if not isinstance(result, dict) or set(result) - {"request_id", "model"} != ASSESSMENT_KEYS:
        raise ValueError("Assessment output keys are invalid")
    text_fields = ("summary", "recommended_action")
    if any(not isinstance(result.get(field), str) for field in text_fields):
        raise ValueError("Assessment text fields are invalid")
    list_fields = (
        "correct_points",
        "missing_points",
        "incorrect_points",
        "formula_feedback",
        "uncertain",
    )
    for field in list_fields:
        value = result.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"Assessment {field} must be a string array")
    if result.get("f_state") not in {f"F{index}" for index in range(6)}:
        raise ValueError("Assessment f_state is invalid")
    return {key: result[key] for key in ASSESSMENT_KEYS}


def normalize_upstream_error(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "Vision service timed out; try again later"
    if isinstance(error, urllib.error.HTTPError):
        return f"Vision service unavailable (upstream HTTP {error.code})"
    return "Vision service request failed"


def validate_bind_host(host: str) -> str:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Vision proxy must bind to a loopback host")
    return host


def _decode_png_data_url(value: object) -> bytes:
    if not isinstance(value, str) or not value.startswith("data:image/png;base64,"):
        raise ValueError("A PNG data URL is required")
    try:
        decoded = base64.b64decode(value.split(",", 1)[1], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("PNG Base64 is invalid") from exc
    if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Decoded payload is not a PNG")
    if len(decoded) > 5 * 1024 * 1024:
        raise ValueError("PNG exceeds the 5MB limit")
    return decoded


def validate_evidence_request(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    submission_id = payload.get("submission_id")
    if not isinstance(submission_id, str) or not submission_id.strip():
        raise ValueError("submission_id is required")
    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict):
        raise ValueError("aggregate is required")
    aggregate_type = aggregate.get("type")
    aggregate_id = aggregate.get("id")
    if not all(isinstance(value, str) and value for value in (aggregate_type, aggregate_id)):
        raise ValueError("aggregate type and id are required")
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    transcript = payload.get("transcript")
    if transcript is not None and not isinstance(transcript, str):
        raise ValueError("transcript must be a string or null")
    if transcript and not payload.get("transcript_confirmed"):
        raise ValueError("A non-empty transcript must be confirmed")
    typed_answer = payload.get("typed_answer")
    if typed_answer is not None and not isinstance(typed_answer, str):
        raise ValueError("typed_answer must be a string or null")
    handwriting = payload.get("handwriting")
    if not isinstance(handwriting, dict) or handwriting.get("schemaVersion") != 2:
        raise ValueError("schema v2 handwriting is required")
    pages = handwriting.get("pages")
    has_ink = isinstance(pages, list) and any(
        isinstance(page, dict) and any(
            isinstance(stroke, dict)
            and stroke.get("tool") == "draw"
            and isinstance(stroke.get("points"), list)
            and bool(stroke["points"])
            for stroke in page.get("strokes", [])
        )
        for page in pages
    )
    has_transcript = isinstance(transcript, str) and bool(transcript.strip())
    has_typed_answer = (
        isinstance(typed_answer, str) and bool(typed_answer.strip())
    )
    if not has_ink and not has_transcript and not has_typed_answer:
        raise ValueError("Evidence requires handwriting or answer text")
    images = payload.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("At least one handwriting image is required")
    if len(images) > 12:
        raise ValueError("No more than 12 handwriting images are allowed")
    decoded_images = []
    for position, image in enumerate(images):
        if not isinstance(image, dict):
            raise ValueError("Each handwriting image must be an object")
        decoded_images.append(
            {
                "page_id": str(image.get("page_id") or "page"),
                "index": int(image.get("index", position)),
                "bytes": _decode_png_data_url(image.get("png_data_url")),
            }
        )
    return {
        "submission_id": submission_id.strip(),
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "question": question.strip(),
        "transcript": transcript.strip() if isinstance(transcript, str) else None,
        "transcript_confirmed": bool(payload.get("transcript_confirmed")),
        "typed_answer": (
            typed_answer.strip() if isinstance(typed_answer, str) and typed_answer.strip()
            else None
        ),
        "handwriting": handwriting,
        "images": decoded_images,
    }


class LearningOSService:
    def __init__(
        self,
        data_root: str | Path,
        relay=None,
        executor=None,
        auto_assess: bool = True,
    ):
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.store = STORE_MODULE.EventStore(self.data_root / "learning-os.db")
        self.core = CORE_MODULE.LearningOSCore(self.data_root)
        self.ai = AI_MODULE.AIGateway(self.core)
        self.artifacts = STORE_MODULE.ArtifactRepository(
            self.data_root / "artifacts"
        )
        self.relay = relay or call_assessment_relay
        self.executor = executor or ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="learning-os-assessment",
        )
        self._owns_executor = executor is None
        self.auto_assess = auto_assess
        self._submission_lock = threading.RLock()
        self._jobs: dict[str, object] = {}
        self._jobs_lock = threading.RLock()

    def _event_for_evidence(self, evidence_id: str) -> dict | None:
        for event in self.store.list_evidence():
            if event["payload"].get("evidence_id") == evidence_id:
                return event
        return None

    def _response_for_event(self, event: dict, created: bool) -> tuple[int, dict]:
        payload = event["payload"]
        detail = self.get_evidence(payload["evidence_id"])
        result = {
            "event_id": event["event_id"],
            "evidence_id": payload["evidence_id"],
            "status": detail["status"],
            "artifact_integrity": detail["artifact_integrity"],
        }
        return (201 if created else 200), result

    def submit_evidence(self, payload: object) -> tuple[int, dict]:
        data = validate_evidence_request(payload)
        with self._submission_lock:
            return self._submit_validated_evidence(data)

    def _submit_validated_evidence(self, data: dict) -> tuple[int, dict]:
        existing = self.store.find_evidence_by_submission_id(
            data["submission_id"]
        )
        if existing is not None:
            return self._response_for_event(existing, created=False)

        evidence_id = str(uuid.uuid4())
        pages = [
            {
                "filename": f"page-{position + 1:03d}-chunk-{image['index'] + 1:03d}.png",
                "bytes": image["bytes"],
            }
            for position, image in enumerate(data["images"])
        ]
        manifest = self.artifacts.write_evidence(
            evidence_id,
            data["handwriting"],
            pages,
            data["transcript"],
            data["typed_answer"],
        )
        if not self.artifacts.verify_manifest(manifest):
            raise RuntimeError("Artifact integrity verification failed")

        event = self.store.append(
            "EvidenceExtracted",
            data["aggregate_type"],
            data["aggregate_id"],
            {
                "submission_id": data["submission_id"],
                "evidence_id": evidence_id,
                "question": data["question"],
                "transcript": data["transcript"],
                "transcript_confirmed": data["transcript_confirmed"],
                "typed_answer": data["typed_answer"],
                "artifact_manifest": manifest,
            },
        )
        self.store.append(
            "AssessmentRequested",
            data["aggregate_type"],
            data["aggregate_id"],
            {
                "evidence_id": evidence_id,
                "job_id": str(uuid.uuid4()),
            },
        )
        if self.auto_assess:
            self.enqueue_assessment(evidence_id)
        return self._response_for_event(event, created=True)

    def enqueue_assessment(self, evidence_id: str):
        with self._jobs_lock:
            if evidence_id in self._jobs:
                return self._jobs[evidence_id]
            self._jobs[evidence_id] = None

        def run_and_release():
            try:
                self._run_assessment(evidence_id)
            finally:
                with self._jobs_lock:
                    self._jobs.pop(evidence_id, None)

        future = self.executor.submit(run_and_release)
        with self._jobs_lock:
            if evidence_id in self._jobs:
                self._jobs[evidence_id] = future
        return future

    def _run_assessment(self, evidence_id: str):
        evidence = self._event_for_evidence(evidence_id)
        if evidence is None:
            return
        payload = evidence["payload"]
        manifest = payload.get("artifact_manifest", {})
        category = None
        try:
            if not self.artifacts.verify_manifest(manifest):
                category = "artifact_integrity"
                raise ValueError("Artifact integrity failed")
            image_urls = []
            for record in manifest.get("files", []):
                if not record.get("path", "").endswith(".png"):
                    continue
                content = self.artifacts.path_for(
                    evidence_id, record["path"]
                ).read_bytes()
                image_urls.append(
                    "data:image/png;base64," + base64.b64encode(content).decode("ascii")
                )
            if not image_urls:
                category = "artifact_integrity"
                raise ValueError("No handwriting images are available")
            result = self.relay(
                {
                    "question": payload.get("question", ""),
                    "transcript": (
                        payload.get("transcript") or payload.get("typed_answer")
                    ),
                    "answer_source": (
                        "confirmed_transcript"
                        if payload.get("transcript")
                        else "typed_answer" if payload.get("typed_answer")
                        else "handwriting_only"
                    ),
                    "image_data_urls": image_urls,
                }
            )
            assessment = validate_assessment_result(result)
            assessment.update(
                {
                    "assessment_id": str(uuid.uuid4()),
                    "evidence_id": evidence_id,
                    "model": result.get("model", MODEL),
                    "request_id": result.get("request_id"),
                }
            )
            self.store.append(
                "AssessmentRecorded",
                evidence["aggregate_type"],
                evidence["aggregate_id"],
                assessment,
            )
            return
        except TimeoutError:
            category = "timeout"
        except ValueError:
            category = category or "invalid_output"
        except Exception:
            category = "upstream_error"
        self.store.append(
            "AssessmentFailed",
            evidence["aggregate_type"],
            evidence["aggregate_id"],
            {
                "failure_id": str(uuid.uuid4()),
                "evidence_id": evidence_id,
                "category": category,
                "retryable": category != "artifact_integrity",
            },
        )

    def retry_assessment(self, evidence_id: str) -> dict:
        detail = self.get_evidence(evidence_id)
        if detail["status"] == "recorded":
            raise ValueError("Recorded assessment cannot be retried")
        if detail["status"] not in {"failed", "assessing", "pending"}:
            raise ValueError("Assessment cannot be retried")
        evidence = self._event_for_evidence(evidence_id)
        with self._jobs_lock:
            if evidence_id in self._jobs:
                raise ValueError("Assessment is already running")
            self.store.append(
                "AssessmentRequested",
                evidence["aggregate_type"],
                evidence["aggregate_id"],
                {"evidence_id": evidence_id, "job_id": str(uuid.uuid4())},
            )
            self.enqueue_assessment(evidence_id)
        return self.get_evidence(evidence_id)

    def get_evidence(self, evidence_id: str) -> dict:
        evidence = self._event_for_evidence(evidence_id)
        if evidence is None:
            raise KeyError(evidence_id)
        events = self.store.replay(
            evidence["aggregate_type"], evidence["aggregate_id"]
        )
        related = [
            event
            for event in events
            if event["payload"].get("evidence_id") == evidence_id
        ]
        status = "pending"
        assessment = None
        failure = None
        for event in related:
            if event["event_type"] == "AssessmentRequested":
                status = "assessing"
                assessment = None
                failure = None
            elif event["event_type"] == "AssessmentRecorded":
                status = "recorded"
                assessment = event["payload"]
                failure = None
            elif event["event_type"] == "AssessmentFailed":
                status = "failed"
                assessment = None
                failure = event["payload"]
        manifest = evidence["payload"].get("artifact_manifest", {})
        return {
            "event_id": evidence["event_id"],
            "evidence_id": evidence_id,
            "aggregate": {
                "type": evidence["aggregate_type"],
                "id": evidence["aggregate_id"],
            },
            "created_at": evidence["occurred_at"],
            "question": evidence["payload"].get("question"),
            "transcript": evidence["payload"].get("transcript"),
            "typed_answer": evidence["payload"].get("typed_answer"),
            "status": status,
            "assessment": assessment,
            "failure": failure,
            "artifact_integrity": (
                "verified" if self.artifacts.verify_manifest(manifest) else "failed"
            ),
            "artifact_files": manifest.get("files", []),
        }

    def list_evidence(
        self,
        aggregate_type: str | None,
        aggregate_id: str | None,
    ) -> dict:
        events = self.store.list_evidence(aggregate_type, aggregate_id)
        return {
            "items": [
                self.get_evidence(event["payload"]["evidence_id"])
                for event in events
            ]
        }

    def timeline(self, aggregate_type: str, aggregate_id: str) -> dict:
        return {"events": self.store.replay(aggregate_type, aggregate_id)}

    def projection(self, aggregate_type: str, aggregate_id: str) -> dict:
        return STORE_MODULE.project_events(
            self.store.replay(aggregate_type, aggregate_id)
        )

    def close(self):
        if self._owns_executor:
            self.executor.shutdown(wait=True, cancel_futures=True)
        self.core.close()
        self.store.close()


class LearningOSHandler(BaseHTTPRequestHandler):
    server_version = "LearningOSLocal/3"

    def _origin(self):
        origin = self.headers.get("Origin")
        return origin if origin in ALLOWED_ORIGINS else None

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _send_ai_error(self, error):
        self._send_json(error.status, error.payload())

    def do_OPTIONS(self):
        if (
            not (self.path.startswith("/api/v1/") or self.path.startswith("/api/v2/"))
            or not self._origin()
        ):
            self._send_json(403, {"error": "Origin is not allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        service = getattr(self.server, "service", None)
        if parsed.path == "/health":
            payload = {"status": "ok", "model": MODEL}
            if service is not None:
                payload.update(
                    {
                        "store": str(service.store.db_path),
                        "artifact_root": str(service.artifacts.root),
                    }
                )
            self._send_json(200, payload)
            return
        if not self._origin():
            self._send_json(403, {"error": "Origin is not allowed"})
            return
        if service is None:
            self._send_json(503, {"error": "Learning OS service is unavailable"})
            return
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/v2/dashboard":
                study_date = query.get("date", [datetime.now().date().isoformat()])[0]
                dashboard = service.core.today(study_date, query.get("time", [None])[0])
                review = service.core.daily_review(study_date)
                dashboard["review"] = {"target_count": 5, "items": review}
                self._send_json(200, dashboard)
                return
            if parsed.path == "/api/v2/tasks":
                self._send_json(200, {"items": service.core.list_tasks(query.get("date", [None])[0])})
                return
            if parsed.path == "/api/v2/error-questions":
                self._send_json(200, {"items": service.core.list_error_questions(query.get("subject", [None])[0])})
                return
            if parsed.path == "/api/v2/daily-review":
                study_date = query.get("date", [datetime.now().date().isoformat()])[0]
                self._send_json(200, {"target_count": 5, "items": service.core.daily_review(study_date)})
                return
            if parsed.path == "/api/v2/status":
                self._send_json(200, {"items": service.core.list_status(query.get("date", [None])[0])})
                return
            if parsed.path == "/api/v2/chats":
                self._send_json(200, {"items": service.core.list_chats(query.get("query", [None])[0])})
                return
            if parsed.path.startswith("/api/v2/chats/") and parsed.path.endswith("/messages"):
                chat_id = parsed.path.split("/")[-2]
                self._send_json(200, {"items": service.core.list_chat_messages(chat_id)})
                return
            if parsed.path == "/api/v2/statistics":
                self._send_json(200, service.core.statistics())
                return
            if parsed.path == "/api/v2/settings/ai":
                self._send_json(200, service.ai.settings())
                return
            if parsed.path == "/api/v1/evidence":
                self._send_json(
                    200,
                    service.list_evidence(
                        query.get("aggregate_type", [None])[0],
                        query.get("aggregate_id", [None])[0],
                    ),
                )
                return
            if parsed.path.startswith("/api/v1/evidence/"):
                evidence_id = parsed.path.rsplit("/", 1)[-1]
                self._send_json(200, service.get_evidence(evidence_id))
                return
            if parsed.path in {"/api/v1/timeline", "/api/v1/projection"}:
                aggregate_type = query.get("aggregate_type", [None])[0]
                aggregate_id = query.get("aggregate_id", [None])[0]
                if not aggregate_type or not aggregate_id:
                    raise ValueError("aggregate_type and aggregate_id are required")
                if parsed.path.endswith("timeline"):
                    self._send_json(
                        200, service.timeline(aggregate_type, aggregate_id)
                    )
                else:
                    self._send_json(
                        200, service.projection(aggregate_type, aggregate_id)
                    )
                return
        except KeyError:
            self._send_json(404, {"error": "Evidence not found"})
            return
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        self._send_json(404, {"error": "Not found"})

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Content-Length is invalid")
        if length <= 0 or length > MAX_BODY_BYTES:
            raise OverflowError("Request body is too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _handle_shutdown(self):
        callback = getattr(self.server, "request_shutdown", None)
        if not callable(callback):
            self._send_json(503, {"error": "Shutdown control is unavailable"})
            return
        # Send the confirmation first, then trigger the in-app shutdown so the response is
        # always delivered before the listening socket is released.
        self._send_json(
            200,
            {
                "status": "shutting_down",
                "message": "学习 OS 已收到退出请求，正在关闭本机服务。可以关闭此页面。",
            },
        )
        try:
            self.wfile.flush()
        except Exception:
            pass
        callback()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {
            "/api/v1/handwriting/recognize",
            "/api/v1/evidence",
        } and not parsed.path.endswith("/assessment/retry") and not parsed.path.startswith("/api/v2/"):
            self._send_json(404, {"error": "Not found"})
            return
        if not self._origin():
            self._send_json(403, {"error": "Origin is not allowed"})
            return
        try:
            payload = self._read_json_body()
        except OverflowError as error:
            self._send_json(413, {"error": str(error)})
            return
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return

        if parsed.path == "/api/v2/shutdown":
            self._handle_shutdown()
            return

        if parsed.path == "/api/v1/handwriting/recognize":
            try:
                request_data = validate_recognition_request(payload)
                result = call_with_deadline(
                    lambda: recognize_chunks(request_data, relay=call_relay)
                )
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            except TimeoutError as error:
                self._send_json(504, {"error": normalize_upstream_error(error)})
                return
            except Exception as error:
                self._send_json(502, {"error": normalize_upstream_error(error)})
                return
            self._send_json(200, result)
            return

        service = getattr(self.server, "service", None)
        if service is None:
            self._send_json(503, {"error": "Learning OS service is unavailable"})
            return
        if parsed.path == "/api/v2/settings/ai":
            try:
                self._send_json(200, service.ai.configure(payload))
            except AI_MODULE.AIProviderError as error:
                self._send_ai_error(error)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except Exception:
                self._send_json(500, {"error": "AI credential configuration failed"})
            return
        if parsed.path == "/api/v2/settings/ai/test":
            try:
                reply = service.ai.test_connection()
                self._send_json(200, {"ok": True, "reply": reply})
            except AI_MODULE.AIProviderError as error:
                self._send_ai_error(error)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except TimeoutError:
                self._send_json(504, {"error": "AI provider timed out; try again later"})
            except Exception:
                self._send_json(502, {"error": "AI provider request failed"})
            return
        if parsed.path == "/api/v2/tasks":
            try:
                self._send_json(201, service.core.create_task(payload))
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            return
        if parsed.path == "/api/v2/quick-entry/error-draft":
            try:
                self._send_json(200, service.ai.extract_error_question(payload.get("images")))
            except AI_MODULE.AIProviderError as error:
                self._send_ai_error(error)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except TimeoutError:
                self._send_json(504, {"error": "AI provider timed out; try again later"})
            except Exception:
                self._send_json(502, {"error": "AI provider request failed"})
            return
        if parsed.path == "/api/v2/error-questions":
            try:
                self._send_json(201, service.core.create_error_question(payload))
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            return
        if parsed.path.startswith("/api/v2/error-questions/") and parsed.path.endswith("/analyze"):
            question_id = parsed.path.split("/")[-2]
            try:
                result = service.ai.analyze_error_question(service.core.get_error_question(question_id))
                if result["information_sufficient"]:
                    service.core.update_error_question(
                        question_id,
                        {
                            "priority": result["review_priority"],
                            "error_types": [result["primary_error_type"], *result["secondary_error_types"]],
                        },
                    )
                self._send_json(201, service.core.record_error_analysis(question_id, result))
            except KeyError:
                self._send_json(404, {"error": "Error question not found"})
            except AI_MODULE.AIProviderError as error:
                self._send_ai_error(error)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except TimeoutError:
                self._send_json(504, {"error": "AI provider timed out; try again later"})
            except Exception:
                self._send_json(502, {"error": "AI provider request failed"})
            return
        if parsed.path.startswith("/api/v2/error-questions/") and parsed.path.endswith("/reviews"):
            question_id = parsed.path.split("/")[-2]
            try:
                self._send_json(
                    201,
                    service.core.record_review(
                        question_id,
                        payload.get("reviewed_on") or datetime.now().date().isoformat(),
                        payload.get("outcome"),
                        payload.get("notes"),
                    ),
                )
            except KeyError:
                self._send_json(404, {"error": "Error question not found"})
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            return
        if parsed.path == "/api/v2/status":
            try:
                self._send_json(201, service.core.record_status(payload))
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            return
        if parsed.path == "/api/v2/chats":
            try:
                self._send_json(201, service.core.create_chat(payload))
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            return
        if parsed.path.startswith("/api/v2/chats/") and parsed.path.endswith("/messages"):
            try:
                chat_id = parsed.path.split("/")[-2]
                user = service.core.add_chat_message(chat_id, payload)
                if user["role"] != "user":
                    self._send_json(201, {"user": user, "assistant": None})
                    return
                # Cloud Hermes path (Track C) — only when explicitly enabled. The local
                # provider path below is retained for rollback and is the default.
                if _CLOUD_BRIDGE is not None and _CLOUD_BRIDGE.is_enabled():
                    try:
                        cloud = _CLOUD_BRIDGE.chat(chat_id, payload, self.headers)
                    except CloudChatError as error:
                        self._send_json(error.status, {"code": error.code, "error": error.message})
                        return
                    assistant = service.core.add_chat_message(
                        chat_id,
                        {"role": "assistant", "content": cloud["reply"],
                         "hermes_run_id": cloud.get("hermes_run_id")},
                    )
                    self._send_json(201, {
                        "user": user, "assistant": assistant,
                        "hermes_run_id": cloud.get("hermes_run_id"),
                        "conversation_id": cloud.get("conversation_id"),
                        "memory_refs": cloud.get("memory_refs", []),
                        "event_ids": cloud.get("event_ids", []),
                        "warnings": cloud.get("warnings", []),
                    })
                    return
                answer = service.ai.answer_chat(service.core.list_chat_messages(chat_id))
                assistant = service.core.add_chat_message(chat_id, {"role": "assistant", "content": answer})
                self._send_json(201, {"user": user, "assistant": assistant})
            except KeyError:
                self._send_json(404, {"error": "Chat not found"})
            except AI_MODULE.AIProviderError as error:
                self._send_ai_error(error)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except TimeoutError:
                self._send_json(504, {"error": "AI provider timed out; try again later"})
            except Exception:
                self._send_json(502, {"error": "AI provider request failed"})
            return
        if parsed.path == "/api/v1/evidence":
            try:
                status, result = service.submit_evidence(payload)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            except Exception:
                self._send_json(500, {"error": "Evidence persistence failed"})
                return
            self._send_json(status, result)
            return
        if parsed.path.endswith("/assessment/retry"):
            evidence_id = parsed.path.split("/")[-3]
            try:
                result = service.retry_assessment(evidence_id)
            except KeyError:
                self._send_json(404, {"error": "Evidence not found"})
                return
            except ValueError as error:
                self._send_json(409, {"error": str(error)})
                return
            self._send_json(202, result)
            return
        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/v2/") or not self._origin():
            self._send_json(404, {"error": "Not found"})
            return
        try:
            payload = self._read_json_body()
        except (OverflowError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return
        service = getattr(self.server, "service", None)
        if service is None:
            self._send_json(503, {"error": "Learning OS service is unavailable"})
            return
        try:
            if parsed.path.startswith("/api/v2/tasks/"):
                task_id = parsed.path.rsplit("/", 1)[-1]
                result = (
                    service.core.transition_task(task_id, payload["status"])
                    if "status" in payload else service.core.update_task(task_id, payload)
                )
                self._send_json(200, result)
                return
            if parsed.path.startswith("/api/v2/error-questions/"):
                self._send_json(200, service.core.update_error_question(parsed.path.rsplit("/", 1)[-1], payload))
                return
        except KeyError:
            self._send_json(404, {"error": "Resource not found"})
            return
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
            return
        self._send_json(404, {"error": "Not found"})

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


def run_server(host: str = "127.0.0.1", port: int = 4174):
    host = validate_bind_host(host)
    server = ThreadingHTTPServer((host, port), LearningOSHandler)
    server.service = LearningOSService(
        Path(__file__).resolve().parents[1] / "data"
    )
    print(f"Learning OS local service listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.service.close()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="Learning OS vision proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4174)
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
