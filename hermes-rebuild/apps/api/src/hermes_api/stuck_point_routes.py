"""HTTP endpoints for first-class learning stuck points."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .domain import PolicyError
from .schemas import Envelope, ErrorEnvelope
from .stuck_point_schemas import (
    CreateStuckPointInput,
    PatchStuckPointInput,
    StuckPointData,
    StuckPointPageData,
)
from .stuck_point_service import StuckPointService
from .stuck_point_storage import SQLStuckPointUnitOfWork


def create_stuck_point_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    def response(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/stuck-points",
        status_code=201,
        response_model=Envelope[StuckPointData],
        responses=errors,
    )
    def create(
        body: CreateStuckPointInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            StuckPointService(SQLStuckPointUnitOfWork(db)).create(
                auth[0].id, body.model_dump(mode="json"), idempotency_key
            ),
        )

    @router.get(
        "/api/v1/stuck-points",
        response_model=Envelope[StuckPointPageData],
        responses=errors,
    )
    def list_items(
        request: Request,
        session_id: UUID | None = None,
        knowledge_point_id: UUID | None = None,
        status: Literal["open", "resolved"] | None = None,
        limit: int = 50,
        cursor: str | None = None,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        value = StuckPointService(SQLStuckPointUnitOfWork(db)).list(
            auth[0].id,
            session_id=str(session_id) if session_id else None,
            knowledge_point_id=str(knowledge_point_id) if knowledge_point_id else None,
            status=status,
            limit=limit,
            cursor=cursor,
        )
        return response(request, value)

    @router.get(
        "/api/v1/stuck-points/{stuck_point_id}",
        response_model=Envelope[StuckPointData],
        responses=errors,
    )
    def get(
        stuck_point_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(
            request,
            StuckPointService(SQLStuckPointUnitOfWork(db)).get(auth[0].id, str(stuck_point_id)),
        )

    @router.patch(
        "/api/v1/stuck-points/{stuck_point_id}",
        response_model=Envelope[StuckPointData],
        responses=errors,
    )
    def patch(
        stuck_point_id: UUID,
        body: PatchStuckPointInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        try:
            version = int(if_match.strip().strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if version is not None and version < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        value = StuckPointService(SQLStuckPointUnitOfWork(db)).patch(
            auth[0].id,
            str(stuck_point_id),
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
        )
        return response(request, value)

    return router
