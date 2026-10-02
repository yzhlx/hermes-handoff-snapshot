"""HTTP boundary for the independently retryable home projection."""

from fastapi import APIRouter, Depends, Query, Request

from .home_schemas import HomeData, HomeSectionName
from .home_service import HomeService
from .home_storage import SQLHomeReader
from .schemas import Envelope, ErrorEnvelope


def create_home_router(engine, identity):
    router = APIRouter(prefix="/api/v1/home", tags=["home"])
    errors = {code: {"model": ErrorEnvelope} for code in (401, 422, 503)}

    @router.get(
        "", response_model=Envelope[HomeData], response_model_exclude_unset=True, responses=errors
    )
    def get_home(
        request: Request,
        section: HomeSectionName | None = Query(default=None),  # noqa: B008
        auth=Depends(identity),  # noqa: B008
    ):
        user, _login = auth
        value = HomeService(SQLHomeReader(engine)).get(user.id, user.timezone, section)
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    return router
