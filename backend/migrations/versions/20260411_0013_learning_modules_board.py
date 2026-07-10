"""learning modules board

Revision ID: 20260411_0013
Revises: 20260329_0012
Create Date: 2026-04-11 14:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0013"
down_revision = "20260329_0012"
branch_labels = None
depends_on = None


SEEDED_MODULES = (
    {
        "id": "00000000-0000-4000-8000-000000000051",
        "module_key": "jp_trust_signals",
        "country_key": "Japan",
        "title_text": "Read hesitation before pricing",
        "summary_text": "Spot trust signals before you introduce price or commitment pressure.",
        "theme_key": "trust",
        "scene_key": "first_introduction",
        "publish_status": "published",
        "sort_order": 10,
    },
    {
        "id": "00000000-0000-4000-8000-000000000052",
        "module_key": "jp_face_safe_pacing",
        "country_key": "Japan",
        "title_text": "Keep face-safe pacing",
        "summary_text": "Slow the exchange and leave room for indirect hesitation to surface.",
        "theme_key": "pacing",
        "scene_key": "first_introduction",
        "publish_status": "published",
        "sort_order": 20,
    },
    {
        "id": "00000000-0000-4000-8000-000000000053",
        "module_key": "de_owner_clarity",
        "country_key": "Germany",
        "title_text": "Make ownership explicit",
        "summary_text": "Clarify who owns the next action, timing, and process before persuasion.",
        "theme_key": "clarity",
        "scene_key": "commercial_alignment",
        "publish_status": "published",
        "sort_order": 30,
    },
    {
        "id": "00000000-0000-4000-8000-000000000054",
        "module_key": "de_risk_without_drama",
        "country_key": "Germany",
        "title_text": "Name risk without drama",
        "summary_text": "Frame risk with mitigation steps instead of urgency-heavy pressure.",
        "theme_key": "risk",
        "scene_key": "commercial_alignment",
        "publish_status": "published",
        "sort_order": 40,
    },
    {
        "id": "00000000-0000-4000-8000-000000000055",
        "module_key": "uae_rapport_first",
        "country_key": "UAE",
        "title_text": "Lead with rapport before scope",
        "summary_text": "Open with mutual intent and relationship respect before operational depth.",
        "theme_key": "rapport",
        "scene_key": "relationship_building",
        "publish_status": "published",
        "sort_order": 50,
    },
    {
        "id": "00000000-0000-4000-8000-000000000056",
        "module_key": "uae_warm_clarity",
        "country_key": "UAE",
        "title_text": "Use warm clarity in follow-ups",
        "summary_text": "Keep the tone warm while making the next step and ask explicit.",
        "theme_key": "clarity",
        "scene_key": "relationship_building",
        "publish_status": "published",
        "sort_order": 60,
    },
)


def upgrade() -> None:
    op.create_table(
        "learning_module_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("module_key", sa.String(length=64), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("title_text", sa.String(length=255), nullable=False),
        sa.Column("summary_text", sa.String(length=500), nullable=False),
        sa.Column("theme_key", sa.String(length=64), nullable=False),
        sa.Column("scene_key", sa.String(length=64), nullable=False),
        sa.Column("publish_status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
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
        sa.PrimaryKeyConstraint("id", name="pk_learning_module_catalog"),
        sa.UniqueConstraint("module_key", name="uq_learning_module_catalog_module_key"),
    )
    op.create_index(
        "ix_learning_module_catalog_country_key",
        "learning_module_catalog",
        ["country_key"],
        unique=False,
    )
    op.create_index(
        "ix_learning_module_catalog_theme_key",
        "learning_module_catalog",
        ["theme_key"],
        unique=False,
    )
    op.create_index(
        "ix_learning_module_catalog_scene_key",
        "learning_module_catalog",
        ["scene_key"],
        unique=False,
    )

    op.create_table(
        "user_learning_module_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("module_id", sa.String(length=36), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["module_id"], ["learning_module_catalog.id"], name="fk_user_learning_module_states_module_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_learning_module_states_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_user_learning_module_states"),
        sa.UniqueConstraint("user_id", "module_id", name="uq_user_learning_module_states_scope"),
    )
    op.create_index(
        "ix_user_learning_module_states_user_id",
        "user_learning_module_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_learning_module_states_module_id",
        "user_learning_module_states",
        ["module_id"],
        unique=False,
    )

    module_catalog = sa.table(
        "learning_module_catalog",
        sa.column("id", sa.String(length=36)),
        sa.column("module_key", sa.String(length=64)),
        sa.column("country_key", sa.String(length=64)),
        sa.column("title_text", sa.String(length=255)),
        sa.column("summary_text", sa.String(length=500)),
        sa.column("theme_key", sa.String(length=64)),
        sa.column("scene_key", sa.String(length=64)),
        sa.column("publish_status", sa.String(length=32)),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(module_catalog, list(SEEDED_MODULES))


def downgrade() -> None:
    op.drop_index("ix_user_learning_module_states_module_id", table_name="user_learning_module_states")
    op.drop_index("ix_user_learning_module_states_user_id", table_name="user_learning_module_states")
    op.drop_table("user_learning_module_states")

    op.drop_index("ix_learning_module_catalog_scene_key", table_name="learning_module_catalog")
    op.drop_index("ix_learning_module_catalog_theme_key", table_name="learning_module_catalog")
    op.drop_index("ix_learning_module_catalog_country_key", table_name="learning_module_catalog")
    op.drop_table("learning_module_catalog")
