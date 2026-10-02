"""HTTP endpoints for self-reported mastery and factual evidence aggregates."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .evidence_schemas import (
    CreatedMasteryAssessmentData,
    CreateMasteryAssessment,
    KnowledgePointEvidenceData,
)
from .evidence_service import EvidenceService
from .evidence_storage import SQLEvidenceUnitOfWork  # register ORM metadata at app import
from .schemas import Envelope, ErrorEnvelope


def create_evidence_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    @router.get(
        "/api/v1/knowledge-points/{knowledge_point_id}/evidence",
        response_model=Envelope[KnowledgePointEvidenceData],
        responses=errors,
    )
    def knowledge_point_evidence(
        knowledge_point_id: UUID,
        request: Request,
        auth=Depends(identity),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
    ):
        result = EvidenceService(SQLEvidenceUnitOfWork(db)).get_evidence(
            auth[0].id, str(knowledge_point_id)
        )
        return {"data": result, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/mastery-assessments",
        status_code=201,
        response_model=Envelope[CreatedMasteryAssessmentData],
        responses=errors,
    )
    def create_mastery_assessment(
        body: CreateMasteryAssessment,
        request: Request,
        auth=Depends(authorized_write),  # noqa: B008
        db: Session = Depends(database),  # noqa: B008
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            point_version = int(if_match.strip().strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if point_version is not None and point_version < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        result = EvidenceService(SQLEvidenceUnitOfWork(db)).create_assessment(
            auth[0].id,
            body.model_dump(mode="json"),
            idempotency_key,
            point_version,
        )
        return {"data": result, "meta": {"request_id": request.state.request_id}}

    return router
