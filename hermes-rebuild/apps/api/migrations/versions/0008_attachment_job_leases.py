"""Give attachment workers a persisted token for conditional result publication."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("attachment_jobs", sa.Column("lease_token", sa.String(36)))


def downgrade():
    with op.batch_alter_table("attachment_jobs") as batch:
        batch.drop_column("lease_token")
