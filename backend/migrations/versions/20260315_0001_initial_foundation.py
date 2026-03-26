"""initial foundation

Revision ID: 20260315_0001
Revises:
Create Date: 2026-03-15 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260315_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("role_title", sa.String(length=200), nullable=True),
        sa.Column("preferred_language", sa.String(length=16), nullable=False, server_default=sa.text("'en'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("role_key", sa.String(length=64), nullable=False),
        sa.Column("membership_status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_memberships_organization_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_memberships_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], unique=False)
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"], unique=False)

    op.create_table(
        "user_twin_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("issue_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_context", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_twin_memories_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_user_twin_memories"),
        sa.UniqueConstraint("user_id", "issue_key", "country_key", name="uq_user_twin_memory_scope"),
    )
    op.create_index("ix_user_twin_memories_user_id", "user_twin_memories", ["user_id"], unique=False)

    op.create_table(
        "country_learning_contents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("content_version", sa.String(length=32), nullable=False),
        sa.Column("content_status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("sections_json", sa.JSON(), nullable=True),
        sa.Column("checklist_json", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_country_learning_contents"),
        sa.UniqueConstraint("country_key", "content_version", name="uq_learning_content_version"),
    )
    op.create_index("ix_country_learning_contents_country_key", "country_learning_contents", ["country_key"], unique=False)

    op.create_table(
        "user_learning_progress",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("content_version", sa.String(length=32), nullable=False),
        sa.Column("progress_status", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_learning_progress_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_user_learning_progress"),
        sa.UniqueConstraint("user_id", "country_key", "content_version", name="uq_learning_progress_scope"),
    )
    op.create_index("ix_user_learning_progress_user_id", "user_learning_progress", ["user_id"], unique=False)
    op.create_index("ix_user_learning_progress_country_key", "user_learning_progress", ["country_key"], unique=False)

    op.create_table(
        "voice_profile_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column("voice_id", sa.String(length=128), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_voice_profile_catalog"),
        sa.UniqueConstraint("voice_id", name="uq_voice_profile_catalog_voice_id"),
    )
    op.create_index("ix_voice_profile_catalog_country_key", "voice_profile_catalog", ["country_key"], unique=False)
    op.create_index("ix_voice_profile_catalog_gender", "voice_profile_catalog", ["gender"], unique=False)

    op.create_table(
        "realtime_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("meeting_type_key", sa.String(length=64), nullable=False),
        sa.Column("goal_key", sa.String(length=64), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("voice_style_key", sa.String(length=64), nullable=False),
        sa.Column("voice_profile_id", sa.String(length=36), nullable=True),
        sa.Column("constraint_text", sa.Text(), nullable=True),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("session_status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_realtime_sessions_user_id"),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profile_catalog.id"], name="fk_realtime_sessions_voice_profile_id"),
        sa.PrimaryKeyConstraint("id", name="pk_realtime_sessions"),
    )
    op.create_index("ix_realtime_sessions_user_id", "realtime_sessions", ["user_id"], unique=False)
    op.create_index("ix_realtime_sessions_country_key", "realtime_sessions", ["country_key"], unique=False)

    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("device_name", sa.String(length=128), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=True),
        sa.Column("connection_state", sa.String(length=32), nullable=False),
        sa.Column("transfer_state", sa.String(length=32), nullable=False),
        sa.Column("battery_percent", sa.Integer(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_devices_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"], unique=False)

    op.create_table(
        "realtime_session_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("speaker", sa.String(length=32), nullable=False),
        sa.Column("input_mode", sa.String(length=32), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["realtime_sessions.id"], name="fk_realtime_session_turns_session_id"),
        sa.PrimaryKeyConstraint("id", name="pk_realtime_session_turns"),
    )
    op.create_index("ix_realtime_session_turns_session_id", "realtime_session_turns", ["session_id"], unique=False)

    op.create_table(
        "realtime_session_alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("title_text", sa.Text(), nullable=False),
        sa.Column("detail_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["realtime_sessions.id"], name="fk_realtime_session_alerts_session_id"),
        sa.ForeignKeyConstraint(["turn_id"], ["realtime_session_turns.id"], name="fk_realtime_session_alerts_turn_id"),
        sa.PrimaryKeyConstraint("id", name="pk_realtime_session_alerts"),
    )
    op.create_index("ix_realtime_session_alerts_session_id", "realtime_session_alerts", ["session_id"], unique=False)
    op.create_index("ix_realtime_session_alerts_turn_id", "realtime_session_alerts", ["turn_id"], unique=False)

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("realtime_session_id", sa.String(length=36), nullable=True),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("review_source", sa.String(length=32), nullable=False),
        sa.Column("country_key", sa.String(length=64), nullable=False),
        sa.Column("title_text", sa.String(length=255), nullable=False),
        sa.Column("score_total", sa.Integer(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("repeated_issues_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name="fk_reviews_device_id"),
        sa.ForeignKeyConstraint(["realtime_session_id"], ["realtime_sessions.id"], name="fk_reviews_realtime_session_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_reviews_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
    )
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"], unique=False)
    op.create_index("ix_reviews_realtime_session_id", "reviews", ["realtime_session_id"], unique=False)
    op.create_index("ix_reviews_device_id", "reviews", ["device_id"], unique=False)
    op.create_index("ix_reviews_country_key", "reviews", ["country_key"], unique=False)

    op.create_table(
        "review_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("speaker", sa.String(length=32), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translation_json", sa.JSON(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("issue_key", sa.String(length=64), nullable=True),
        sa.Column("advice_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name="fk_review_lines_review_id"),
        sa.PrimaryKeyConstraint("id", name="pk_review_lines"),
    )
    op.create_index("ix_review_lines_review_id", "review_lines", ["review_id"], unique=False)

    op.create_table(
        "device_sync_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("review_id", sa.String(length=36), nullable=True),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name="fk_device_sync_events_device_id"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name="fk_device_sync_events_review_id"),
        sa.PrimaryKeyConstraint("id", name="pk_device_sync_events"),
    )
    op.create_index("ix_device_sync_events_device_id", "device_sync_events", ["device_id"], unique=False)
    op.create_index("ix_device_sync_events_review_id", "device_sync_events", ["review_id"], unique=False)

    op.create_table(
        "billing_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plan_key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("billing_cycle", sa.String(length=32), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("amount_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_billing_plans"),
        sa.UniqueConstraint("plan_key", name="uq_billing_plans_plan_key"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("amount_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("payment_status", sa.String(length=32), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["plan_id"], ["billing_plans.id"], name="fk_payments_plan_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_payments_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_audit_logs_actor_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("billing_plans")
    op.drop_index("ix_device_sync_events_review_id", table_name="device_sync_events")
    op.drop_index("ix_device_sync_events_device_id", table_name="device_sync_events")
    op.drop_table("device_sync_events")
    op.drop_index("ix_review_lines_review_id", table_name="review_lines")
    op.drop_table("review_lines")
    op.drop_index("ix_reviews_country_key", table_name="reviews")
    op.drop_index("ix_reviews_device_id", table_name="reviews")
    op.drop_index("ix_reviews_realtime_session_id", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_realtime_session_alerts_turn_id", table_name="realtime_session_alerts")
    op.drop_index("ix_realtime_session_alerts_session_id", table_name="realtime_session_alerts")
    op.drop_table("realtime_session_alerts")
    op.drop_index("ix_realtime_session_turns_session_id", table_name="realtime_session_turns")
    op.drop_table("realtime_session_turns")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_realtime_sessions_country_key", table_name="realtime_sessions")
    op.drop_index("ix_realtime_sessions_user_id", table_name="realtime_sessions")
    op.drop_table("realtime_sessions")
    op.drop_index("ix_voice_profile_catalog_gender", table_name="voice_profile_catalog")
    op.drop_index("ix_voice_profile_catalog_country_key", table_name="voice_profile_catalog")
    op.drop_table("voice_profile_catalog")
    op.drop_index("ix_user_learning_progress_country_key", table_name="user_learning_progress")
    op.drop_index("ix_user_learning_progress_user_id", table_name="user_learning_progress")
    op.drop_table("user_learning_progress")
    op.drop_index("ix_country_learning_contents_country_key", table_name="country_learning_contents")
    op.drop_table("country_learning_contents")
    op.drop_index("ix_user_twin_memories_user_id", table_name="user_twin_memories")
    op.drop_table("user_twin_memories")
    op.drop_index("ix_memberships_organization_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
