"""Account data sovereignty: exports and the deletion lifecycle (03 §9).

An export is a private, short-lived package of the owner's own records plus a
manifest and a data dictionary. A deletion request is an explicit, two-step,
revocable state: pending -> cancelled, or pending -> completed with a tombstone.
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.create_table(
        "account_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("byte_size", sa.Integer()),
        sa.Column("sha256", sa.String(64)),
        sa.Column("record_counts", sa.Text()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_account_export_owner_id"),
        sa.CheckConstraint(
            "status IN ('ready','failed','expired')", name="ck_account_export_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_account_export_version"),
    )
    op.create_index("ix_account_exports_owner_id", "account_exports", ["owner_id"])
    op.create_index(
        "ix_account_exports_owner_created", "account_exports", ["owner_id", "created_at", "id"]
    )
    op.create_table(
        "account_deletions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("confirmation", sa.String(40), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_account_deletion_owner_id"),
        sa.CheckConstraint(
            "status IN ('pending','cancelled','completed')", name="ck_account_deletion_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_account_deletion_version"),
    )
    op.create_index("ix_account_deletions_owner_id", "account_deletions", ["owner_id"])
    # At most one pending request per account.
    op.create_index(
        "uq_account_deletion_pending",
        "account_deletions",
        ["owner_id"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade():
    op.drop_index("uq_account_deletion_pending", table_name="account_deletions")
    op.drop_index("ix_account_deletions_owner_id", table_name="account_deletions")
    op.drop_table("account_deletions")
    op.drop_index("ix_account_exports_owner_created", table_name="account_exports")
    op.drop_index("ix_account_exports_owner_id", table_name="account_exports")
    op.drop_table("account_exports")
    op.drop_column("users", "status")
