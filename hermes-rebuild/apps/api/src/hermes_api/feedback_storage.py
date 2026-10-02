"""SQLAlchemy repository adapters for feedback facts."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select

from .domain import PolicyError, utc_now
from .storage import (
    AttemptErrorRow,
    AttemptRevisionRow,
    ProblemAttemptRow,
    ProblemRow,
    SessionReflectionRow,
    SessionRow,
    Subject,
)


def iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class SQLFeedbackRepository:
    def __init__(self, db):
        self.db = db

    def _attempt(self, row):
        categories = self.db.scalars(
            select(AttemptErrorRow.category)
            .where(AttemptErrorRow.owner_id == row.owner_id, AttemptErrorRow.attempt_id == row.id)
            .order_by(AttemptErrorRow.category)
        )
        eligible = (
            row.answer_check == "checked"
            and row.independence == "independent"
            and row.result == "correct"
        )
        return {
            "id": row.id,
            "session_id": row.session_id,
            "problem_id": row.problem_id,
            "independence": row.independence,
            "answer_check": row.answer_check,
            "result": row.result,
            "attempt_text": row.attempt_text,
            "stuck_note": row.stuck_note,
            "occurred_at": iso(row.occurred_at),
            "verified_at": iso(row.verified_at),
            "version": row.version,
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
            "error_categories": list(categories),
            "other_error_note": self.db.scalar(
                select(AttemptErrorRow.note).where(
                    AttemptErrorRow.owner_id == row.owner_id,
                    AttemptErrorRow.attempt_id == row.id,
                    AttemptErrorRow.category == "other",
                )
            ),
            "evidence_eligibility": {
                "eligible": eligible,
                "reason": "independent_correct"
                if eligible
                else (
                    "answer_not_checked"
                    if row.answer_check != "checked"
                    else "not_independent_correct"
                ),
            },
        }

    def _problem(self, row, include_attempts=True):
        from .knowledge_storage import ProblemKnowledgeLinkRow

        links = self._attachment_links(row.owner_id, row.id)

        value = {
            "id": row.id,
            "subject_id": row.subject_id,
            "title": row.title,
            "statement": row.statement,
            "source_note": row.source_note,
            "correct_answer": row.correct_answer,
            "is_representative": row.is_representative,
            "archived": row.archived_at is not None,
            "version": row.version,
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
            "knowledge_point_ids": list(
                self.db.scalars(
                    select(ProblemKnowledgeLinkRow.knowledge_point_id).where(
                        ProblemKnowledgeLinkRow.owner_id == row.owner_id,
                        ProblemKnowledgeLinkRow.problem_id == row.id,
                    )
                )
            ),
            "attachment_links": links,
        }
        if include_attempts:
            rows = self.db.scalars(
                select(ProblemAttemptRow)
                .where(
                    ProblemAttemptRow.owner_id == row.owner_id,
                    ProblemAttemptRow.problem_id == row.id,
                )
                .order_by(ProblemAttemptRow.occurred_at, ProblemAttemptRow.id)
            )
            value["attempts"] = [self._attempt(item) for item in rows]
        return value

    def _attachment_links(self, owner, problem_id):
        from .attachment_storage import AttachmentRow, ProblemAttachmentLinkRow

        rows = self.db.execute(
            select(ProblemAttachmentLinkRow, AttachmentRow)
            .join(
                AttachmentRow,
                (AttachmentRow.id == ProblemAttachmentLinkRow.attachment_id)
                & (AttachmentRow.owner_id == ProblemAttachmentLinkRow.owner_id),
            )
            .where(
                ProblemAttachmentLinkRow.owner_id == owner,
                ProblemAttachmentLinkRow.problem_id == problem_id,
            )
            .order_by(ProblemAttachmentLinkRow.created_at, ProblemAttachmentLinkRow.link_id)
        ).all()
        return [
            {
                "link_id": link.link_id,
                "attachment_id": attachment.id,
                "role": link.role,
                "page_start": link.page_start,
                "page_end": link.page_end,
                "original_name": attachment.original_name,
                "detected_mime": attachment.detected_mime,
                "byte_size": attachment.byte_size,
                "status": "ready",
            }
            for link, attachment in rows
        ]

    def _create_attachment_link(self, owner, problem, values):
        from .attachment_storage import AttachmentRow, ProblemAttachmentLinkRow

        attachment = self.db.scalar(
            select(AttachmentRow).where(
                AttachmentRow.owner_id == owner,
                AttachmentRow.id == values["attachment_id"],
            )
        )
        if attachment is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if attachment.status != "ready":
            raise PolicyError("ATTACHMENT_NOT_READY", "Attachment is not ready to link.", 409)
        start, end = values.get("page_start"), values.get("page_end")
        if start is not None:
            page_count = attachment.page_count or (
                1 if attachment.detected_mime != "application/pdf" else 0
            )
            if end is None or end > page_count:
                raise PolicyError("VALIDATION_ERROR", "Attachment page range is invalid.", 422)
        elif end is not None:
            raise PolicyError("VALIDATION_ERROR", "Both page bounds are required.", 422)
        links = list(
            self.db.scalars(
                select(ProblemAttachmentLinkRow).where(
                    ProblemAttachmentLinkRow.owner_id == owner,
                    ProblemAttachmentLinkRow.problem_id == problem.id,
                )
            )
        )
        if len(links) >= 10:
            raise PolicyError("ATTACHMENT_LIMIT", "A problem can have at most 10 attachments.", 422)
        if any(
            link.attachment_id == attachment.id
            and link.role == values["role"]
            and link.page_start == start
            and link.page_end == end
            for link in links
        ):
            raise PolicyError(
                "ATTACHMENT_LINK_EXISTS", "Equivalent attachment link already exists.", 409
            )
        from uuid import uuid4

        link = ProblemAttachmentLinkRow(
            link_id=str(uuid4()),
            owner_id=owner,
            problem_id=problem.id,
            attachment_id=attachment.id,
            role=values["role"],
            page_start=start,
            page_end=end,
            created_at=utc_now(),
        )
        self.db.add(link)
        self.db.flush()
        return next(
            item
            for item in self._attachment_links(owner, problem.id)
            if item["link_id"] == link.link_id
        )

    def _conflict(self, current, snapshot=None):
        error = PolicyError("VERSION_CONFLICT", "Record changed; reload before editing.", 409)
        error.current_version = current
        if snapshot is not None:
            error.current = snapshot
        return error

    def create_reflection(self, owner, values):
        session = self.db.scalar(
            select(SessionRow).where(
                SessionRow.owner_id == owner, SessionRow.id == values["session_id"]
            )
        )
        if session is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if session.status != "ended":
            raise PolicyError(
                "SESSION_NOT_ENDED", "Feedback can be saved after ending the session.", 409
            )
        if self.db.scalar(
            select(SessionReflectionRow.id).where(
                SessionReflectionRow.owner_id == owner,
                SessionReflectionRow.session_id == session.id,
            )
        ):
            raise PolicyError("REFLECTION_EXISTS", "This session already has feedback.", 409)
        now = utc_now()
        row = SessionReflectionRow(
            id=str(uuid4()),
            owner_id=owner,
            session_id=session.id,
            version=1,
            created_at=now,
            updated_at=now,
            **{k: v for k, v in values.items() if k not in ("operation_id", "session_id")},
        )
        self.db.add(row)
        if "resume_note" in values and session.resume_note != values["resume_note"]:
            session.resume_note = values["resume_note"]
            session.version += 1
        self.db.flush()
        return self._reflection(row)

    @staticmethod
    def _reflection(row):
        return {
            "id": row.id,
            "session_id": row.session_id,
            "summary": row.summary,
            "recalled_text": row.recalled_text,
            "reference_checked": row.reference_checked,
            "missing_parts": row.missing_parts,
            "stuck_note": row.stuck_note,
            "resume_note": row.resume_note,
            "version": row.version,
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
        }

    def get_reflection(self, owner, session_id):
        row = self.db.scalar(
            select(SessionReflectionRow).where(
                SessionReflectionRow.owner_id == owner,
                SessionReflectionRow.session_id == session_id,
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._reflection(row)

    def update_reflection(self, owner, session_id, values, version):
        row = self.db.scalar(
            select(SessionReflectionRow).where(
                SessionReflectionRow.owner_id == owner,
                SessionReflectionRow.session_id == session_id,
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row.version, self._reflection(row))
        for key, value in values.items():
            if key != "operation_id":
                setattr(row, key, value)
        if (
            not any((row.summary or "").strip() for _ in [0])
            and not (row.recalled_text or "").strip()
            and not (row.missing_parts or "").strip()
            and not (row.stuck_note or "").strip()
        ):
            raise PolicyError(
                "VALIDATION_ERROR", "Reflection must contain actual learning content.", 422
            )
        row.version += 1
        row.updated_at = utc_now()
        if "resume_note" in values:
            session = self.db.scalar(
                select(SessionRow).where(SessionRow.owner_id == owner, SessionRow.id == session_id)
            )
            if session and session.resume_note != values["resume_note"]:
                session.resume_note = values["resume_note"]
                session.version += 1
        self.db.flush()
        return self._reflection(row)

    def create_problem(self, owner, values):
        if (
            values.get("subject_id")
            and self.db.scalar(
                select(Subject.id).where(
                    Subject.owner_id == owner, Subject.id == values["subject_id"]
                )
            )
            is None
        ):
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        now = utc_now()
        row = ProblemRow(
            id=str(uuid4()),
            owner_id=owner,
            version=1,
            created_at=now,
            updated_at=now,
            is_representative=False,
            **{k: v for k, v in values.items() if k not in ("operation_id", "attachment_links")},
        )
        self.db.add(row)
        self.db.flush()
        for link in values.get("attachment_links", []):
            self._create_attachment_link(owner, row, link)
        if not (row.statement or "").strip() and not any(
            link["role"] == "question" for link in self._attachment_links(owner, row.id)
        ):
            raise PolicyError(
                "VALIDATION_ERROR", "Problem needs statement text or a question attachment.", 422
            )
        return self._problem(row)

    def list_attachment_links(self, owner, problem_id):
        row = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return {"items": self._attachment_links(owner, problem_id), "problem_version": row.version}

    def link_attachment(self, owner, problem_id, values, version):
        row = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row.version, self._problem(row))
        if row.archived_at is not None:
            raise PolicyError(
                "RESOURCE_ARCHIVED", "Archived problems cannot receive attachments.", 409
            )
        link = self._create_attachment_link(owner, row, values)
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return {"link": link, "problem_version": row.version}

    def unlink_attachment(self, owner, problem_id, link_id, version):
        from .attachment_storage import ProblemAttachmentLinkRow

        row = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row.version, self._problem(row))
        link = self.db.scalar(
            select(ProblemAttachmentLinkRow).where(
                ProblemAttachmentLinkRow.owner_id == owner,
                ProblemAttachmentLinkRow.problem_id == problem_id,
                ProblemAttachmentLinkRow.link_id == link_id,
            )
        )
        if link is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if link.role == "question" and not (row.statement or "").strip():
            count = self.db.scalar(
                select(ProblemAttachmentLinkRow.link_id)
                .where(
                    ProblemAttachmentLinkRow.owner_id == owner,
                    ProblemAttachmentLinkRow.problem_id == problem_id,
                    ProblemAttachmentLinkRow.role == "question",
                    ProblemAttachmentLinkRow.link_id != link_id,
                )
                .limit(1)
            )
            if count is None:
                raise PolicyError(
                    "PROBLEM_QUESTION_REQUIRED",
                    "A problem must keep text or a question attachment.",
                    422,
                )
        self.db.delete(link)
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return {"problem_version": row.version}

    def get_problem(self, owner, problem_id):
        row = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._problem(row)

    def list_problems(
        self, owner, subject_id, representative, limit, cursor_id=None, archived=False
    ):
        query = select(ProblemRow).where(
            ProblemRow.owner_id == owner,
            ProblemRow.archived_at.is_not(None) if archived else ProblemRow.archived_at.is_(None),
        )
        if subject_id:
            query = query.where(ProblemRow.subject_id == subject_id)
        if representative is not None:
            query = query.where(ProblemRow.is_representative.is_(representative))
        if cursor_id:
            cursor = self.db.scalar(
                select(ProblemRow).where(
                    ProblemRow.owner_id == owner,
                    ProblemRow.id == cursor_id,
                    ProblemRow.archived_at.is_not(None)
                    if archived
                    else ProblemRow.archived_at.is_(None),
                )
            )
            if (
                cursor is None
                or (subject_id and cursor.subject_id != subject_id)
                or (representative is not None and cursor.is_representative != representative)
            ):
                raise PolicyError("VALIDATION_ERROR", "Problem cursor is invalid.", 422)
            query = query.where(
                (ProblemRow.created_at < cursor.created_at)
                | ((ProblemRow.created_at == cursor.created_at) & (ProblemRow.id < cursor.id))
            )
        return [
            self._problem(row, False)
            for row in self.db.scalars(
                query.order_by(ProblemRow.created_at.desc(), ProblemRow.id.desc()).limit(limit)
            )
        ]

    def update_problem(self, owner, problem_id, values, version):
        row = self.db.scalar(
            select(ProblemRow).where(ProblemRow.owner_id == owner, ProblemRow.id == problem_id)
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row.version, self._problem(row))
        if "archived" in values:
            values["archived_at"] = utc_now() if values.pop("archived") else None
        for key, value in values.items():
            setattr(row, key, value)
        if not (row.statement or "").strip() and not any(
            link["role"] == "question" for link in self._attachment_links(owner, row.id)
        ):
            raise PolicyError(
                "VALIDATION_ERROR",
                "Problem needs statement text or a question attachment.",
                422,
            )
        row.version += 1
        row.updated_at = utc_now()
        self.db.flush()
        return self._problem(row)

    def create_attempt(self, owner, values):
        session = self.db.scalar(
            select(SessionRow).where(
                SessionRow.owner_id == owner, SessionRow.id == values["session_id"]
            )
        )
        problem = self.db.scalar(
            select(ProblemRow).where(
                ProblemRow.owner_id == owner,
                ProblemRow.id == values["problem_id"],
                ProblemRow.archived_at.is_(None),
            )
        )
        if session is None or problem is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        now = utc_now()
        occurred = values.get("occurred_at") or now
        if isinstance(occurred, str):
            occurred = datetime.fromisoformat(occurred)
        if occurred.tzinfo is None:
            raise PolicyError("VALIDATION_ERROR", "Attempt time must include a timezone.", 422)
        occurred = occurred.astimezone(UTC)
        if occurred > now:
            raise PolicyError("VALIDATION_ERROR", "Attempt time cannot be in the future.", 422)
        row = ProblemAttemptRow(
            id=str(uuid4()),
            owner_id=owner,
            session_id=session.id,
            problem_id=problem.id,
            independence=values["independence"],
            answer_check=values["answer_check"],
            result=values.get("result"),
            attempt_text=values.get("attempt_text"),
            stuck_note=values.get("stuck_note"),
            occurred_at=occurred,
            verified_at=now if values["answer_check"] == "checked" else None,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        for category in values.get("error_categories", []):
            self.db.add(
                AttemptErrorRow(
                    id=str(uuid4()),
                    owner_id=owner,
                    attempt_id=row.id,
                    category=category,
                    note=values.get("other_error_note") if category == "other" else None,
                )
            )
        return self._attempt(row)

    def get_attempt(self, owner, attempt_id):
        row = self.db.scalar(
            select(ProblemAttemptRow).where(
                ProblemAttemptRow.owner_id == owner, ProblemAttemptRow.id == attempt_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return self._attempt(row)

    def update_attempt(self, owner, attempt_id, values, version):
        row = self.db.scalar(
            select(ProblemAttemptRow).where(
                ProblemAttemptRow.owner_id == owner, ProblemAttemptRow.id == attempt_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        if row.version != version:
            raise self._conflict(row.version, self._attempt(row))
        old = self._attempt(row)
        from pydantic import ValidationError

        from .feedback import AttemptFeedback

        combined = {
            "independence": values.get("independence", row.independence),
            "answer_check": values.get("answer_check", row.answer_check),
            "result": values.get("result", row.result),
            "error_categories": values.get("error_categories", old["error_categories"]),
            "attempt_text": values.get("attempt_text", row.attempt_text),
            "stuck_note": values.get("stuck_note", row.stuck_note),
            "other_error_note": values.get("other_error_note", old["other_error_note"]),
        }
        try:
            validated = AttemptFeedback.model_validate(combined)
        except ValidationError as exc:
            raise PolicyError("VALIDATION_ERROR", "Attempt feedback is inconsistent.", 422) from exc
        now = utc_now()
        facts_changed = (
            validated.answer_check.value != old["answer_check"]
            or (validated.result.value if validated.result is not None else None) != old["result"]
        )
        categories = [item.value for item in validated.error_categories]
        for key in ("independence", "answer_check", "result", "attempt_text", "stuck_note"):
            setattr(
                row,
                key,
                getattr(validated, key).value
                if key in ("independence", "answer_check", "result")
                and getattr(validated, key) is not None
                else getattr(validated, key),
            )
        if row.answer_check != "checked":
            row.verified_at = None
        elif facts_changed:
            row.verified_at = now
        if row.answer_check != "checked":
            row.result = None
        row.version += 1
        row.updated_at = now
        self.db.add(
            AttemptRevisionRow(
                id=str(uuid4()),
                owner_id=owner,
                attempt_id=row.id,
                version=old["version"],
                snapshot=json.dumps(old),
                changed_at=now,
            )
        )
        if "error_categories" in values or "other_error_note" in values:
            self.db.execute(
                delete(AttemptErrorRow).where(
                    AttemptErrorRow.owner_id == owner, AttemptErrorRow.attempt_id == row.id
                )
            )
            for category in categories:
                self.db.add(
                    AttemptErrorRow(
                        id=str(uuid4()),
                        owner_id=owner,
                        attempt_id=row.id,
                        category=category,
                        note=(
                            values.get("other_error_note", old["other_error_note"])
                            if category == "other"
                            else None
                        ),
                    )
                )
        self.db.flush()
        return self._attempt(row)
