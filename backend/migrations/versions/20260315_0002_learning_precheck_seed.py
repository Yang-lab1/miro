"""learning precheck seed

Revision ID: 20260315_0002
Revises: 20260315_0001
Create Date: 2026-03-15 10:30:00
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260315_0002"
down_revision = "20260315_0001"
branch_labels = None
depends_on = None

DEMO_ORG_ID = "00000000-0000-4000-8000-000000000001"
DEMO_USER_ID = "00000000-0000-4000-8000-000000000002"
DEMO_MEMBERSHIP_ID = "00000000-0000-4000-8000-000000000003"

COUNTRY_IDS = {
    "Japan": "00000000-0000-4000-8000-000000000011",
    "Germany": "00000000-0000-4000-8000-000000000012",
    "UAE": "00000000-0000-4000-8000-000000000013",
}

VOICE_IDS = {
    "Japan_female": "00000000-0000-4000-8000-000000000021",
    "Japan_male": "00000000-0000-4000-8000-000000000022",
    "Germany_male": "00000000-0000-4000-8000-000000000023",
    "UAE_female": "00000000-0000-4000-8000-000000000024",
}

LEARNING_CONTENT_IDS = {
    "Japan_2026.03": "00000000-0000-4000-8000-000000000031",
    "Germany_2026.03": "00000000-0000-4000-8000-000000000032",
    "Germany_2026.04": "00000000-0000-4000-8000-000000000033",
    "UAE_2026.03": "00000000-0000-4000-8000-000000000034",
}

PROGRESS_IDS = {
    "Japan": "00000000-0000-4000-8000-000000000041",
    "Germany": "00000000-0000-4000-8000-000000000042",
}


def _localized(en: str, zh: str | None = None) -> dict[str, str]:
    return {"en": en, "zh": zh or en}


def upgrade() -> None:
    op.create_table(
        "country_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("country_name_json", sa.JSON(), nullable=False),
        sa.Column("default_meeting_type_key", sa.String(length=64), nullable=False),
        sa.Column("default_goal_key", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id", name="pk_country_catalog"),
        sa.UniqueConstraint("country_key", name="uq_country_catalog_country_key"),
    )

    with op.batch_alter_table("voice_profile_catalog") as batch_op:
        batch_op.drop_constraint("uq_voice_profile_catalog_voice_id", type_="unique")
        batch_op.alter_column(
            "voice_id",
            new_column_name="provider_voice_id",
            existing_type=sa.String(length=128),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("voice_profile_id", sa.String(length=128), nullable=False))
        batch_op.create_unique_constraint(
            "uq_voice_profile_catalog_provider_voice_id",
            ["provider_voice_id"],
        )
        batch_op.create_unique_constraint(
            "uq_voice_profile_catalog_voice_profile_id",
            ["voice_profile_id"],
        )

    country_catalog = sa.table(
        "country_catalog",
        sa.column("id", sa.String()),
        sa.column("country_key", sa.String()),
        sa.column("country_name_json", sa.JSON()),
        sa.column("default_meeting_type_key", sa.String()),
        sa.column("default_goal_key", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("country_key", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("email", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("company_name", sa.String()),
        sa.column("role_title", sa.String()),
        sa.column("preferred_language", sa.String()),
        sa.column("status", sa.String()),
    )
    memberships = sa.table(
        "memberships",
        sa.column("id", sa.String()),
        sa.column("user_id", sa.String()),
        sa.column("organization_id", sa.String()),
        sa.column("role_key", sa.String()),
        sa.column("membership_status", sa.String()),
    )
    voice_profiles = sa.table(
        "voice_profile_catalog",
        sa.column("id", sa.String()),
        sa.column("voice_profile_id", sa.String()),
        sa.column("provider_voice_id", sa.String()),
        sa.column("country_key", sa.String()),
        sa.column("gender", sa.String()),
        sa.column("locale", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    learning_contents = sa.table(
        "country_learning_contents",
        sa.column("id", sa.String()),
        sa.column("country_key", sa.String()),
        sa.column("content_version", sa.String()),
        sa.column("content_status", sa.String()),
        sa.column("sections_json", sa.JSON()),
        sa.column("checklist_json", sa.JSON()),
        sa.column("published_at", sa.DateTime(timezone=True)),
    )
    learning_progress = sa.table(
        "user_learning_progress",
        sa.column("id", sa.String()),
        sa.column("user_id", sa.String()),
        sa.column("country_key", sa.String()),
        sa.column("content_version", sa.String()),
        sa.column("progress_status", sa.String()),
        sa.column("completed_at", sa.DateTime(timezone=True)),
        sa.column("expires_at", sa.DateTime(timezone=True)),
    )

    published_at = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    germany_latest_at = datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc)
    completed_at = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    expires_at = datetime(2026, 4, 14, 10, 0, tzinfo=timezone.utc)

    op.bulk_insert(
        country_catalog,
        [
            {
                "id": COUNTRY_IDS["Japan"],
                "country_key": "Japan",
                "country_name_json": _localized("Japan", "\u65e5\u672c"),
                "default_meeting_type_key": "first_introduction",
                "default_goal_key": "establish_trust_before_pricing",
                "is_active": True,
            },
            {
                "id": COUNTRY_IDS["Germany"],
                "country_key": "Germany",
                "country_name_json": _localized("Germany", "\u5fb7\u56fd"),
                "default_meeting_type_key": "commercial_alignment",
                "default_goal_key": "clarify_process_and_risk_ownership",
                "is_active": True,
            },
            {
                "id": COUNTRY_IDS["UAE"],
                "country_key": "UAE",
                "country_name_json": _localized("UAE", "\u963f\u8054\u914b"),
                "default_meeting_type_key": "relationship_building",
                "default_goal_key": "build_rapport_before_scope_depth",
                "is_active": True,
            },
        ],
    )

    op.bulk_insert(
        organizations,
        [
            {
                "id": DEMO_ORG_ID,
                "name": "Miro Demo Org",
                "country_key": "Japan",
                "is_active": True,
            }
        ],
    )
    op.bulk_insert(
        users,
        [
            {
                "id": DEMO_USER_ID,
                "email": "demo@miro.local",
                "full_name": "Miro Demo User",
                "company_name": "Miro Demo Org",
                "role_title": "Demo Operator",
                "preferred_language": "en",
                "status": "active",
            }
        ],
    )
    op.bulk_insert(
        memberships,
        [
            {
                "id": DEMO_MEMBERSHIP_ID,
                "user_id": DEMO_USER_ID,
                "organization_id": DEMO_ORG_ID,
                "role_key": "demo_admin",
                "membership_status": "active",
            }
        ],
    )

    op.bulk_insert(
        voice_profiles,
        [
            {
                "id": VOICE_IDS["Japan_female"],
                "voice_profile_id": "vp_japan_female_01",
                "provider_voice_id": "ja_female_01",
                "country_key": "Japan",
                "gender": "female",
                "locale": "ja-JP",
                "display_name": "Japan Female 01",
                "is_active": True,
            },
            {
                "id": VOICE_IDS["Japan_male"],
                "voice_profile_id": "vp_japan_male_01",
                "provider_voice_id": "ja_male_01",
                "country_key": "Japan",
                "gender": "male",
                "locale": "ja-JP",
                "display_name": "Japan Male 01",
                "is_active": True,
            },
            {
                "id": VOICE_IDS["Germany_male"],
                "voice_profile_id": "vp_germany_male_01",
                "provider_voice_id": "de_male_01",
                "country_key": "Germany",
                "gender": "male",
                "locale": "de-DE",
                "display_name": "Germany Male 01",
                "is_active": True,
            },
            {
                "id": VOICE_IDS["UAE_female"],
                "voice_profile_id": "vp_uae_female_01",
                "provider_voice_id": "ar_female_01",
                "country_key": "UAE",
                "gender": "female",
                "locale": "ar-AE",
                "display_name": "UAE Female 01",
                "is_active": True,
            },
        ],
    )

    op.bulk_insert(
        learning_contents,
        [
            {
                "id": LEARNING_CONTENT_IDS["Japan_2026.03"],
                "country_key": "Japan",
                "content_version": "2026.03",
                "content_status": "published",
                "sections_json": [
                    {
                        "id": "high-context",
                        "title": _localized("Treat hesitation as signal"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "If the client needs to think carefully, do not push for instant closure."
                                ),
                            }
                        ],
                    },
                    {
                        "id": "face-management",
                        "title": _localized("Keep value language elevated"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "Avoid low-value words like cheap or bargain in first trust-building meetings."
                                ),
                            }
                        ],
                    },
                ],
                "checklist_json": [
                    {
                        "id": "avoid-price-push",
                        "label": _localized("Avoid pushing price before trust is established."),
                    },
                    {
                        "id": "leave-pause-window",
                        "label": _localized("Leave a pause after each key ask."),
                    },
                ],
                "published_at": published_at,
            },
            {
                "id": LEARNING_CONTENT_IDS["Germany_2026.03"],
                "country_key": "Germany",
                "content_version": "2026.03",
                "content_status": "published",
                "sections_json": [
                    {
                        "id": "clarity",
                        "title": _localized("Be explicit about assumptions"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "State dependencies, dates, and responsibilities directly."
                                ),
                            }
                        ],
                    }
                ],
                "checklist_json": [
                    {
                        "id": "sequence-before-persuasion",
                        "label": _localized("Anchor the meeting with process before persuasion."),
                    }
                ],
                "published_at": published_at,
            },
            {
                "id": LEARNING_CONTENT_IDS["Germany_2026.04"],
                "country_key": "Germany",
                "content_version": "2026.04",
                "content_status": "published",
                "sections_json": [
                    {
                        "id": "clarity",
                        "title": _localized("Be explicit about assumptions"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "State dependencies, dates, and responsibilities directly."
                                ),
                            }
                        ],
                    },
                    {
                        "id": "risk",
                        "title": _localized("Name risk without drama"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "Describe mitigation steps instead of emotional urgency."
                                ),
                            }
                        ],
                    },
                ],
                "checklist_json": [
                    {
                        "id": "stay-factual",
                        "label": _localized("Stay factual and concise."),
                    }
                ],
                "published_at": germany_latest_at,
            },
            {
                "id": LEARNING_CONTENT_IDS["UAE_2026.03"],
                "country_key": "UAE",
                "content_version": "2026.03",
                "content_status": "published",
                "sections_json": [
                    {
                        "id": "relationship",
                        "title": _localized("Respect before detail"),
                        "items": [
                            {
                                "type": "bullet",
                                "content": _localized(
                                    "Open with respect and mutual intent before pushing operational asks."
                                ),
                            }
                        ],
                    }
                ],
                "checklist_json": [
                    {
                        "id": "dont-rush-closure",
                        "label": _localized("Do not rush closure in the opening."),
                    }
                ],
                "published_at": published_at,
            },
        ],
    )

    op.bulk_insert(
        learning_progress,
        [
            {
                "id": PROGRESS_IDS["Japan"],
                "user_id": DEMO_USER_ID,
                "country_key": "Japan",
                "content_version": "2026.03",
                "progress_status": "completed",
                "completed_at": completed_at,
                "expires_at": expires_at,
            },
            {
                "id": PROGRESS_IDS["Germany"],
                "user_id": DEMO_USER_ID,
                "country_key": "Germany",
                "content_version": "2026.03",
                "progress_status": "completed",
                "completed_at": completed_at,
                "expires_at": expires_at,
            },
        ],
    )


def downgrade() -> None:
    for progress_id in PROGRESS_IDS.values():
        op.execute(sa.text(f"DELETE FROM user_learning_progress WHERE id = '{progress_id}'"))

    for content_id in LEARNING_CONTENT_IDS.values():
        op.execute(sa.text(f"DELETE FROM country_learning_contents WHERE id = '{content_id}'"))

    for voice_id in VOICE_IDS.values():
        op.execute(sa.text(f"DELETE FROM voice_profile_catalog WHERE id = '{voice_id}'"))

    op.execute(sa.text(f"DELETE FROM memberships WHERE id = '{DEMO_MEMBERSHIP_ID}'"))
    op.execute(sa.text(f"DELETE FROM users WHERE id = '{DEMO_USER_ID}'"))
    op.execute(sa.text(f"DELETE FROM organizations WHERE id = '{DEMO_ORG_ID}'"))

    for country_id in COUNTRY_IDS.values():
        op.execute(sa.text(f"DELETE FROM country_catalog WHERE id = '{country_id}'"))

    with op.batch_alter_table("voice_profile_catalog") as batch_op:
        batch_op.drop_constraint("uq_voice_profile_catalog_voice_profile_id", type_="unique")
        batch_op.drop_constraint("uq_voice_profile_catalog_provider_voice_id", type_="unique")
        batch_op.drop_column("voice_profile_id")
        batch_op.alter_column(
            "provider_voice_id",
            new_column_name="voice_id",
            existing_type=sa.String(length=128),
            existing_nullable=False,
        )
        batch_op.create_unique_constraint("uq_voice_profile_catalog_voice_id", ["voice_id"])

    op.drop_table("country_catalog")
