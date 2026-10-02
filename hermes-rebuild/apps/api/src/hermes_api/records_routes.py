"""HTTP routes for factual records and day summaries."""

# ruff: noqa: B008

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from .domain import PolicyError
from .records_schemas import DaySummaryData, RecordsPageData
from .records_service import RecordsService
from .records_storage import SQLRecordsRepository
from .schemas import Envelope, ErrorEnvelope

API_ERRORS = {code: {"model": ErrorEnvelope} for code in (401, 404, 422, 503)}


def create_records_router(database, identity):
    router = APIRouter()

    @router.get("/api/v1/records", response_model=Envelope[RecordsPageData], responses=API_ERRORS)
    def records(
        request: Request,
        from_date: date | None = Query(default=None, alias="from"),
        to_date: date | None = Query(default=None, alias="to"),
        subject_id: UUID | None = None,
        limit: int = 50,
        cursor: UUID | None = None,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        value = RecordsService(_Uow(db)).list_records(
            auth[0].id,
            auth[0].timezone,
            from_date,
            to_date,
            str(subject_id) if subject_id else None,
            limit,
            str(cursor) if cursor else None,
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get(
        "/api/v1/day-summary", response_model=Envelope[DaySummaryData], responses=API_ERRORS
    )
    def day_summary(
        request: Request,
        day: date | None = Query(default=None, alias="date"),
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        value = RecordsService(_Uow(db)).day_summary(auth[0].id, auth[0].timezone, day)
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    return router


class _Uow:
    def __init__(self, db):
        self.records = SQLRecordsRepository(db)
