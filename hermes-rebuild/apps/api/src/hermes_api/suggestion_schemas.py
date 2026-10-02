"""Wire contracts for deterministic suggestions and factual learning records."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceRef(BaseModel):
    kind: Literal["session", "reflection", "attempt", "problem", "knowledge_point"]
    id: str
    version: int
    label: str
    occurred_at: datetime
    session_id: str | None = None
    problem_id: str | None = None


class SuggestionData(BaseModel):
    id: str
    version: int
    kind: Literal["continue", "unverified", "review", "repeated_error"]
    status: Literal["available", "accepted", "snoozed", "dismissed", "stale"]
    subject_id: str | None = None
    knowledge_point_id: str | None = None
    problem_id: str | None = None
    reason: str
    source_refs: list[SourceRef]
    source_revision: str
    rule_version: str
    generated_at: datetime
    expires_at: datetime | None = None
    snoozed_until: datetime | None = None


class SuggestionPageData(BaseModel):
    items: list[SuggestionData]
    next_cursor: str | None
    rule_version: str


class SuggestionActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    action: Literal["accept", "snooze", "dismiss"]
    snoozed_until: datetime | None = None
