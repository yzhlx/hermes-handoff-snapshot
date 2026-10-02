"""ORM models and SQL repository for private knowledge organization."""

from datetime import UTC

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    delete,
    select,
)

from .domain import PolicyError, utc_now
from .knowledge_domain import normalize_knowledge_name, validate_link_subject
from .storage import Base, ProblemRow, SessionRow, Subject


class ChapterRow(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_chapters_subject_owner",
        ),
        UniqueConstraint("owner_id", "id", name="uq_chapters_owner_id"),
        UniqueConstraint("owner_id", "id", "subject_id", name="uq_chapters_owner_subject"),
        Index("ix_chapters_owner_subject", "owner_id", "subject_id", "archived_at"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    subject_id = Column(String(36), nullable=False)
    name = Column(String(200), nullable=False)
    order_index = Column(Integer, nullable=False, default=0, server_default="0")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True))


class KnowledgePointRow(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "chapter_id", "subject_id"],
            ["chapters.owner_id", "chapters.id", "chapters.subject_id"],
            name="fk_knowledge_points_chapter_scope",
        ),
        UniqueConstraint("owner_id", "id", name="uq_knowledge_points_owner_id"),
        UniqueConstraint("owner_id", "id", "subject_id", name="uq_knowledge_points_owner_subject"),
        Index("ix_knowledge_points_owner_chapter", "owner_id", "chapter_id", "archived_at"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    chapter_id = Column(String(36), nullable=False)
    subject_id = Column(String(36), nullable=False)
    name = Column(String(200), nullable=False)
    notes = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True))


class ProblemKnowledgeLinkRow(Base):
    __tablename__ = "problem_knowledge_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_problem_knowledge_problem_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_problem_knowledge_point_owner",
        ),
        Index("ix_problem_knowledge_links_point", "owner_id", "knowledge_point_id"),
    )
    owner_id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), primary_key=True)
    knowledge_point_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


def iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class SQLKnowledgeRepository:
    def __init__(self, db):
        self.db = db

    def _chapter(self, row):
        return {
            "id": row.id,
            "subject_id": row.subject_id,
            "name": row.name,
            "order_index": row.order_index,
            "version": row.version,
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
            "archived": row.archived_at is not None,
        }

    def _point(self, row):
        return {
            "id": row.id,
            "chapter_id": row.chapter_id,
            "subject_id": row.subject_id,
            "name": row.name,
            "notes": row.notes,
            "version": row.version,
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
            "archived": row.archived_at is not None,
        }

    def _conflict(self, row, snapshot):
        error = PolicyError("VERSION_CONFLICT", "Record changed; reload before editing.", 409)
        error.current_version = row.version
        error.current = snapshot
        return error

    def create_chapter(self, owner, values):
        subject = self.db.scalar(
            select(Subject).where(Subject.id == values["subject_id"], Subject.owner_id == owner)
        )
        if subject is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        now = utc_now()
        row = ChapterRow(
            id=values["id"],
            owner_id=owner,
            subject_id=subject.id,
            name=normalize_knowledge_name(values["name"]),
            order_index=values.get("order_index", 0),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return self._chapter(row)

    def get_chapter(self, owner, chapter_id):
        row = self.db.scalar(
            select(ChapterRow).where(ChapterRow.owner_id == owner, ChapterRow.id == chapter_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._chapter(row)

    def list_chapters(self, owner, subject_id, archived, limit, cursor_id=None):
        subject = self.db.scalar(
            select(Subject.id).where(Subject.owner_id == owner, Subject.id == subject_id)
        )
        if subject is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        query = select(ChapterRow).where(
            ChapterRow.owner_id == owner,
            ChapterRow.subject_id == subject_id,
            ChapterRow.archived_at.is_not(None) if archived else ChapterRow.archived_at.is_(None),
        )
        if cursor_id:
            cursor = self.db.scalar(
                select(ChapterRow).where(
                    ChapterRow.owner_id == owner,
                    ChapterRow.id == cursor_id,
                    ChapterRow.subject_id == subject_id,
                    ChapterRow.archived_at.is_not(None)
                    if archived
                    else ChapterRow.archived_at.is_(None),
                )
            )
            if cursor is None:
                raise PolicyError("VALIDATION_ERROR", "Chapter cursor is invalid.", 422)
            query = query.where(
                (ChapterRow.order_index > cursor.order_index)
                | ((ChapterRow.order_index == cursor.order_index) & (ChapterRow.id > cursor.id))
            )
        return [
            self._chapter(r)
            for r in self.db.scalars(
                query.order_by(ChapterRow.order_index, ChapterRow.id).limit(limit)
            )
        ]

    def update_chapter(self, owner, chapter_id, values, version):
        row = self.db.scalar(
            select(ChapterRow).where(ChapterRow.owner_id == owner, ChapterRow.id == chapter_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row, self._chapter(row))
        if "archived" in values:
            row.archived_at = utc_now() if values["archived"] else None
        if "name" in values:
            row.name = normalize_knowledge_name(values["name"])
        if "order_index" in values:
            row.order_index = values["order_index"]
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return self._chapter(row)

    def create_point(self, owner, values):
        chapter = self.db.scalar(
            select(ChapterRow).where(
                ChapterRow.owner_id == owner,
                ChapterRow.id == values["chapter_id"],
                ChapterRow.archived_at.is_(None),
            )
        )
        if chapter is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        now = utc_now()
        row = KnowledgePointRow(
            id=values["id"],
            owner_id=owner,
            chapter_id=chapter.id,
            subject_id=chapter.subject_id,
            name=normalize_knowledge_name(values["name"]),
            notes=values.get("notes"),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return self._point(row)

    def get_point(self, owner, point_id):
        row = self.db.scalar(
            select(KnowledgePointRow).where(
                KnowledgePointRow.owner_id == owner, KnowledgePointRow.id == point_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._point(row)

    def get_active_point(self, owner, point_id):
        row = self.db.scalar(
            select(KnowledgePointRow)
            .join(
                ChapterRow,
                (ChapterRow.owner_id == KnowledgePointRow.owner_id)
                & (ChapterRow.id == KnowledgePointRow.chapter_id),
            )
            .where(
                KnowledgePointRow.owner_id == owner,
                KnowledgePointRow.id == point_id,
                KnowledgePointRow.archived_at.is_(None),
                ChapterRow.archived_at.is_(None),
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._point(row)

    def subject_space(self, owner, subject_id):
        subject = self.db.scalar(
            select(Subject).where(Subject.owner_id == owner, Subject.id == subject_id)
        )
        if subject is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        chapters = self.list_chapters(owner, subject_id, False, 101)
        has_more_chapters = len(chapters) > 100
        chapters = chapters[:100]
        sessions = list(
            self.db.scalars(
                select(SessionRow)
                .where(SessionRow.owner_id == owner, SessionRow.subject_id == subject_id)
                .order_by(SessionRow.started_at.desc(), SessionRow.id.desc())
                .limit(5)
            )
        )
        problems = list(
            self.db.scalars(
                select(ProblemRow)
                .where(
                    ProblemRow.owner_id == owner,
                    ProblemRow.subject_id == subject_id,
                    ProblemRow.archived_at.is_(None),
                )
                .order_by(ProblemRow.created_at.desc(), ProblemRow.id.desc())
                .limit(5)
            )
        )
        from .application import serialize
        from .catalog import subject_group_label
        from .feedback_storage import SQLFeedbackRepository
        from .storage import SQLSessionRepository

        return {
            "subject": {
                "id": subject.id,
                "name": subject.name,
                "group_label": subject_group_label(subject.name),
            },
            "chapters": chapters,
            "chapters_next_cursor": chapters[-1]["id"] if has_more_chapters and chapters else None,
            "recent_sessions": [
                serialize(SQLSessionRepository(self.db)._entity(row)) for row in sessions
            ],
            "recent_problems": [
                SQLFeedbackRepository(self.db)._problem(row, False) for row in problems
            ],
        }

    def list_points(self, owner, chapter_id, archived, limit, cursor_id=None):
        chapter = self.db.scalar(
            select(ChapterRow.id).where(ChapterRow.owner_id == owner, ChapterRow.id == chapter_id)
        )
        if chapter is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        query = select(KnowledgePointRow).where(
            KnowledgePointRow.owner_id == owner,
            KnowledgePointRow.chapter_id == chapter_id,
            KnowledgePointRow.archived_at.is_not(None)
            if archived
            else KnowledgePointRow.archived_at.is_(None),
        )
        if cursor_id:
            cursor = self.db.scalar(
                select(KnowledgePointRow).where(
                    KnowledgePointRow.owner_id == owner,
                    KnowledgePointRow.id == cursor_id,
                    KnowledgePointRow.chapter_id == chapter_id,
                    KnowledgePointRow.archived_at.is_not(None)
                    if archived
                    else KnowledgePointRow.archived_at.is_(None),
                )
            )
            if cursor is None:
                raise PolicyError("VALIDATION_ERROR", "Knowledge point cursor is invalid.", 422)
            query = query.where(
                (KnowledgePointRow.created_at < cursor.created_at)
                | (
                    (KnowledgePointRow.created_at == cursor.created_at)
                    & (KnowledgePointRow.id < cursor.id)
                )
            )
        return [
            self._point(r)
            for r in self.db.scalars(
                query.order_by(
                    KnowledgePointRow.created_at.desc(), KnowledgePointRow.id.desc()
                ).limit(limit)
            )
        ]

    def update_point(self, owner, point_id, values, version):
        row = self.db.scalar(
            select(KnowledgePointRow).where(
                KnowledgePointRow.owner_id == owner, KnowledgePointRow.id == point_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row, self._point(row))
        if "archived" in values:
            row.archived_at = utc_now() if values["archived"] else None
        if "name" in values:
            row.name = normalize_knowledge_name(values["name"])
        if "notes" in values:
            row.notes = values["notes"]
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return self._point(row)

    def link_problem(self, owner, problem_id, point_ids, version):
        problem = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if problem is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if problem.version != version:
            from .feedback_storage import SQLFeedbackRepository

            error = PolicyError("VERSION_CONFLICT", "Problem changed.", 409)
            error.current_version = problem.version
            error.current = SQLFeedbackRepository(self.db)._problem(problem)
            raise error
        points = (
            list(
                self.db.scalars(
                    select(KnowledgePointRow)
                    .join(
                        ChapterRow,
                        (ChapterRow.owner_id == KnowledgePointRow.owner_id)
                        & (ChapterRow.id == KnowledgePointRow.chapter_id),
                    )
                    .where(
                        KnowledgePointRow.owner_id == owner,
                        KnowledgePointRow.id.in_(point_ids),
                        KnowledgePointRow.archived_at.is_(None),
                        ChapterRow.archived_at.is_(None),
                    )
                )
            )
            if point_ids
            else []
        )
        if len(points) != len(point_ids):
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        validate_link_subject(problem.subject_id, [point.subject_id for point in points])
        self.db.execute(
            delete(ProblemKnowledgeLinkRow).where(
                ProblemKnowledgeLinkRow.owner_id == owner,
                ProblemKnowledgeLinkRow.problem_id == problem_id,
            )
        )
        now = utc_now()
        for point in points:
            self.db.add(
                ProblemKnowledgeLinkRow(
                    owner_id=owner,
                    problem_id=problem_id,
                    knowledge_point_id=point.id,
                    created_at=now,
                )
            )
        problem.version += 1
        problem.updated_at = now
        self.db.flush()
        from .feedback_storage import SQLFeedbackRepository

        value = SQLFeedbackRepository(self.db)._problem(problem, False)
        value["knowledge_point_ids"] = list(point_ids)
        return {"problem": value, "knowledge_point_ids": list(point_ids)}
