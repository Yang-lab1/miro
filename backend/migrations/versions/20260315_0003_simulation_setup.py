"""simulation setup

Revision ID: 20260315_0003
Revises: 20260315_0002
Create Date: 2026-03-15 20:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260315_0003"
down_revision = "20260315_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("meeting_type_key", sa.String(length=64), nullable=True),
        sa.Column("goal_key", sa.String(length=64), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("voice_style_key", sa.String(length=64), nullable=True),
        sa.Column("voice_profile_catalog_id", sa.String(length=36), nullable=True),
        sa.Column("constraints_text", sa.Text(), nullable=True),
        sa.Column("simulation_status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("setup_revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("strategy_payload_json", sa.JSON(), nullable=True),
        sa.Column("strategy_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("strategy_for_setup_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_simulations_user_id"),
        sa.ForeignKeyConstraint(
            ["voice_profile_catalog_id"],
            ["voice_profile_catalog.id"],
            name="fk_simulations_voice_profile_catalog_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_simulations"),
    )
    op.create_index("ix_simulations_user_id", "simulations", ["user_id"], unique=False)
    op.create_index("ix_simulations_country_key", "simulations", ["country_key"], unique=False)
    op.create_index(
        "ix_simulations_voice_profile_catalog_id",
        "simulations",
        ["voice_profile_catalog_id"],
        unique=False,
    )

    op.create_table(
        "simulation_uploaded_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("upload_status", sa.String(length=32), nullable=False, server_default=sa.text("'registered'")),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("parse_status", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["simulation_id"],
            ["simulations.id"],
            name="fk_simulation_uploaded_files_simulation_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_simulation_uploaded_files"),
    )
    op.create_index(
        "ix_simulation_uploaded_files_simulation_id",
        "simulation_uploaded_files",
        ["simulation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_simulation_uploaded_files_simulation_id", table_name="simulation_uploaded_files")
    op.drop_table("simulation_uploaded_files")
    op.drop_index("ix_simulations_voice_profile_catalog_id", table_name="simulations")
    op.drop_index("ix_simulations_country_key", table_name="simulations")
    op.drop_index("ix_simulations_user_id", table_name="simulations")
    op.drop_table("simulations")
