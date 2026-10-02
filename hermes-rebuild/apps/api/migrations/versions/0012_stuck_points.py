"""Persist first-class learning stuck points with an open/resolved lifecycle.

A stuck point is one sentence about where the learner actually got stuck. It is
its own record (not only a free-text field on an attempt or a session
reflection) so it can be listed, filtered and resolved independently, and so a
source attempt is never counted twice.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stuck_points",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("attempt_id", sa.String(36)),
        sa.Column("knowledge_point_id", sa.String(36)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_stuck_point_session_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_stuck_point_attempt_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_stuck_point_knowledge_owner",
        ),
        sa.UniqueConstraint("owner_id", "id", name="uq_stuck_point_owner_id"),
        sa.CheckConstraint("status IN ('open','resolved')", name="ck_stuck_point_status"),
        sa.CheckConstraint("version >= 1", name="ck_stuck_point_version"),
        sa.CheckConstraint("length(trim(coalesce(text,''))) > 0", name="ck_stuck_point_text"),
        sa.CheckConstraint(
            "(status = 'resolved') = (resolved_at IS NOT NULL)",
            name="ck_stuck_point_resolved_at",
        ),
    )
    op.create_index("ix_stuck_points_owner_id", "stuck_points", ["owner_id"])
    op.create_index(
        "ix_stuck_points_owner_status",
        "stuck_points",
        ["owner_id", "status", "created_at", "id"],
    )
    # A source attempt can be promoted into a stuck point at most once, so the
    # same attempt is never double-counted by derived summaries.
    op.create_index(
        "uq_stuck_point_source_attempt",
        "stuck_points",
        ["owner_id", "attempt_id"],
        unique=True,
        sqlite_where=sa.text("attempt_id IS NOT NULL"),
        postgresql_where=sa.text("attempt_id IS NOT NULL"),
    )


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT count(*) FROM stuck_points")).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade 0012 while stuck points exist; preserve data first.")
    op.drop_index("uq_stuck_point_source_attempt", table_name="stuck_points")
    op.drop_index("ix_stuck_points_owner_status", table_name="stuck_points")
    op.drop_index("ix_stuck_points_owner_id", table_name="stuck_points")
    op.drop_table("stuck_points")
