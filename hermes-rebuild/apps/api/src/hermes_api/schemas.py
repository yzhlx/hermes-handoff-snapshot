"""Versioned HTTP schemas; these produce the frontend contract."""

from datetime import datetime
from typing import Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str


class Envelope[T](BaseModel):
    data: T
    meta: Meta


class HealthData(BaseModel):
    status: Literal["ok"] = "ok"


class ProductMeta(BaseModel):
    name: Literal["Hermes"] = "Hermes"
    version: Literal["0.1.0"] = "0.1.0"
    agent_mode: Literal["mock"] = "mock"
    environment: str


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=1024)


class UserData(BaseModel):
    id: str
    username: str
    timezone: str


class AuthData(BaseModel):
    user: UserData
    csrf_token: str


class SubjectData(BaseModel):
    id: str
    name: str
    group_label: str | None = None


class SubjectsData(BaseModel):
    items: list[SubjectData]


class ChapterData(BaseModel):
    id: str
    subject_id: str
    name: str
    order_index: int
    version: int
    created_at: str
    updated_at: str
    archived: bool


class KnowledgePointData(BaseModel):
    id: str
    chapter_id: str
    subject_id: str
    name: str
    notes: str | None
    version: int
    created_at: str
    updated_at: str
    archived: bool


class ChapterPageData(BaseModel):
    items: list[ChapterData]
    next_cursor: str | None


class KnowledgePointPageData(BaseModel):
    items: list[KnowledgePointData]
    next_cursor: str | None


class CreateChapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    subject_id: UUID
    name: str = Field(min_length=1, max_length=200)
    order_index: int = Field(default=0, ge=0, le=100000)


class PatchChapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=200)
    order_index: int | None = Field(default=None, ge=0, le=100000)
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if not (self.model_fields_set - {"operation_id"}):
            raise ValueError("At least one chapter field is required.")
        for field in ("name", "order_index", "archived"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class CreateKnowledgePointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    chapter_id: UUID
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=20000)


class PatchKnowledgePointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=20000)
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if not (self.model_fields_set - {"operation_id"}):
            raise ValueError("At least one knowledge point field is required.")
        for field in ("name", "archived"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ProblemKnowledgeLinksInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    knowledge_point_ids: list[UUID] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.knowledge_point_ids)) != len(self.knowledge_point_ids):
            raise ValueError("Knowledge point ids must be unique.")
        return self


class ProblemKnowledgeLinksData(BaseModel):
    problem: "ProblemData"
    knowledge_point_ids: list[str]


class SubjectSpaceData(BaseModel):
    subject: SubjectData
    chapters: list[ChapterData]
    chapters_next_cursor: str | None = None
    recent_sessions: list["SessionData"]
    recent_problems: list["ProblemData"]


class CreateSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    goal: str | None = Field(default=None, max_length=2000)
    subject_id: UUID | None = None
    timing_enabled: bool = False
    method_id: str | None = Field(default=None, max_length=80)
    kind: Literal["problem", "recall", "reading", "free"] = "free"
    previous_session_id: UUID | None = None
    resume_note: str | None = Field(default=None, max_length=2000)
    knowledge_point_id: UUID | None = None


class EndSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class SessionTimeSegmentData(BaseModel):
    id: str
    started_at: str
    ended_at: str | None
    duration_seconds: int
    excluded: bool = False
    excluded_at: str | None = None
    original_ended_at: str | None = None
    correction_note: str | None = None
    anomalies: list[str] = Field(default_factory=list)
    review_required: bool = False


class CorrectTimeSegmentInput(BaseModel):
    """Corrections may only shorten a span or exclude it, never extend it."""

    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    ended_at: datetime | None = None
    exclude: bool | None = None
    correction_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def has_changes(self):
        if not (self.model_fields_set - {"operation_id"}):
            raise ValueError("At least one correction field is required.")
        if (
            "ended_at" in self.model_fields_set
            and self.ended_at is not None
            and self.ended_at.tzinfo is None
        ):
            raise ValueError("Correction time must include a timezone.")
        return self


