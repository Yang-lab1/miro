"""Make User Twin refreshes idempotent per review."""

import sqlalchemy as sa
from alembic import op

revision = "20260710_0016"
down_revision = "20260710_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_twin_memories",
        sa.Column("last_review_id", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_twin_memories", "last_review_id")
