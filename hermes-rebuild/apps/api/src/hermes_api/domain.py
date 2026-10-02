"""Pure learning policy. No transport, database, or model SDK dependencies."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


def utc_now() -> datetime:
    return datetime.now(UTC)


class PolicyError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


@dataclass(frozen=True)
class LearningSession:
    id: str
    owner_id: str
    goal: str | None
    subject_id: str | None
    status: Literal["active", "paused", "ended", "cancelled"]
    version: int
    started_at: datetime
    ended_at: datetime | None
    day_timezone: str
    learning_date: str
    timing_enabled: bool = False
    method_id: str | None = None
    kind: Literal["problem", "recall", "reading", "free"] = "free"
    previous_session_id: str | None = None
    resume_note: str | None = None
    knowledge_point_id: str | None = None
    time_segments: tuple["SessionTimeSegment", ...] = ()

    @property
    def effective_duration_seconds(self) -> int:
        """Sum of counted timer spans. Spans the learner excluded never count."""
        now = utc_now()
        total = 0
        for segment in self.time_segments:
            if segment.excluded_at is not None:
                continue
            start = segment.started_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            end = segment.ended_at or now
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)
            total += max(0, int((end - start).total_seconds()))
        return total

    def check_transition(self, action: str) -> str:
        transitions = {
            ("active", "pause"): "paused",
            ("paused", "resume"): "active",
            ("active", "end"): "ended",
            ("paused", "end"): "ended",
            ("active", "cancel"): "cancelled",
            ("paused", "cancel"): "cancelled",
        }
        if (self.status, action) not in transitions:
            raise PolicyError("INVALID_TRANSITION", "This session cannot perform that action.")
        return transitions[(self.status, action)]


@dataclass(frozen=True)
class SessionTimeSegment:
    id: str
    started_at: datetime
    ended_at: datetime | None
    excluded_at: datetime | None = None
    original_ended_at: datetime | None = None
    correction_note: str | None = None

    @property
    def excluded(self) -> bool:
        return self.excluded_at is not None