class SessionData(BaseModel):
    id: str
    goal: str | None
    subject_id: str | None
    status: Literal["active", "paused", "ended", "cancelled"]
    version: int
    started_at: str
    ended_at: str | None
    day_timezone: str
    learning_date: str
    method_id: str | None
    timing_enabled: bool
    time_segments: list["SessionTimeSegmentData"]
    effective_duration_seconds: int
    timing_review_required: bool = False
    kind: Literal["problem", "recall", "reading", "free"] = "free"
    previous_session_id: str | None = None
    resume_note: str | None = None
    knowledge_point_id: str | None = None


class SessionHistoryData(BaseModel):
    items: list[SessionData]
    next_cursor: str | None = None


class ProblemPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    title: str | None = Field(default=None, max_length=300)
    statement: str | None = Field(default=None, max_length=50000)
    source_note: str | None = Field(default=None, max_length=10000)
    correct_answer: str | None = Field(default=None, max_length=50000)
    is_representative: bool | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_patch_fields(self):
        if not self.model_fields_set - {"operation_id"}:
            raise ValueError("At least one problem field must be provided.")
        for field in ("is_representative", "archived"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ReflectionData(BaseModel):
    id: str
    session_id: str
    summary: str | None
    recalled_text: str | None
    reference_checked: bool | None
    missing_parts: str | None
    stuck_note: str | None
    resume_note: str | None
    version: int
    created_at: str
    updated_at: str


class EvidenceEligibilityData(BaseModel):
    eligible: bool
    reason: str


class ProblemAttemptData(BaseModel):
    id: str
    session_id: str
    problem_id: str
    independence: Literal["independent", "hinted", "after_answer", "unable"]
    answer_check: Literal["pending", "checked"]
    result: Literal["correct", "partial", "incorrect"] | None
    attempt_text: str | None
    stuck_note: str | None
    occurred_at: str
    verified_at: str | None
    version: int
    created_at: str
    updated_at: str
    error_categories: list[
        Literal[
            "concept",
            "modeling",
            "condition",
            "formula",
            "derivation",
            "calculation",
            "sign",
            "unit",
            "reading",
            "other",
        ]
    ]
    other_error_note: str | None = None
    evidence_eligibility: EvidenceEligibilityData


class ProblemData(BaseModel):
    id: str
    subject_id: str | None
    title: str | None
    statement: str | None
    source_note: str | None
    correct_answer: str | None
    is_representative: bool
    archived: bool
    version: int
    created_at: str
    updated_at: str
    knowledge_point_ids: list[str] = Field(default_factory=list)
    attempts: list[ProblemAttemptData] = Field(default_factory=list)
    attachment_links: list["AttachmentLinkData"] = Field(default_factory=list)


class AttachmentLinkData(BaseModel):
    link_id: str
    attachment_id: str
    role: Literal["question", "attempt", "answer", "source"]
    page_start: int | None
    page_end: int | None
    original_name: str
    detected_mime: str
    byte_size: int
    status: Literal["ready"]


class ProblemAttachmentLinksData(BaseModel):
    items: list[AttachmentLinkData]
    problem_version: int


class ProblemAttachmentLinkWriteData(BaseModel):
    link: AttachmentLinkData
    problem_version: int


class ProblemAttachmentUnlinkData(BaseModel):
    problem_version: int


class ProblemPageData(BaseModel):
    items: list[ProblemData]
    next_cursor: str | None = None


class LearningMethodData(BaseModel):
    id: str
    title: str
    summary: str
    problem: str
    situations: list[str]
    steps: list[str]
    pitfalls: list[str]
    content_version: int


class LearningMethodsData(BaseModel):
    items: list[LearningMethodData]


class LearningSituationData(BaseModel):
    id: str
    label: str
    method_ids: list[str]
    reason: str
    allow_free_learning: bool


class LearningSituationsData(BaseModel):
    items: list[LearningSituationData]


class ErrorData(BaseModel):
    code: str
    message: str
    request_id: str
    current_version: int | None = None
    current: dict | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorData
