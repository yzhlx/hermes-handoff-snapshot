"""Pure rules for the optional AI advisor.

The advisor is a study consultant, never a commander. This module owns the
deterministic evidence summary, the output contract shared with 03, and the
server-side policy checks that keep model output honest.

It has no transport, database, or model SDK dependency. ``facts`` are built
here from the user's own records and stay available even when no model runs;
``inferences`` are model-authored and must pass :func:`validate_inferences`
before they are shown.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

RULE_VERSION = "advisor-evidence-v1"
POLICY_VERSION = "advisor-policy-v2"

MAX_EVIDENCE_RECORDS = 20
MAX_TOPIC_LENGTH = 2000
MAX_TEXT_LENGTH = 1000
MAX_INFERENCES = 12
MAX_FACTS = 12
MAX_MISSING = 8

# How many repeated same-category errors and how many same-knowledge-point
# independent-correct records a statement needs before it may be shown
# (04 §2: 重复错误 ≥3 次；真实变化 最近 3 次同知识点独立正确).
REPEAT_ERROR_THRESHOLD = 3
VARIANT_STABLE_THRESHOLD = 3

CATEGORY_LABELS = {
    "concept": "概念",
    "modeling": "思路 / 建模",
    "condition": "条件判断",
    "formula": "公式",
    "derivation": "推导",
    "calculation": "计算",
    "sign": "符号 / 正负 / 方向",
    "unit": "单位",
    "reading": "审题",
    "other": "其他",
}

INDEPENDENCE_LABELS = {
    "independent": "独立完成",
    "hinted": "有一些提示",
    "after_answer": "看过答案以后完成",
    "unable": "基本不会",
}

RESULT_LABELS = {"correct": "正确", "partial": "部分正确", "incorrect": "错误"}

# Stable codes stored on a run; the UI maps them to honest, non-commanding copy.
DEGRADATION_MODEL_UNAVAILABLE = "model_unavailable"
DEGRADATION_MODEL_ERROR = "model_error"

# Commander / mastery-claim / false-progress / debt language the advisor must
# never emit (FR-045, 04 §3). Matching runs on NFKC-normalised text with
# whitespace and punctuation removed, so spaces or punctuation cannot bypass it.
FORBIDDEN_PATTERNS = (
    # claims of mastery or automatic state change
    r"已(经)?(完全|基本|大致|初步)?掌握",
    r"掌握(程度|度|等级)?(已达|已提升|已更新|提升|升级|更新)",
    r"(判定|认定|认为|确认|视为)(为)?(已)?掌握",
    r"自动(认为|判定|确认为|升级)",
    r"无需再(学|复习|练习)",
    # review debt / overdue
    r"(复习|学习)?(债务|欠债)",
    r"逾期",
    r"(还)?欠(着)?[0-9零一二三四五六七八九十百]+",
    r"欠了",
    r"落后[0-9零一二三四五六七八九十]+天",
    r"归零",
    r"完成率(要求|不足|不达标)",
    # commanding the next move / forced action / auto scheduling
    r"(今天|今日|现在|接下来)(最|首要|第一)?(必须|务必|一定要|应该|应当|该)(优先)?",
    r"(必须|务必|一定要|强制)(完成|复习|学|做|开始|安排)",
    r"(今天|今日)(最该学|最应该学|最重要|优先学)",
    r"(由系统|系统替你|系统为你)(决定|安排|选择)",
    r"(自动)?(安排|排期|托管)(学习|复习)(计划|任务|排期)",
    r"推荐你(优先|先)(学|复习|完成)",
    # empty praise / false progress
    r"太棒了",
    r"非常厉害",
    r"超级努力",
    r"你一定可以",
    r"你进步很大",
    r"你已经完全学会",
    r"你的水平(已经|已)(很高|达到)",
)

_STRIP = re.compile(
    r"[\s\u200b-\u200f\u2028-\u202f\u2060\ufeff"
    r",，。.!！?？:：;；、·．\-—_~/\\|@#$%^&*+=~"
    r"()（）\[\]【】{}<>《》\"'“”‘’`]"
)
_COMPILED = tuple(re.compile(pattern) for pattern in FORBIDDEN_PATTERNS)


class AdvisorPolicyError(ValueError):
    """Model output cannot be shown to the owner as-is."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        self.message = message
        super().__init__(message)


