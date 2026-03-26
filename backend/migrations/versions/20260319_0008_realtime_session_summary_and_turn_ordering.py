"""realtime session summary and turn ordering

Revision ID: 20260319_0008
Revises: 20260319_0007
Create Date: 2026-03-19 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0008"
down_revision = "20260319_0007"
branch_labels = None
depends_on = None


def _backfill_realtime_session_state() -> None:
    bind = op.get_bind()
    session_ids = [
        row.id
        for row in bind.execute(sa.text("SELECT id FROM realtime_sessions")).mappings().all()
    ]

    for session_id in session_ids:
        ordered_turn_ids = [
            row.id
            for row in bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM realtime_session_turns
                    WHERE session_id = :session_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"session_id": session_id},
            ).mappings()
        ]

        for index, turn_id in enumerate(ordered_turn_ids, start=1):
            bind.execute(
                sa.text(
                    """
                    UPDATE realtime_session_turns
                    SET turn_index = :turn_index
                    WHERE id = :turn_id
                    """
                ),
                {"turn_index": index, "turn_id": turn_id},
            )

        turn_count = len(ordered_turn_ids)
        next_turn_index = turn_count + 1
        last_user_turn_at = bind.execute(
            sa.text(
                """
                SELECT created_at
                FROM realtime_session_turns
                WHERE session_id = :session_id
                  AND speaker = 'user'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"session_id": session_id},
        ).scalar_one_or_none()
        last_assistant_turn_at = bind.execute(
            sa.text(
                """
                SELECT created_at
                FROM realtime_session_turns
                WHERE session_id = :session_id
                  AND speaker = 'assistant'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"session_id": session_id},
        ).scalar_one_or_none()
        alert_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM realtime_session_alerts
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id},
        ).scalar_one()
        last_alert_severity = bind.execute(
            sa.text(
                """
                SELECT severity
                FROM realtime_session_alerts
                WHERE session_id = :session_id
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"session_id": session_id},
        ).scalar_one_or_none()

        bind.execute(
            sa.text(
                """
                UPDATE realtime_sessions
                SET next_turn_index = :next_turn_index,
                    last_user_turn_at = :last_user_turn_at,
                    last_assistant_turn_at = :last_assistant_turn_at,
                    turn_count = :turn_count,
                    alert_count = :alert_count,
                    last_alert_severity = :last_alert_severity
                WHERE id = :session_id
                """
            ),
            {
                "next_turn_index": next_turn_index,
                "last_user_turn_at": last_user_turn_at,
                "last_assistant_turn_at": last_assistant_turn_at,
                "turn_count": turn_count,
                "alert_count": alert_count,
                "last_alert_severity": last_alert_severity,
                "session_id": session_id,
            },
        )


def upgrade() -> None:
    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.add_column(sa.Column("next_turn_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_user_turn_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("last_assistant_turn_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("turn_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("alert_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_alert_severity", sa.String(length=32), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE realtime_sessions
            SET next_turn_index = 1,
                turn_count = 0,
                alert_count = 0
            WHERE next_turn_index IS NULL
            """
        )
    )

    _backfill_realtime_session_state()

    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.alter_column("next_turn_index", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("turn_count", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("alert_count", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("realtime_session_turns") as batch_op:
        batch_op.create_unique_constraint(
            "uq_realtime_session_turns_session_id_turn_index",
            ["session_id", "turn_index"],
        )


def downgrade() -> None:
    with op.batch_alter_table("realtime_session_turns") as batch_op:
        batch_op.drop_constraint(
            "uq_realtime_session_turns_session_id_turn_index",
            type_="unique",
        )

    with op.batch_alter_table("realtime_sessions") as batch_op:
        batch_op.drop_column("last_alert_severity")
        batch_op.drop_column("alert_count")
        batch_op.drop_column("turn_count")
        batch_op.drop_column("last_assistant_turn_at")
        batch_op.drop_column("last_user_turn_at")
        batch_op.drop_column("next_turn_index")
