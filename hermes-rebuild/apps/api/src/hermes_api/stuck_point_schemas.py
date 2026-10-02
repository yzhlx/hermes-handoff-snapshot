"""Wire contracts for stuck points."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateStuckPointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    session_id: UUID
    knowledge_point_id: UUID | None = None
    attempt_id: UUID | None = None
    text: str = Field(min_length=1, max_length=1000)


class PatchStuckPointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    text: str | None = Field(default=None, max_length=1000)
    status: Literal["open", "resolved"] | None = None
    resolution_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def has_changes(self):
        if not (self.model_fields_set - {"operation_id"}):
            raise ValueError("At least one stuck point field is required.")
        return self


class StuckPointData(BaseModel):
    id: str
    version: int
    session_id: str
    attempt_id: str | None
    knowledge_point_id: str | None
    text: str
    status: Literal["open", "resolved"]
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class StuckPointPageData(BaseModel):
    items: list[StuckPointData]
    next_cursor: str | None
