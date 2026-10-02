"""HTTP endpoints for the optional AI advisor."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .advisor_schemas import (
    AdvisorPageData,
    AdvisorRunData,
    CancelAdvisorInput,
    CreateAdvisorInput,
)
from .advisor_service import AdvisorService
from .advisor_storage import SQLAdvisorUnitOfWork
from .schemas import Envelope, ErrorEnvelope


def create_advisor_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 503)}

    def response(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    def service(request: Request, db: Session):
        # The provider adapter is resolved from app state so a deployment (or a
        # test) can swap it without the use cases importing a model SDK.
        return AdvisorService(SQLAdvisorUnitOfWork(db), request.app.state.advisor_model)

    @router.post(
        "/api/v1/advisor/analyses",
        status_code=201,
        response_model=Envelope[AdvisorRunData],
        responses=errors,
    )
    def create(
        body: CreateAdvisorInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            service(request, db).analyze(auth[0].id, body.model_dump(mode="json"), idempotency_key),
        )

    @router.get(
        "/api/v1/advisor/analyses",
        response_model=Envelope[AdvisorPageData],
        responses=errors,
    )
    def list_items(
        request: Request,
        limit: int = 50,
        cursor: str | None = None,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(
            request,
            service(request, db).list(auth[0].id, limit=limit, cursor=cursor or None),
        )

    @router.get(
        "/api/v1/advisor/analyses/{run_id}",
        response_model=Envelope[AdvisorRunData],
        responses=errors,
    )
    def get(
        run_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(request, service(request, db).get(auth[0].id, str(run_id)))

    @router.post(
        "/api/v1/advisor/analyses/{run_id}/cancel",
        response_model=Envelope[AdvisorRunData],
        responses=errors,
    )
    def cancel(
        run_id: UUID,
        body: CancelAdvisorInput,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            service(request, db).cancel(
                auth[0].id, str(run_id), body.model_dump(mode="json"), idempotency_key
            ),
        )

    return router
