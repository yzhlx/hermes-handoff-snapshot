"""HTTP endpoints for account data sovereignty."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .account_schemas import (
    AccountDeletionData,
    AccountExportData,
    AccountExportPageData,
    AccountStatusData,
    CancelDeletionInput,
    CreateDeletionInput,
    CreateExportInput,
    ExportDownloadData,
    PurgeDeletionInput,
)
from .account_service import AccountService
from .account_storage import SQLAccountUnitOfWork
from .domain import PolicyError
from .schemas import Envelope, ErrorEnvelope


def create_account_router(database, identity, sanitized_write):
    """Account-level endpoints intentionally bypass the pending-deletion write
    block: while a deletion is pending the learner must still be able to export
    their data, re-request (to get a clear 409) and above all cancel it."""
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 410, 422, 428, 503)}

    def response(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    def version_of(if_match):
        try:
            version = int(if_match.strip().strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if version is not None and version < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        return version

    @router.get("/api/v1/account", response_model=Envelope[AccountStatusData], responses=errors)
    def status(request: Request, auth=Depends(identity), db: Session = Depends(database)):  # noqa: B008
        user = auth[0]
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).status(user.id, user.username, user.timezone),
        )

    @router.post(
        "/api/v1/account/exports",
        status_code=201,
        response_model=Envelope[AccountExportData],
        responses=errors,
    )
    def create_export(
        body: CreateExportInput,
        request: Request,
        auth=Depends(sanitized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).create_export(
                auth[0].id, body.model_dump(mode="json"), idempotency_key
            ),
        )

    @router.get(
        "/api/v1/account/exports",
        response_model=Envelope[AccountExportPageData],
        responses=errors,
    )
    def list_exports(
        request: Request,
        limit: int = 20,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(
            request, AccountService(SQLAccountUnitOfWork(db)).list_exports(auth[0].id, limit)
        )

    @router.get(
        "/api/v1/account/exports/{export_id}/download",
        response_model=Envelope[ExportDownloadData],
        responses=errors,
    )
    def download_export(
        export_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).download(auth[0].id, str(export_id)),
        )

    @router.post(
        "/api/v1/account/deletion",
        status_code=201,
        response_model=Envelope[AccountDeletionData],
        responses=errors,
    )
    def request_deletion(
        body: CreateDeletionInput,
        request: Request,
        auth=Depends(sanitized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
    ):
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).request_deletion(
                auth[0].id, body.model_dump(mode="json"), idempotency_key
            ),
        )

    @router.post(
        "/api/v1/account/deletion/cancel",
        response_model=Envelope[AccountDeletionData],
        responses=errors,
    )
    def cancel_deletion(
        body: CancelDeletionInput,
        request: Request,
        auth=Depends(sanitized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).cancel_deletion(
                auth[0].id, body.model_dump(mode="json"), idempotency_key, version_of(if_match)
            ),
        )

    @router.post(
        "/api/v1/account/deletion/purge",
        response_model=Envelope[AccountDeletionData],
        responses=errors,
    )
    def purge_deletion(
        body: PurgeDeletionInput,
        request: Request,
        auth=Depends(sanitized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        return response(
            request,
            AccountService(SQLAccountUnitOfWork(db)).complete_deletion(
                auth[0].id, body.model_dump(mode="json"), idempotency_key, version_of(if_match)
            ),
        )

    return router
