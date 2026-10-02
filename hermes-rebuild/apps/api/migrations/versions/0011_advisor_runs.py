"""Persist optional AI advisor analyses with their evidence snapshot."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "advisor_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("topic", sa.Text()),
        sa.Column("subject_id", sa.String(36)),
        sa.Column("knowledge_point_id", sa.String(36)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("degradation_reason", sa.Text()),
        sa.Column("facts", sa.Text(), nullable=False),
        sa.Column("inferences", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("evidence_refs", sa.Text(), nullable=False),
        sa.Column("data_version", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("rule_version", sa.String(80), nullable=False),
        sa.Column("externally_hosted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_advisor_run_owner_id"),
        sa.CheckConstraint(
            "status IN ('ready','insufficient','degraded','blocked','cancelled')",
            name="ck_advisor_run_status",
        ),
        sa.CheckConstraint("evidence_count >= 0", name="ck_advisor_run_evidence_count"),
        sa.CheckConstraint("version >= 1", name="ck_advisor_run_version"),
    )
    op.create_index("ix_advisor_runs_owner_id", "advisor_runs", ["owner_id"])
    op.create_index(
        "ix_advisor_runs_owner_created", "advisor_runs", ["owner_id", "created_at", "id"]
    )


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT count(*) FROM advisor_runs")).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade 0011 while advisor runs exist; preserve data first.")
    op.drop_index("ix_advisor_runs_owner_created", table_name="advisor_runs")
    op.drop_index("ix_advisor_runs_owner_id", table_name="advisor_runs")
    op.drop_table("advisor_runs")
