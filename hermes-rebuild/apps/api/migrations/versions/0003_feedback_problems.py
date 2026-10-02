"""Persist optional session reflections and honest problem attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("learning_sessions", recreate="always") as batch:
        batch.add_column(sa.Column("kind", sa.String(20), nullable=False, server_default="free"))
        batch.add_column(sa.Column("previous_session_id", sa.String(36)))
        batch.add_column(sa.Column("resume_note", sa.Text()))
        batch.create_check_constraint(
            "ck_session_kind", "kind IN ('problem','recall','reading','free')"
        )
        batch.create_foreign_key(
            "fk_session_previous_owner",
            "learning_sessions",
            ["owner_id", "previous_session_id"],
            ["owner_id", "id"],
        )
    op.create_table(
        "session_reflections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("recalled_text", sa.Text()),
        sa.Column("reference_checked", sa.Boolean()),
        sa.Column("missing_parts", sa.Text()),
        sa.Column("stuck_note", sa.Text()),
        sa.Column("resume_note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "session_id", name="uq_reflection_session"),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_reflection_session_owner",
        ),
        sa.CheckConstraint(
            "length(trim(coalesce(summary,''))) + length(trim(coalesce(recalled_text,''))) + length(trim(coalesce(missing_parts,''))) + length(trim(coalesce(stuck_note,''))) > 0",
            name="ck_reflection_has_content",
        ),
    )
    op.create_table(
        "problems",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36)),
        sa.Column("title", sa.String(300)),
        sa.Column("statement", sa.Text()),
        sa.Column("source_note", sa.Text()),
        sa.Column("correct_answer", sa.Text()),
        sa.Column("is_representative", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_problem_owner_id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_problem_owner"),
        sa.ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_problem_subject_owner",
        ),
        sa.CheckConstraint("length(trim(coalesce(statement,''))) > 0", name="ck_problem_has_text"),
    )
    op.create_index("ix_problems_owner_id", "problems", ["owner_id"])
    op.create_table(
        "problem_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("problem_id", sa.String(36), nullable=False),
        sa.Column("independence", sa.String(20), nullable=False),
        sa.Column("answer_check", sa.String(20), nullable=False),
        sa.Column("result", sa.String(20)),
        sa.Column("attempt_text", sa.Text()),
        sa.Column("stuck_note", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_attempt_owner_id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_attempt_owner"),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id"],
            ["learning_sessions.owner_id", "learning_sessions.id"],
            name="fk_attempt_session_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_attempt_problem_owner",
        ),
        sa.CheckConstraint(
            "independence IN ('independent','hinted','after_answer','unable')",
            name="ck_attempt_independence",
        ),
        sa.CheckConstraint(
            "(answer_check = 'pending' AND result IS NULL AND verified_at IS NULL) OR (answer_check = 'checked' AND result IN ('correct','partial','incorrect') AND verified_at IS NOT NULL)",
            name="ck_attempt_check_result",
        ),
    )
    op.create_index("ix_problem_attempts_owner_id", "problem_attempts", ["owner_id"])
    op.create_table(
        "attempt_errors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("note", sa.Text()),
        sa.UniqueConstraint("owner_id", "attempt_id", "category", name="uq_attempt_error_category"),
        sa.ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_attempt_error_owner",
        ),
        sa.CheckConstraint(
            "category IN ('concept','modeling','condition','formula','derivation','calculation','sign','unit','reading','other')",
            name="ck_attempt_error_category",
        ),
    )
    op.create_table(
        "attempt_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_attempt_revision_owner",
        ),
    )
    op.create_index("ix_attempt_revisions_owner_id", "attempt_revisions", ["owner_id"])


def downgrade():
    op.drop_index("ix_attempt_revisions_owner_id", table_name="attempt_revisions")
    op.drop_table("attempt_revisions")
    op.drop_table("attempt_errors")
    op.drop_table("problem_attempts")
    op.drop_index("ix_problems_owner_id", table_name="problems")
    op.drop_table("problems")
    op.drop_table("session_reflections")
    with op.batch_alter_table("learning_sessions", recreate="always") as batch:
        batch.drop_constraint("fk_session_previous_owner", type_="foreignkey")
        batch.drop_constraint("ck_session_kind", type_="check")
        batch.drop_column("resume_note")
        batch.drop_column("previous_session_id")
        batch.drop_column("kind")
