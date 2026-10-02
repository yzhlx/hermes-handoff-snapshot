"""Persist derived suggestions and user handling state."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suggestions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("subject_id", sa.String(36)),
        sa.Column("knowledge_point_id", sa.String(36)),
        sa.Column("problem_id", sa.String(36)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_refs", sa.Text(), nullable=False),
        sa.Column("source_revision", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("snoozed_until", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("owner_id", "fingerprint", name="uq_suggestions_owner_fingerprint"),
    )
    op.create_index("ix_suggestions_owner_status_id", "suggestions", ["owner_id", "status", "id"])


def downgrade():
    op.drop_index("ix_suggestions_owner_status_id", table_name="suggestions")
    op.drop_table("suggestions")
