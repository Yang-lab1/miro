"""realtime review bridge snapshot

Revision ID: 20260319_0009
Revises: 20260319_0008
Create Date: 2026-03-19 21:15:00
"""

import json

from alembic import op
import sqlalchemy as sa


revision = "20260319_0009"
down_revision = "20260319_0008"
branch_labels = None
depends_on = None


def _backfill_review_lines() -> None:
    bind = op.get_bind()
    review_ids = [
        row.review_id
        for row in bind.execute(
            sa.text("SELECT DISTINCT review_id FROM review_lines ORDER BY review_id ASC")
        ).mappings()
    ]

    for review_id in review_ids:
        rows = bind.execute(
            sa.text(
                """
                SELECT id, source_text, issue_key
                FROM review_lines
                WHERE review_id = :review_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"review_id": review_id},
        ).mappings().all()

        for line_index, row in enumerate(rows, start=1):
            alert_issue_keys = [row.issue_key] if row.issue_key else []
            bind.execute(
                sa.text(
                    """
                    UPDATE review_lines
                    SET line_index = :line_index,
                        turn_index = :turn_index,
                        text = :text,
                        alert_issue_keys_json = :alert_issue_keys_json
                    WHERE id = :line_id
                    """
                ),
                {
                    "line_index": line_index,
                    "turn_index": line_index,
                    "text": row.source_text,
                    "alert_issue_keys_json": json.dumps(alert_issue_keys),
                    "line_id": row.id,
                },
            )


def upgrade() -> None:
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.add_column(sa.Column("meeting_type_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("goal_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("voice_style_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("voice_profile_catalog_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("setup_revision", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("strategy_for_setup_revision", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("review_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("overall_assessment", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("metrics_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_reviews_voice_profile_catalog_id",
            "voice_profile_catalog",
            ["voice_profile_catalog_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_reviews_voice_profile_catalog_id",
            ["voice_profile_catalog_id"],
            unique=False,
        )

    op.execute(
        sa.text(
            """
            UPDATE reviews
            SET review_status = 'ready'
            WHERE review_status IS NULL
            """
        )
    )

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column("review_status", existing_type=sa.String(length=32), nullable=False)
        batch_op.create_unique_constraint(
            "uq_reviews_review_source_realtime_session_id",
            ["review_source", "realtime_session_id"],
        )

    with op.batch_alter_table("review_lines") as batch_op:
        batch_op.add_column(sa.Column("line_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("turn_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("alert_issue_keys_json", sa.JSON(), nullable=True))

    _backfill_review_lines()


def downgrade() -> None:
    with op.batch_alter_table("review_lines") as batch_op:
        batch_op.drop_column("alert_issue_keys_json")
        batch_op.drop_column("text")
        batch_op.drop_column("turn_index")
        batch_op.drop_column("line_index")

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_constraint(
            "uq_reviews_review_source_realtime_session_id",
            type_="unique",
        )
        batch_op.drop_index("ix_reviews_voice_profile_catalog_id")
        batch_op.drop_constraint(
            "fk_reviews_voice_profile_catalog_id",
            type_="foreignkey",
        )
        batch_op.drop_column("ended_at")
        batch_op.drop_column("metrics_json")
        batch_op.drop_column("overall_assessment")
        batch_op.drop_column("review_status")
        batch_op.drop_column("strategy_for_setup_revision")
        batch_op.drop_column("setup_revision")
        batch_op.drop_column("voice_profile_catalog_id")
        batch_op.drop_column("voice_style_key")
        batch_op.drop_column("duration_minutes")
        batch_op.drop_column("goal_key")
        batch_op.drop_column("meeting_type_key")
