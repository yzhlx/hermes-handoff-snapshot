"""Pure factual aggregation rules for records and day summaries."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

RULE_VERSION = "learning-records-v1"


@dataclass(frozen=True)
class SessionFact:
    id: str
    version: int
    goal: str | None
    subject_id: str | None
    status: str
    learning_date: str
    day_timezone: str
    started_at: datetime
    ended_at: datetime | None
    resume_note: str | None
    knowledge_point_id: str | None = None


@dataclass(frozen=True)
class ReflectionFact:
    id: str
    session_id: str
    version: int
    summary: str | None
    recalled_text: str | None
    missing_parts: str | None
    stuck_note: str | None
    updated_at: datetime


@dataclass(frozen=True)
class AttemptFact:
    id: str
    session_id: str
    problem_id: str
    version: int
    answer_check: str
    independence: str
    result: str | None
    occurred_at: datetime
    stuck_note: str | None


@dataclass(frozen=True)
class ProblemFact:
    id: str
    version: int
    title: str | None
    statement: str | None
    updated_at: datetime


@dataclass(frozen=True)
class KnowledgePointFact:
    id: str
    version: int
    name: str
    updated_at: datetime


@dataclass(frozen=True)
class RecordFacts:
    sessions: list[SessionFact]
    reflections: dict[str, ReflectionFact]
    attempts: list[AttemptFact]
    subjects: dict[str, str]
    problems: dict[str, ProblemFact]
    errors: dict[str, list[str]]
    history_attempts: list[AttemptFact]
    problem_points: dict[str, list[str]]
    history_points: dict[str, list[str]]
    knowledge_points: dict[str, KnowledgePointFact]

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


def effective(reflection, attempts):
    return bool(attempts) or bool(
        reflection
        and any(
            (
                (reflection.summary or "").strip(),
                (reflection.recalled_text or "").strip(),
                (reflection.missing_parts or "").strip(),
                (reflection.stuck_note or "").strip(),
            )
        )
    )


def counts(attempts):
    pending = [a for a in attempts if a.answer_check == "pending"]
    checked = [a for a in attempts if a.answer_check == "checked"]
    correct = [a for a in checked if a.result == "correct" and a.independence == "independent"]
    return len(attempts), len(pending), len(checked), len(correct)


def revision(refs):
    payload = json.dumps(refs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((RULE_VERSION + payload).encode()).hexdigest()
