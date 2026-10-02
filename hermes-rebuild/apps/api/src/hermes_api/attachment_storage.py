"""Private attachment and durable processing metadata."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .storage import Base


class AttachmentRow(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_attachments_owner"),
        UniqueConstraint("owner_id", "id", name="uq_attachments_owner_id"),
        UniqueConstraint("storage_key", name="uq_attachments_storage_key"),
        CheckConstraint("version >= 1", name="ck_attachments_version"),
        CheckConstraint("byte_size IS NULL OR byte_size > 0", name="ck_attachments_size"),
        CheckConstraint(
            "status IN ('pending_upload','uploaded','validating','ready','rejected','expired')",
            name="ck_attachments_status",
        ),
        Index("ix_attachments_owner_status", "owner_id", "status", "created_at"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    storage_key = Column(String(128), nullable=False)
    original_name = Column(String(255), nullable=False)
    declared_mime = Column(String(100), nullable=False)
    detected_mime = Column(String(100))
    byte_size = Column(Integer)
    declared_size = Column(Integer, nullable=False)
    expected_sha256 = Column(String(64))
    sha256 = Column(String(64))
    page_count = Column(Integer)
    status = Column(String(24), nullable=False)
    failure_code = Column(String(64))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class AttachmentJobRow(Base):
    __tablename__ = "attachment_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            name="fk_attachment_jobs_attachment_owner",
        ),
        CheckConstraint("kind IN ('validate','preview')", name="ck_attachment_jobs_kind"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="ck_attachment_jobs_status"
        ),
        CheckConstraint("attempt_count >= 0", name="ck_attachment_jobs_attempts"),
        Index("ix_attachment_jobs_claim", "status", "available_at"),
        Index("ix_attachment_jobs_owner_attachment", "owner_id", "attachment_id", "created_at"),
    )
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    attachment_id = Column(String(36), nullable=False)
    kind = Column(String(24), nullable=False)
    status = Column(String(20), nullable=False)
    input_version = Column(Integer, nullable=False)
    page = Column(Integer)
    attempt_count = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime(timezone=True), nullable=False)
    locked_at = Column(DateTime(timezone=True))
    lease_token = Column(String(36))
    completed_at = Column(DateTime(timezone=True))
    error_code = Column(String(64))
    result_json = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ProblemAttachmentLinkRow(Base):
    __tablename__ = "problem_attachment_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_problem_attachment_problem_owner",
        ),
        ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            name="fk_problem_attachment_attachment_owner",
        ),
        UniqueConstraint(
            "owner_id",
            "problem_id",
            "attachment_id",
            "role",
            "page_start",
            "page_end",
            name="uq_problem_attachment_scope",
        ),
        CheckConstraint(
            "role IN ('question','attempt','answer','source')", name="ck_problem_attachment_role"
        ),
        CheckConstraint(
            "(page_start IS NULL AND page_end IS NULL) OR (page_start > 0 AND page_end >= page_start)",
            name="ck_problem_attachment_pages",
        ),
        Index("ix_problem_attachment_owner_problem", "owner_id", "problem_id"),
    )
    link_id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False)
    problem_id = Column(String(36), nullable=False)
    attachment_id = Column(String(36), nullable=False)
    role = Column(String(20), nullable=False)
    page_start = Column(Integer)
    page_end = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False)
