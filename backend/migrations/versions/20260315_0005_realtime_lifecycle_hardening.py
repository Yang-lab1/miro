"""realtime lifecycle hardening

Revision ID: 20260315_0005
Revises: 20260315_0004
Create Date: 2026-03-16 00:25:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260315_0005"
down_revision = "20260315_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.add_column(sa.Column("status_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.drop_column("status_reason")
