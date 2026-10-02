"""Router factory for the server-owned daily quote and quote-preference API."""

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from .domain import PolicyError
from .quotes_schemas import (
    QuoteFavoritesData,
    QuotePreferenceInput,
    QuotePreferenceResultData,
    QuoteTodayData,
)
from .quotes_storage import QuoteRepository
from .schemas import Envelope, ErrorEnvelope


def create_quotes_router(database, identity, authorized_write, *, now=None, shuffle=None):
    router = APIRouter(prefix="/api/v1/quotes", tags=["quotes"])
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    def result(request: Request, data):
        return {"data": data, "meta": {"request_id": request.state.request_id}}

    @router.get("/today", response_model=Envelope[QuoteTodayData], responses=errors)
    def today(request: Request, auth=Depends(identity), db: Session = Depends(database)):  # noqa: B008
        user, _login = auth
        data = QuoteRepository(db, now=now, shuffle=shuffle).today(user.id, user.timezone)
        db.commit()  # The first GET for a local date persists its one-time allocation.
        return result(request, data)

    @router.get("/favorites", response_model=Envelope[QuoteFavoritesData], responses=errors)
    def favorites(
        request: Request,
        cursor: str | None = Query(default=None, max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        user, _login = auth
        return result(
            request,
            QuoteRepository(db, now=now, shuffle=shuffle).favorites(user.id, cursor, limit),
        )

    @router.put(
        "/{quote_id}/preference",
        response_model=Envelope[QuotePreferenceResultData],
        responses=errors,
    )
    def update_preference(
        quote_id: str,
        body: QuotePreferenceInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
        if_match: str | None = Header(default=None, alias="If-Match"),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        if not idempotency_key or len(idempotency_key) > 128:
            raise PolicyError("VALIDATION_ERROR", "A valid Idempotency-Key is required.", 422)
        user, _login = auth
        data = QuoteRepository(db, now=now, shuffle=shuffle).update_preference(
            user.id,
            quote_id,
            body.model_dump(mode="json"),
            idempotency_key,
            if_match,
            if_none_match,
            user.timezone,
        )
        db.commit()
        return result(request, data)

    return router
