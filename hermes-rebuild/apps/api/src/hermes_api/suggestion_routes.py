"""HTTP endpoints for deterministic learning suggestions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .domain import PolicyError
from .schemas import Envelope, ErrorEnvelope
from .suggestion_schemas import SuggestionActionInput, SuggestionData, SuggestionPageData
from .suggestion_service import SuggestionService
from .suggestion_storage import SQLSuggestionUnitOfWork


def create_suggestion_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    def envelope(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get(
        "/api/v1/suggestions", response_model=Envelope[SuggestionPageData], responses=errors
    )
    def suggestions(
        request: Request,
        kind: str | None = None,
        subject_id: UUID | None = None,
        status: str = "available",
        limit: int = 20,
        cursor: UUID | None = None,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        result = SuggestionService(SQLSuggestionUnitOfWork(db)).list(
            auth[0].id,
            kind=kind,
            subject_id=str(subject_id) if subject_id else None,
            status=status,
            limit=limit,
            cursor=str(cursor) if cursor else None,
        )
        return envelope(request, result)

    @router.get(
        "/api/v1/suggestions/{suggestion_id}",
        response_model=Envelope[SuggestionData],
        responses=errors,
    )
    def suggestion(
        suggestion_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return envelope(
            request,
            SuggestionService(SQLSuggestionUnitOfWork(db)).get(auth[0].id, str(suggestion_id)),
        )

    @router.post(
        "/api/v1/suggestions/{suggestion_id}/actions",
        response_model=Envelope[SuggestionData],
        responses=errors,
    )
    def action(
        suggestion_id: UUID,
        body: SuggestionActionInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        if if_match is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        try:
            version = int(if_match.strip().strip('"'))
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if version < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        payload = body.model_dump(mode="python")
        payload["operation_id"] = str(body.operation_id)
        result = SuggestionService(SQLSuggestionUnitOfWork(db)).act(
            auth[0].id, str(suggestion_id), payload, idempotency_key, version
        )
        return envelope(request, result)

    return router
