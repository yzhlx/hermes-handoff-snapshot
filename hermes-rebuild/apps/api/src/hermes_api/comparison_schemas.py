"""Wire contracts for problem comparisons."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    left_problem_id: UUID
    right_problem_id: UUID
    left_attempt_id: UUID | None = None
    right_attempt_id: UUID | None = None
    conditions: str | None = Field(default=None, max_length=2000)
    known_values: str | None = Field(default=None, max_length=2000)
    formulas: str | None = Field(default=None, max_length=2000)
    entry_point: str | None = Field(default=None, max_length=2000)
    diagram: str | None = Field(default=None, max_length=2000)
    boundary: str | None = Field(default=None, max_length=2000)
    assumptions: str | None = Field(default=None, max_length=2000)
    conclusion: str | None = Field(default=None, max_length=2000)


class PatchComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    conditions: str | None = Field(default=None, max_length=2000)
    known_values: str | None = Field(default=None, max_length=2000)
    formulas: str | None = Field(default=None, max_length=2000)
    entry_point: str | None = Field(default=None, max_length=2000)
    diagram: str | None = Field(default=None, max_length=2000)
    boundary: str | None = Field(default=None, max_length=2000)
    assumptions: str | None = Field(default=None, max_length=2000)
    conclusion: str | None = Field(default=None, max_length=2000)
    archived: bool | None = None

    @model_validator(mode="after")
    def has_changes(self):
        if not (self.model_fields_set - {"operation_id"}):
            raise ValueError("At least one comparison field is required.")
        if "archived" in self.model_fields_set and self.archived is None:
            raise ValueError("archived cannot be null.")
        return self


class ComparisonData(BaseModel):
    id: str
    version: int
    left_problem_id: str
    right_problem_id: str
    left_attempt_id: str | None
    right_attempt_id: str | None
    conditions: str | None
    known_values: str | None
    formulas: str | None
    entry_point: str | None
    diagram: str | None
    boundary: str | None
    assumptions: str | None
    conclusion: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime
    source_versions: dict[str, int]
    source_changed: bool


class ComparisonPageData(BaseModel):
    items: list[ComparisonData]
    next_cursor: str | None
