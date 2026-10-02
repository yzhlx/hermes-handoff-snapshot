"""SQLAlchemy persistence adapter for immutable mastery evidence snapshots."""

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
    UniqueConstraint,
    select,
    update,
)
from sqlalchemy.orm import Session

from .domain import PolicyError, utc_now
from .evidence_domain import (
    RULE_VERSION,
    EvidenceRuleError,
    assessment_status,
    derive_counts,
    source_revision,
    validate_assessment,
)
from .evidence_ports import EvidenceRepository
from .knowledge_storage import (
    ChapterRow,
    KnowledgePointRow,
    ProblemKnowledgeLinkRow,
    SQLKnowledgeRepository,
)
from .storage import (
    AttemptErrorRow,
    Base,
    Operation,
    ProblemAttemptRow,
    ProblemRow,
    User,
)


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class MasteryAssessmentRow(Base):
    __tablename__ = "mastery_assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_mastery_assessment_point_owner",
        ),
        UniqueConstraint("owner_id", "id", name="uq_mastery_assessment_owner_id"),
        Index(
            "ix_mastery_assessments_owner_point_created",
            "owner_id",
            "knowledge_point_id",
            "created_at",
            "id",
        ),
        CheckConstraint(
            "level IN ('unfamiliar','encountered','typical','independent','variant_stable')",
            name="ck_mastery_assessment_level",
        ),
        CheckConstraint("version = 1", name="ck_mastery_assessment_immutable_version"),
        CheckConstraint("knowledge_point_version >= 1", name="ck_mastery_point_version"),
        CheckConstraint(
            "reason IS NULL OR length(reason) <= 2000", name="ck_mastery_reason_length"
        ),
        CheckConstraint(
            "variant_note IS NULL OR length(variant_note) <= 2000",
            name="ck_mastery_variant_note_length",
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    knowledge_point_id = Column(String(36), nullable=False)
    level = Column(String(24), nullable=False)
    reason = Column(Text)
    variant_note = Column(Text)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    knowledge_point_version = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class MasteryEvidenceLinkRow(Base):
    __tablename__ = "mastery_evidence_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "assessment_id"],
            ["mastery_assessments.owner_id", "mastery_assessments.id"],
            name="fk_mastery_evidence_assessment_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_mastery_evidence_attempt_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_mastery_evidence_problem_owner",
        ),
        Index("ix_mastery_evidence_owner_attempt", "owner_id", "attempt_id"),
        CheckConstraint(
            "attempt_version >= 1 AND problem_version >= 1", name="ck_evidence_versions"
        ),
    )
    owner_id = Column(String(36), primary_key=True)
    assessment_id = Column(String(36), primary_key=True)
    attempt_id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), nullable=False)
    attempt_version = Column(Integer, nullable=False)
    problem_version = Column(Integer, nullable=False)
    attempt_snapshot = Column(Text, nullable=False)
    problem_snapshot = Column(Text, nullable=False)


