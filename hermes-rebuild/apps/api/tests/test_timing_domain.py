"""Unit checks for the pure timer correction rules (03 §3)."""

from datetime import UTC, datetime, timedelta

import pytest

from hermes_api.domain import PolicyError
from hermes_api.timing_domain import (
    CROSSES_LOCAL_DAY,
    EXCESSIVE_SPAN,
    MAX_SEGMENT_SECONDS,
    clean_note,
    segment_anomalies,
    span_seconds,
    validate_shortening,
)

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)  # 20:00 in Shanghai


def test_plausible_span_is_not_flagged():
    assert (
        segment_anomalies(
            started_at=T0, ended_at=T0 + timedelta(minutes=40), day_timezone="Asia/Shanghai"
        )
        == []
    )


def test_span_over_the_boundary_is_flagged_as_excessive():
    codes = segment_anomalies(
        started_at=T0,
        ended_at=T0 + timedelta(seconds=MAX_SEGMENT_SECONDS + 1),
        day_timezone="UTC",
    )
    assert codes == [EXCESSIVE_SPAN]


def test_span_that_ends_on_another_local_day_is_flagged():
    # 20:00 -> 05:00 next day in Shanghai: an overnight span.
    codes = segment_anomalies(
        started_at=T0, ended_at=T0 + timedelta(hours=9), day_timezone="Asia/Shanghai"
    )
    assert CROSSES_LOCAL_DAY in codes
    assert EXCESSIVE_SPAN in codes


def test_open_span_is_judged_against_now():
    codes = segment_anomalies(
        started_at=T0, ended_at=None, day_timezone="UTC", now=T0 + timedelta(hours=10)
    )
    assert codes == [EXCESSIVE_SPAN]
    assert (
        segment_anomalies(
            started_at=T0, ended_at=None, day_timezone="UTC", now=T0 + timedelta(minutes=5)
        )
        == []
    )


def test_unknown_timezone_does_not_break_reading():
    assert isinstance(
        segment_anomalies(
            started_at=T0, ended_at=T0 + timedelta(minutes=5), day_timezone="Nowhere/X"
        ),
        list,
    )


def test_span_seconds_uses_now_for_an_open_span():
    assert span_seconds(T0, None, T0 + timedelta(seconds=90)) == 90
    assert span_seconds(T0, T0 + timedelta(seconds=30)) == 30
    assert span_seconds(T0, T0 - timedelta(seconds=30)) == 0


def test_a_correction_may_only_shorten_the_span():
    ended = T0 + timedelta(hours=9)
    now = T0 + timedelta(hours=10)
    # Shortening is allowed.
    assert validate_shortening(
        started_at=T0,
        current_ended_at=ended,
        proposed_ended_at=T0 + timedelta(minutes=30),
        session_ended_at=ended,
        now=now,
    ) == T0 + timedelta(minutes=30)
    # Extending is refused.
    for proposed in (ended + timedelta(seconds=1), now + timedelta(seconds=1)):
        with pytest.raises(PolicyError) as error:
            validate_shortening(
                started_at=T0,
                current_ended_at=ended,
                proposed_ended_at=proposed,
                session_ended_at=ended,
                now=now,
            )
        assert error.value.status == 422
    # Ending before the span started is refused.
    with pytest.raises(PolicyError):
        validate_shortening(
            started_at=T0,
            current_ended_at=ended,
            proposed_ended_at=T0 - timedelta(seconds=1),
            session_ended_at=ended,
            now=now,
        )
    # No end supplied is refused.
    with pytest.raises(PolicyError):
        validate_shortening(
            started_at=T0,
            current_ended_at=ended,
            proposed_ended_at=None,
            session_ended_at=ended,
            now=now,
        )


def test_clean_note_trims_and_bounds():
    assert clean_note(None) is None
    assert clean_note("  ") is None
    assert clean_note("  睡着了  ") == "睡着了"
    with pytest.raises(PolicyError):
        clean_note("n" * 1001)
