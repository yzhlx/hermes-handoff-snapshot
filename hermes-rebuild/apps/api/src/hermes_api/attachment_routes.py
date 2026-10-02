"""Authenticated private binary transfer and attachment metadata endpoints."""

from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .attachment_object_store import make_store
from .attachment_repository import SQLAttachmentRepository
from .attachment_service import AttachmentService
from .attachment_validation import ProcessFileValidator
from .schemas import Envelope, ErrorEnvelope


class UploadInit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    declared_mime: str = Field(min_length=1, max_length=100)
    byte_size: int = Field(gt=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class CompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


class PreviewJobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    kind: str = "preview"
    page: int = Field(ge=1, le=100)


class AttachmentData(BaseModel):
    id: str
    version: int
    status: Literal["pending_upload", "uploaded", "validating", "ready", "rejected", "expired"]
    original_name: str
    detected_mime: str | None
    byte_size: int | None
    sha256: str | None
    page_count: int | None
    failure_code: str | None
    created_at: str
    updated_at: str
    expires_at: str


class AttachmentJobData(BaseModel):
    id: str
    attachment_id: str
    kind: Literal["validate", "preview"]
    status: Literal["queued", "running", "succeeded", "failed"]
    input_version: int
    attempt_count: int
    error_code: str | None


def create_attachment_router(database, identity, authorized_write, settings):
    router = APIRouter(
        responses={
            code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 413, 415, 422, 429, 503)
        }
    )

    def service(db):
        repository = SQLAttachmentRepository(
            db,
            make_store(settings),
            ProcessFileValidator(),
            settings.attachment_max_pending_per_owner,
        )
        return AttachmentService(repository)

    def envelope(request, data):
        return {"data": data, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/attachments/uploads", status_code=201, response_model=Envelope[AttachmentData]
    )
    def initialize(
        body: UploadInit,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        key = idempotency_key or ""
        data = service(db).initialize(auth[0].id, body.model_dump(mode="json"), key)
        return envelope(request, data)

    @router.put(
        "/api/v1/attachments/{attachment_id}/content", response_model=Envelope[AttachmentData]
    )
    async def upload(
        attachment_id: UUID,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        data = await service(db).upload(
            auth[0].id,
            str(attachment_id),
            request.stream(),
            request.headers.get("content-type", ""),
            idempotency_key,
        )
        return envelope(request, data)

    @router.post(
        "/api/v1/attachments/{attachment_id}/complete",
        status_code=202,
        response_model=Envelope[AttachmentJobData],
    )
    def complete(
        attachment_id: UUID,
        body: CompleteInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        data = service(db).complete(
            auth[0].id, str(attachment_id), body.operation_id, idempotency_key
        )
        return envelope(request, data)

    @router.post(
        "/api/v1/attachments/{attachment_id}/jobs",
        status_code=202,
        response_model=Envelope[AttachmentJobData],
    )
    def preview_job(
        attachment_id: UUID,
        body: PreviewJobInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        data = service(db).create_preview_job(
            auth[0].id, str(attachment_id), body.operation_id, body.kind, body.page, idempotency_key
        )
        return envelope(request, data)

    @router.get("/api/v1/jobs/{job_id}", response_model=Envelope[AttachmentJobData])
    def get_job(
        job_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        return envelope(request, service(db).get_job(auth[0].id, str(job_id)))

    @router.get("/api/v1/attachments/{attachment_id}", response_model=Envelope[AttachmentData])
    def get_attachment(
        attachment_id: UUID,
        request: Request,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        return envelope(request, service(db).get_attachment(auth[0].id, str(attachment_id)))

    def stream_chunks(stream):
        try:
            while chunk := stream.read(128 * 1024):
                yield chunk
        finally:
            stream.close()

    @router.get(
        "/api/v1/attachments/{attachment_id}/content",
        responses={
            200: {
                "content": {
                    "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
                }
            }
        },
    )
    def content(attachment_id: UUID, auth=Depends(identity), db: Session = Depends(database)):
        svc = service(db)
        stream, filename = svc.open_original(auth[0].id, str(attachment_id))
        disposition = (
            f"attachment; filename=attachment; filename*=UTF-8''{quote(filename, safe='')}"
        )
        return StreamingResponse(
            stream_chunks(stream),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": disposition,
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
            },
        )

    @router.get(
        "/api/v1/attachments/{attachment_id}/preview",
        responses={
            200: {"content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}}
        },
    )
    def preview(
        attachment_id: UUID, page: int, auth=Depends(identity), db: Session = Depends(database)
    ):
        svc = service(db)
        return StreamingResponse(
            stream_chunks(svc.open_preview(auth[0].id, str(attachment_id), page)),
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=preview.png",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
                "Content-Security-Policy": "default-src 'none'; sandbox",
            },
        )

    return router