def normalize(text: str) -> str:
    """Fold full-width characters and drop whitespace/punctuation for matching."""

    return _STRIP.sub("", unicodedata.normalize("NFKC", text))


def has_forbidden_language(text: str) -> str | None:
    """Return the matched pattern when text claims mastery or issues commands."""

    if not isinstance(text, str):
        return None
    folded = normalize(text)
    for pattern, compiled in zip(FORBIDDEN_PATTERNS, _COMPILED, strict=True):
        if compiled.search(folded):
            return pattern
    return None


def _assert_safe_text(text: str) -> None:
    if has_forbidden_language(text):
        raise AdvisorPolicyError(
            "forbidden_language",
            "The model produced commanding or mastery-claiming language.",
        )


def _counts(records: list[dict]) -> dict:
    ordered = sorted(
        records, key=lambda item: (item["occurred_at"] or "", item["id"]), reverse=True
    )
    checked = [item for item in ordered if item["answer_check"] == "checked"]
    correct = [item for item in checked if item["result"] == "correct"]
    independent_correct = [item for item in correct if item["independence"] == "independent"]
    pending = [item for item in ordered if item["answer_check"] == "pending"]
    categories: dict[str, list[dict]] = {}
    for item in checked:
        for category in sorted(set(item.get("error_categories") or [])):
            categories.setdefault(category, []).append(item)
    return {
        "ordered": ordered,
        "checked": checked,
        "correct": correct,
        "independent_correct": independent_correct,
        "pending": pending,
        "categories": categories,
    }


def knowledge_point_streaks(records: list[dict]) -> dict[str, dict]:
    """Leading run of independent-correct checked records per knowledge point.

    A "recent change" statement may only be made for a specific knowledge point
    with enough consecutive independent-correct records (04 §2).
    """

    ordered = sorted(
        records, key=lambda item: (item["occurred_at"] or "", item["id"]), reverse=True
    )
    checked = [item for item in ordered if item["answer_check"] == "checked"]
    streaks: dict[str, dict] = {}
    for item in checked:
        for point in sorted(set(item.get("knowledge_point_ids") or [])):
            entry = streaks.setdefault(point, {"count": 0, "records": [], "broken": False})
            if entry["broken"]:
                continue
            if item["independence"] == "independent" and item["result"] == "correct":
                entry["count"] += 1
                entry["records"].append(item)
            else:
                entry["broken"] = True
    return streaks


def _ids(items: list[dict]) -> list[str]:
    return [item["id"] for item in items]


def build_facts(evidence: dict) -> list[dict]:
    """Deterministic, traceable record facts. Never model-authored."""

    records = evidence.get("records") or []
    if not records:
        return []
    counts = _counts(records)
    facts: list[dict] = []

    facts.append(
        {
            "text": (
                f"最近 {len(records)} 条记录中，已核对 {len(counts['checked'])} 条，"
                f"未核对 {len(counts['pending'])} 条。"
            ),
            "source_refs": _ids(counts["ordered"]),
        }
    )
    if counts["checked"]:
        facts.append(
            {
                "text": (
                    f"已核对的记录里，核对正确 {len(counts['correct'])} 条，"
                    f"其中独立完成且核对正确 {len(counts['independent_correct'])} 条。"
                ),
                "source_refs": _ids(counts["checked"]),
            }
        )
    if counts["pending"]:
        facts.append(
            {
                "text": "有记录尚未核对，这些记录不计入正确证据。",
                "source_refs": _ids(counts["pending"]),
            }
        )
    for category, rows in sorted(
        counts["categories"].items(), key=lambda item: (-len(item[1]), item[0])
    ):
        if category not in CATEGORY_LABELS:
            continue
        facts.append(
            {
                "text": f"已核对记录中，「{CATEGORY_LABELS[category]}」类错误出现 {len(rows)} 次。",
                "source_refs": _ids(rows),
            }
        )
    stuck = [item for item in counts["ordered"] if (item.get("stuck_note") or "").strip()]
    if stuck:
        facts.append(
            {
                "text": f"保存了 {len(stuck)} 条卡壳点描述，可以逐条打开回顾。",
                "source_refs": _ids(stuck),
            }
        )
    return facts[:MAX_FACTS]


