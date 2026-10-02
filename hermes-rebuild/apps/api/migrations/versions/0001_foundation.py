"""Initial foundation schema; no legacy data is accessed."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
    )
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("csrf", sa.String(80), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_subject_owner_id"),
    )
    op.create_index("ix_subjects_owner_id", "subjects", ["owner_id"])
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("goal", sa.Text()),
        sa.Column("subject_id", sa.String(36)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("day_timezone", sa.String(80), nullable=False),
        sa.Column("learning_date", sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_session_subject_owner",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'ended', 'cancelled')", name="ck_session_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_session_version"),
    )
    op.create_index("ix_learning_sessions_owner_id", "learning_sessions", ["owner_id"])
    op.create_index(
        "uq_session_running_owner",
        "learning_sessions",
        ["owner_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('active', 'paused')"),
        postgresql_where=sa.text("status IN ('active', 'paused')"),
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.UniqueConstraint("owner_id", "operation", "key"),
    )


def downgrade():
    for table in ("operations", "learning_sessions", "subjects", "login_sessions", "users"):
        op.drop_table(table)