class SQLEvidenceRepository(EvidenceRepository):
    def __init__(self, db: Session):
        self.db = db

    def _point(self, owner_id: str, point_id: str):
        row = self.db.scalar(
            select(KnowledgePointRow).where(
                KnowledgePointRow.owner_id == owner_id,
                KnowledgePointRow.id == point_id,
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        chapter = self.db.scalar(
            select(ChapterRow).where(
                ChapterRow.owner_id == owner_id,
                ChapterRow.id == row.chapter_id,
            )
        )
        return row, chapter

    @staticmethod
    def _source_ref(attempt_id, attempt_version, problem_id, problem_version):
        return {
            "attempt_id": attempt_id,
            "attempt_version": attempt_version,
            "problem_id": problem_id,
            "problem_version": problem_version,
        }

    def _current_attempts(self, owner_id, point_id):
        rows = self.db.execute(
            select(ProblemAttemptRow, ProblemRow)
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
                ProblemAttemptRow.owner_id == owner_id,
                ProblemKnowledgeLinkRow.knowledge_point_id == point_id,
            )
        ).all()
        attempt_ids = [attempt.id for attempt, _problem in rows]
        categories_by_attempt: dict[str, list[str]] = {item: [] for item in attempt_ids}
        if attempt_ids:
            category_rows = self.db.execute(
                select(AttemptErrorRow.attempt_id, AttemptErrorRow.category)
                .where(
                    AttemptErrorRow.owner_id == owner_id,
                    AttemptErrorRow.attempt_id.in_(attempt_ids),
                )
                .order_by(AttemptErrorRow.category)
            )
            for attempt_id, category in category_rows:
                categories_by_attempt[attempt_id].append(category)
        return [
            {
                "id": attempt.id,
                "version": attempt.version,
                "problem_id": problem.id,
                "problem_version": problem.version,
                "independence": attempt.independence,
                "answer_check": attempt.answer_check,
                "result": attempt.result,
                "occurred_at": _iso(attempt.occurred_at),
                "error_categories": categories_by_attempt[attempt.id],
            }
            for attempt, problem in rows
        ]

    def get_knowledge_point_evidence(self, owner_id: str, point_id: str) -> dict:
        point, _chapter = self._point(owner_id, point_id)
        attempts = self._current_attempts(owner_id, point_id)
        counts = derive_counts(attempts)
        refs = counts.pop("source_refs")
        category_items = counts.pop("error_categories")
        streak = counts.pop("recent_checked_streak")

        associations = {
            (row[0], row[1])
            for row in self.db.execute(
                select(
                    ProblemKnowledgeLinkRow.problem_id,
                    ProblemKnowledgeLinkRow.knowledge_point_id,
                ).where(
                    ProblemKnowledgeLinkRow.owner_id == owner_id,
                    ProblemKnowledgeLinkRow.knowledge_point_id == point_id,
                )
            )
        }
        assessment_rows = self.db.scalars(
            select(MasteryAssessmentRow)
            .where(
                MasteryAssessmentRow.owner_id == owner_id,
                MasteryAssessmentRow.knowledge_point_id == point_id,
            )
            .order_by(MasteryAssessmentRow.created_at.desc(), MasteryAssessmentRow.id.desc())
        )
        assessments = []
        for assessment in assessment_rows:
            links = self.db.scalars(
                select(MasteryEvidenceLinkRow)
                .where(
                    MasteryEvidenceLinkRow.owner_id == owner_id,
                    MasteryEvidenceLinkRow.assessment_id == assessment.id,
                )
                .order_by(MasteryEvidenceLinkRow.attempt_id)
            )
            live_links = []
            source_refs = []
            for link in links:
                current_attempt = self.db.scalar(
                    select(ProblemAttemptRow).where(
                        ProblemAttemptRow.owner_id == owner_id,
                        ProblemAttemptRow.id == link.attempt_id,
                    )
                )
                current_problem = self.db.scalar(
                    select(ProblemRow).where(
                        ProblemRow.owner_id == owner_id,
                        ProblemRow.id == link.problem_id,
                    )
                )
                if current_attempt is None or current_problem is None:
                    live_links.append(
                        {
                            "level": assessment.level,
                            "currently_linked": False,
                            "attempt_version": link.attempt_version,
                            "problem_version": link.problem_version,
                            "current_attempt_version": -1,
                            "current_problem_version": -1,
                            "current_answer_check": None,
                            "current_independence": None,
                            "current_result": None,
                        }
                    )
                    source_refs.append(
                        self._source_ref(
                            link.attempt_id,
                            link.attempt_version,
                            link.problem_id,
                            link.problem_version,
                        )
                    )
                    continue
                is_linked = (current_problem.id, point_id) in associations
                live_links.append(
                    {
                        "level": assessment.level,
                        "attempt_version": link.attempt_version,
                        "problem_version": link.problem_version,
                        "current_attempt_version": current_attempt.version,
                        "current_problem_version": current_problem.version,
                        "currently_linked": is_linked,
                        "current_answer_check": current_attempt.answer_check,
                        "current_independence": current_attempt.independence,
                        "current_result": current_attempt.result,
                    }
                )
                source_refs.append(
                    self._source_ref(
                        link.attempt_id, link.attempt_version, link.problem_id, link.problem_version
                    )
                )
            status = assessment_status(live_links)
            message = {
                "unsupported": "自评，暂无已核证据",
                "current": "关联来源当前有效；掌握等级仍是用户自评",
                "stale": "关联来源已变化，原自评仍保留",
            }[status]
            assessments.append(
                {
                    "id": assessment.id,
                    "level": assessment.level,
                    "reason": assessment.reason,
                    "variant_note": assessment.variant_note,
                    "version": assessment.version,
                    "knowledge_point_version": assessment.knowledge_point_version,
                    "created_at": _iso(assessment.created_at),
                    "evidence_status": status,
                    "evidence_message": message,
                    "source_refs": source_refs,
                }
            )
        return {
            "knowledge_point_id": point.id,
            "knowledge_point_version": point.version,
            "rule_version": RULE_VERSION,
            "source_revision": source_revision(refs),
            "counts": counts,
            "recent_checked_streak": streak,
            "error_categories": category_items,
            "source_refs": refs,
            "assessments": assessments,
        }

    def create_assessment(self, owner_id: str, values: dict, point_version: int) -> dict:
        point, chapter = self._point(owner_id, values["knowledge_point_id"])
        if point.version != point_version:
            error = PolicyError("VERSION_CONFLICT", "Record changed; reload before editing.", 409)
            error.current_version = point.version
            error.current = SQLKnowledgeRepository(self.db)._point(point)
            raise error
        if point.archived_at is not None or chapter is None or chapter.archived_at is not None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        ids = values["evidence_attempt_ids"]
        if len(set(ids)) != len(ids):
            raise PolicyError(
                "VALIDATION_ERROR", "Duplicate evidence attempts are not allowed.", 422
            )

        source_rows = []
        for attempt_id in ids:
            attempt = self.db.scalar(
                select(ProblemAttemptRow).where(
                    ProblemAttemptRow.owner_id == owner_id,
                    ProblemAttemptRow.id == attempt_id,
                )
            )
            if attempt is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            problem = self.db.scalar(
                select(ProblemRow).where(
                    ProblemRow.owner_id == owner_id,
                    ProblemRow.id == attempt.problem_id,
                )
            )
            if problem is None:
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            linked = self.db.scalar(
                select(ProblemKnowledgeLinkRow.problem_id).where(
                    ProblemKnowledgeLinkRow.owner_id == owner_id,
                    ProblemKnowledgeLinkRow.problem_id == problem.id,
                    ProblemKnowledgeLinkRow.knowledge_point_id == point.id,
                )
            )
            if linked is None:
                raise PolicyError(
                    "VALIDATION_ERROR",
                    "Evidence problem is not linked to this knowledge point.",
                    422,
                )
            if attempt.answer_check != "checked":
                raise PolicyError(
                    "VALIDATION_ERROR", "Evidence attempts must be checked first.", 422
                )
            categories = list(
                self.db.scalars(
                    select(AttemptErrorRow.category)
                    .where(
                        AttemptErrorRow.owner_id == owner_id,
                        AttemptErrorRow.attempt_id == attempt.id,
                    )
                    .order_by(AttemptErrorRow.category)
                )
            )
            source_rows.append(
                {
                    "id": attempt.id,
                    "version": attempt.version,
                    "problem_id": problem.id,
                    "problem_version": problem.version,
                    "independence": attempt.independence,
                    "answer_check": attempt.answer_check,
                    "result": attempt.result,
                    "occurred_at": _iso(attempt.occurred_at),
                    "error_categories": categories,
                }
            )
        try:
            validate_assessment(values["level"], values.get("variant_note"), source_rows)
        except EvidenceRuleError as exc:
            raise PolicyError("VALIDATION_ERROR", str(exc), 422) from exc

        now = utc_now()
        point.version += 1
        point.updated_at = now
        assessment = MasteryAssessmentRow(
            id=str(uuid4()),
            owner_id=owner_id,
            knowledge_point_id=point.id,
            level=values["level"],
            reason=values.get("reason"),
            variant_note=values.get("variant_note"),
            version=1,
            knowledge_point_version=point.version,
            created_at=now,
        )
        self.db.add(assessment)
        for attempt, snapshot in zip(
            [
                self.db.scalar(
                    select(ProblemAttemptRow).where(
                        ProblemAttemptRow.owner_id == owner_id,
                        ProblemAttemptRow.id == source["id"],
                    )
                )
                for source in source_rows
            ],
            source_rows,
            strict=True,
        ):
            problem = self.db.scalar(
                select(ProblemRow).where(
                    ProblemRow.owner_id == owner_id,
                    ProblemRow.id == snapshot["problem_id"],
                )
            )
            self.db.add(
                MasteryEvidenceLinkRow(
                    owner_id=owner_id,
                    assessment_id=assessment.id,
                    attempt_id=attempt.id,
                    problem_id=problem.id,
                    attempt_version=attempt.version,
                    problem_version=problem.version,
                    attempt_snapshot=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                    problem_snapshot=json.dumps(
                        {
                            "id": problem.id,
                            "version": problem.version,
                            "title": problem.title,
                            "statement": problem.statement,
                            "subject_id": problem.subject_id,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                )
            )
        self.db.flush()
        ref = lambda item: self._source_ref(
            item["id"], item["version"], item["problem_id"], item["problem_version"]
        )
        assessment_data = {
            "id": assessment.id,
            "level": assessment.level,
            "reason": assessment.reason,
            "variant_note": assessment.variant_note,
            "version": 1,
            "knowledge_point_version": point.version,
            "created_at": _iso(now),
            "evidence_status": "current" if source_rows else "unsupported",
            "evidence_message": "关联来源当前有效；掌握等级仍是用户自评"
            if source_rows
            else "自评，暂无已核证据",
            "source_refs": [ref(item) for item in source_rows],
        }
        return {"assessment": assessment_data, "knowledge_point_version": point.version}


class SQLEvidenceUnitOfWork:
    """Evidence transaction adapter; the composition root owns its DB session."""

    def __init__(self, db: Session):
        self.db = db
        self.evidence = SQLEvidenceRepository(db)

    def lock_owner(self, owner_id: str) -> None:
        self.db.execute(update(User).where(User.id == owner_id).values(timezone=User.timezone))

    def replay(self, owner_id: str, operation: str, key: str, fingerprint: str):
        row = self.db.scalar(
            select(Operation).where(
                Operation.owner_id == owner_id,
                Operation.operation == operation,
                Operation.key == key,
            )
        )
        if row is None:
            return None
        if row.fingerprint != fingerprint:
            raise PolicyError("IDEMPOTENCY_CONFLICT", "Operation key was reused.", 409)
        return json.loads(row.response)

    def remember(self, owner_id: str, operation: str, key: str, fingerprint: str, response: dict):
        self.db.add(
            Operation(
                owner_id=owner_id,
                operation=operation,
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(response, ensure_ascii=False),
            )
        )

    def commit(self) -> None:
        self.db.commit()
