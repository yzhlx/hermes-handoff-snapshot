"""Owner-scoped SQL adapter for current source facts and persisted suggestion state."""

import json
from datetime import UTC

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    update,
)

from .domain import PolicyError
from .knowledge_storage import ChapterRow, KnowledgePointRow, ProblemKnowledgeLinkRow
from .storage import (
    AttemptErrorRow,
    Base,
    ProblemAttemptRow,
    ProblemRow,
    SessionReflectionRow,
    SessionRow,
    Subject,
    User,
)
from .suggestion_domain import build_candidates


def _utc(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC) if value else None


class SuggestionRow(Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        UniqueConstraint("owner_id", "fingerprint", name="uq_suggestions_owner_fingerprint"),
        Index("ix_suggestions_owner_status_id", "owner_id", "status", "id"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    kind = Column(String(24), nullable=False)
    status = Column(String(24), nullable=False)
    subject_id = Column(String(36))
    knowledge_point_id = Column(String(36))
    problem_id = Column(String(36))
    reason = Column(Text, nullable=False)
    source_refs = Column(Text, nullable=False)
    source_revision = Column(String(64), nullable=False)
    rule_version = Column(String(40), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    snoozed_until = Column(DateTime(timezone=True))


class SQLSuggestionRepository:
    def __init__(self, db):
        self.db = db

    def _facts(self, owner):
        session_rows = list(self.db.scalars(select(SessionRow).where(SessionRow.owner_id == owner)))
        session_ids = [row.id for row in session_rows]
        reflections = list(
            self.db.scalars(
                select(SessionReflectionRow).where(
                    SessionReflectionRow.owner_id == owner,
                    SessionReflectionRow.session_id.in_(session_ids) if session_ids else False,
                )
            )
        )
        reflection_by_session = {row.session_id: row for row in reflections}
        sessions = []
        for row in session_rows:
            reflection = reflection_by_session.get(row.id)
            session = {
                "id": row.id,
                "status": row.status,
                "version": row.version,
                "resume_note": row.resume_note,
                "subject_id": row.subject_id,
                "knowledge_point_id": row.knowledge_point_id,
                "source_ref": {
                    "kind": "session",
                    "id": row.id,
                    "version": row.version,
                    "label": row.goal or "学习记录",
                    "occurred_at": _utc(row.ended_at or row.started_at),
                    "session_id": row.id,
                },
            }
            if reflection:
                session["reflection"] = {
                    "resume_note": reflection.resume_note,
                    "source_ref": {
                        "kind": "reflection",
                        "id": reflection.id,
                        "version": reflection.version,
                        "label": "学习反馈",
                        "occurred_at": _utc(reflection.updated_at),
                        "session_id": row.id,
                    },
                }
            sessions.append(session)

        problem_rows = list(
            self.db.scalars(
                select(ProblemRow).where(
                    ProblemRow.owner_id == owner, ProblemRow.archived_at.is_(None)
                )
            )
        )
        problem_by_id = {row.id: row for row in problem_rows}
        all_attempts = list(
            self.db.scalars(
                select(ProblemAttemptRow)
                .where(
                    ProblemAttemptRow.owner_id == owner,
                    ProblemAttemptRow.problem_id.in_(problem_by_id) if problem_by_id else False,
                )
                .order_by(ProblemAttemptRow.occurred_at.desc(), ProblemAttemptRow.id.desc())
            )
        )
        attempt_ids = [row.id for row in all_attempts]
        categories_by_attempt = {}
        if attempt_ids:
            for attempt_id, category in self.db.execute(
                select(AttemptErrorRow.attempt_id, AttemptErrorRow.category)
                .where(
                    AttemptErrorRow.owner_id == owner, AttemptErrorRow.attempt_id.in_(attempt_ids)
                )
                .order_by(AttemptErrorRow.category)
            ):
                categories_by_attempt.setdefault(attempt_id, []).append(category)

        def attempt_fact(attempt, problem):
            return {
                "id": attempt.id,
                "version": attempt.version,
                "answer_check": attempt.answer_check,
                "result": attempt.result,
                "independence": attempt.independence,
                "occurred_at": _utc(attempt.occurred_at),
                "error_categories": categories_by_attempt.get(attempt.id, []),
                "source_ref": {
                    "kind": "attempt",
                    "id": attempt.id,
                    "version": attempt.version,
                    "label": "作答记录",
                    "occurred_at": _utc(attempt.occurred_at),
                    "session_id": attempt.session_id,
                    "problem_id": problem.id,
                },
                "problem_source_ref": {
                    "kind": "problem",
                    "id": problem.id,
                    "version": problem.version,
                    "label": problem.title or "错题",
                    "occurred_at": _utc(problem.created_at),
                    "problem_id": problem.id,
                },
            }

        attempts_by_problem = {}
        for attempt in all_attempts:
            problem = problem_by_id[attempt.problem_id]
            attempts_by_problem.setdefault(problem.id, []).append(attempt_fact(attempt, problem))
        problems = [
            {
                "id": problem.id,
                "subject_id": problem.subject_id,
                "source_ref": {
                    "kind": "problem",
                    "id": problem.id,
                    "version": problem.version,
                    "label": problem.title or "错题",
                    "occurred_at": _utc(problem.created_at),
                    "problem_id": problem.id,
                },
                "attempts": attempts_by_problem.get(problem.id, []),
            }
            for problem in problem_rows
        ]

        points = list(
            self.db.scalars(
                select(KnowledgePointRow).where(
                    KnowledgePointRow.owner_id == owner, KnowledgePointRow.archived_at.is_(None)
                )
            )
        )
        point_ids = [point.id for point in points]
        chapters = {
            row.id: row
            for row in self.db.scalars(
                select(ChapterRow).where(
                    ChapterRow.owner_id == owner,
                    ChapterRow.id.in_([point.chapter_id for point in points]) if points else False,
                )
            )
        }
        linked_attempts = self.db.execute(
            select(ProblemKnowledgeLinkRow.knowledge_point_id, ProblemAttemptRow, ProblemRow)
            .join(
                ProblemRow,
                (ProblemRow.owner_id == ProblemAttemptRow.owner_id)
                & (ProblemRow.id == ProblemAttemptRow.problem_id),
            )
            .join(
                ProblemKnowledgeLinkRow,
                (ProblemKnowledgeLinkRow.owner_id == ProblemRow.owner_id)
                & (ProblemKnowledgeLinkRow.problem_id == ProblemRow.id),
            )
            .where(
                ProblemKnowledgeLinkRow.owner_id == owner,
                ProblemKnowledgeLinkRow.knowledge_point_id.in_(point_ids) if point_ids else False,
                ProblemAttemptRow.answer_check == "checked",
                ProblemRow.archived_at.is_(None),
            )
            .order_by(
                ProblemKnowledgeLinkRow.knowledge_point_id,
                ProblemAttemptRow.occurred_at.desc(),
                ProblemAttemptRow.id.desc(),
            )
        ).all()
        attempts_by_point = {}
        checked_counts = {}
        for point_id, attempt, problem in linked_attempts:
            # Retain only the twenty latest checked attempts for each point.
            if checked_counts.get(point_id, 0) >= 20:
                continue
            checked_counts[point_id] = checked_counts.get(point_id, 0) + 1
            attempts_by_point.setdefault(point_id, []).append(attempt_fact(attempt, problem))
        point_facts = []
        for point in points:
            chapter = chapters.get(point.chapter_id)
            if chapter is None or chapter.archived_at is not None:
                continue
            point_facts.append(
                {
                    "id": point.id,
                    "subject_id": point.subject_id,
                    "source_ref": {
                        "kind": "knowledge_point",
                        "id": point.id,
                        "version": point.version,
                        "label": point.name,
                        "occurred_at": _utc(point.updated_at),
                    },
                    "attempts": attempts_by_point.get(point.id, []),
                }
            )
        return {"sessions": sessions, "problems": problems, "knowledge_points": point_facts}

    @staticmethod
    def _data(row):
        from .suggestion_schemas import SuggestionData

        return SuggestionData(
            id=row.id,
            version=row.version,
            kind=row.kind,
            status=row.status,
            subject_id=row.subject_id,
            knowledge_point_id=row.knowledge_point_id,
            problem_id=row.problem_id,
            reason=row.reason,
            source_refs=json.loads(row.source_refs),
            source_revision=row.source_revision,
            rule_version=row.rule_version,
            generated_at=_utc(row.generated_at),
            expires_at=_utc(row.expires_at),
            snoozed_until=_utc(row.snoozed_until),
        ).model_dump(mode="json")

    def candidates(self, owner, now):
        facts = self._facts(owner)
        candidates = build_candidates(facts, now)
        current = {item["fingerprint"] for item in candidates}
        existing = list(
            self.db.scalars(select(SuggestionRow).where(SuggestionRow.owner_id == owner))
        )
        by_fp = {row.fingerprint: row for row in existing}
        for item in candidates:
            row = by_fp.get(item["fingerprint"])
            if row is None:
                import uuid

                row = SuggestionRow(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    fingerprint=item["fingerprint"],
                    kind=item["kind"],
                    status="available",
                    subject_id=item["subject_id"],
                    knowledge_point_id=item["knowledge_point_id"],
                    problem_id=item["problem_id"],
                    reason=item["reason"],
                    source_refs=json.dumps(
                        item["source_refs"], ensure_ascii=False, default=lambda v: v.isoformat()
                    ),
                    source_revision=item["source_revision"],
                    rule_version=item["rule_version"],
                    version=1,
                    generated_at=item["generated_at"],
                )
                self.db.add(row)
                by_fp[item["fingerprint"]] = row
            else:
                if row.status == "snoozed" and row.snoozed_until and _utc(row.snoozed_until) <= now:
                    row.status = "available"
                    row.snoozed_until = None
                    row.version += 1
        for row in existing:
            if row.fingerprint not in current and row.status != "stale":
                row.status = "stale"
                row.version += 1
        self.db.flush()

    def list_suggestions(self, owner, filters, limit, cursor):
        self.candidates(owner, filters["now"])
        query = select(SuggestionRow).where(SuggestionRow.owner_id == owner)
        status = filters["status"]
        if status != "all":
            query = query.where(SuggestionRow.status == status)
        if filters["kind"]:
            query = query.where(SuggestionRow.kind == filters["kind"])
        if filters["subject_id"]:
            # A foreign subject is deliberately indistinguishable from an empty scope.
            if (
                self.db.scalar(
                    select(Subject.id).where(
                        Subject.id == filters["subject_id"], Subject.owner_id == owner
                    )
                )
                is None
            ):
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            query = query.where(SuggestionRow.subject_id == filters["subject_id"])
        if cursor:
            cursor_row = self.db.scalar(
                select(SuggestionRow).where(
                    SuggestionRow.owner_id == owner, SuggestionRow.id == cursor
                )
            )
            if cursor_row is None:
                raise PolicyError("VALIDATION_ERROR", "Suggestion cursor is invalid.", 422)
            if (
                (status != "all" and cursor_row.status != status)
                or (filters["kind"] and cursor_row.kind != filters["kind"])
                or (filters["subject_id"] and cursor_row.subject_id != filters["subject_id"])
            ):
                raise PolicyError("VALIDATION_ERROR", "Suggestion cursor is invalid.", 422)
            query = query.where(SuggestionRow.id > cursor)
        return [
            self._data(r) for r in self.db.scalars(query.order_by(SuggestionRow.id).limit(limit))
        ]

    def get_suggestion(self, owner, suggestion_id, now):
        self.candidates(owner, now)
        row = self.db.scalar(
            select(SuggestionRow).where(
                SuggestionRow.owner_id == owner, SuggestionRow.id == suggestion_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._data(row)

    def act(self, owner, suggestion_id, action, until, version, now):
        self.candidates(owner, now)
        row = self.db.scalar(
            select(SuggestionRow).where(
                SuggestionRow.owner_id == owner, SuggestionRow.id == suggestion_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.status == "stale":
            self._conflict(row)
        if row.version != version:
            self._conflict(row)
        wanted = {"accept": "accepted", "snooze": "snoozed", "dismiss": "dismissed"}[action]
        if row.status == wanted and (action != "snooze" or _utc(row.snoozed_until) == until):
            return self._data(row)
        row.status = wanted
        row.snoozed_until = until
        row.version += 1
        self.db.flush()
        return self._data(row)

    def _conflict(self, row):
        error = PolicyError("VERSION_CONFLICT", "Suggestion changed or its evidence is stale.", 409)
        error.current_version = row.version
        error.current = self._data(row)
        raise error


class SQLSuggestionUnitOfWork:
    def __init__(self, db):
        from .storage import Operation

        self.db, self.Operation = db, Operation
        self.suggestions = SQLSuggestionRepository(db)

    def lock_owner(self, owner_id):
        self.db.execute(update(User).where(User.id == owner_id).values(timezone=User.timezone))

    def replay(self, owner_id, operation, key, fingerprint):
        row = self.db.scalar(
            select(self.Operation).where(
                self.Operation.owner_id == owner_id,
                self.Operation.operation == operation,
                self.Operation.key == key,
            )
        )
        if row is None:
            return None
        if row.fingerprint != fingerprint:
            raise PolicyError("IDEMPOTENCY_CONFLICT", "Key was used for another request.", 409)
        return json.loads(row.response)

    def remember(self, owner_id, operation, key, fingerprint, response):
        self.db.add(
            self.Operation(
                owner_id=owner_id,
                operation=operation,
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(response, ensure_ascii=False),
            )
        )

    def commit(self):
        self.db.commit()
