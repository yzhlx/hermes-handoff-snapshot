"""Unit checks for the pure stuck point rules."""

import pytest

from hermes_api.domain import PolicyError
from hermes_api.stuck_point_domain import (
    MAX_RESOLUTION_NOTE,
    MAX_TEXT,
    check_status,
    clean_note,
    clean_text,
)


def test_clean_text_trims_and_requires_content():
    assert clean_text("  为什么 ωs=2π/T？  ") == "为什么 ωs=2π/T？"
    for empty in (None, "", "   ", "\n\t"):
        with pytest.raises(PolicyError) as error:
            clean_text(empty)
        assert error.value.status == 422


def test_clean_text_rejects_over_length():
    assert len(clean_text("x" * MAX_TEXT)) == MAX_TEXT
    with pytest.raises(PolicyError):
        clean_text("x" * (MAX_TEXT + 1))


def test_clean_note_treats_blank_as_cleared():
    assert clean_note(None) is None
    assert clean_note("   ") is None
    assert clean_note("  换元后清楚  ") == "换元后清楚"
    assert len(clean_note("n" * MAX_RESOLUTION_NOTE)) == MAX_RESOLUTION_NOTE
    with pytest.raises(PolicyError):
        clean_note("n" * (MAX_RESOLUTION_NOTE + 1))


def test_check_status_only_accepts_the_declared_lifecycle():
    assert check_status("open") == "open"
    assert check_status("resolved") == "resolved"
    for other in ("archived", "done", "", None):
        with pytest.raises(PolicyError) as error:
            check_status(other)
        assert error.value.status == 422
