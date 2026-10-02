"""Wire contracts for the optional AI advisor."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .advisor_domain import MAX_TOPIC_LENGTH


class CreateAdvisorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    topic: str | None = Field(default=None, max_length=MAX_TOPIC_LENGTH)
    subject_id: UUID | None = None
    knowledge_point_id: UUID | None = None


class CancelAdvisorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class CitedText(BaseModel):
    text: str
    source_refs: list[str]


class EvidenceRef(BaseModel):
    id: str
    kind: str
    version: int
    label: str | None


class AdvisorPrivacy(BaseModel):
    external: bool
    provider: str
    scope: str


class AdvisorRunData(BaseModel):
    id: str
    status: str
    topic: str | None
    subject_id: str | None
    knowledge_point_id: str | None
    facts: list[CitedText]
    inferences: list[CitedText]
    missing_information: list[str]
    summary: str
    degradation_reason: str | None
    evidence_count: int
    evidence_refs: list[EvidenceRef]
    data_version: str
    model_id: str
    provider: str
    prompt_version: str
    policy_version: str
    rule_version: str
    privacy: AdvisorPrivacy
    created_at: datetime
    updated_at: datetime


class AdvisorPageData(BaseModel):
    items: list[AdvisorRunData]
    next_cursor: str | None
