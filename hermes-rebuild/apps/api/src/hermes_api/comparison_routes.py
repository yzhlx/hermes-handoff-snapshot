"""HTTP endpoints for user-authored comparisons."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .comparison_schemas import (
    ComparisonData,
    ComparisonPageData,
    CreateComparisonInput,
    PatchComparisonInput,
)
from .comparison_service import ComparisonService
from .comparison_storage import SQLComparisonUnitOfWork
from .domain import PolicyError
from .schemas import Envelope, ErrorEnvelope


def create_comparison_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    def response(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/problem-comparisons",
        status_code=201,
        response_model=Envelope[ComparisonData],
        responses=errors,
    )
    def create(
        body: CreateComparisonInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            ComparisonService(SQLComparisonUnitOfWork(db)).create(
                auth[0].id, body.model_dump(mode="json"), idempotency_key
            ),
        )

    @router.get(
        "/api/v1/problem-comparisons", response_model=Envelope[ComparisonPageData], responses=errors
    )
    def list_items(
        request: Request,
        problem_id: UUID | None = None,
        subject_id: UUID | None = None,
        archived: bool | None = False,
        limit: int = 50,
        cursor: UUID | None = None,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        value = ComparisonService(SQLComparisonUnitOfWork(db)).list(
            auth[0].id,
            problem_id=str(problem_id) if problem_id else None,
            subject_id=str(subject_id) if subject_id else None,
            archived=archived,
            limit=limit,
            cursor=str(cursor) if cursor else None,
        )
        return response(request, value)

    @router.get(
        "/api/v1/problem-comparisons/{comparison_id}",
        response_model=Envelope[ComparisonData],
        responses=errors,
    )
    def get(
        comparison_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(
            request,
            ComparisonService(SQLComparisonUnitOfWork(db)).get(auth[0].id, str(comparison_id)),
        )

    @router.patch(
        "/api/v1/problem-comparisons/{comparison_id}",
        response_model=Envelope[ComparisonData],
        responses=errors,
    )
    def patch(
        comparison_id: UUID,
        body: PatchComparisonInput,
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
        value = ComparisonService(SQLComparisonUnitOfWork(db)).patch(
            auth[0].id,
            str(comparison_id),
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
        )
        return response(request, value)

    return router
