"""Validation rules for first-class learning stuck points.

Pure policy: no transport, database or model dependencies. A stuck point is one
short sentence ("just where did it actually break?"), never a long error
analysis, and it never carries a mastery judgement.
"""

from .domain import PolicyError

STATUSES = ("open", "resolved")
MAX_TEXT = 1000
MAX_RESOLUTION_NOTE = 2000


def clean_text(value):
    """Trim and validate the one-sentence description of the stuck point."""
    text = (value or "").strip()
    if not text:
        raise PolicyError("VALIDATION_ERROR", "Stuck point text is required.", 422)
    if len(text) > MAX_TEXT:
        raise PolicyError(
            "VALIDATION_ERROR", f"Stuck point text must be at most {MAX_TEXT} characters.", 422
        )
    return text


def clean_note(value):
    """Optional short note; an empty value clears the note instead of storing ``""``."""
    if value is None:
        return None
    note = value.strip()
    if len(note) > MAX_RESOLUTION_NOTE:
        raise PolicyError(
            "VALIDATION_ERROR",
            f"Resolution note must be at most {MAX_RESOLUTION_NOTE} characters.",
            422,
        )
    return note or None


def check_status(value):
    if value not in STATUSES:
        raise PolicyError("VALIDATION_ERROR", "Unknown stuck point status.", 422)
    return value
