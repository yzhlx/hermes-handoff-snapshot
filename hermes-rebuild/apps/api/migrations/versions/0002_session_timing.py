"""Add optional session timing and persisted timer segments."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "learning_sessions",
        sa.Column("timing_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("learning_sessions", sa.Column("method_id", sa.String(80), nullable=True))
    op.create_index("uq_session_owner_id", "learning_sessions", ["owner_id", "id"], unique=True)
    op.create_table(
        "session_time_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="ck_segment_time_order"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_time_segment_session_owner",
        ),
    )
    op.create_index(
        "ix_time_segment_owner_session",
        "session_time_segments",
        ["owner_id", "session_id"],
    )
    op.create_index(
        "uq_time_segment_open_session",
        "session_time_segments",
        ["session_id"],
        unique=True,
        sqlite_where=sa.text("ended_at IS NULL"),
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade():
    op.drop_index("uq_time_segment_open_session", table_name="session_time_segments")
    op.drop_index("ix_time_segment_owner_session", table_name="session_time_segments")
    op.drop_table("session_time_segments")
    op.drop_index("uq_session_owner_id", table_name="learning_sessions")
    op.drop_column("learning_sessions", "method_id")
    op.drop_column("learning_sessions", "timing_enabled")
