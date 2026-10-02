"""Honest feedback vocabulary and validation, independent of AI and persistence."""

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Independence(StrEnum):
    INDEPENDENT = "independent"
    HINTED = "hinted"
    AFTER_ANSWER = "after_answer"
    UNABLE = "unable"


class AnswerCheck(StrEnum):
    PENDING = "pending"
    CHECKED = "checked"


class Result(StrEnum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class ErrorCategory(StrEnum):
    CONCEPT = "concept"
    MODELING = "modeling"
    CONDITION = "condition"
    FORMULA = "formula"
    DERIVATION = "derivation"
    CALCULATION = "calculation"
    SIGN = "sign"
    UNIT = "unit"
    READING = "reading"
    OTHER = "other"


class AttachmentRole(StrEnum):
    QUESTION = "question"
    ATTEMPT = "attempt"
    ANSWER = "answer"
    SOURCE = "source"


class ProblemAttachmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attachment_id: UUID
    role: AttachmentRole
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_page_range(self) -> Self:
        if (self.page_start is None) != (self.page_end is None):
            raise ValueError("Both page_start and page_end must be provided together.")
        if self.page_start is not None and self.page_end < self.page_start:
            raise ValueError("page_end must not be before page_start.")
        return self


class AttemptFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    independence: Independence
    answer_check: AnswerCheck
    result: Result | None = None
    error_categories: list[ErrorCategory] = Field(default_factory=list, max_length=10)
    attempt_text: str | None = Field(default=None, max_length=10000)
    stuck_note: str | None = Field(default=None, max_length=2000)
    other_error_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def honest_result(self) -> Self:
        if self.answer_check == AnswerCheck.PENDING and self.result is not None:
            raise ValueError("An unchecked attempt cannot have a result.")
        if self.answer_check == AnswerCheck.CHECKED and self.result is None:
            raise ValueError("A checked attempt must include the user's result.")
        if len(set(self.error_categories)) != len(self.error_categories):
            raise ValueError("Each error category may occur only once per attempt.")
        if self.result == Result.CORRECT and self.error_categories:
            raise ValueError("A fully correct result cannot include error categories.")
        if self.other_error_note and ErrorCategory.OTHER not in self.error_categories:
            raise ValueError("An other-error note needs the other category.")
        return self

    @property
    def independently_correct(self) -> bool:
        return (
            self.independence == Independence.INDEPENDENT
            and self.answer_check == AnswerCheck.CHECKED
            and self.result == Result.CORRECT
        )


class ReflectionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, max_length=10000)
    recalled_text: str | None = Field(default=None, max_length=10000)
    reference_checked: bool | None = None
    missing_parts: str | None = Field(default=None, max_length=10000)
    stuck_note: str | None = Field(default=None, max_length=2000)
    resume_note: str | None = Field(default=None, max_length=2000)

    @property
    def has_learning_evidence(self) -> bool:
        # A timer, a future position, or merely checking a box is not learning evidence.
        return any(value and value.strip() for value in (self.summary, self.recalled_text))


class CreateReflection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    session_id: UUID
    summary: str | None = Field(default=None, max_length=10000)
    recalled_text: str | None = Field(default=None, max_length=10000)
    reference_checked: bool | None = None
    missing_parts: str | None = Field(default=None, max_length=10000)
    stuck_note: str | None = Field(default=None, max_length=2000)
    resume_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def nonempty_reflection(self) -> Self:
        if not any(
            value.strip()
            for value in (self.summary, self.recalled_text, self.missing_parts, self.stuck_note)
            if value
        ):
            raise ValueError("Reflection must contain actual learning content.")
        return self


class CreateProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    subject_id: UUID | None = None
    title: str | None = Field(default=None, max_length=300)
    statement: str | None = Field(default=None, max_length=50000)
    source_note: str | None = Field(default=None, max_length=10000)
    attachment_links: list[ProblemAttachmentInput] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def has_question(self) -> Self:
        if not (self.statement or "").strip() and not any(
            link.role == AttachmentRole.QUESTION for link in self.attachment_links
        ):
            raise ValueError("Problem needs statement text or a question attachment.")
        keys = [
            (item.attachment_id, item.role, item.page_start, item.page_end)
            for item in self.attachment_links
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Equivalent attachment links may not be repeated.")
        return self


class LinkProblemAttachment(ProblemAttachmentInput):
    operation_id: UUID


class UnlinkProblemAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class UpdateReflection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    summary: str | None = Field(default=None, max_length=10000)
    recalled_text: str | None = Field(default=None, max_length=10000)
    reference_checked: bool | None = None
    missing_parts: str | None = Field(default=None, max_length=10000)
    stuck_note: str | None = Field(default=None, max_length=2000)
    resume_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def patch_has_fields(self) -> Self:
        if self.model_fields_set == {"operation_id"}:
            raise ValueError("At least one feedback field is required.")
        return self


class CreateAttempt(AttemptFeedback):
    operation_id: UUID
    session_id: UUID
    problem_id: UUID
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def aware_time(self) -> Self:
        if self.occurred_at is not None and self.occurred_at.tzinfo is None:
            raise ValueError("Attempt time must include a timezone.")
        return self


class UpdateAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    independence: Independence | None = None
    answer_check: AnswerCheck | None = None
    result: Result | None = None
    error_categories: list[ErrorCategory] | None = Field(default=None, max_length=10)
    attempt_text: str | None = Field(default=None, max_length=10000)
    stuck_note: str | None = Field(default=None, max_length=2000)
    other_error_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_patch(self) -> Self:
        if self.model_fields_set == {"operation_id"}:
            raise ValueError("At least one feedback field is required.")
        if "independence" in self.model_fields_set and self.independence is None:
            raise ValueError("Independence cannot be cleared.")
        if "answer_check" in self.model_fields_set and self.answer_check is None:
            raise ValueError("Answer check cannot be cleared.")
        if len(set(self.error_categories or [])) != len(self.error_categories or []):
            raise ValueError("Each error category may occur only once per attempt.")
        if self.answer_check == AnswerCheck.CHECKED and self.result is None:
            raise ValueError("A checked attempt must include the user's result.")
        if self.answer_check == AnswerCheck.PENDING and self.result is not None:
            raise ValueError("An unchecked attempt cannot have a result.")
        if self.result == Result.CORRECT and self.error_categories:
            raise ValueError("A fully correct result cannot include error categories.")
        return self
