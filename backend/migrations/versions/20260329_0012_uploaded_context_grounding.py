"""uploaded context grounding scaffold

Revision ID: 20260329_0012
Revises: 20260326_0011
Create Date: 2026-03-29 20:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_0012"
down_revision = "20260326_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulation_uploaded_files",
        sa.Column("extracted_summary_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "simulation_uploaded_files",
        sa.Column("extracted_excerpt_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulation_uploaded_files", "extracted_excerpt_text")
    op.drop_column("simulation_uploaded_files", "extracted_summary_text")