def build_missing(evidence: dict) -> list[str]:
    """Deterministic gaps. Points at missing material instead of guessing."""

    records = evidence.get("records") or []
    if not records:
        return ["记录还不足，可以先开始学习。"]
    counts = _counts(records)
    missing: list[str] = []
    if not counts["checked"]:
        missing.append("还没有已核对的记录，暂时无法说明错误分布。")
    if len(counts["checked"]) < 2:
        missing.append("还没有两次可比较的已核对记录，暂时无法说明变化趋势。")
    if not counts["independent_correct"]:
        missing.append("还没有独立完成且核对正确的记录。")
    if counts["checked"] and not counts["categories"]:
        missing.append("已核对记录里没有标注错误原因，暂时无法归纳错误类型。")
    return missing[:MAX_MISSING]


def normalize_refs(refs, allowed: dict[str, int]) -> list[str]:
    """Validate reference ids, accepting ``"id"`` or ``{"id": ..., "version": ...}``.

    When a version is supplied it must match the bundle, so a statement cannot
    cite a stale snapshot of a record.
    """

    if not isinstance(refs, list) or not refs:
        raise AdvisorPolicyError(
            "unknown_reference", "Every inference must cite at least one record id."
        )
    clean: list[str] = []
    for ref in refs:
        if isinstance(ref, str):
            ref_id: object = ref
            version = None
        elif isinstance(ref, dict):
            ref_id = ref.get("id")
            version = ref.get("version")
            if version is not None and not isinstance(version, int):
                raise AdvisorPolicyError(
                    "malformed_output", "Reference version must be an integer."
                )
        else:
            raise AdvisorPolicyError(
                "malformed_output", "References must be ids or {id, version} objects."
            )
        if not isinstance(ref_id, str) or not ref_id:
            raise AdvisorPolicyError("malformed_output", "Reference ids must be non-empty strings.")
        if ref_id not in allowed:
            raise AdvisorPolicyError(
                "unknown_reference", "An inference cited a record outside your own evidence."
            )
        if version is not None and allowed[ref_id] != version:
            raise AdvisorPolicyError(
                "unknown_reference", "An inference cited a stale record version."
            )
        if ref_id not in clean:
            clean.append(ref_id)
    return clean


def validate_inferences(items, allowed: dict[str, int]) -> list[dict]:
    """Validate model-authored inferences against the supplied evidence bundle."""

    if not isinstance(items, list):
        raise AdvisorPolicyError("malformed_output", "Inferences must be a list.")
    if len(items) > MAX_INFERENCES:
        raise AdvisorPolicyError("too_long", "Too many inferences.")
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            raise AdvisorPolicyError("malformed_output", "Each inference must be an object.")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise AdvisorPolicyError("malformed_output", "Inference text is empty.")
        if len(text) > MAX_TEXT_LENGTH:
            raise AdvisorPolicyError("too_long", "Inference text is too long.")
        clean_refs = normalize_refs(item.get("source_refs"), allowed)
        _assert_safe_text(text)
        normalized.append({"text": text.strip(), "source_refs": clean_refs})
    return normalized


def validate_missing(items, allowed: dict[str, int] | None = None) -> list[str]:
    """Sanitize model-authored missing-material notes.

    These are shown to the user, so they pass exactly the same policy gate as
    inferences; a model cannot smuggle a command through this channel.
    """

    if not isinstance(items, list):
        raise AdvisorPolicyError("malformed_output", "Missing material must be a list.")
    clean: list[str] = []
    for item in items[:MAX_MISSING]:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text or len(text) > MAX_TEXT_LENGTH:
            continue
        _assert_safe_text(text)
        if clean and text in clean:
            continue
        clean.append(text)
    return clean


def summarize(facts: list[dict], inferences: list[dict], missing: list[str]) -> str:
    """A summary built only from already-validated content."""

    if inferences:
        return inferences[0]["text"]
    if facts:
        return facts[0]["text"]
    if missing:
        return missing[0]
    return "记录还不足，可以先开始学习。"


def data_version(evidence: dict) -> str:
    """Identify the record snapshot so older output never overwrites newer data."""

    refs = [
        {"id": item["id"], "version": item["version"]} for item in (evidence.get("records") or [])
    ]
    payload = json.dumps(
        {"rule_version": RULE_VERSION, "refs": refs}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
