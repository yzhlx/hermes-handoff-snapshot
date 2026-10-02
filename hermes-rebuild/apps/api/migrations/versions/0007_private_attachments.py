"""Add private attachment metadata, durable jobs, and problem links."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    # Textless questions are now legal when a ready question attachment is linked;
    # the application enforces that invariant in the same transaction as the link.
    with op.batch_alter_table("problems") as batch:
        batch.drop_constraint("ck_problem_has_text", type_="check")
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("storage_key", sa.String(128), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("declared_mime", sa.String(100), nullable=False),
        sa.Column("detected_mime", sa.String(100)),
        sa.Column("byte_size", sa.Integer()),
        sa.Column("declared_size", sa.Integer(), nullable=False),
        sa.Column("expected_sha256", sa.String(64)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("page_count", sa.Integer()),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_attachments_owner"),
        sa.UniqueConstraint("owner_id", "id", name="uq_attachments_owner_id"),
        sa.UniqueConstraint("storage_key", name="uq_attachments_storage_key"),
        sa.CheckConstraint("version >= 1", name="ck_attachments_version"),
        sa.CheckConstraint("byte_size IS NULL OR byte_size > 0", name="ck_attachments_size"),
        sa.CheckConstraint(
            "status IN ('pending_upload','uploaded','validating','ready','rejected','expired')",
            name="ck_attachments_status",
        ),
    )
    op.create_index(
        "ix_attachments_owner_status", "attachments", ["owner_id", "status", "created_at"]
    )
    op.create_table(
        "attachment_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("attachment_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_version", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("result_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            name="fk_attachment_jobs_attachment_owner",
        ),
        sa.CheckConstraint("kind IN ('validate','preview')", name="ck_attachment_jobs_kind"),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="ck_attachment_jobs_status"
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_attachment_jobs_attempts"),
    )
    op.create_index("ix_attachment_jobs_claim", "attachment_jobs", ["status", "available_at"])
    op.create_index(
        "ix_attachment_jobs_owner_attachment",
        "attachment_jobs",
        ["owner_id", "attachment_id", "created_at"],
    )
    op.create_table(
        "problem_attachment_links",
        sa.Column("link_id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("problem_id", sa.String(36), nullable=False),
        sa.Column("attachment_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_problem_attachment_problem_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            name="fk_problem_attachment_attachment_owner",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "problem_id",
            "attachment_id",
            "role",
            "page_start",
            "page_end",
            name="uq_problem_attachment_scope",
        ),
        sa.CheckConstraint(
            "role IN ('question','attempt','answer','source')", name="ck_problem_attachment_role"
        ),
        sa.CheckConstraint(
            "(page_start IS NULL AND page_end IS NULL) OR (page_start > 0 AND page_end >= page_start)",
            name="ck_problem_attachment_pages",
        ),
    )
    op.create_index(
        "ix_problem_attachment_owner_problem",
        "problem_attachment_links",
        ["owner_id", "problem_id"],
    )


def downgrade():
    connection = op.get_bind()
    textless_with_links = connection.execute(
        sa.text(
            "SELECT count(*) FROM problems p JOIN problem_attachment_links l "
            "ON l.owner_id=p.owner_id AND l.problem_id=p.id "
            "WHERE l.role='question' AND length(trim(coalesce(p.statement,'')))=0"
        )
    ).scalar_one()
    if textless_with_links:
        raise RuntimeError(
            "Cannot downgrade attachments while a textless question depends on an attachment."
        )
    with op.batch_alter_table("problems") as batch:
        batch.create_check_constraint(
            "ck_problem_has_text", "length(trim(coalesce(statement,''))) > 0"
        )
    op.drop_index("ix_problem_attachment_owner_problem", table_name="problem_attachment_links")
    op.drop_table("problem_attachment_links")
    op.drop_index("ix_attachment_jobs_owner_attachment", table_name="attachment_jobs")
    op.drop_index("ix_attachment_jobs_claim", table_name="attachment_jobs")
    op.drop_table("attachment_jobs")
    op.drop_index("ix_attachments_owner_status", table_name="attachments")
    op.drop_table("attachments")
