"""Owner-scoped SQL persistence for advisor analyses."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    select,
)

from .advisor_domain import MAX_EVIDENCE_RECORDS
from .domain import PolicyError, utc_now
from .knowledge_storage import KnowledgePointRow, ProblemKnowledgeLinkRow
from .storage import (
    AttemptErrorRow,
    Base,
    ProblemAttemptRow,
    ProblemRow,
    SQLUnitOfWork,
    Subject,
)

STATUSES = ("ready", "insufficient", "degraded", "blocked", "cancelled")


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class AdvisorRunRow(Base):
    __tablename__ = "advisor_runs"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_advisor_run_owner_id"),
        Index("ix_advisor_runs_owner_created", "owner_id", "created_at", "id"),
        CheckConstraint(
            "status IN ('ready','insufficient','degraded','blocked','cancelled')",
            name="ck_advisor_run_status",
        ),
        CheckConstraint("evidence_count >= 0", name="ck_advisor_run_evidence_count"),
        CheckConstraint("version >= 1", name="ck_advisor_run_version"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    request_id = Column(String(128), nullable=False)
    topic = Column(Text)
    subject_id = Column(String(36))
    knowledge_point_id = Column(String(36))
    status = Column(String(20), nullable=False)
    degradation_reason = Column(Text)
    facts = Column(Text, nullable=False)
    inferences = Column(Text, nullable=False)
    missing_information = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    evidence_count = Column(Integer, nullable=False)
    evidence_refs = Column(Text, nullable=False)
    data_version = Column(String(64), nullable=False)
    model_id = Column(String(80), nullable=False)
    provider = Column(String(80), nullable=False)
    prompt_version = Column(String(80), nullable=False)
    policy_version = Column(String(80), nullable=False)
    rule_version = Column(String(80), nullable=False)
    externally_hosted = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class SQLAdvisorRepository:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ evidence
    def _assert_owner_scope(self, owner, subject_id, knowledge_point_id):
        if subject_id:
            exists = self.db.scalar(
                select(Subject.id).where(Subject.owner_id == owner, Subject.id == subject_id)
            )
            if exists is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if knowledge_point_id:
            exists = self.db.scalar(
                select(KnowledgePointRow.id).where(
                    KnowledgePointRow.owner_id == owner,
                    KnowledgePointRow.id == knowledge_point_id,
                )
            )
            if exists is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)

    def collect_evidence(self, owner, subject_id, knowledge_point_id):
        self._assert_owner_scope(owner, subject_id, knowledge_point_id)
        query = (
            select(ProblemAttemptRow, ProblemRow, Subject)
            .join(
                ProblemRow,
                (ProblemRow.owner_id == ProblemAttemptRow.owner_id)
                & (ProblemRow.id == ProblemAttemptRow.problem_id),
            )
            .outerjoin(
                Subject,
                (Subject.owner_id == ProblemRow.owner_id) & (Subject.id == ProblemRow.subject_id),
            )
            .where(ProblemAttemptRow.owner_id == owner)
        )
        if subject_id:
            query = query.where(ProblemRow.subject_id == subject_id)
        if knowledge_point_id:
            query = query.join(
                ProblemKnowledgeLinkRow,
                (ProblemKnowledgeLinkRow.owner_id == ProblemRow.owner_id)
                & (ProblemKnowledgeLinkRow.problem_id == ProblemRow.id),
            ).where(ProblemKnowledgeLinkRow.knowledge_point_id == knowledge_point_id)
        rows = self.db.execute(
            query.order_by(ProblemAttemptRow.occurred_at.desc(), ProblemAttemptRow.id.desc()).limit(
                MAX_EVIDENCE_RECORDS
            )
        ).all()

        attempt_ids = [attempt.id for attempt, _problem, _subject in rows]
        problem_ids = [problem.id for _attempt, problem, _subject in rows]
        categories: dict[str, list[str]] = {item: [] for item in attempt_ids}
        if attempt_ids:
            for attempt_id, category in self.db.execute(
                select(AttemptErrorRow.attempt_id, AttemptErrorRow.category)
                .where(
                    AttemptErrorRow.owner_id == owner,
                    AttemptErrorRow.attempt_id.in_(attempt_ids),
                )
                .order_by(AttemptErrorRow.category)
            ):
                categories[attempt_id].append(category)
        points: dict[str, list[str]] = {item: [] for item in problem_ids}
        if problem_ids:
            for problem_id, point_id in self.db.execute(
                select(
                    ProblemKnowledgeLinkRow.problem_id,
                    ProblemKnowledgeLinkRow.knowledge_point_id,
                )
                .where(
                    ProblemKnowledgeLinkRow.owner_id == owner,
                    ProblemKnowledgeLinkRow.problem_id.in_(problem_ids),
                )
                .order_by(ProblemKnowledgeLinkRow.knowledge_point_id)
            ):
                points[problem_id].append(point_id)

        records = [
            {
                "id": attempt.id,
                "version": attempt.version,
                "problem_id": problem.id,
                "problem_title": problem.title or problem.statement,
                "subject_id": problem.subject_id,
                "subject_name": subject.name if subject is not None else None,
                "independence": attempt.independence,
                "answer_check": attempt.answer_check,
                "result": attempt.result,
                "error_categories": categories[attempt.id],
                "knowledge_point_ids": points[problem.id],
                "stuck_note": attempt.stuck_note,
                "occurred_at": _iso(attempt.occurred_at),
            }
            for attempt, problem, subject in rows
        ]
        return {"records": records}

    # ------------------------------------------------------------------ runs
    @staticmethod
    def _data(row):
        return {
            "id": row.id,
            "status": row.status,
            "topic": row.topic,
            "subject_id": row.subject_id,
            "knowledge_point_id": row.knowledge_point_id,
            "facts": json.loads(row.facts),
            "inferences": json.loads(row.inferences),
            "missing_information": json.loads(row.missing_information),
            "summary": row.summary,
            "degradation_reason": row.degradation_reason,
            "evidence_count": row.evidence_count,
            "evidence_refs": json.loads(row.evidence_refs),
            "data_version": row.data_version,
            "model_id": row.model_id,
            "provider": row.provider,
            "prompt_version": row.prompt_version,
            "policy_version": row.policy_version,
            "rule_version": row.rule_version,
            "privacy": {
                "external": bool(row.externally_hosted),
                "provider": row.provider,
                "scope": (
                    "仅使用你本人的学习记录，最多 20 条；"
                    + (
                        "本次调用发送给外部服务。"
                        if row.externally_hosted
                        else "本次调用不发送到外部服务。"
                    )
                ),
            },
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def create_run(self, owner, data):
        now = utc_now()
        row = AdvisorRunRow(
            id=str(uuid4()),
            owner_id=owner,
            version=1,
            request_id=data["request_id"],
            topic=data.get("topic"),
            subject_id=data.get("subject_id"),
            knowledge_point_id=data.get("knowledge_point_id"),
            status=data["status"],
            degradation_reason=data.get("degradation_reason"),
            facts=json.dumps(data["facts"], ensure_ascii=False),
            inferences=json.dumps(data["inferences"], ensure_ascii=False),
            missing_information=json.dumps(data["missing_information"], ensure_ascii=False),
            summary=data["summary"],
            evidence_count=data["evidence_count"],
            evidence_refs=json.dumps(data["evidence_refs"], ensure_ascii=False),
            data_version=data["data_version"],
            model_id=data["model_id"],
            provider=data["provider"],
            prompt_version=data["prompt_version"],
            policy_version=data["policy_version"],
            rule_version=data["rule_version"],
            externally_hosted=data["externally_hosted"],
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return self._data(row)

    def _row(self, owner, run_id):
        row = self.db.scalar(
            select(AdvisorRunRow).where(AdvisorRunRow.owner_id == owner, AdvisorRunRow.id == run_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return row

    def get_run(self, owner, run_id):
        return self._data(self._row(owner, run_id))

    def list_runs(self, owner, limit, cursor):
        query = select(AdvisorRunRow).where(AdvisorRunRow.owner_id == owner)
        if cursor:
            created_raw, _, run_id = cursor.partition("|")
            try:
                created = datetime.fromisoformat(created_raw).replace(tzinfo=None)
            except ValueError:
                raise PolicyError("VALIDATION_ERROR", "Advisor cursor is invalid.", 422) from None
            if not run_id:
                raise PolicyError("VALIDATION_ERROR", "Advisor cursor is invalid.", 422)
            exists = self.db.scalar(
                select(AdvisorRunRow.id).where(
                    AdvisorRunRow.owner_id == owner,
                    AdvisorRunRow.id == run_id,
                    AdvisorRunRow.created_at == created,
                )
            )
            if exists is None:
                # Also rejects a cursor that belongs to another owner.
                raise PolicyError("VALIDATION_ERROR", "Advisor cursor is invalid.", 422)
            query = query.where(
                (AdvisorRunRow.created_at < created)
                | ((AdvisorRunRow.created_at == created) & (AdvisorRunRow.id < run_id))
            )
        rows = self.db.scalars(
            query.order_by(AdvisorRunRow.created_at.desc(), AdvisorRunRow.id.desc()).limit(limit)
        )
        return [self._data(row) for row in rows]

    def cancel_run(self, owner, run_id):
        row = self._row(owner, run_id)
        if row.status != "cancelled":
            row.status = "cancelled"
            row.version += 1
            row.updated_at = utc_now()
            self.db.flush()
        return self._data(row)


class SQLAdvisorUnitOfWork:
    """Adds the advisor repository while keeping established SQL UoW semantics."""

    def __init__(self, db):
        self.db = db
        self.base = SQLUnitOfWork(db)
        self.advisor = SQLAdvisorRepository(db)

    def lock_owner(self, owner_id):
        return self.base.lock_owner(owner_id)

    def replay(self, *args):
        return self.base.replay(*args)

    def remember(self, *args):
        return self.base.remember(*args)

    def commit(self):
        return self.base.commit()
