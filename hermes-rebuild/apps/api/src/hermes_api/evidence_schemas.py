"""Public wire schemas for user mastery declarations and evidence snapshots."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .evidence_domain import MasteryLevel
from .feedback import ErrorCategory


class CreateMasteryAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    knowledge_point_id: UUID
    level: MasteryLevel
    reason: str | None = Field(default=None, max_length=2000)
    variant_note: str | None = Field(default=None, max_length=2000)
    evidence_attempt_ids: list[UUID] = Field(default_factory=list, max_length=100)


class EvidenceSourceRef(BaseModel):
    attempt_id: str
    attempt_version: int
    problem_id: str
    problem_version: int


class EvidenceCounts(BaseModel):
    attempt_count: int
    pending_count: int
    checked_count: int
    checked_correct_count: int
    checked_correct_rate: float | None
    independent_correct_count: int


class RecentCheckedStreak(BaseModel):
    count: int
    label: str
    pending_count: int
    source_refs: list[EvidenceSourceRef]


class ErrorCategoryEvidence(BaseModel):
    category: ErrorCategory
    attempt_count: int
    source_refs: list[EvidenceSourceRef]


class MasteryAssessmentData(BaseModel):
    id: str
    level: MasteryLevel
    reason: str | None
    variant_note: str | None
    version: int
    knowledge_point_version: int
    created_at: datetime
    evidence_status: Literal["unsupported", "current", "stale"]
    evidence_message: str
    source_refs: list[EvidenceSourceRef]


class KnowledgePointEvidenceData(BaseModel):
    knowledge_point_id: str
    knowledge_point_version: int
    rule_version: str
    source_revision: str
    counts: EvidenceCounts
    recent_checked_streak: RecentCheckedStreak
    error_categories: list[ErrorCategoryEvidence]
    source_refs: list[EvidenceSourceRef]
    assessments: list[MasteryAssessmentData]


class CreatedMasteryAssessmentData(BaseModel):
    assessment: MasteryAssessmentData
    knowledge_point_version: int
