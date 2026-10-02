"""OpenAI-compatible advisor provider（真实模型适配器）。

契约来自 advisor_service._evaluate：
    raw = self.model.analyze({"topic": topic}, evidence)
    inferences = validate_inferences(raw.get("inferences", []), allowed)
    missing    = validate_missing(raw.get("missing_information", []), allowed)

要点：
1. **facts 不由模型产出**——service 用 build_facts(evidence) 自己从证据构造。
   模型只负责 inferences 与 missing_information。
2. **不信任模型输出**：模型可能编造证据 id、漏字段、把 JSON 包在代码块里。
   这里先做一次确定性收敛（丢弃指向不存在证据的引用），再去撞 validate_*。
   宁少勿错：少一条推断，好过整次分析被判 malformed_output 而降级。
3. **不抛裸异常**：连不上/超时/非 200 一律转成 AdvisorModelUnavailable，
   让 service 走既有的 degraded 降级路径，而不是变成 500 或 blocked。
4. 密钥只驻内存，不落库、不进日志、不进异常文本；HTTP 层可注入以便测试。
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import ClassVar

from .advisor_ports import AdvisorModelUnavailable


SYSTEM_PROMPT = """你是 Hermes 学习助手。你要根据给定的学习记录（题目与作答证据），
给出**有依据的**推断，帮助学习者看清自己的状态。

严格规则：
1. 只输出 JSON，不要解释，不要 markdown 代码块。
2. 每条推断必须带 source_refs，元素形如 {"id": "<证据 id>", "version": <证据 version>}，
   id 与 version 必须**原样抄自记录**。指向不存在证据的推断会被丢弃。
3. 只写记录支持得住的推断。证据不足时不要硬猜——把缺什么写进 missing_information。
4. 不要给出医学、心理或诊断类结论；不要断言"已掌握"。
5. 输出形如：
{"inferences":[{"text":"...","source_refs":[{"id":"...","version":1}]}],
 "missing_information":["..."]}"""


def extract_json(text: str) -> dict | None:
    """从模型回复里取出 JSON 对象；容忍代码块包裹与前后废话。"""
    if not text:
        return None
    candidates = []
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        candidates.append(fence.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    candidates.append(text)
    for raw in candidates:
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def render_evidence(evidence: dict) -> str:
    """把证据包压成模型能读的紧凑文本。只取记录里真实存在的字段。"""
    records = evidence.get("records") or []
    lines = []
    for record in records:
        parts = [f"id={record.get('id')}", f"version={record.get('version')}"]
        title = record.get("problem_title") or record.get("title")
        if title:
            parts.append(f"题目={title}")
        for key in ("statement", "independence", "check_status", "result", "error_categories"):
            value = record.get(key)
            if value:
                parts.append(f"{key}={value}")
        lines.append(" | ".join(str(p) for p in parts))
    if not lines:
        return "（没有可用的学习记录）"
    return "学习记录（每行一条）：\n" + "\n".join(lines)


class OpenAIModel:
    """OpenAI 兼容 /chat/completions 适配器。

    capabilities 是**诚实声明**：只有确认模型支持图片输入时才置 image，
    否则界面不得暗示可以拍照识题（AGENTS.md §13.4）。
    """

    model_id = "openai-compatible"
    provider = "openai-compatible"
    prompt_version = "advisor-prompt-v1"
    externally_hosted = True

    capabilities: ClassVar[dict] = {
        "modalities": ["text"],
        "structured_output": True,
        "streaming": False,
        "cancellable": False,
        "tools": [],
    }

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: int = 60,
        max_tokens: int = 2048,
        supports_image: bool = False,
        transport=None,
    ):
        if not base_url or not api_key or not model:
            raise ValueError("Provider requires base_url, api_key and model.")
        self.model = model
        self.model_id = model
        self.timeout = timeout
        # 见 analyze() 的注释：推理型模型需要足够的预算覆盖 reasoning + 正文。
        self.max_tokens = max(256, min(int(max_tokens), 8192))
        self._api_key = api_key  # 仅驻内存
        self._endpoint = self._endpoint_for(base_url)
        self._transport = transport or self._post
        if supports_image:
            self.capabilities = {**self.capabilities, "modalities": ["text", "image"]}

    @staticmethod
    def _endpoint_for(base_url: str) -> str:
        url = base_url.strip().rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        return f"{url}/chat/completions"

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            # 只带状态码与截断正文，绝不回显 Authorization 头
            raise AdvisorModelUnavailable(f"Provider HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise AdvisorModelUnavailable(
                f"Provider unavailable: {type(error).__name__}"
            ) from None

    def analyze(self, request: dict, evidence: dict) -> dict:
        prompt = render_evidence(evidence)
        topic = (request or {}).get("topic")
        if topic:
            prompt = f"学习者想了解的主题：{topic}\n\n{prompt}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            # 推理型模型（实测 deepseek-flash）会先产出 reasoning_content 并计入
            # 同一个 token 预算：max_tokens 给小了，content 会是空字符串。
            # 所以这里给的预算要覆盖"推理 + 正文"，由 provider_max_tokens 控制。
            "max_tokens": self.max_tokens,
        }
        try:
            response = self._transport(payload)
        except AdvisorModelUnavailable:
            raise
        except Exception as error:  # noqa: BLE001 - 任何 provider 故障都走降级，不冒 500
            raise AdvisorModelUnavailable(
                f"Provider call failed: {type(error).__name__}"
            ) from None

        parsed = extract_json(self._content_of(response))
        return self._conform(parsed, evidence)

    @staticmethod
    def _content_of(response) -> str:
        try:
            content = response["choices"][0]["message"].get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
        except (KeyError, IndexError, TypeError):
            pass
        return ""

    @staticmethod
    def _conform(parsed, evidence: dict) -> dict:
        """把模型输出收敛到契约内：丢弃指向不存在证据的引用与空推断。

        这是与 validate_inferences 之间的缓冲层——模型幻觉不该让整次分析降级。
        """
        allowed = {
            record["id"]: record["version"] for record in (evidence.get("records") or [])
        }
        if not isinstance(parsed, dict):
            return {"inferences": [], "missing_information": []}

        inferences = []
        for item in parsed.get("inferences") or []:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            refs = {}
            for ref in item.get("source_refs") or []:
                if not isinstance(ref, dict):
                    continue
                rid = ref.get("id")
                if rid in allowed and ref.get("version") == allowed[rid]:
                    refs[rid] = {"id": rid, "version": allowed[rid]}
            # 没有有效引用的推断一律不采纳（契约要求有依据）
            if refs:
                inferences.append({"text": text.strip(), "source_refs": list(refs.values())})

        missing = [
            text.strip()
            for text in (parsed.get("missing_information") or [])
            if isinstance(text, str) and text.strip()
        ]
        return {"inferences": inferences, "missing_information": missing}
