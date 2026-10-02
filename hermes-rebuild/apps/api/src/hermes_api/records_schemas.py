"""Wire schemas for factual records and day summaries."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from .suggestion_schemas import SourceRef


class RecordData(BaseModel):
    id: str
    version: int
    goal: str | None
    subject_id: str | None
    subject_name: str | None = None
    status: Literal["active", "paused", "ended", "cancelled"]
    learning_date: date
    day_timezone: str
    started_at: datetime
    ended_at: datetime | None
    resume_note: str | None
    summary: str | None
    recalled_text: str | None
    missing_parts: str | None
    stuck_note: str | None
    attempt_count: int
    pending_count: int
    checked_count: int
    independent_correct_count: int
    effective: bool
    source_refs: list[SourceRef]


class RecordsTotals(BaseModel):
    session_count: int
    effective_record_count: int
    pending_count: int
    checked_count: int
    independent_correct_count: int


class RecordsPageData(BaseModel):
    items: list[RecordData]
    next_cursor: str | None
    from_date: date
    to_date: date
    timezone: str
    rule_version: str
    source_revision: str
    totals: RecordsTotals


class SummaryTextItem(BaseModel):
    text: str
    source_refs: list[SourceRef]


class ErrorCategoryData(BaseModel):
    category: str
    count: int
    source_refs: list[SourceRef]


class DaySummaryData(BaseModel):
    date: date
    timezone: str
    rule_version: str
    source_revision: str
    session_count: int
    effective_record_count: int
    pending_count: int
    checked_count: int
    independent_correct_count: int
    learned: list[SummaryTextItem]
    changes: list[SummaryTextItem]
    stuck_points: list[SummaryTextItem]
    error_categories: list[ErrorCategoryData]
    review_candidates: list[SummaryTextItem]
    source_refs: list[SourceRef]
