"""Pure rules for naming and subject-scoped knowledge links."""

from .domain import PolicyError


def normalize_knowledge_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise PolicyError("VALIDATION_ERROR", "Name must contain non-whitespace text.", 422)
    return name


def validate_link_subject(problem_subject_id: str | None, point_subject_ids: list[str]) -> None:
    if problem_subject_id and any(
        subject_id != problem_subject_id for subject_id in point_subject_ids
    ):
        raise PolicyError(
            "VALIDATION_ERROR", "Knowledge point must match the problem subject.", 422
        )
