"""Owner-scoped SQL persistence for comparisons."""

import json
from datetime import UTC
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
    select,
)

from .domain import PolicyError, utc_now
from .storage import Base, ProblemAttemptRow, ProblemRow, Subject


def _utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ProblemComparisonRow(Base):
    __tablename__ = "problem_comparisons"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "left_problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_comparison_left_problem_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "right_problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_comparison_right_problem_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "left_attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_comparison_left_attempt_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "right_attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_comparison_right_attempt_owner",
        ),
        CheckConstraint(
            "left_problem_id != right_problem_id", name="ck_comparison_distinct_problems"
        ),
        CheckConstraint("version >= 1", name="ck_comparison_version"),
        Index("ix_comparisons_owner_id", "owner_id", "id"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    left_problem_id = Column(String(36), nullable=False)
    right_problem_id = Column(String(36), nullable=False)
    left_attempt_id = Column(String(36))
    right_attempt_id = Column(String(36))
    conditions = Column(Text)
    known_values = Column(Text)
    formulas = Column(Text)
    entry_point = Column(Text)
    diagram = Column(Text)
    boundary = Column(Text)
    assumptions = Column(Text)
    conclusion = Column(Text)
    archived_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    source_versions = Column(Text, nullable=False)


class SQLComparisonRepository:
    def __init__(self, db):
        self.db = db

    def _data(self, row):
        versions = json.loads(row.source_versions)
        current = {}
        for pid in (row.left_problem_id, row.right_problem_id):
            prob = self.db.scalar(
                select(ProblemRow).where(ProblemRow.owner_id == row.owner_id, ProblemRow.id == pid)
            )
            if prob is not None:
                current[pid] = prob.version
        for aid in (row.left_attempt_id, row.right_attempt_id):
            if aid:
                att = self.db.scalar(
                    select(ProblemAttemptRow).where(
                        ProblemAttemptRow.owner_id == row.owner_id, ProblemAttemptRow.id == aid
                    )
                )
                if att is not None:
                    current[aid] = att.version
        return {
            "id": row.id,
            "version": row.version,
            "left_problem_id": row.left_problem_id,
            "right_problem_id": row.right_problem_id,
            "left_attempt_id": row.left_attempt_id,
            "right_attempt_id": row.right_attempt_id,
            **{
                field: getattr(row, field)
                for field in (
                    "conditions",
                    "known_values",
                    "formulas",
                    "entry_point",
                    "diagram",
                    "boundary",
                    "assumptions",
                    "conclusion",
                )
            },
            "archived": row.archived_at is not None,
            "created_at": _utc(row.created_at).isoformat(),
            "updated_at": _utc(row.updated_at).isoformat(),
            "source_versions": versions,
            "source_changed": any(current.get(key) != value for key, value in versions.items()),
        }

    def _get_row(self, owner, cid):
        row = self.db.scalar(
            select(ProblemComparisonRow).where(
                ProblemComparisonRow.owner_id == owner, ProblemComparisonRow.id == cid
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return row

    def create(self, owner, data):
        left = self.db.scalar(
            select(ProblemRow).where(
                ProblemRow.owner_id == owner, ProblemRow.id == data["left_problem_id"]
            )
        )
        right = self.db.scalar(
            select(ProblemRow).where(
                ProblemRow.owner_id == owner, ProblemRow.id == data["right_problem_id"]
            )
        )
        if left is None or right is None or left.id == right.id:
            raise PolicyError(
                "RESOURCE_NOT_FOUND" if left is None or right is None else "VALIDATION_ERROR",
                "Selected problems are unavailable or identical.",
                404 if left is None or right is None else 422,
            )
        versions = {left.id: left.version, right.id: right.version}
        for side, problem in (("left", left), ("right", right)):
            aid = data.get(f"{side}_attempt_id")
            if aid:
                attempt = self.db.scalar(
                    select(ProblemAttemptRow).where(
                        ProblemAttemptRow.owner_id == owner, ProblemAttemptRow.id == aid
                    )
                )
                if attempt is None:
                    raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
                if attempt.problem_id != problem.id:
                    raise PolicyError(
                        "VALIDATION_ERROR", "Selected attempt does not belong to its problem.", 422
                    )
                versions[aid] = attempt.version
        now = utc_now()
        row = ProblemComparisonRow(
            id=str(uuid4()),
            owner_id=owner,
            version=1,
            left_problem_id=left.id,
            right_problem_id=right.id,
            left_attempt_id=data.get("left_attempt_id"),
            right_attempt_id=data.get("right_attempt_id"),
            **{
                field: data.get(field)
                for field in (
                    "conditions",
                    "known_values",
                    "formulas",
                    "entry_point",
                    "diagram",
                    "boundary",
                    "assumptions",
                    "conclusion",
                )
            },
            archived_at=None,
            created_at=now,
            updated_at=now,
            source_versions=json.dumps(versions, sort_keys=True),
        )
        self.db.add(row)
        self.db.flush()
        return self._data(row)

    def get(self, owner, cid):
        return self._data(self._get_row(owner, cid))

    def list(self, owner, filters, limit, cursor):
        query = select(ProblemComparisonRow).where(ProblemComparisonRow.owner_id == owner)
        if filters["archived"] is not None:
            query = query.where(
                ProblemComparisonRow.archived_at.is_not(None)
                if filters["archived"]
                else ProblemComparisonRow.archived_at.is_(None)
            )
        if filters["problem_id"]:
            problem = self.db.scalar(
                select(ProblemRow.id).where(
                    ProblemRow.owner_id == owner, ProblemRow.id == filters["problem_id"]
                )
            )
            if problem is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            query = query.where(
                (ProblemComparisonRow.left_problem_id == filters["problem_id"])
                | (ProblemComparisonRow.right_problem_id == filters["problem_id"])
            )
        if filters["subject_id"]:
            subject = self.db.scalar(
                select(Subject.id).where(
                    Subject.owner_id == owner, Subject.id == filters["subject_id"]
                )
            )
            if subject is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            query = query.where(
                ProblemComparisonRow.id.in_(
                    select(ProblemComparisonRow.id)
                    .join(
                        ProblemRow,
                        (ProblemRow.owner_id == ProblemComparisonRow.owner_id)
                        & (
                            (ProblemRow.id == ProblemComparisonRow.left_problem_id)
                            | (ProblemRow.id == ProblemComparisonRow.right_problem_id)
                        ),
                    )
                    .where(
                        ProblemRow.owner_id == owner, ProblemRow.subject_id == filters["subject_id"]
                    )
                )
            )
        if cursor:
            cursor_row = self.db.scalar(
                select(ProblemComparisonRow).where(
                    ProblemComparisonRow.owner_id == owner,
                    ProblemComparisonRow.id == cursor,
                )
            )
            if cursor_row is None:
                raise PolicyError("VALIDATION_ERROR", "Comparison cursor is invalid.", 422)
            if (
                filters["archived"] is not None
                and (cursor_row.archived_at is not None) != filters["archived"]
            ):
                raise PolicyError("VALIDATION_ERROR", "Comparison cursor is invalid.", 422)
            if filters["problem_id"] and filters["problem_id"] not in (
                cursor_row.left_problem_id,
                cursor_row.right_problem_id,
            ):
                raise PolicyError("VALIDATION_ERROR", "Comparison cursor is invalid.", 422)
            if filters["subject_id"]:
                in_subject = self.db.scalar(
                    select(ProblemRow.id)
                    .where(
                        ProblemRow.owner_id == owner,
                        ProblemRow.subject_id == filters["subject_id"],
                        ProblemRow.id.in_(
                            (cursor_row.left_problem_id, cursor_row.right_problem_id)
                        ),
                    )
                    .limit(1)
                )
                if in_subject is None:
                    raise PolicyError("VALIDATION_ERROR", "Comparison cursor is invalid.", 422)
            query = query.where(ProblemComparisonRow.id > cursor)
        return [
            self._data(row)
            for row in self.db.scalars(query.order_by(ProblemComparisonRow.id).limit(limit))
        ]

    def patch(self, owner, cid, data, version):
        row = self._get_row(owner, cid)
        if row.version != version:
            error = PolicyError(
                "VERSION_CONFLICT", "Comparison changed; reload before editing.", 409
            )
            error.current_version = row.version
            error.current = self._data(row)
            raise error
        for field, value in data.items():
            if field == "archived":
                row.archived_at = utc_now() if value else None
            else:
                setattr(row, field, value)
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return self._data(row)


class SQLComparisonUnitOfWork:
    """Adds comparison repository while retaining the established SQL UoW semantics."""

    def __init__(self, db):
        from .storage import SQLUnitOfWork

        self.db = db
        self.base = SQLUnitOfWork(db)
        self.comparisons = SQLComparisonRepository(db)

    def lock_owner(self, owner_id):
        return self.base.lock_owner(owner_id)

    def replay(self, *args):
        return self.base.replay(*args)

    def remember(self, *args):
        return self.base.remember(*args)

    def commit(self):
        return self.base.commit()
