"""hardware demo logs

Revision ID: 20260324_0010
Revises: 20260319_0009
Create Date: 2026-03-24 12:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0010"
down_revision = "20260319_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("review_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title_text", sa.Text(), nullable=False),
        sa.Column("detail_text", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name="fk_device_logs_device_id_devices"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name="fk_device_logs_review_id_reviews"),
        sa.PrimaryKeyConstraint("id", name="pk_device_logs"),
    )
    op.create_index("ix_device_logs_device_id", "device_logs", ["device_id"], unique=False)
    op.create_index("ix_device_logs_review_id", "device_logs", ["review_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_device_logs_review_id", table_name="device_logs")
    op.drop_index("ix_device_logs_device_id", table_name="device_logs")
    op.drop_table("device_logs")
