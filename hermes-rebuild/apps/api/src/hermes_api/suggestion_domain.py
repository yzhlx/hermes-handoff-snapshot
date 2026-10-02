"""Deterministic suggestion policy; deliberately independent of persistence and HTTP."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

from .domain import PolicyError

RULE_VERSION = "suggestions-1"
REVIEW_AFTER_DAYS = 7
INDEPENDENT_REVIEW_AFTER_DAYS = 14
REPEATED_ERROR_WINDOW = 20
REPEATED_ERROR_THRESHOLD = 3


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise PolicyError("VALIDATION_ERROR", "Time must include a timezone.", 422)
    return value.astimezone(UTC)


def source_revision(refs: list[dict]) -> str:
    payload = sorted((ref["kind"], ref["id"], ref["version"]) for ref in refs)
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def candidate_fingerprint(kind: str, subject_id, point_id, problem_id, category, refs) -> str:
    payload = {
        "kind": kind,
        "subject_id": subject_id,
        "knowledge_point_id": point_id,
        "problem_id": problem_id,
        "category": category,
        "rule_version": RULE_VERSION,
        "sources": sorted((ref["kind"], ref["id"], ref["version"]) for ref in refs),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def make_candidate(
    kind,
    refs,
    reason,
    *,
    subject_id=None,
    knowledge_point_id=None,
    problem_id=None,
    category=None,
    now=None,
):
    refs = list(refs)
    return {
        "fingerprint": candidate_fingerprint(
            kind, subject_id, knowledge_point_id, problem_id, category, refs
        ),
        "kind": kind,
        "subject_id": subject_id,
        "knowledge_point_id": knowledge_point_id,
        "problem_id": problem_id,
        "reason": reason,
        "source_refs": refs,
        "source_revision": source_revision(refs),
        "rule_version": RULE_VERSION,
        "generated_at": aware(now or datetime.now(UTC)),
    }


def _localized_result(result: str) -> str:
    return {"partial": "部分正确", "incorrect": "错误", "correct": "独立正确"}.get(result, result)


def _localized_category(category: str) -> str:
    return {
        "concept": "概念",
        "modeling": "建模",
        "condition": "条件",
        "formula": "公式",
        "derivation": "推导",
        "calculation": "计算",
        "sign": "符号",
        "unit": "单位",
        "reading": "审题",
        "other": "其他",
    }.get(category, category)


def review_due(attempt: dict, now: datetime) -> bool:
    occurred = aware(attempt["occurred_at"])
    age = aware(now) - occurred
    if attempt["answer_check"] == "pending":
        return False
    if attempt["result"] in ("partial", "incorrect"):
        return age >= timedelta(days=REVIEW_AFTER_DAYS)
    return (
        attempt["result"] == "correct"
        and attempt["independence"] == "independent"
        and age >= timedelta(days=INDEPENDENT_REVIEW_AFTER_DAYS)
    )


def build_candidates(facts: dict, now: datetime) -> list[dict]:
    """Build candidates from already owner-scoped, current source facts."""
    now = aware(now)
    result = []
    for session in facts.get("sessions", []):
        reflection = session.get("reflection")
        resume = session.get("resume_note") or (reflection or {}).get("resume_note")
        if session.get("status") == "ended" and resume and resume.strip():
            refs = [session["source_ref"]]
            if reflection:
                refs.append(reflection["source_ref"])
            result.append(
                make_candidate(
                    "continue",
                    refs,
                    f"上次留下的位置：{resume.strip()[:160]}",
                    subject_id=session.get("subject_id"),
                    knowledge_point_id=session.get("knowledge_point_id"),
                    now=now,
                )
            )

    for problem in facts.get("problems", []):
        attempts = problem.get("attempts", [])
        if not attempts:
            continue
        latest = max(attempts, key=lambda item: (aware(item["occurred_at"]), item["id"]))
        if latest["answer_check"] == "pending":
            result.append(
                make_candidate(
                    "unverified",
                    [problem["source_ref"], latest["source_ref"]],
                    "最近一次作答还没有核对。",
                    subject_id=problem.get("subject_id"),
                    problem_id=problem["id"],
                    now=now,
                )
            )
        elif review_due(latest, now):
            age_days = max(0, int((now - aware(latest["occurred_at"])).total_seconds() // 86400))
            independent = latest["result"] == "correct" and latest["independence"] == "independent"
            threshold = INDEPENDENT_REVIEW_AFTER_DAYS if independent else REVIEW_AFTER_DAYS
            result_label = _localized_result("correct" if independent else latest["result"])
            date_label = aware(latest["occurred_at"]).date().isoformat()
            result.append(
                make_candidate(
                    "review",
                    [problem["source_ref"], latest["source_ref"]],
                    f"上次作答于{date_label} UTC，结果为{result_label}；截至{now.date().isoformat()}已过{age_days}天，达到{threshold}天回顾阈值。",
                    subject_id=problem.get("subject_id"),
                    problem_id=problem["id"],
                    now=now,
                )
            )

    for point in facts.get("knowledge_points", []):
        # The policy window is the latest 20 checked attempts. Pending attempts must
        # not crowd checked evidence out of the window.
        attempts = [
            attempt for attempt in point.get("attempts", []) if attempt["answer_check"] == "checked"
        ][:REPEATED_ERROR_WINDOW]
        categories: dict[str, list[dict]] = {}
        for attempt in attempts:
            if attempt["result"] in ("partial", "incorrect"):
                for category in attempt.get("error_categories", []):
                    categories.setdefault(category, []).append(attempt)
        for category, matches in categories.items():
            if len(matches) >= REPEATED_ERROR_THRESHOLD:
                refs = [point["source_ref"]]
                for attempt in matches:
                    refs.extend([attempt["problem_source_ref"], attempt["source_ref"]])
                result.append(
                    make_candidate(
                        "repeated_error",
                        refs,
                        f"最近{len(attempts)}次已核对作答中，{_localized_category(category)}类错误出现{len(matches)}次。",
                        subject_id=point["subject_id"],
                        knowledge_point_id=point["id"],
                        category=category,
                        now=now,
                    )
                )
    return result


def validate_action(action: str, until: datetime | None, now: datetime) -> datetime | None:
    if action not in {"accept", "snooze", "dismiss"}:
        raise PolicyError("VALIDATION_ERROR", "Unsupported suggestion action.", 422)
    now = aware(now)
    if action != "snooze":
        if until is not None:
            raise PolicyError("VALIDATION_ERROR", "Only snooze accepts a due time.", 422)
        return None
    if until is None:
        until = now + timedelta(days=7)
    until = aware(until)
    delta = until - now
    if delta < timedelta(days=1) or delta > timedelta(days=365):
        raise PolicyError("VALIDATION_ERROR", "Snooze must be 1 to 365 days in the future.", 422)
    return until
