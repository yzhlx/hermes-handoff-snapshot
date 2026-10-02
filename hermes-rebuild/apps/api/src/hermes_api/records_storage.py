"""SQL adapter that reads source facts for the records projection."""

from datetime import UTC

from sqlalchemy import func, select

from .knowledge_storage import KnowledgePointRow, ProblemKnowledgeLinkRow
from .records_domain import (
    AttemptFact,
    KnowledgePointFact,
    ProblemFact,
    RecordFacts,
    ReflectionFact,
    SessionFact,
)
from .storage import (
    AttemptErrorRow,
    ProblemAttemptRow,
    ProblemRow,
    SessionReflectionRow,
    SessionRow,
    Subject,
)


def _aware(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


class SQLRecordsRepository:
    def __init__(self, db):
        self.db = db

    def collect(self, owner_id: str, from_date: str, to_date: str, subject_id: str | None):
        sessions = list(
            self.db.scalars(
                select(SessionRow)
                .where(
                    SessionRow.owner_id == owner_id,
                    SessionRow.learning_date >= from_date,
                    SessionRow.learning_date <= to_date,
                    *([SessionRow.subject_id == subject_id] if subject_id else []),
                )
                .order_by(
                    SessionRow.learning_date.desc(),
                    SessionRow.started_at.desc(),
                    SessionRow.id.desc(),
                )
            )
        )
        ids = [row.id for row in sessions]
        reflections = (
            {
                row.session_id: row
                for row in self.db.scalars(
                    select(SessionReflectionRow).where(
                        SessionReflectionRow.owner_id == owner_id,
                        SessionReflectionRow.session_id.in_(ids),
                    )
                )
            }
            if ids
            else {}
        )
        attempts = (
            list(
                self.db.scalars(
                    select(ProblemAttemptRow)
                    .where(
                        ProblemAttemptRow.owner_id == owner_id,
                        ProblemAttemptRow.session_id.in_(ids),
                    )
                    .order_by(ProblemAttemptRow.occurred_at, ProblemAttemptRow.id)
                )
            )
            if ids
            else []
        )
        subject_ids = {row.subject_id for row in sessions if row.subject_id}
        subjects = (
            {
                row.id: row.name
                for row in self.db.scalars(
                    select(Subject).where(Subject.owner_id == owner_id, Subject.id.in_(subject_ids))
                )
            }
            if subject_ids
            else {}
        )
        problems_ids = {row.problem_id for row in attempts}
        problem_points = {}
        point_ids = set()
        if problems_ids:
            for link in self.db.scalars(
                select(ProblemKnowledgeLinkRow).where(
                    ProblemKnowledgeLinkRow.owner_id == owner_id,
                    ProblemKnowledgeLinkRow.problem_id.in_(problems_ids),
                )
            ):
                problem_points.setdefault(link.problem_id, []).append(link.knowledge_point_id)
                point_ids.add(link.knowledge_point_id)
        errors = {}
        if attempts:
            for row in self.db.scalars(
                select(AttemptErrorRow).where(
                    AttemptErrorRow.owner_id == owner_id,
                    AttemptErrorRow.attempt_id.in_([a.id for a in attempts]),
                )
            ):
                errors.setdefault(row.attempt_id, []).append(row.category)
        history = []
        history_points = {}
        if problems_ids:
            related_problem_ids = set(problems_ids)
            if point_ids:
                related_problem_ids.update(
                    self.db.scalars(
                        select(ProblemKnowledgeLinkRow.problem_id).where(
                            ProblemKnowledgeLinkRow.owner_id == owner_id,
                            ProblemKnowledgeLinkRow.knowledge_point_id.in_(point_ids),
                        )
                    )
                )
            ranked = (
                select(
                    ProblemAttemptRow.id.label("attempt_id"),
                    ProblemAttemptRow.problem_id.label("problem_id"),
                    func.row_number()
                    .over(
                        partition_by=ProblemAttemptRow.problem_id,
                        order_by=(
                            ProblemAttemptRow.occurred_at.desc(),
                            ProblemAttemptRow.id.desc(),
                        ),
                    )
                    .label("rank"),
                )
                .join(
                    SessionRow,
                    (SessionRow.owner_id == ProblemAttemptRow.owner_id)
                    & (SessionRow.id == ProblemAttemptRow.session_id),
                )
                .where(
                    ProblemAttemptRow.owner_id == owner_id,
                    ProblemAttemptRow.problem_id.in_(related_problem_ids),
                    SessionRow.learning_date <= to_date,
                )
                .subquery()
            )
            bounded_ids = list(
                self.db.scalars(select(ranked.c.attempt_id).where(ranked.c.rank <= 20))
            )
            history = (
                list(
                    self.db.scalars(
                        select(ProblemAttemptRow)
                        .where(
                            ProblemAttemptRow.owner_id == owner_id,
                            ProblemAttemptRow.id.in_(bounded_ids),
                        )
                        .order_by(ProblemAttemptRow.occurred_at, ProblemAttemptRow.id)
                    )
                )
                if bounded_ids
                else []
            )
            for link in self.db.scalars(
                select(ProblemKnowledgeLinkRow).where(
                    ProblemKnowledgeLinkRow.owner_id == owner_id,
                    ProblemKnowledgeLinkRow.problem_id.in_(related_problem_ids),
                )
            ):
                history_points.setdefault(link.problem_id, []).append(link.knowledge_point_id)
            missing = [a.id for a in history if a.id not in errors]
            if missing:
                for row in self.db.scalars(
                    select(AttemptErrorRow).where(
                        AttemptErrorRow.owner_id == owner_id,
                        AttemptErrorRow.attempt_id.in_(missing),
                    )
                ):
                    errors.setdefault(row.attempt_id, []).append(row.category)
        problems_ids.update(a.problem_id for a in history)
        problems = (
            {
                row.id: row
                for row in self.db.scalars(
                    select(ProblemRow).where(
                        ProblemRow.owner_id == owner_id,
                        ProblemRow.id.in_(problems_ids),
                    )
                )
            }
            if problems_ids
            else {}
        )
        knowledge_points = (
            {
                row.id: row
                for row in self.db.scalars(
                    select(KnowledgePointRow).where(
                        KnowledgePointRow.owner_id == owner_id,
                        KnowledgePointRow.id.in_(
                            point_ids
                            | {
                                point_id
                                for values in history_points.values()
                                for point_id in values
                            }
                        ),
                    )
                )
            }
            if point_ids or history_points
            else {}
        )
        return RecordFacts(
            sessions=[
                SessionFact(
                    id=row.id,
                    version=row.version,
                    goal=row.goal,
                    subject_id=row.subject_id,
                    status=row.status,
                    learning_date=row.learning_date,
                    day_timezone=row.day_timezone,
                    started_at=_aware(row.started_at),
                    ended_at=_aware(row.ended_at),
                    resume_note=row.resume_note,
                    knowledge_point_id=row.knowledge_point_id,
                )
                for row in sessions
            ],
            reflections={
                session_id: ReflectionFact(
                    id=row.id,
                    session_id=row.session_id,
                    version=row.version,
                    summary=row.summary,
                    recalled_text=row.recalled_text,
                    missing_parts=row.missing_parts,
                    stuck_note=row.stuck_note,
                    updated_at=_aware(row.updated_at),
                )
                for session_id, row in reflections.items()
            },
            attempts=[
                AttemptFact(
                    id=row.id,
                    session_id=row.session_id,
                    problem_id=row.problem_id,
                    version=row.version,
                    answer_check=row.answer_check,
                    independence=row.independence,
                    result=row.result,
                    occurred_at=_aware(row.occurred_at),
                    stuck_note=row.stuck_note,
                )
                for row in attempts
            ],
            subjects=subjects,
            problems={
                key: ProblemFact(
                    id=row.id,
                    version=row.version,
                    title=row.title,
                    statement=row.statement,
                    updated_at=_aware(row.updated_at),
                )
                for key, row in problems.items()
            },
            errors=errors,
            history_attempts=[
                AttemptFact(
                    id=row.id,
                    session_id=row.session_id,
                    problem_id=row.problem_id,
                    version=row.version,
                    answer_check=row.answer_check,
                    independence=row.independence,
                    result=row.result,
                    occurred_at=_aware(row.occurred_at),
                    stuck_note=row.stuck_note,
                )
                for row in history
            ],
            problem_points=problem_points,
            history_points=history_points,
            knowledge_points={
                key: KnowledgePointFact(
                    id=row.id, version=row.version, name=row.name, updated_at=_aware(row.updated_at)
                )
                for key, row in knowledge_points.items()
            },
        )
