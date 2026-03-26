"""realtime provider runtime

Revision ID: 20260316_0006
Revises: 20260315_0005
Create Date: 2026-03-16 01:25:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_0006"
down_revision = "20260315_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.add_column(sa.Column("provider_mode", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("provider_session_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("provider_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("provider_payload_json", sa.JSON(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE realtime_sessions
            SET provider_mode = 'stub',
                provider_status = CASE
                    WHEN session_status = 'active' THEN 'connected'
                    WHEN session_status = 'ended' THEN 'closed'
                    WHEN session_status = 'failed' THEN 'failed'
                    ELSE 'created'
                END,
                provider_payload_json = launch_payload_json
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.drop_column("provider_payload_json")
        batch_op.drop_column("provider_status")
        batch_op.drop_column("provider_session_id")
        batch_op.drop_column("provider_mode")
