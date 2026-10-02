"""Pure rules for user-declared mastery and current evidence signals."""

import hashlib
import json
from enum import StrEnum

RULE_VERSION = "mastery-evidence-v1"
ERROR_CATEGORIES = (
    "concept",
    "modeling",
    "condition",
    "formula",
    "derivation",
    "calculation",
    "sign",
    "unit",
    "reading",
    "other",
)


class MasteryLevel(StrEnum):
    UNFAMILIAR = "unfamiliar"
    ENCOUNTERED = "encountered"
    TYPICAL = "typical"
    INDEPENDENT = "independent"
    VARIANT_STABLE = "variant_stable"


class EvidenceRuleError(ValueError):
    """A submitted evidence selection is not valid for its self-assessment."""


def validate_assessment(level: str, variant_note: str | None, attempts: list[dict]) -> None:
    if level == MasteryLevel.VARIANT_STABLE and attempts and not (variant_note or "").strip():
        raise EvidenceRuleError("A linked variant-stable assessment needs the user's variant note.")
    if level in (MasteryLevel.INDEPENDENT, MasteryLevel.VARIANT_STABLE) and any(
        attempt.get("independence") != "independent" or attempt.get("result") != "correct"
        for attempt in attempts
    ):
        raise EvidenceRuleError(
            "This self-assessment level only accepts independent correct attempts."
        )


def assess_link_status(link: dict) -> str:
    """Compare an immutable source snapshot to its current rows and association."""
    if (
        link["current_attempt_version"] != link["attempt_version"]
        or link["current_problem_version"] != link["problem_version"]
        or not link["currently_linked"]
        or link["current_answer_check"] != "checked"
    ):
        return "stale"
    if link["level"] in (MasteryLevel.INDEPENDENT, MasteryLevel.VARIANT_STABLE) and (
        link["current_independence"] != "independent" or link["current_result"] != "correct"
    ):
        return "stale"
    return "current"


def assessment_status(links: list[dict]) -> str:
    if not links:
        return "unsupported"
    return "stale" if any(assess_link_status(link) == "stale" for link in links) else "current"


def derive_counts(attempts: list[dict]) -> dict:
    ordered = sorted(attempts, key=lambda item: (item["occurred_at"], item["id"]), reverse=True)
    checked = [item for item in ordered if item["answer_check"] == "checked"]
    checked_correct = [item for item in checked if item["result"] == "correct"]
    independent_correct = [
        item for item in checked_correct if item["independence"] == "independent"
    ]
    categories: dict[str, list[dict]] = {category: [] for category in ERROR_CATEGORIES}
    for item in checked:
        for category in set(item.get("error_categories", [])):
            if category in categories:
                categories[category].append(item)

    # This is a recent checked-record sequence, never a claim that every attempt was consecutive.
    streak: list[dict] = []
    for item in checked:
        if item["independence"] != "independent" or item["result"] != "correct":
            break
        streak.append(item)
    pending_count = sum(item["answer_check"] == "pending" for item in ordered)

    def ref(item):
        return {
            "attempt_id": item["id"],
            "attempt_version": item["version"],
            "problem_id": item["problem_id"],
            "problem_version": item["problem_version"],
        }

    return {
        "attempt_count": len(ordered),
        "pending_count": pending_count,
        "checked_count": len(checked),
        "checked_correct_count": len(checked_correct),
        "checked_correct_rate": len(checked_correct) / len(checked) if checked else None,
        "independent_correct_count": len(independent_correct),
        "recent_checked_streak": {
            "count": len(streak),
            "label": f"最近 {len(streak)} 个已核对记录",
            "pending_count": pending_count,
            "source_refs": [ref(item) for item in streak],
        },
        "error_categories": [
            {
                "category": category,
                "attempt_count": len(rows),
                "source_refs": [ref(row) for row in rows],
            }
            for category, rows in categories.items()
        ],
        "source_refs": [ref(item) for item in ordered],
    }


def source_revision(source_refs: list[dict]) -> str:
    payload = json.dumps(
        {"rule_version": RULE_VERSION, "source_refs": source_refs},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
