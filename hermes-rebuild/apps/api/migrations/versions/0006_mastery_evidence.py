"""Persist immutable user mastery assessments and source-version snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mastery_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("knowledge_point_id", sa.String(36), nullable=False),
        sa.Column("level", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("variant_note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("knowledge_point_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_mastery_assessment_owner_id"),
        sa.ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_mastery_assessment_point_owner",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_mastery_assessment_user"),
        sa.CheckConstraint(
            "level IN ('unfamiliar','encountered','typical','independent','variant_stable')",
            name="ck_mastery_assessment_level",
        ),
        sa.CheckConstraint("version = 1", name="ck_mastery_assessment_immutable_version"),
        sa.CheckConstraint("knowledge_point_version >= 1", name="ck_mastery_point_version"),
        sa.CheckConstraint(
            "reason IS NULL OR length(reason) <= 2000", name="ck_mastery_reason_length"
        ),
        sa.CheckConstraint(
            "variant_note IS NULL OR length(variant_note) <= 2000",
            name="ck_mastery_variant_note_length",
        ),
    )
    op.create_index("ix_mastery_assessments_owner_id", "mastery_assessments", ["owner_id"])
    op.create_index(
        "ix_mastery_assessments_owner_point_created",
        "mastery_assessments",
        ["owner_id", "knowledge_point_id", "created_at", "id"],
    )

    op.create_table(
        "mastery_evidence_links",
        sa.Column("owner_id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(36), primary_key=True),
        sa.Column("attempt_id", sa.String(36), primary_key=True),
        sa.Column("problem_id", sa.String(36), nullable=False),
        sa.Column("attempt_version", sa.Integer(), nullable=False),
        sa.Column("problem_version", sa.Integer(), nullable=False),
        sa.Column("attempt_snapshot", sa.Text(), nullable=False),
        sa.Column("problem_snapshot", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "assessment_id"],
            ["mastery_assessments.owner_id", "mastery_assessments.id"],
            name="fk_mastery_evidence_assessment_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "attempt_id"],
            ["problem_attempts.owner_id", "problem_attempts.id"],
            name="fk_mastery_evidence_attempt_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_mastery_evidence_problem_owner",
        ),
        sa.CheckConstraint(
            "attempt_version >= 1 AND problem_version >= 1", name="ck_evidence_versions"
        ),
    )
    op.create_index(
        "ix_mastery_evidence_owner_attempt", "mastery_evidence_links", ["owner_id", "attempt_id"]
    )


def downgrade():
    op.drop_index("ix_mastery_evidence_owner_attempt", table_name="mastery_evidence_links")
    op.drop_table("mastery_evidence_links")
    op.drop_index("ix_mastery_assessments_owner_point_created", table_name="mastery_assessments")
    op.drop_index("ix_mastery_assessments_owner_id", table_name="mastery_assessments")
    op.drop_table("mastery_assessments")
