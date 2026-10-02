"""Validation rules for persisted, user-authored problem comparisons."""

from .domain import PolicyError

FIELDS = (
    "conditions",
    "known_values",
    "formulas",
    "entry_point",
    "diagram",
    "boundary",
    "assumptions",
    "conclusion",
)
TEXT_FIELDS = FIELDS


def validate_texts(values, *, require_content):
    cleaned = {}
    for field in FIELDS:
        if field in values:
            value = values[field]
            if value is not None:
                value = value.strip()
                if len(value) > 2000:
                    raise PolicyError(
                        "VALIDATION_ERROR", f"{field} must be at most 2000 characters.", 422
                    )
            cleaned[field] = value
    if require_content and not any(cleaned.get(field, "") for field in FIELDS):
        raise PolicyError(
            "VALIDATION_ERROR", "At least one comparison field must contain text.", 422
        )
    return cleaned
