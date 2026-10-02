"""SQLAlchemy adapters. Ownership is part of every repository query."""

from dataclasses import replace
from datetime import UTC
from uuid import uuid4

from sqlalchemy import (
    Boolean,
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
    create_engine,
    event,
    select,
    text,
    update,
)
from sqlalchemy.orm import DeclarativeBase, Session

from .domain import LearningSession, PolicyError, SessionTimeSegment, utc_now
from .timing_domain import validate_shortening


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    timezone = Column(String(80), nullable=False)
    status = Column(String(20), nullable=False, default="active", server_default="active")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash = Column(String(64), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    csrf = Column(String(80), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("owner_id", "id", name="uq_subject_owner_id"),)
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(80), nullable=False)


class SessionRow(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_session_subject_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "subject_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.subject_id", "knowledge_points.id"],
            name="fk_session_knowledge_scope",
        ),
        ForeignKeyConstraint(
            ["owner_id", "previous_session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_session_previous_owner",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'ended', 'cancelled')", name="ck_session_status"
        ),
        CheckConstraint("version >= 1", name="ck_session_version"),
        CheckConstraint("kind IN ('problem','recall','reading','free')", name="ck_session_kind"),
        CheckConstraint(
            "knowledge_point_id IS NULL OR subject_id IS NOT NULL",
            name="ck_session_knowledge_requires_subject",
        ),
        Index("uq_session_owner_id", "owner_id", "id", unique=True),
        Index(
            "uq_session_running_owner",
            "owner_id",
            unique=True,
            sqlite_where=text("status IN ('active', 'paused')"),
            postgresql_where=text("status IN ('active', 'paused')"),
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    goal = Column(Text)
    subject_id = Column(String(36))
    knowledge_point_id = Column(String(36))
    status = Column(String(20), nullable=False)
    version = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    day_timezone = Column(String(80), nullable=False)
    learning_date = Column(String(10), nullable=False)
    timing_enabled = Column(Boolean, nullable=False, default=False, server_default="0")
    method_id = Column(String(80))
    kind = Column(String(20), nullable=False, default="free", server_default="free")
    previous_session_id = Column(String(36))
    resume_note = Column(Text)


class SessionTimeSegmentRow(Base):
    __tablename__ = "session_time_segments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_time_segment_session_owner",
        ),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_segment_time_order"),
        Index(
            "uq_time_segment_open_session",
            "session_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("ix_time_segment_owner_session", "owner_id", "session_id"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    session_id = Column(String(36), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    excluded_at = Column(DateTime(timezone=True))
    original_ended_at = Column(DateTime(timezone=True))
    correction_note = Column(Text)


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (UniqueConstraint("owner_id", "operation", "key"),)
    id = Column(Integer, primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    operation = Column(String(100), nullable=False)
    key = Column(String(128), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    response = Column(Text, nullable=False)


class SessionReflectionRow(Base):
    __tablename__ = "session_reflections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_reflection_session_owner",
        ),
        UniqueConstraint("owner_id", "session_id", name="uq_reflection_session"),
        CheckConstraint(
            "length(trim(coalesce(summary,''))) + length(trim(coalesce(recalled_text,''))) + length(trim(coalesce(missing_parts,''))) + length(trim(coalesce(stuck_note,''))) > 0",
            name="ck_reflection_has_content",
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    session_id = Column(String(36), nullable=False)
    summary = Column(Text)
    recalled_text = Column(Text)
    reference_checked = Column(Boolean)
    missing_parts = Column(Text)
    stuck_note = Column(Text)
    resume_note = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class ProblemRow(Base):
    __tablename__ = "problems"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_problem_subject_owner",
        ),
        UniqueConstraint("owner_id", "id", name="uq_problem_owner_id"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(String(36))
    title = Column(String(300))
    statement = Column(Text)
    source_note = Column(Text)
    correct_answer = Column(Text)
    is_representative = Column(Boolean, nullable=False, default=False, server_default="0")
    archived_at = Column(DateTime(timezone=True))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class ProblemAttemptRow(Base):
    __tablename__ = "problem_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_attempt_session_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_attempt_problem_owner",
        ),
        UniqueConstraint("owner_id", "id", name="uq_attempt_owner_id"),
        CheckConstraint(
            "independence IN ('independent','hinted','after_answer','unable')",
            name="ck_attempt_independence",
        ),
        CheckConstraint(
            "(answer_check = 'pending' AND result IS NULL AND verified_at IS NULL) OR (answer_check = 'checked' AND result IN ('correct','partial','incorrect') AND verified_at IS NOT NULL)",
            name="ck_attempt_check_result",
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False)
    problem_id = Column(String(36), nullable=False)
    independence = Column(String(20), nullable=False)
    answer_check = Column(String(20), nullable=False)
    result = Column(String(20))
    attempt_text = Column(Text)
    stuck_note = Column(Text)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class AttemptErrorRow(Base):
    __tablename__ = "attempt_errors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_attempt_error_owner",
        ),
        UniqueConstraint("owner_id", "attempt_id", "category", name="uq_attempt_error_category"),
        CheckConstraint(
            "category IN ('concept','modeling','condition','formula','derivation','calculation','sign','unit','reading','other')",
            name="ck_attempt_error_category",
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    attempt_id = Column(String(36), nullable=False)
    category = Column(String(20), nullable=False)
    note = Column(Text)


class AttemptRevisionRow(Base):
    __tablename__ = "attempt_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_attempt_revision_owner",
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False, index=True)
    attempt_id = Column(String(36), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot = Column(Text, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False)


def make_engine(url):
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30}
        if url.startswith("sqlite")
        else {},
        pool_pre_ping=True,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def entity(row, segment_rows=()):
    fields = {
        key: getattr(row, key)
        for key in LearningSession.__dataclass_fields__
        if key != "time_segments"
    }
    for name in ("started_at", "ended_at"):
        if fields[name] and fields[name].tzinfo is None:
            fields[name] = fields[name].replace(tzinfo=UTC)

    def moment(value):
        if value and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    segments = tuple(
        SessionTimeSegment(
            id=segment.id,
            started_at=moment(segment.started_at),
            ended_at=moment(segment.ended_at),
            excluded_at=moment(segment.excluded_at),
            original_ended_at=moment(segment.original_ended_at),
            correction_note=segment.correction_note,
        )
        for segment in segment_rows
    )
    fields["time_segments"] = segments
    return LearningSession(**fields)


class SQLSessionRepository:
    def __init__(self, db):
        self.db = db

    def current(self, owner_id):
        row = self.db.scalar(
            select(SessionRow).where(
                SessionRow.owner_id == owner_id, SessionRow.status.in_(["active", "paused"])
            )
        )
        return self._entity(row) if row else None

    def _entity(self, row):
        segments = self.db.scalars(
            select(SessionTimeSegmentRow)
            .where(
                SessionTimeSegmentRow.owner_id == row.owner_id,
                SessionTimeSegmentRow.session_id == row.id,
            )
            .order_by(SessionTimeSegmentRow.started_at, SessionTimeSegmentRow.id)
        )
        return entity(row, segments)

    def get(self, owner_id, session_id):
        row = self.db.scalar(
            select(SessionRow).where(SessionRow.owner_id == owner_id, SessionRow.id == session_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._entity(row)

    def list(self, owner_id, limit, cursor_id=None):
        statement = select(SessionRow).where(SessionRow.owner_id == owner_id)
        if cursor_id:
            cursor = self.db.scalar(
                select(SessionRow).where(
                    SessionRow.owner_id == owner_id, SessionRow.id == cursor_id
                )
            )
            if cursor is None:
                raise PolicyError("VALIDATION_ERROR", "History cursor is invalid.", 422)
            statement = statement.where(
                (SessionRow.started_at < cursor.started_at)
                | ((SessionRow.started_at == cursor.started_at) & (SessionRow.id < cursor.id))
            )
        rows = self.db.scalars(
            statement.order_by(SessionRow.started_at.desc(), SessionRow.id.desc()).limit(limit)
        )
        return [self._entity(row) for row in rows]

    def add(self, value):
        from dataclasses import asdict

        fields = asdict(value)
        fields.pop("time_segments")
        self.db.add(SessionRow(**fields))
        if value.timing_enabled:
            segment = SessionTimeSegment(str(uuid4()), value.started_at, None)
            self.db.add(
                SessionTimeSegmentRow(
                    id=segment.id,
                    owner_id=value.owner_id,
                    session_id=value.id,
                    started_at=value.started_at,
                )
            )
            return replace(value, time_segments=(segment,))
        return value

    def transition(self, value, action, version):
        if value.version != version:
            error = PolicyError("VERSION_CONFLICT", "Session changed; reload before editing.", 409)
            error.current_version = value.version
            raise error
        status = value.check_transition(action)
        now = utc_now()
        ended_at = now if status in ("ended", "cancelled") else None
        result = self.db.execute(
            update(SessionRow)
            .where(
                SessionRow.id == value.id,
                SessionRow.owner_id == value.owner_id,
                SessionRow.version == version,
            )
            .values(status=status, ended_at=ended_at, version=version + 1)
        )
        if result.rowcount != 1:
            raise PolicyError("VERSION_CONFLICT", "Session changed; reload before editing.", 409)
        segments = list(value.time_segments)
        open_segment = next((item for item in segments if item.ended_at is None), None)
        if status in ("paused", "ended", "cancelled") and open_segment:
            self.db.execute(
                update(SessionTimeSegmentRow)
                .where(
                    SessionTimeSegmentRow.owner_id == value.owner_id,
                    SessionTimeSegmentRow.session_id == value.id,
                    SessionTimeSegmentRow.id == open_segment.id,
                    SessionTimeSegmentRow.ended_at.is_(None),
                )
                .values(ended_at=now)
            )
            segments = [
                replace(item, ended_at=now) if item.id == open_segment.id else item
                for item in segments
            ]
        if status == "active" and value.timing_enabled and open_segment is None:
            segment = SessionTimeSegment(str(uuid4()), now, None)
            self.db.add(
                SessionTimeSegmentRow(
                    id=segment.id,
                    owner_id=value.owner_id,
                    session_id=value.id,
                    started_at=now,
                )
            )
            segments.append(segment)
        return replace(
            value,
            status=status,
            ended_at=ended_at,
            version=version + 1,
            time_segments=tuple(segments),
        )

    def correct_segment(self, value, segment_id, changes, version):
        """Apply one user correction to a timer span; only shortening is allowed."""
        now = utc_now()
        segment = next((item for item in value.time_segments if item.id == segment_id), None)
        if segment is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        updates = {}
        if "exclude" in changes:
            if changes["exclude"] and segment.excluded_at is None:
                updates["excluded_at"] = now
            elif not changes["exclude"]:
                updates["excluded_at"] = None
        if changes.get("ended_at") is not None:
            if segment.ended_at is None:
                raise PolicyError("VALIDATION_ERROR", "An open span has no end to correct.", 422)
            updates["ended_at"] = validate_shortening(
                started_at=segment.started_at,
                current_ended_at=segment.ended_at,
                proposed_ended_at=changes["ended_at"],
                session_ended_at=value.ended_at,
                now=now,
            )
            if segment.original_ended_at is None:
                updates["original_ended_at"] = segment.ended_at
        if "correction_note" in changes:
            updates["correction_note"] = changes["correction_note"]
        if not updates:
            raise PolicyError("VALIDATION_ERROR", "Nothing to correct.", 422)
        self.db.execute(
            update(SessionTimeSegmentRow)
            .where(
                SessionTimeSegmentRow.owner_id == value.owner_id,
                SessionTimeSegmentRow.session_id == value.id,
                SessionTimeSegmentRow.id == segment_id,
            )
            .values(**updates)
        )
        result = self.db.execute(
            update(SessionRow)
            .where(
                SessionRow.id == value.id,
                SessionRow.owner_id == value.owner_id,
                SessionRow.version == version,
            )
            .values(version=version + 1)
        )
        if result.rowcount != 1:
            raise PolicyError("VERSION_CONFLICT", "Session changed; reload before editing.", 409)
        self.db.flush()
        row = self.db.scalar(
            select(SessionRow).where(
                SessionRow.owner_id == value.owner_id, SessionRow.id == value.id
            )
        )
        return self._entity(row)


class SQLUnitOfWork:
    def __init__(self, db: Session):
        self.db = db
        self.sessions = SQLSessionRepository(db)
        from .feedback_storage import SQLFeedbackRepository
        from .knowledge_storage import SQLKnowledgeRepository

        self.feedback = SQLFeedbackRepository(db)
        self.knowledge = SQLKnowledgeRepository(db)

    def lock_owner(self, owner_id):
        # UPDATE locks the owner row until commit on both SQLite and PostgreSQL.
        self.db.execute(update(User).where(User.id == owner_id).values(timezone=User.timezone))

    def owns_subject(self, owner_id, subject_id):
        return (
            self.db.scalar(
                select(Subject.id).where(Subject.owner_id == owner_id, Subject.id == subject_id)
            )
            is not None
        )

    def replay(self, owner_id, operation, key, fingerprint):
        import json

        row = self.db.scalar(
            select(Operation).where(
                Operation.owner_id == owner_id,
                Operation.operation == operation,
                Operation.key == key,
            )
        )
        if row:
            if row.fingerprint != fingerprint:
                raise PolicyError("IDEMPOTENCY_CONFLICT", "Operation key was reused.", 409)
            return json.loads(row.response)
        return None

    def remember(self, owner_id, operation, key, fingerprint, response):
        import json

        self.db.add(
            Operation(
                owner_id=owner_id,
                operation=operation,
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(response),
            )
        )

    def commit(self):
        self.db.commit()
