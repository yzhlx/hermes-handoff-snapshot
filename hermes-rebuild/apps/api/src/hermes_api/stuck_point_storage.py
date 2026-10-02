"""Owner-scoped SQL persistence for stuck points."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
)

from .domain import PolicyError, utc_now
from .knowledge_storage import KnowledgePointRow
from .storage import Base, ProblemAttemptRow, SessionRow, SQLUnitOfWork


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class StuckPointRow(Base):
    __tablename__ = "stuck_points"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_stuck_point_session_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_stuck_point_attempt_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_stuck_point_knowledge_owner",
        ),
        UniqueConstraint("owner_id", "id", name="uq_stuck_point_owner_id"),
        CheckConstraint("status IN ('open','resolved')", name="ck_stuck_point_status"),
        CheckConstraint("version >= 1", name="ck_stuck_point_version"),
        CheckConstraint("length(trim(coalesce(text,''))) > 0", name="ck_stuck_point_text"),
        CheckConstraint(
            "(status = 'resolved') = (resolved_at IS NOT NULL)",
            name="ck_stuck_point_resolved_at",
        ),
        Index("ix_stuck_points_owner_status", "owner_id", "status", "created_at", "id"),
        Index(
            "uq_stuck_point_source_attempt",
            "owner_id",
            "attempt_id",
            unique=True,
            sqlite_where=text("attempt_id IS NOT NULL"),
            postgresql_where=text("attempt_id IS NOT NULL"),
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    session_id = Column(String(36), nullable=False)
    attempt_id = Column(String(36))
    knowledge_point_id = Column(String(36))
    text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    resolution_note = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class SQLStuckPointRepository:
    def __init__(self, db):
        self.db = db

    def _data(self, row):
        return {
            "id": row.id,
            "version": row.version,
            "session_id": row.session_id,
            "attempt_id": row.attempt_id,
            "knowledge_point_id": row.knowledge_point_id,
            "text": row.text,
            "status": row.status,
            "resolved_at": _iso(row.resolved_at),
            "resolution_note": row.resolution_note,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _row(self, owner, stuck_point_id):
        row = self.db.scalar(
            select(StuckPointRow).where(
                StuckPointRow.owner_id == owner, StuckPointRow.id == stuck_point_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return row

    def _assert_session(self, owner, session_id):
        exists = self.db.scalar(
            select(SessionRow.id).where(SessionRow.owner_id == owner, SessionRow.id == session_id)
        )
        if exists is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)

    def _assert_knowledge_point(self, owner, knowledge_point_id):
        exists = self.db.scalar(
            select(KnowledgePointRow.id).where(
                KnowledgePointRow.owner_id == owner, KnowledgePointRow.id == knowledge_point_id
            )
        )
        if exists is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)

    def create(self, owner, data):
        self._assert_session(owner, data["session_id"])
        if data.get("knowledge_point_id"):
            self._assert_knowledge_point(owner, data["knowledge_point_id"])
        if data.get("attempt_id"):
            attempt = self.db.scalar(
                select(ProblemAttemptRow).where(
                    ProblemAttemptRow.owner_id == owner,
                    ProblemAttemptRow.id == data["attempt_id"],
                )
            )
            if attempt is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            linked = self.db.scalar(
                select(StuckPointRow.id).where(
                    StuckPointRow.owner_id == owner,
                    StuckPointRow.attempt_id == data["attempt_id"],
                )
            )
            if linked is not None:
                # Unique by source: the same attempt is never counted twice.
                raise PolicyError("ALREADY_LINKED", "This attempt already has a stuck point.", 409)
        now = utc_now()
        row = StuckPointRow(
            id=str(uuid4()),
            owner_id=owner,
            version=1,
            session_id=data["session_id"],
            attempt_id=data.get("attempt_id"),
            knowledge_point_id=data.get("knowledge_point_id"),
            text=data["text"],
            status="open",
            resolved_at=None,
            resolution_note=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return self._data(row)

    def get(self, owner, stuck_point_id):
        return self._data(self._row(owner, stuck_point_id))

    def list(self, owner, filters, limit, cursor):
        query = select(StuckPointRow).where(StuckPointRow.owner_id == owner)
        if filters.get("status"):
            query = query.where(StuckPointRow.status == filters["status"])
        if filters.get("session_id"):
            self._assert_session(owner, filters["session_id"])
            query = query.where(StuckPointRow.session_id == filters["session_id"])
        if filters.get("knowledge_point_id"):
            self._assert_knowledge_point(owner, filters["knowledge_point_id"])
            query = query.where(StuckPointRow.knowledge_point_id == filters["knowledge_point_id"])
        if cursor:
            created_raw, _, stuck_point_id = cursor.partition("|")
            try:
                created = datetime.fromisoformat(created_raw).replace(tzinfo=None)
            except ValueError:
                raise PolicyError(
                    "VALIDATION_ERROR", "Stuck point cursor is invalid.", 422
                ) from None
            if not stuck_point_id:
                raise PolicyError("VALIDATION_ERROR", "Stuck point cursor is invalid.", 422)
            exists = self.db.scalar(
                select(StuckPointRow.id).where(
                    StuckPointRow.owner_id == owner,
                    StuckPointRow.id == stuck_point_id,
                    StuckPointRow.created_at == created,
                )
            )
            if exists is None:
                # Also rejects a cursor that belongs to another owner.
                raise PolicyError("VALIDATION_ERROR", "Stuck point cursor is invalid.", 422)
            query = query.where(
                (StuckPointRow.created_at < created)
                | ((StuckPointRow.created_at == created) & (StuckPointRow.id < stuck_point_id))
            )
        rows = self.db.scalars(
            query.order_by(StuckPointRow.created_at.desc(), StuckPointRow.id.desc()).limit(limit)
        )
        return [self._data(row) for row in rows]

    def patch(self, owner, stuck_point_id, data, version):
        row = self._row(owner, stuck_point_id)
        if row.version != version:
            error = PolicyError(
                "VERSION_CONFLICT", "Stuck point changed; reload before editing.", 409
            )
            error.current_version = row.version
            error.current = self._data(row)
            raise error
        if "text" in data:
            row.text = data["text"]
        if "resolution_note" in data:
            row.resolution_note = data["resolution_note"]
        if "status" in data:
            if data["status"] == "resolved" and row.status != "resolved":
                row.resolved_at = utc_now()
            elif data["status"] == "open":
                row.resolved_at = None
            row.status = data["status"]
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return self._data(row)


class SQLStuckPointUnitOfWork:
    """Adds the stuck point repository while keeping established UoW semantics."""

    def __init__(self, db):
        self.db = db
        self.base = SQLUnitOfWork(db)
        self.stuck_points = SQLStuckPointRepository(db)

    def lock_owner(self, owner_id):
        return self.base.lock_owner(owner_id)

    def replay(self, *args):
        return self.base.replay(*args)

    def remember(self, *args):
        return self.base.remember(*args)

    def commit(self):
        return self.base.commit()
