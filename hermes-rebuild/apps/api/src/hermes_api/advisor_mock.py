"""Baseline deterministic advisor model.

The base build never transmits learning data to an external provider. This
adapter turns the already-assembled, owner-scoped evidence bundle into
candidate inferences. It states only what the evidence supports and lists what
is missing instead of guessing, and its thresholds follow the initial rules in
04 §2 (a repeated error needs three occurrences; a "recent change" statement
needs three consecutive independent-correct records on one knowledge point).

The user's own text (``request["topic"]``) is treated strictly as content: it
is never read here, so no instruction inside it can change the adapter's scope.

Test-only modes let the suite exercise the failure and policy paths without a
network: ``unavailable``, ``malformed``, ``unknown_ref``, ``stale_ref``,
``forbidden``, ``empty``, ``error``.
"""

from __future__ import annotations

from typing import ClassVar

from .advisor_domain import (
    CATEGORY_LABELS,
    REPEAT_ERROR_THRESHOLD,
    VARIANT_STABLE_THRESHOLD,
    knowledge_point_streaks,
)
from .advisor_ports import AdvisorModelUnavailable


class DeterministicAdvisorModel:
    model_id = "mock-advisor-1"
    provider = "local-deterministic"
    prompt_version = "advisor-prompt-v1"
    externally_hosted = False
    capabilities: ClassVar[dict] = {
        "modalities": ["text"],
        "structured_output": True,
        "streaming": False,
        "cancellable": True,
        "tools": [],
    }

    def __init__(self, mode: str = "ready"):
        self.mode = mode
        self.calls = 0

    def analyze(self, request: dict, evidence: dict) -> dict:
        self.calls += 1
        if self.mode == "unavailable":
            raise AdvisorModelUnavailable("Advisor model is not configured.")
        if self.mode == "error":
            raise RuntimeError("QA_TEST provider blew up")
        if self.mode == "malformed":
            return {"inferences": "not-a-list"}
        if self.mode == "empty":
            return {"inferences": [], "missing_information": []}
        if self.mode == "unknown_ref":
            return {
                "inferences": [
                    {
                        "text": "这来自另一份记录。",
                        "source_refs": ["00000000-0000-0000-0000-000000000000"],
                    }
                ]
            }
        if self.mode == "stale_ref":
            records = evidence.get("records") or []
            if not records:
                return {"inferences": [], "missing_information": []}
            return {
                "inferences": [
                    {
                        "text": "这条记录的两个版本对不上。",
                        "source_refs": [
                            {"id": records[0]["id"], "version": records[0]["version"] + 99}
                        ],
                    }
                ]
            }
        if self.mode == "forbidden":
            return {
                "inferences": [
                    {
                        "text": "你今天必须优先学习这一科，它已经掌握。",
                        "source_refs": [r["id"] for r in (evidence.get("records") or [])[:1]],
                    }
                ]
            }
        return self._grounded(evidence)

    def _grounded(self, evidence: dict) -> dict:
        records = evidence.get("records") or []
        if not records:
            return {"inferences": [], "missing_information": ["记录还不足，可以先开始学习。"]}

        ordered = sorted(
            records, key=lambda item: (item["occurred_at"] or "", item["id"]), reverse=True
        )
        checked = [item for item in ordered if item["answer_check"] == "checked"]
        pending = [item for item in ordered if item["answer_check"] == "pending"]
        independent_correct = [
            item
            for item in checked
            if item["independence"] == "independent" and item["result"] == "correct"
        ]

        categories: dict[str, list[dict]] = {}
        for item in checked:
            for category in sorted(set(item.get("error_categories") or [])):
                if category in CATEGORY_LABELS:
                    categories.setdefault(category, []).append(item)

        inferences: list[dict] = []
        for category, rows in sorted(categories.items(), key=lambda pair: (-len(pair[1]), pair[0])):
            if len(rows) < REPEAT_ERROR_THRESHOLD:
                continue
            label = CATEGORY_LABELS[category]
            inferences.append(
                {
                    "text": (
                        f"这些已核对记录中，「{label}」类错误出现过 {len(rows)} 次，"
                        f"可以先不看资料自己复述一次「{label}」的使用条件，再对答案比较。"
                    ),
                    "source_refs": [row["id"] for row in rows],
                }
            )
            break

        for _point, streak in sorted(knowledge_point_streaks(records).items()):
            if streak["count"] < VARIANT_STABLE_THRESHOLD:
                continue
            inferences.append(
                {
                    "text": (
                        f"同一个知识点最近连续 {streak['count']} 次独立完成且核对正确，"
                        "可以用这些记录本身来检验是否稳定。"
                    ),
                    "source_refs": [item["id"] for item in streak["records"]],
                }
            )
            break

        if pending:
            inferences.append(
                {
                    "text": f"还有 {len(pending)} 条记录没有核对；核对之后它们才能成为判断依据。",
                    "source_refs": [item["id"] for item in pending],
                }
            )

        missing: list[str] = []
        if len(checked) < 2:
            missing.append("已核对记录少于两次，暂时不能判断变化趋势。")
        if not independent_correct:
            missing.append("还没有独立完成且核对正确的记录。")
        if checked and not categories:
            missing.append("已核对记录没有标注错误原因，暂时无法归纳错误类型。")
        return {"inferences": inferences, "missing_information": missing}
