"""realtime session observability tables

Revision ID: 20260418_0014
Revises: 20260411_0013
Create Date: 2026-04-18 09:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260418_0014"
down_revision = "20260411_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "realtime_session_observability",
        sa.Column("realtime_session_id", sa.String(length=36), nullable=False),
        sa.Column("doubao_session_id", sa.String(length=128), nullable=True),
        sa.Column("session_status", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voice_ws_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("client_audio_frame_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("client_audio_total_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("server_received_audio_frame_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("server_received_audio_total_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("server_forwarded_audio_frame_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("server_forwarded_audio_total_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_transcript_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assistant_text_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assistant_audio_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assistant_turn_end_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_user_turn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_assistant_turn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column(
            "final_status",
            sa.String(length=64),
            nullable=False,
            server_default="diagnostic_incomplete",
        ),
        sa.Column(
            "root_block_point",
            sa.String(length=64),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["realtime_session_id"],
            ["realtime_sessions.id"],
            name=op.f("fk_realtime_session_observability_realtime_session_id_realtime_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_realtime_session_observability")),
        sa.UniqueConstraint("realtime_session_id", name=op.f("uq_realtime_session_observability_realtime_session_id")),
    )
    op.create_index(
        op.f("ix_realtime_session_observability_realtime_session_id"),
        "realtime_session_observability",
        ["realtime_session_id"],
        unique=False,
    )

    op.create_table(
        "realtime_session_events",
        sa.Column("realtime_session_id", sa.String(length=36), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=True),
        sa.Column("payload_size", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["realtime_session_id"],
            ["realtime_sessions.id"],
            name=op.f("fk_realtime_session_events_realtime_session_id_realtime_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_realtime_session_events")),
        sa.UniqueConstraint(
            "realtime_session_id",
            "sequence_no",
            name="uq_realtime_session_events_session_sequence",
        ),
    )
    op.create_index(
        op.f("ix_realtime_session_events_realtime_session_id"),
        "realtime_session_events",
        ["realtime_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_realtime_session_events_event_time"),
        "realtime_session_events",
        ["event_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_realtime_session_events_source"),
        "realtime_session_events",
        ["source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_realtime_session_events_event_type"),
        "realtime_session_events",
        ["event_type"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO realtime_session_observability (
                id,
                realtime_session_id,
                doubao_session_id,
                session_status,
                started_at,
                ended_at,
                client_connected,
                voice_ws_ready,
                client_audio_frame_count,
                client_audio_total_bytes,
                server_received_audio_frame_count,
                server_received_audio_total_bytes,
                server_forwarded_audio_frame_count,
                server_forwarded_audio_total_bytes,
                user_transcript_event_count,
                assistant_text_event_count,
                assistant_audio_chunk_count,
                assistant_turn_end_count,
                persisted_turn_count,
                last_user_turn_at,
                last_assistant_turn_at,
                error_count,
                last_error_code,
                last_error_message,
                final_status,
                root_block_point,
                created_at,
                updated_at
            )
            SELECT
                id,
                id,
                provider_session_id,
                session_status,
                started_at,
                ended_at,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                turn_count,
                last_user_turn_at,
                last_assistant_turn_at,
                0,
                NULL,
                NULL,
                'diagnostic_incomplete',
                'NONE',
                created_at,
                updated_at
            FROM realtime_sessions
            WHERE NOT EXISTS (
                SELECT 1
                FROM realtime_session_observability o
                WHERE o.realtime_session_id = realtime_sessions.id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_realtime_session_events_event_type"), table_name="realtime_session_events")
    op.drop_index(op.f("ix_realtime_session_events_source"), table_name="realtime_session_events")
    op.drop_index(op.f("ix_realtime_session_events_event_time"), table_name="realtime_session_events")
    op.drop_index(op.f("ix_realtime_session_events_realtime_session_id"), table_name="realtime_session_events")
    op.drop_table("realtime_session_events")
    op.drop_index(
        op.f("ix_realtime_session_observability_realtime_session_id"),
        table_name="realtime_session_observability",
    )
    op.drop_table("realtime_session_observability")
