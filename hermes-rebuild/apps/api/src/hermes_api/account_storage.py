"""Owner-scoped SQL persistence for exports and the deletion lifecycle."""

import hashlib
import json
import secrets
from datetime import UTC, date
from uuid import uuid4

from argon2 import PasswordHasher
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    delete,
    func,
    select,
    text,
)

from .account_domain import (
    NEVER_EXPORTED_TABLES,
    SECRET_COLUMNS,
    build_impact,
    export_expiry,
    purge_after,
)
from .domain import PolicyError, utc_now
from .storage import Base, SQLUnitOfWork, User


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class AccountExportRow(Base):
    __tablename__ = "account_exports"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_account_export_owner_id"),
        CheckConstraint("status IN ('ready','failed','expired')", name="ck_account_export_status"),
        CheckConstraint("version >= 1", name="ck_account_export_version"),
        Index("ix_account_exports_owner_created", "owner_id", "created_at", "id"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String(20), nullable=False)
    payload = Column(Text)
    byte_size = Column(Integer)
    sha256 = Column(String(64))
    record_counts = Column(Text)
    error_code = Column(String(80))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class AccountDeletionRow(Base):
    __tablename__ = "account_deletions"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="uq_account_deletion_owner_id"),
        CheckConstraint(
            "status IN ('pending','cancelled','completed')", name="ck_account_deletion_status"
        ),
        CheckConstraint("version >= 1", name="ck_account_deletion_version"),
        Index(
            "uq_account_deletion_pending",
            "owner_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String(20), nullable=False)
    confirmation = Column(String(40), nullable=False)
    impact = Column(Text, nullable=False)
    purge_after = Column(DateTime(timezone=True), nullable=False)
    cancelled_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


def _exportable_tables():
    """Owner-scoped tables that hold the learner's own content."""
    return [
        table
        for name, table in sorted(Base.metadata.tables.items())
        if "owner_id" in table.columns and name not in NEVER_EXPORTED_TABLES
    ]


# The deletion record is the tombstone: it is what the purge writes, so it is
# the one owner-scoped table the purge must not remove.
PURGE_KEEPS = ("account_deletions",)


def _deletion_order():
    """Child tables before parents, so foreign keys stay satisfied."""
    return [
        table
        for table in reversed(Base.metadata.sorted_tables)
        if "owner_id" in table.columns and table.name not in PURGE_KEEPS
    ]


class SQLAccountRepository:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ reading
    def status(self, owner_id):
        return self.db.scalar(select(User.status).where(User.id == owner_id)) or "active"

    def count_records(self, owner_id):
        counts = {}
        for table in _exportable_tables():
            total = self.db.scalar(
                select(func.count()).select_from(table).where(table.c.owner_id == owner_id)
            )
            if total:
                counts[table.name] = int(total)
        return counts

    def export_document(self, owner_id):
        """The owner's own rows, secrets and storage internals removed."""
        document = {
            "format": "hermes-account-export/1",
            "generated_at": utc_now().isoformat(),
            "owner_id": owner_id,
            "data_dictionary": {},
            "tables": {},
            "attachment_manifest": [],
        }
        for table in _exportable_tables():
            columns = [c.name for c in table.columns if c.name not in SECRET_COLUMNS]
            rows = self.db.execute(
                select(*[table.c[name] for name in columns]).where(table.c.owner_id == owner_id)
            ).all()
            document["data_dictionary"][table.name] = columns
            document["tables"][table.name] = [
                {
                    # `datetime` is a `date` subclass, so this covers both the
                    # timestamps and the plain dates (for example a daily
                    # quote's local_date and the frozen learning_date).
                    name: (value.isoformat() if isinstance(value, date) else value)
                    for name, value in zip(columns, row)
                }
                for row in rows
            ]
        attachments = Base.metadata.tables["attachments"]
        document["attachment_manifest"] = [
            {
                "id": row.id,
                "original_name": row.original_name,
                "detected_mime": row.detected_mime,
                "byte_size": row.byte_size,
                "sha256": row.sha256,
                "status": row.status,
            }
            for row in self.db.scalars(
                select(attachments).where(attachments.c.owner_id == owner_id)
            )
        ]
        return document

    # ------------------------------------------------------------------ exports
    def _export_data(self, row, counts):
        return {
            "id": row.id,
            "status": row.status,
            "byte_size": row.byte_size,
            "sha256": row.sha256,
            "record_counts": counts,
            "expires_at": _iso(row.expires_at),
            "created_at": _iso(row.created_at),
        }

    def create_export(self, owner_id, data):
        now = utc_now()
        counts = self.count_records(owner_id)
        document = self.export_document(owner_id)
        payload = json.dumps(document, ensure_ascii=False, sort_keys=True)
        row = AccountExportRow(
            id=str(uuid4()),
            owner_id=owner_id,
            version=1,
            status="ready",
            payload=payload,
            byte_size=len(payload.encode("utf-8")),
            sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            record_counts=json.dumps(counts, sort_keys=True),
            error_code=None,
            expires_at=export_expiry(now),
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        data.update(self._export_data(row, counts))
        return data

    def _export_row(self, owner_id, export_id):
        row = self.db.scalar(
            select(AccountExportRow).where(
                AccountExportRow.owner_id == owner_id, AccountExportRow.id == export_id
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return row

    def get_export(self, owner_id, export_id):
        row = self._export_row(owner_id, export_id)
        return self._export_data(row, json.loads(row.record_counts or "{}"))

    def list_exports(self, owner_id, limit):
        rows = self.db.scalars(
            select(AccountExportRow)
            .where(AccountExportRow.owner_id == owner_id)
            .order_by(AccountExportRow.created_at.desc(), AccountExportRow.id.desc())
            .limit(limit)
        )
        return [self._export_data(row, json.loads(row.record_counts or "{}")) for row in rows]

    def download_export(self, owner_id, export_id):
        row = self._export_row(owner_id, export_id)
        if row.status != "ready":
            raise PolicyError("RESOURCE_GONE", "This export is no longer available.", 410)
        expires = row.expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires is not None and expires <= utc_now():
            row.status = "expired"
            self.db.flush()
            raise PolicyError("RESOURCE_GONE", "This export has expired.", 410)
        return {
            "id": row.id,
            "payload": row.payload or "{}",
            "byte_size": row.byte_size or 0,
            "sha256": row.sha256,
            "expires_at": _iso(row.expires_at),
        }

    # ------------------------------------------------------------------ deletion
    def _deletion_data(self, row, impact):
        return {
            "id": row.id,
            "version": row.version,
            "status": row.status,
            "confirmation": row.confirmation,
            "impact": impact,
            "purge_after": _iso(row.purge_after),
            "cancelled_at": _iso(row.cancelled_at),
            "completed_at": _iso(row.completed_at),
            "created_at": _iso(row.created_at),
        }

    def pending_deletion(self, owner_id):
        row = self.db.scalar(
            select(AccountDeletionRow).where(
                AccountDeletionRow.owner_id == owner_id, AccountDeletionRow.status == "pending"
            )
        )
        if row is None:
            return None
        return self._deletion_data(row, json.loads(row.impact))

    def latest_deletion(self, owner_id):
        row = self.db.scalar(
            select(AccountDeletionRow)
            .where(AccountDeletionRow.owner_id == owner_id)
            .order_by(AccountDeletionRow.created_at.desc(), AccountDeletionRow.id.desc())
        )
        if row is None:
            return None
        return self._deletion_data(row, json.loads(row.impact))

    def create_deletion(self, owner_id, data):
        if self.pending_deletion(owner_id) is not None:
            raise PolicyError(
                "DELETION_ALREADY_PENDING", "A deletion request is already pending.", 409
            )
        now = utc_now()
        impact = build_impact(self.count_records(owner_id))
        row = AccountDeletionRow(
            id=str(uuid4()),
            owner_id=owner_id,
            version=1,
            status="pending",
            confirmation=data["confirmation"],
            impact=json.dumps(impact, ensure_ascii=False),
            purge_after=purge_after(now),
            cancelled_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        self.db.execute(
            User.__table__.update().where(User.id == owner_id).values(status="deletion_pending")
        )
        self.db.flush()
        data.update(self._deletion_data(row, impact))
        return data

    def _pending_row(self, owner_id, version):
        row = self.db.scalar(
            select(AccountDeletionRow).where(
                AccountDeletionRow.owner_id == owner_id, AccountDeletionRow.status == "pending"
            )
        )
        if row is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "No pending deletion request.", 404)
        if version is not None and row.version != version:
            error = PolicyError(
                "VERSION_CONFLICT", "Deletion request changed; reload before editing.", 409
            )
            error.current_version = row.version
            raise error
        return row

    def cancel_deletion(self, owner_id, version):
        row = self._pending_row(owner_id, version)
        row.status = "cancelled"
        row.cancelled_at = utc_now()
        row.version += 1
        row.updated_at = utc_now()
        self.db.execute(User.__table__.update().where(User.id == owner_id).values(status="active"))
        self.db.flush()
        return self._deletion_data(row, json.loads(row.impact))

    def complete_deletion(self, owner_id, version):
        """Purge the owner's own data and keep a minimal tombstone."""
        row = self._pending_row(owner_id, version)
        removed = self.purge(owner_id)
        row.impact = json.dumps(
            {
                "total_records": 0,
                "by_table": {},
                "purged": removed,
                "note": "本次删除已完成，学习内容已清除。",
            },
            ensure_ascii=False,
        )
        row.status = "completed"
        row.completed_at = utc_now()
        row.version += 1
        row.updated_at = utc_now()
        # Revoke the credential by replacing the hash with one for a random
        # secret, and free the username. The row itself stays: it is the
        # minimal tombstone that stops already-deleted data from reappearing.
        self.db.execute(
            User.__table__.update()
            .where(User.id == owner_id)
            .values(
                status="deleted",
                username=f"deleted:{uuid4().hex}",
                password_hash=PasswordHasher().hash(secrets.token_urlsafe(32)),
            )
        )
        self.db.flush()
        return self._deletion_data(row, json.loads(row.impact))

    def purge(self, owner_id):
        """Delete every owner-scoped row, children first."""
        removed = {}
        for table in _deletion_order():
            result = self.db.execute(delete(table).where(table.c.owner_id == owner_id))
            if result.rowcount:
                removed[table.name] = int(result.rowcount)
        self.db.flush()
        return removed


class SQLAccountUnitOfWork:
    """Adds the account repository while keeping established UoW semantics."""

    def __init__(self, db):
        self.db = db
        self.base = SQLUnitOfWork(db)
        self.account = SQLAccountRepository(db)

    def lock_owner(self, owner_id):
        return self.base.lock_owner(owner_id)

    def replay(self, *args):
        return self.base.replay(*args)

    def remember(self, *args):
        return self.base.remember(*args)

    def commit(self):
        return self.base.commit()
