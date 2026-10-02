"""Let the learner correct implausible timer spans (03 §3).

The contract requires timer segments to show spans the user can correct, so
overnight or idle time is never silently counted as study. A correction may
only shorten or exclude a span, never extend it, and the original end time is
kept so the change stays auditable.
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("session_time_segments", sa.Column("excluded_at", sa.DateTime(timezone=True)))
    op.add_column(
        "session_time_segments", sa.Column("original_ended_at", sa.DateTime(timezone=True))
    )
    op.add_column("session_time_segments", sa.Column("correction_note", sa.Text()))


def downgrade():
    op.drop_column("session_time_segments", "correction_note")
    op.drop_column("session_time_segments", "original_ended_at")
    op.drop_column("session_time_segments", "excluded_at")
