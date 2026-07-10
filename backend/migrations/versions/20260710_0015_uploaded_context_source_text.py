"""persist uploaded source text for retrieval"""

import sqlalchemy as sa
from alembic import op

revision = "20260710_0015"
down_revision = "20260418_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulation_uploaded_files",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulation_uploaded_files", "extracted_text")
