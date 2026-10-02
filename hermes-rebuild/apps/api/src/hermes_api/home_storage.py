"""Independent-session SQL composition adapter for the seven home sections."""

from datetime import date, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .application import serialize
from .catalog import get_method
from .home_ports import HomeReadError
from .quotes_storage import QuoteRepository
from .records_schemas import RecordData
from .records_service import RecordsService
from .records_storage import SQLRecordsRepository
from .storage import SQLUnitOfWork
from .suggestion_service import SuggestionService
from .suggestion_storage import SQLSuggestionUnitOfWork


class SQLHomeReader:
    def __init__(self, engine, *, quote_shuffle=None):
        self.engine = engine
        self.quote_shuffle = quote_shuffle

    def read_section(self, owner_id, timezone, today, section, now):
        try:
            return self._read_section(owner_id, timezone, today, section, now)
        except SQLAlchemyError:
            raise HomeReadError from None

    def _read_section(self, owner_id, timezone, today, section, now):
        with Session(self.engine) as db:
            if section == "quote":
                value = QuoteRepository(db, now=lambda: now, shuffle=self.quote_shuffle).today(
                    owner_id, timezone
                )
                db.commit()
                return value, None
            if section == "subjects":
                from sqlalchemy import select

                from .catalog import subject_group_label
                from .storage import Subject

                items = [
                    {"id": row.id, "name": row.name, "group_label": subject_group_label(row.name)}
                    for row in db.scalars(
                        select(Subject).where(Subject.owner_id == owner_id).order_by(Subject.name)
                    )
                ]
                return {"items": items}, None
            if section == "continue_learning":
                from sqlalchemy import exists, func, or_, select

                from .storage import ProblemAttemptRow, SessionReflectionRow, SessionRow

                sessions = SQLUnitOfWork(db).sessions
                current = sessions.current(owner_id)
                has_attempt = exists(
                    select(ProblemAttemptRow.id).where(
                        ProblemAttemptRow.owner_id == owner_id,
                        ProblemAttemptRow.session_id == SessionRow.id,
                    )
                )
                has_reflection_content = exists(
                    select(SessionReflectionRow.id).where(
                        SessionReflectionRow.owner_id == owner_id,
                        SessionReflectionRow.session_id == SessionRow.id,
                        or_(
                            func.length(func.trim(func.coalesce(SessionReflectionRow.summary, "")))
                            > 0,
                            func.length(
                                func.trim(func.coalesce(SessionReflectionRow.recalled_text, ""))
                            )
                            > 0,
                            func.length(
                                func.trim(func.coalesce(SessionReflectionRow.missing_parts, ""))
                            )
                            > 0,
                            func.length(
                                func.trim(func.coalesce(SessionReflectionRow.stuck_note, ""))
                            )
                            > 0,
                        ),
                    )
                )
                last_id = db.scalar(
                    select(SessionRow.id)
                    .where(
                        SessionRow.owner_id == owner_id,
                        SessionRow.status == "ended",
                        or_(
                            func.length(func.trim(func.coalesce(SessionRow.resume_note, ""))) > 0,
                            has_attempt,
                            has_reflection_content,
                        ),
                    )
                    .order_by(SessionRow.started_at.desc(), SessionRow.id.desc())
                    .limit(1)
                )
                last = None
                if last_id:
                    session = sessions.get(owner_id, last_id)
                    record, record_revision = RecordsService(
                        _RecordsUnitOfWork(SQLRecordsRepository(db)), clock=lambda: now
                    ).record_projection(
                        owner_id,
                        timezone,
                        date.fromisoformat(session.learning_date),
                        last_id,
                    )
                    last = RecordData(**record).model_dump(mode="json") if record else None
                else:
                    record_revision = None
                return {
                    "current": serialize(current) if current else None,
                    "last": last,
                }, _revision(
                    [
                        {"id": current.id, "version": current.version} if current else None,
                        record_revision,
                    ]
                )
            if section in {"suggestions", "review"}:
                service = SuggestionService(SQLSuggestionUnitOfWork(db), clock=lambda: now)
                kinds = (
                    ("unverified", "repeated_error") if section == "suggestions" else ("review",)
                )
                pages = [
                    service.list(owner_id, kind=kind, status="available", limit=4) for kind in kinds
                ]
                selected = [item for page in pages for item in page["items"]]
                selected.sort(key=lambda item: (item["generated_at"], item["id"]), reverse=True)
                items = selected[:3]
                return {
                    "items": items,
                    "has_more": len(selected) > len(items)
                    or any(page["next_cursor"] is not None for page in pages),
                }, _revision([item["source_revision"] for item in selected])
            if section == "methods":
                items = [
                    {
                        "id": method_id,
                        "title": method.title,
                        "summary": method.summary,
                        "content_version": method.content_version,
                    }
                    for method_id in ("active-recall", "practice-feedback", "spaced-review")
                    if (method := get_method(method_id)) is not None
                ]
                data = {"items": items}
                return data, _revision(data)
            if section == "changes":
                start, end = today - timedelta(days=6), today
                data = RecordsService(
                    _RecordsUnitOfWork(SQLRecordsRepository(db)), clock=lambda: now
                ).changes_range(owner_id, timezone, start, end)
                return data, data["source_revision"]
            raise ValueError(f"Unknown home section: {section}")


class _RecordsUnitOfWork:
    def __init__(self, records):
        self.records = records


def _revision(value):
    import hashlib
    import json

    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
