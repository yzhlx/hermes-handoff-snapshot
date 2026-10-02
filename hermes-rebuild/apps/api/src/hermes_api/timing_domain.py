"""Pure rules for reading and correcting persisted timer spans.

Time is recorded, never scored. A correction only changes how long the timer
says a session ran; it never changes what was learned and never becomes a
mastery signal. Corrections may only **shorten** an implausible span, so the
timer can be brought back in line with reality but never inflated.

The authoritative requirement is 03 §3: a timer segment must show spans the
user can correct, and overnight time must not silently count as study.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .domain import PolicyError

# A single uninterrupted span longer than this is surfaced for review: in
# practice it usually means the page stayed open while the learner walked away.
MAX_SEGMENT_SECONDS = 4 * 3600

EXCESSIVE_SPAN = "excessive_span"
CROSSES_LOCAL_DAY = "crosses_local_day"
ANOMALY_CODES = (EXCESSIVE_SPAN, CROSSES_LOCAL_DAY)
MAX_CORRECTION_NOTE = 1000


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def span_seconds(
    started_at: datetime, ended_at: datetime | None, now: datetime | None = None
) -> int:
    start = aware(started_at)
    end = aware(ended_at) or aware(now) or datetime.now(UTC)
    if start is None:
        return 0
    return max(0, int((end - start).total_seconds()))


def _local_date(value: datetime, timezone_name: str):
    moment = aware(value)
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:  # noqa: BLE001 - an unknown timezone must not break reading
        zone = ZoneInfo("UTC")
    return moment.astimezone(zone).date()


def segment_anomalies(
    *,
    started_at: datetime,
    ended_at: datetime | None,
    day_timezone: str,
    now: datetime | None = None,
) -> list[str]:
    """Review codes for one span. An empty list means it looks plausible."""
    moment = aware(now) or datetime.now(UTC)
    end = aware(ended_at) or moment
    start = aware(started_at)
    if start is None:
        return []
    codes: list[str] = []
    if (end - start).total_seconds() > MAX_SEGMENT_SECONDS:
        codes.append(EXCESSIVE_SPAN)
    if _local_date(start, day_timezone) != _local_date(end, day_timezone):
        codes.append(CROSSES_LOCAL_DAY)
    return codes


def clean_note(value: str | None) -> str | None:
    if value is None:
        return None
    note = value.strip()
    if len(note) > MAX_CORRECTION_NOTE:
        raise PolicyError(
            "VALIDATION_ERROR",
            f"Correction note must be at most {MAX_CORRECTION_NOTE} characters.",
            422,
        )
    return note or None


def validate_shortening(
    *, started_at, current_ended_at, proposed_ended_at, session_ended_at, now=None
):
    """Return the validated end time. A correction may only shorten the span."""
    start = aware(started_at)
    proposed = aware(proposed_ended_at)
    moment = aware(now) or datetime.now(UTC)
    if proposed is None:
        raise PolicyError("VALIDATION_ERROR", "Correction needs an end time.", 422)
    if proposed < start:
        raise PolicyError("VALIDATION_ERROR", "Correction cannot end before the span started.", 422)
    if proposed > moment:
        raise PolicyError("VALIDATION_ERROR", "Correction cannot end in the future.", 422)
    limit = aware(current_ended_at) or aware(session_ended_at) or moment
    if proposed > limit:
        raise PolicyError("VALIDATION_ERROR", "Correction cannot extend the recorded span.", 422)
    return proposed
