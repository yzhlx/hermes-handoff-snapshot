"""HTTP surface for private knowledge organization."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from .domain import PolicyError
from .knowledge_service import KnowledgeService
from .schemas import (
    ChapterData,
    ChapterPageData,
    CreateChapterInput,
    CreateKnowledgePointInput,
    Envelope,
    ErrorEnvelope,
    KnowledgePointData,
    KnowledgePointPageData,
    PatchChapterInput,
    PatchKnowledgePointInput,
    ProblemKnowledgeLinksData,
    ProblemKnowledgeLinksInput,
    SubjectSpaceData,
)
from .storage import SQLUnitOfWork


def create_knowledge_router(database, identity, authorized_write):
    router = APIRouter()
    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    def envelope(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    def expected_version(if_match):
        if if_match is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        try:
            value = int(if_match.strip().strip('"'))
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if value < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        return value

    @router.get(
        "/api/v1/subjects/{subject_id}/space",
        response_model=Envelope[SubjectSpaceData],
        responses=errors,
    )
    def subject_space(
        subject_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).knowledge.subject_space(auth[0].id, str(subject_id))
        return envelope(request, value)

    @router.post(
        "/api/v1/chapters", status_code=201, response_model=Envelope[ChapterData], responses=errors
    )
    def create_chapter(
        body: CreateChapterInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = KnowledgeService(SQLUnitOfWork(db)).write(
            auth[0].id, "create_chapter", body.model_dump(mode="json"), idempotency_key
        )
        return envelope(request, value)

    @router.get("/api/v1/chapters", response_model=Envelope[ChapterPageData], responses=errors)
    def chapters(
        request: Request,
        subject_id: UUID,
        archived: bool = False,
        limit: int = 20,
        cursor: UUID | None = None,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        repo = SQLUnitOfWork(db).knowledge
        rows = repo.list_chapters(
            auth[0].id, str(subject_id), archived, limit + 1, str(cursor) if cursor else None
        )
        items = rows[:limit]
        return envelope(
            request, {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None}
        )

    @router.get(
        "/api/v1/chapters/{chapter_id}", response_model=Envelope[ChapterData], responses=errors
    )
    def chapter(
        chapter_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        return envelope(
            request, SQLUnitOfWork(db).knowledge.get_chapter(auth[0].id, str(chapter_id))
        )

    @router.patch(
        "/api/v1/chapters/{chapter_id}", response_model=Envelope[ChapterData], responses=errors
    )
    def patch_chapter(
        chapter_id: UUID,
        body: PatchChapterInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        version = expected_version(if_match)
        value = KnowledgeService(SQLUnitOfWork(db)).write(
            auth[0].id,
            "patch_chapter",
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
            str(chapter_id),
        )
        return envelope(request, value)

    @router.post(
        "/api/v1/knowledge-points",
        status_code=201,
        response_model=Envelope[KnowledgePointData],
        responses=errors,
    )
    def create_point(
        body: CreateKnowledgePointInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = KnowledgeService(SQLUnitOfWork(db)).write(
            auth[0].id, "create_point", body.model_dump(mode="json"), idempotency_key
        )
        return envelope(request, value)

    @router.get(
        "/api/v1/knowledge-points",
        response_model=Envelope[KnowledgePointPageData],
        responses=errors,
    )
    def points(
        request: Request,
        chapter_id: UUID,
        archived: bool = False,
        limit: int = 20,
        cursor: UUID | None = None,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        repo = SQLUnitOfWork(db).knowledge
        rows = repo.list_points(
            auth[0].id, str(chapter_id), archived, limit + 1, str(cursor) if cursor else None
        )
        items = rows[:limit]
        return envelope(
            request, {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None}
        )

    @router.get(
        "/api/v1/knowledge-points/{point_id}",
        response_model=Envelope[KnowledgePointData],
        responses=errors,
    )
    def point(
        point_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        return envelope(request, SQLUnitOfWork(db).knowledge.get_point(auth[0].id, str(point_id)))

    @router.patch(
        "/api/v1/knowledge-points/{point_id}",
        response_model=Envelope[KnowledgePointData],
        responses=errors,
    )
    def patch_point(
        point_id: UUID,
        body: PatchKnowledgePointInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        version = expected_version(if_match)
        value = KnowledgeService(SQLUnitOfWork(db)).write(
            auth[0].id,
            "patch_point",
            body.model_dump(mode="json", exclude_unset=True),
            idempotency_key,
            version,
            str(point_id),
        )
        return envelope(request, value)

    @router.put(
        "/api/v1/problems/{problem_id}/knowledge-links",
        response_model=Envelope[ProblemKnowledgeLinksData],
        responses=errors,
    )
    def link_problem(
        problem_id: UUID,
        body: ProblemKnowledgeLinksInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        version = expected_version(if_match)
        value = KnowledgeService(SQLUnitOfWork(db)).write(
            auth[0].id,
            "link_problem",
            body.model_dump(mode="json"),
            idempotency_key,
            version,
            str(problem_id),
        )
        return envelope(request, value)

    return router
