"""realtime turn pipeline stub

Revision ID: 20260319_0007
Revises: 20260316_0006
Create Date: 2026-03-19 10:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0007"
down_revision = "20260316_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("realtime_session_turns") as batch_op:
        batch_op.add_column(sa.Column("turn_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("parent_turn_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            "ix_realtime_session_turns_parent_turn_id",
            ["parent_turn_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_realtime_session_turns_parent_turn_id",
            "realtime_session_turns",
            ["parent_turn_id"],
            ["id"],
        )

    op.execute(
        sa.text(
            """
            UPDATE realtime_session_turns
            SET turn_index = 1
            WHERE turn_index IS NULL
            """
        )
    )

    with op.batch_alter_table("realtime_session_turns") as batch_op:
        batch_op.alter_column("turn_index", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("realtime_session_turns") as batch_op:
        batch_op.drop_constraint(
            "fk_realtime_session_turns_parent_turn_id",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_realtime_session_turns_parent_turn_id")
        batch_op.drop_column("parent_turn_id")
        batch_op.drop_column("turn_index")
