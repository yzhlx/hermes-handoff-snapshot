"""SQLAlchemy records and repository operations for public quotes and private choices."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
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

from .domain import PolicyError
from .storage import Base, User


class QuoteRow(Base):
    __tablename__ = "quotes"
    id = Column(String(40), primary_key=True)
    text = Column(Text, nullable=False)
    author = Column(Text)
    enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    content_version = Column(Integer, nullable=False, default=1, server_default="1")


class QuotePreferenceRow(Base):
    __tablename__ = "quote_preferences"
    __table_args__ = (
        ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_quote_pref_quote"),
        UniqueConstraint("owner_id", "quote_id", name="uq_quote_preference_owner_quote"),
        CheckConstraint("version >= 1", name="ck_quote_preference_version"),
        Index("ix_quote_preference_owner_favorite", "owner_id", "favorited", "updated_at"),
        Index("ix_quote_preference_owner_disliked", "owner_id", "disliked", "updated_at"),
    )
    owner_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    quote_id = Column(String(40), primary_key=True)
    text_snapshot = Column(Text, nullable=False)
    favorited = Column(Boolean, nullable=False, default=False, server_default="0")
    disliked = Column(Boolean, nullable=False, default=False, server_default="0")
    version = Column(Integer, nullable=False, default=1, server_default="1")
    updated_at = Column(DateTime(timezone=True), nullable=False)


class QuoteRoundRow(Base):
    __tablename__ = "quote_rounds"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_quote_round_owner_id"),
        UniqueConstraint("owner_id", "round_number", name="uq_quote_round_owner_number"),
        CheckConstraint("round_number >= 1", name="ck_quote_round_number"),
        Index("ix_quote_round_owner", "owner_id", "round_number"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class QuoteQueueRow(Base):
    __tablename__ = "quote_round_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "round_id"],
            ["quote_rounds.owner_id", "quote_rounds.id"],
            name="fk_quote_item_round_owner",
        ),
        ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_quote_item_quote"),
        UniqueConstraint("round_id", "quote_id", name="uq_quote_round_item"),
        UniqueConstraint("round_id", "position", name="uq_quote_round_position"),
        CheckConstraint("position >= 0", name="ck_quote_round_position"),
        Index("ix_quote_round_item_next", "owner_id", "round_id", "consumed_at", "position"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    round_id = Column(String(36), nullable=False)
    quote_id = Column(String(40), nullable=False)
    position = Column(Integer, nullable=False)
    consumed_at = Column(DateTime(timezone=True))


class DailyQuoteRow(Base):
    __tablename__ = "daily_quotes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "round_id"],
            ["quote_rounds.owner_id", "quote_rounds.id"],
            name="fk_daily_quote_round_owner",
        ),
        ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_daily_quote_quote"),
        UniqueConstraint("owner_id", "local_date", name="uq_daily_quote_owner_date"),
        CheckConstraint(
            "(quote_id IS NULL AND quote_text IS NULL) OR (quote_id IS NOT NULL AND quote_text IS NOT NULL)",
            name="ck_daily_quote_snapshot",
        ),
        Index("ix_daily_quote_owner_date", "owner_id", "local_date"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    local_date = Column(Date, nullable=False)
    day_timezone = Column(String(80), nullable=False)
    round_id = Column(String(36), nullable=False)
    quote_id = Column(String(40))
    quote_text = Column(Text)
    reason = Column(String(40))
    created_at = Column(DateTime(timezone=True), nullable=False)


class QuoteOperationRow(Base):
    __tablename__ = "quote_operations"
    __table_args__ = (
        UniqueConstraint("owner_id", "key", name="uq_quote_operation_owner_key"),
        ForeignKeyConstraint(
            ["owner_id", "quote_id"],
            ["quote_preferences.owner_id", "quote_preferences.quote_id"],
            name="fk_quote_operation_preference",
        ),
        Index("ix_quote_operation_owner", "owner_id", "created_at"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    quote_id = Column(String(40), nullable=False)
    key = Column(String(128), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def preference_data(row: QuotePreferenceRow) -> dict:
    return {
        "quote_id": row.quote_id,
        "text": row.text_snapshot,
        "favorited": bool(row.favorited),
        "disliked": bool(row.disliked),
        "version": row.version,
        "updated_at": aware(row.updated_at).isoformat(),
    }


class QuoteRepository:
    """All reads and writes are scoped by owner; daily allocation is serialized per owner."""

    def __init__(self, db: Session, *, now=None, shuffle=None):
        import random

        self.db = db
        self.now = now or (lambda: datetime.now(UTC))
        self.shuffle = shuffle or random.SystemRandom().shuffle

    def lock_owner(self, owner_id: str) -> None:
        # PostgreSQL row lock; SQLite obtains its write reservation before reading queue state.
        self.db.execute(update(User).where(User.id == owner_id).values(timezone=User.timezone))

    def _pref(self, owner_id, quote_id):
        return self.db.scalar(
            select(QuotePreferenceRow).where(
                QuotePreferenceRow.owner_id == owner_id,
                QuotePreferenceRow.quote_id == quote_id,
            )
        )

    def _is_disliked(self, owner_id, quote_id):
        preference = self._pref(owner_id, quote_id)
        return preference is not None and bool(preference.disliked)

    def _current_round(self, owner_id):
        return self.db.scalar(
            select(QuoteRoundRow)
            .where(QuoteRoundRow.owner_id == owner_id)
            .order_by(QuoteRoundRow.round_number.desc())
            .limit(1)
        )

    def _new_round(self, owner_id):
        previous = self._current_round(owner_id)
        number = previous.round_number + 1 if previous else 1
        row = QuoteRoundRow(
            id=str(uuid4()), owner_id=owner_id, round_number=number, created_at=self.now()
        )
        self.db.add(row)
        self.db.flush()
        eligible = list(self.db.scalars(select(QuoteRow).where(QuoteRow.enabled.is_(True))))
        eligible = [quote for quote in eligible if not self._is_disliked(owner_id, quote.id)]
        self.shuffle(eligible)
        self.db.add_all(
            [
                QuoteQueueRow(
                    id=str(uuid4()),
                    owner_id=owner_id,
                    round_id=row.id,
                    quote_id=quote.id,
                    position=index,
                )
                for index, quote in enumerate(eligible)
            ]
        )
        self.db.flush()
        return row

    def _next_quote(self, owner_id):
        round_row = self._current_round(owner_id)
        if round_row is None:
            round_row = self._new_round(owner_id)
        while True:
            pending = list(
                self.db.scalars(
                    select(QuoteQueueRow)
                    .where(
                        QuoteQueueRow.owner_id == owner_id,
                        QuoteQueueRow.round_id == round_row.id,
                        QuoteQueueRow.consumed_at.is_(None),
                    )
                    .order_by(QuoteQueueRow.position)
                )
            )
            candidate = None
            for item in pending:
                quote = self.db.get(QuoteRow, item.quote_id)
                if quote and quote.enabled and not self._is_disliked(owner_id, quote.id):
                    candidate = (item, quote)
                    break
            if candidate:
                item, quote = candidate
                item.consumed_at = self.now()
                return round_row, quote
            if not any(
                self.db.scalar(
                    select(QuoteRow.id).where(
                        QuoteRow.id == item.quote_id, QuoteRow.enabled.is_(True)
                    )
                )
                and not self._is_disliked(owner_id, item.quote_id)
                for item in pending
            ):
                eligible = list(self.db.scalars(select(QuoteRow).where(QuoteRow.enabled.is_(True))))
                eligible = [
                    quote for quote in eligible if not self._is_disliked(owner_id, quote.id)
                ]
                if not eligible:
                    return round_row, None
                round_row = self._new_round(owner_id)
                if not eligible:
                    return round_row, None

    def today(self, owner_id: str, timezone_name: str) -> dict:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            local_date = self.now().astimezone(ZoneInfo(timezone_name)).date()
        except (ZoneInfoNotFoundError, ValueError):
            local_date = self.now().astimezone(UTC).date()
        self.lock_owner(owner_id)
        row = self.db.scalar(
            select(DailyQuoteRow).where(
                DailyQuoteRow.owner_id == owner_id, DailyQuoteRow.local_date == local_date
            )
        )
        if row is None:
            round_row, quote = self._next_quote(owner_id)
            row = DailyQuoteRow(
                id=str(uuid4()),
                owner_id=owner_id,
                local_date=local_date,
                day_timezone=timezone_name,
                round_id=round_row.id,
                quote_id=quote.id if quote else None,
                quote_text=quote.text if quote else None,
                reason=None if quote else "no_eligible_quotes",
                created_at=self.now(),
            )
            self.db.add(row)
            self.db.flush()
        pref = self._pref(owner_id, row.quote_id) if row.quote_id else None
        hidden = bool(pref and pref.disliked)
        quote_data = None
        if row.quote_id and not hidden:
            quote_data = {"id": row.quote_id, "text": row.quote_text, "author": None}
        return {
            "daily_quote": {
                "local_date": row.local_date.isoformat(),
                "day_timezone": row.day_timezone,
                "quote": quote_data,
                "reason": "disliked_today" if hidden else row.reason,
                "preference": preference_data(pref) if pref else None,
            }
        }

    def favorites(self, owner_id: str, cursor: str | None, limit: int = 50) -> dict:
        statement = select(QuotePreferenceRow).where(
            QuotePreferenceRow.owner_id == owner_id, QuotePreferenceRow.favorited.is_(True)
        )
        if cursor:
            cursor_row = self._pref(owner_id, cursor)
            if not cursor_row or not cursor_row.favorited:
                raise PolicyError("VALIDATION_ERROR", "Favorites cursor is invalid.", 422)
            statement = statement.where(
                (QuotePreferenceRow.updated_at < cursor_row.updated_at)
                | (
                    (QuotePreferenceRow.updated_at == cursor_row.updated_at)
                    & (QuotePreferenceRow.quote_id < cursor_row.quote_id)
                )
            )
        favorites = list(
            self.db.scalars(
                statement.order_by(
                    QuotePreferenceRow.updated_at.desc(), QuotePreferenceRow.quote_id.desc()
                ).limit(limit + 1)
            )
        )
        has_more = len(favorites) > limit
        items = favorites[:limit]
        disliked = list(
            self.db.scalars(
                select(QuotePreferenceRow)
                .where(
                    QuotePreferenceRow.owner_id == owner_id, QuotePreferenceRow.disliked.is_(True)
                )
                .order_by(QuotePreferenceRow.updated_at.desc(), QuotePreferenceRow.quote_id.desc())
            )
        )
        return {
            "items": [preference_data(row) for row in items],
            "disliked": [preference_data(row) for row in disliked],
            "next_cursor": items[-1].quote_id if has_more and items else None,
        }

    def update_preference(
        self, owner_id, quote_id, body, key, if_match, if_none_match, timezone_name
    ):
        import hashlib
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        self.lock_owner(owner_id)
        quote = self.db.get(QuoteRow, quote_id)
        if quote is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        fingerprint = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        replay = self.db.scalar(
            select(QuoteOperationRow).where(
                QuoteOperationRow.owner_id == owner_id, QuoteOperationRow.key == key
            )
        )
        if replay:
            if replay.quote_id != quote_id or replay.fingerprint != fingerprint:
                raise PolicyError("IDEMPOTENCY_CONFLICT", "Operation key was reused.", 409)
            return json.loads(replay.response)

        current = self._pref(owner_id, quote_id)
        previous_disliked = bool(current and current.disliked)
        if current is None:
            if if_none_match != "*":
                raise PolicyError(
                    "PRECONDITION_REQUIRED", "Use If-None-Match: * for a new preference.", 428
                )
        else:
            try:
                expected = int(if_match.strip('"')) if if_match else None
            except ValueError:
                raise PolicyError(
                    "VALIDATION_ERROR", "If-Match must be a version number.", 422
                ) from None
            if expected is None:
                raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
            if expected != current.version:
                error = PolicyError(
                    "VERSION_CONFLICT", "Quote preference changed; reload before editing.", 409
                )
                error.current_version = current.version
                raise error
        now = self.now()
        if current is None:
            current = QuotePreferenceRow(
                owner_id=owner_id,
                quote_id=quote_id,
                text_snapshot=quote.text,
                favorited=body["favorited"],
                disliked=body["disliked"],
                version=1,
                updated_at=now,
            )
            self.db.add(current)
        else:
            result = self.db.execute(
                update(QuotePreferenceRow)
                .where(
                    QuotePreferenceRow.owner_id == owner_id,
                    QuotePreferenceRow.quote_id == quote_id,
                    QuotePreferenceRow.version == current.version,
                )
                .values(
                    favorited=body["favorited"],
                    disliked=body["disliked"],
                    version=current.version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                raise PolicyError(
                    "VERSION_CONFLICT", "Quote preference changed; reload before editing.", 409
                )
            self.db.refresh(current)
        self.db.flush()
        if previous_disliked and not current.disliked:
            round_row = self._current_round(owner_id)
            if round_row and not self.db.scalar(
                select(QuoteQueueRow.id).where(
                    QuoteQueueRow.owner_id == owner_id,
                    QuoteQueueRow.round_id == round_row.id,
                    QuoteQueueRow.quote_id == quote_id,
                )
            ):
                last_position = self.db.scalar(
                    select(QuoteQueueRow.position)
                    .where(QuoteQueueRow.round_id == round_row.id)
                    .order_by(QuoteQueueRow.position.desc())
                    .limit(1)
                )
                self.db.add(
                    QuoteQueueRow(
                        id=str(uuid4()),
                        owner_id=owner_id,
                        round_id=round_row.id,
                        quote_id=quote_id,
                        position=(last_position + 1) if last_position is not None else 0,
                    )
                )
                self.db.flush()
        response = {"preference": preference_data(current)}
        try:
            local_date = now.astimezone(ZoneInfo(timezone_name)).date()
        except (ZoneInfoNotFoundError, ValueError):
            local_date = now.astimezone(UTC).date()
        daily = self.db.scalar(
            select(DailyQuoteRow).where(
                DailyQuoteRow.owner_id == owner_id, DailyQuoteRow.local_date == local_date
            )
        )
        if daily:
            hidden = daily.quote_id == quote_id and current.disliked
            response["daily_quote"] = {
                "local_date": daily.local_date.isoformat(),
                "day_timezone": daily.day_timezone,
                "quote": None
                if hidden or not daily.quote_id
                else {"id": daily.quote_id, "text": daily.quote_text, "author": None},
                "reason": "disliked_today" if hidden else daily.reason,
                "preference": preference_data(current) if daily.quote_id == quote_id else None,
            }
        self.db.add(
            QuoteOperationRow(
                id=str(uuid4()),
                owner_id=owner_id,
                quote_id=quote_id,
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(response, ensure_ascii=False),
                created_at=now,
            )
        )
        self.db.flush()
        return response
