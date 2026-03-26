"""realtime launch minimal closure

Revision ID: 20260315_0004
Revises: 20260315_0003
Create Date: 2026-03-15 23:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260315_0004"
down_revision = "20260315_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.add_column(sa.Column("simulation_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column("voice_profile_catalog_id", sa.String(length=36), nullable=True)
        )
        batch_op.add_column(sa.Column("setup_revision", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("strategy_for_setup_revision", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("launch_payload_json", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("launch_expires_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.execute(
        sa.text(
            """
            UPDATE realtime_sessions
            SET voice_profile_catalog_id = voice_profile_id,
                session_status = CASE
                    WHEN session_status = 'created' THEN 'pending'
                    WHEN session_status IN ('completed', 'cancelled') THEN 'ended'
                    ELSE session_status
                END
            """
        )
    )

    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.drop_constraint(
            "fk_realtime_sessions_voice_profile_id",
            type_="foreignkey",
        )
        batch_op.drop_column("voice_profile_id")
        batch_op.drop_column("constraint_text")
        batch_op.create_foreign_key(
            "fk_realtime_sessions_simulation_id",
            "simulations",
            ["simulation_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_realtime_sessions_voice_profile_catalog_id",
            "voice_profile_catalog",
            ["voice_profile_catalog_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_realtime_sessions_simulation_id",
            ["simulation_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_realtime_sessions_voice_profile_catalog_id",
            ["voice_profile_catalog_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.add_column(sa.Column("constraint_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("voice_profile_id", sa.String(length=36), nullable=True))
        batch_op.drop_index("ix_realtime_sessions_voice_profile_catalog_id")
        batch_op.drop_index("ix_realtime_sessions_simulation_id")
        batch_op.drop_constraint(
            "fk_realtime_sessions_voice_profile_catalog_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_realtime_sessions_simulation_id",
            type_="foreignkey",
        )

    op.execute(
        sa.text(
            """
            UPDATE realtime_sessions
            SET voice_profile_id = voice_profile_catalog_id,
                session_status = CASE
                    WHEN session_status = 'pending' THEN 'created'
                    WHEN session_status = 'ended' THEN 'completed'
                    ELSE session_status
                END
            """
        )
    )

    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.create_foreign_key(
            "fk_realtime_sessions_voice_profile_id",
            "voice_profile_catalog",
            ["voice_profile_id"],
            ["id"],
        )
        batch_op.drop_column("launch_expires_at")
        batch_op.drop_column("launch_payload_json")
        batch_op.drop_column("strategy_for_setup_revision")
        batch_op.drop_column("setup_revision")
        batch_op.drop_column("voice_profile_catalog_id")
        batch_op.drop_column("simulation_id")
