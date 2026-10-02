"""HTTP adapter for feedback and problem records."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .feedback import (
    CreateAttempt,
    CreateProblem,
    CreateReflection,
    LinkProblemAttachment,
    UnlinkProblemAttachment,
    UpdateAttempt,
    UpdateReflection,
)
from .feedback_service import FeedbackService
from .schemas import (
    Envelope,
    ErrorEnvelope,
    ProblemAttachmentLinksData,
    ProblemAttachmentLinkWriteData,
    ProblemAttachmentUnlinkData,
    ProblemAttemptData,
    ProblemData,
    ProblemPageData,
    ProblemPatchInput,
    ReflectionData,
)
from .storage import SQLUnitOfWork

API_ERRORS = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}


def create_feedback_router(database, identity, authorized_write):
    router = APIRouter(responses=API_ERRORS)

    @router.post(
        "/api/v1/session-reflections",
        status_code=201,
        response_model=Envelope[ReflectionData],
    )
    def create_reflection(
        body: CreateReflection,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = FeedbackService(SQLUnitOfWork(db)).create_reflection(
            auth[0].id, body.model_dump(mode="json"), idempotency_key
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get("/api/v1/session-reflections/{session_id}", response_model=Envelope[ReflectionData])
    def reflection(
        session_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).feedback.get_reflection(auth[0].id, str(session_id))
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.patch(
        "/api/v1/session-reflections/{session_id}", response_model=Envelope[ReflectionData]
    )
    def update_reflection(
        session_id: UUID,
        body: UpdateReflection,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = FeedbackService(SQLUnitOfWork(db)).update_reflection(
            auth[0].id,
            str(session_id),
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.post("/api/v1/problems", status_code=201, response_model=Envelope[ProblemData])
    def create_problem(
        body: CreateProblem,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = FeedbackService(SQLUnitOfWork(db)).create_problem(
            auth[0].id, body.model_dump(mode="json"), idempotency_key
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get("/api/v1/problems", response_model=Envelope[ProblemPageData])
    def problems(
        request: Request,
        subject_id: UUID | None = None,
        representative: bool | None = None,
        archived: bool = False,
        limit: int = 50,
        cursor: UUID | None = None,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        if not 1 <= limit <= 100:
            from .domain import PolicyError

            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        rows = SQLUnitOfWork(db).feedback.list_problems(
            auth[0].id,
            str(subject_id) if subject_id else None,
            representative,
            limit + 1,
            str(cursor) if cursor else None,
            archived,
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        return {
            "data": {
                "items": items,
                "next_cursor": items[-1]["id"] if has_more and items else None,
            },
            "meta": {"request_id": request.state.request_id},
        }

    @router.get("/api/v1/problems/{problem_id}", response_model=Envelope[ProblemData])
    def problem(
        problem_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).feedback.get_problem(auth[0].id, str(problem_id))
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.patch("/api/v1/problems/{problem_id}", response_model=Envelope[ProblemData])
    def update_problem(
        problem_id: UUID,
        body: ProblemPatchInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = FeedbackService(SQLUnitOfWork(db)).update_problem(
            auth[0].id,
            str(problem_id),
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get(
        "/api/v1/problems/{problem_id}/attachment-links",
        response_model=Envelope[ProblemAttachmentLinksData],
    )
    def problem_attachment_links(
        problem_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).feedback.list_attachment_links(auth[0].id, str(problem_id))
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/problems/{problem_id}/attachment-links",
        status_code=201,
        response_model=Envelope[ProblemAttachmentLinkWriteData],
    )
    def link_problem_attachment(
        problem_id: UUID,
        body: LinkProblemAttachment,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = FeedbackService(SQLUnitOfWork(db)).link_attachment(
            auth[0].id, str(problem_id), body.model_dump(mode="json"), idempotency_key, version
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.delete(
        "/api/v1/problems/{problem_id}/attachment-links/{link_id}",
        response_model=Envelope[ProblemAttachmentUnlinkData],
    )
    def unlink_problem_attachment(
        problem_id: UUID,
        link_id: UUID,
        body: UnlinkProblemAttachment,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = FeedbackService(SQLUnitOfWork(db)).unlink_attachment(
            auth[0].id,
            str(problem_id),
            str(link_id),
            body.model_dump(mode="json"),
            idempotency_key,
            version,
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.post(
        "/api/v1/problem-attempts", status_code=201, response_model=Envelope[ProblemAttemptData]
    )
    def create_attempt(
        body: CreateAttempt,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = FeedbackService(SQLUnitOfWork(db)).create_attempt(
            auth[0].id, body.model_dump(mode="json"), idempotency_key
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.get(
        "/api/v1/problem-attempts/{attempt_id}", response_model=Envelope[ProblemAttemptData]
    )
    def attempt(
        attempt_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).feedback.get_attempt(auth[0].id, str(attempt_id))
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @router.patch(
        "/api/v1/problem-attempts/{attempt_id}", response_model=Envelope[ProblemAttemptData]
    )
    def update_attempt(
        attempt_id: UUID,
        body: UpdateAttempt,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        from .domain import PolicyError

        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        valid = UpdateAttempt.model_validate(body).model_dump(mode="json", exclude_unset=True)
        value = FeedbackService(SQLUnitOfWork(db)).update_attempt(
            auth[0].id, str(attempt_id), valid, idempotency_key, version
        )
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    return router
