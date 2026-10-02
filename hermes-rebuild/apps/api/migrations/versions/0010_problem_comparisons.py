"""Persist user-authored comparisons between two problems."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "problem_comparisons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("left_problem_id", sa.String(36), nullable=False),
        sa.Column("right_problem_id", sa.String(36), nullable=False),
        sa.Column("left_attempt_id", sa.String(36)),
        sa.Column("right_attempt_id", sa.String(36)),
        sa.Column("conditions", sa.Text()),
        sa.Column("known_values", sa.Text()),
        sa.Column("formulas", sa.Text()),
        sa.Column("entry_point", sa.Text()),
        sa.Column("diagram", sa.Text()),
        sa.Column("boundary", sa.Text()),
        sa.Column("assumptions", sa.Text()),
        sa.Column("conclusion", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_versions", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "left_problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_comparison_left_problem_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "right_problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_comparison_right_problem_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "left_attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_comparison_left_attempt_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "right_attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_comparison_right_attempt_owner",
        ),
        sa.CheckConstraint(
            "left_problem_id != right_problem_id", name="ck_comparison_distinct_problems"
        ),
        sa.CheckConstraint("version >= 1", name="ck_comparison_version"),
    )
    op.create_index("ix_comparisons_owner_id", "problem_comparisons", ["owner_id", "id"])


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT count(*) FROM problem_comparisons")).scalar_one()
    if count:
        raise RuntimeError(
            "Cannot downgrade 0010 while problem comparisons exist; preserve data first."
        )
    op.drop_index("ix_comparisons_owner_id", table_name="problem_comparisons")
    op.drop_table("problem_comparisons")
