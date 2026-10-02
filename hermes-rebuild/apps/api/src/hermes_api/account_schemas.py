"""Wire contracts for account data sovereignty."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateDeletionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    confirmation: str = Field(max_length=40)


class CancelDeletionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class PurgeDeletionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    confirmation: str = Field(max_length=40)


class CreateExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class AccountDeletionData(BaseModel):
    id: str
    version: int
    status: Literal["pending", "cancelled", "completed"]
    confirmation: str
    impact: dict
    purge_after: str
    cancelled_at: str | None
    completed_at: str | None
    created_at: str


class AccountExportData(BaseModel):
    id: str
    status: Literal["ready", "failed", "expired"]
    byte_size: int | None
    sha256: str | None
    record_counts: dict
    expires_at: str | None
    created_at: str


class AccountExportPageData(BaseModel):
    items: list[AccountExportData]
    next_cursor: str | None = None


class AccountStatusData(BaseModel):
    status: Literal["active", "deletion_pending", "deleted"]
    username: str
    timezone: str
    record_count: int
    deletion: AccountDeletionData | None


class ExportDownloadData(BaseModel):
    id: str
    document: dict
    byte_size: int
    sha256: str | None
    expires_at: str | None
