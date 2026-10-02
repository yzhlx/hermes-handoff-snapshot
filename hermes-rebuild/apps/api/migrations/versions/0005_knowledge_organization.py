"""Add owner-scoped chapters, knowledge points, and problem links."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chapters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_chapters_owner"),
        sa.ForeignKeyConstraint(
            ["owner_id", "subject_id"],
            ["subjects.owner_id", "subjects.id"],
            name="fk_chapters_subject_owner",
        ),
        sa.UniqueConstraint("owner_id", "id", name="uq_chapters_owner_id"),
        sa.UniqueConstraint("owner_id", "id", "subject_id", name="uq_chapters_owner_subject"),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="ck_chapter_name"),
        sa.CheckConstraint("version >= 1", name="ck_chapter_version"),
    )
    op.create_index(
        "ix_chapters_owner_subject", "chapters", ["owner_id", "subject_id", "archived_at"]
    )
    op.create_table(
        "knowledge_points",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_knowledge_points_owner"),
        sa.ForeignKeyConstraint(
            ["owner_id", "chapter_id", "subject_id"],
            ["chapters.owner_id", "chapters.id", "chapters.subject_id"],
            name="fk_knowledge_points_chapter_scope",
        ),
        sa.UniqueConstraint("owner_id", "id", name="uq_knowledge_points_owner_id"),
        sa.UniqueConstraint(
            "owner_id", "id", "subject_id", name="uq_knowledge_points_owner_subject"
        ),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="ck_knowledge_point_name"),
        sa.CheckConstraint("version >= 1", name="ck_knowledge_point_version"),
        sa.CheckConstraint(
            "notes IS NULL OR length(notes) <= 20000", name="ck_knowledge_point_notes"
        ),
    )
    op.create_index(
        "ix_knowledge_points_owner_chapter",
        "knowledge_points",
        ["owner_id", "chapter_id", "archived_at"],
    )
    op.create_table(
        "problem_knowledge_links",
        sa.Column("owner_id", sa.String(36), primary_key=True),
        sa.Column("problem_id", sa.String(36), primary_key=True),
        sa.Column("knowledge_point_id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "problem_id"],
            ["problems.owner_id", "problems.id"],
            name="fk_problem_knowledge_problem_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "knowledge_point_id"],
            ["knowledge_points.owner_id", "knowledge_points.id"],
            name="fk_problem_knowledge_point_owner",
        ),
    )
    op.create_index(
        "ix_problem_knowledge_links_point",
        "problem_knowledge_links",
        ["owner_id", "knowledge_point_id"],
    )
    with op.batch_alter_table("learning_sessions") as batch:
        batch.add_column(sa.Column("knowledge_point_id", sa.String(36)))
        batch.create_foreign_key(
            "fk_session_knowledge_scope",
            "knowledge_points",
            ["owner_id", "subject_id", "knowledge_point_id"],
            ["owner_id", "subject_id", "id"],
        )
        batch.create_check_constraint(
            "ck_session_knowledge_requires_subject",
            "knowledge_point_id IS NULL OR subject_id IS NOT NULL",
        )


def downgrade():
    with op.batch_alter_table("learning_sessions") as batch:
        batch.drop_constraint("ck_session_knowledge_requires_subject", type_="check")
        batch.drop_constraint("fk_session_knowledge_scope", type_="foreignkey")
        batch.drop_column("knowledge_point_id")
    op.drop_index("ix_problem_knowledge_links_point", table_name="problem_knowledge_links")
    op.drop_table("problem_knowledge_links")
    op.drop_index("ix_knowledge_points_owner_chapter", table_name="knowledge_points")
    op.drop_table("knowledge_points")
    op.drop_index("ix_chapters_owner_subject", table_name="chapters")
    op.drop_table("chapters")
