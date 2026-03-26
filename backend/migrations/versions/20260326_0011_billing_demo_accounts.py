"""billing demo accounts

Revision ID: 20260326_0011
Revises: 20260324_0010
Create Date: 2026-03-26 14:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0011"
down_revision = "20260324_0010"
branch_labels = None
depends_on = None


SEEDED_PLANS = (
    {
        "id": "f2f0f7a2-8f86-4a6d-b9f0-000000000001",
        "plan_key": "free",
        "display_name": "Free",
        "billing_cycle": "monthly",
        "currency_code": "USD",
        "amount_value": 0,
        "is_active": True,
    },
    {
        "id": "f2f0f7a2-8f86-4a6d-b9f0-000000000002",
        "plan_key": "go",
        "display_name": "Go",
        "billing_cycle": "monthly",
        "currency_code": "USD",
        "amount_value": 8,
        "is_active": True,
    },
    {
        "id": "f2f0f7a2-8f86-4a6d-b9f0-000000000003",
        "plan_key": "plus",
        "display_name": "Plus",
        "billing_cycle": "monthly",
        "currency_code": "USD",
        "amount_value": 20,
        "is_active": True,
    },
    {
        "id": "f2f0f7a2-8f86-4a6d-b9f0-000000000004",
        "plan_key": "pro",
        "display_name": "Pro",
        "billing_cycle": "monthly",
        "currency_code": "USD",
        "amount_value": 200,
        "is_active": True,
    },
)


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "billing_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("current_plan_id", sa.String(length=36), nullable=False),
        sa.Column("credit_balance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("renewal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
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
        sa.ForeignKeyConstraint(["current_plan_id"], ["billing_plans.id"], name="fk_billing_accounts_current_plan_id_billing_plans"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_billing_accounts_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_billing_accounts"),
        sa.UniqueConstraint("user_id", name="uq_billing_accounts_user_id"),
    )
    op.create_index("ix_billing_accounts_current_plan_id", "billing_accounts", ["current_plan_id"], unique=False)

    for plan in SEEDED_PLANS:
        bind.execute(
            sa.text(
                """
                INSERT INTO billing_plans (
                    id,
                    plan_key,
                    display_name,
                    billing_cycle,
                    currency_code,
                    amount_value,
                    is_active
                )
                SELECT
                    :id,
                    :plan_key,
                    :display_name,
                    :billing_cycle,
                    :currency_code,
                    :amount_value,
                    :is_active
                WHERE NOT EXISTS (
                    SELECT 1 FROM billing_plans WHERE plan_key = :plan_key
                )
                """
            ),
            plan,
        )


def downgrade() -> None:
    op.drop_index("ix_billing_accounts_current_plan_id", table_name="billing_accounts")
    op.drop_table("billing_accounts")

    op.execute(
        sa.text(
            """
            UPDATE payments
            SET plan_id = NULL
            WHERE plan_id IN (
                SELECT id FROM billing_plans WHERE plan_key IN ('free', 'go', 'plus', 'pro')
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM billing_plans
            WHERE plan_key IN ('free', 'go', 'plus', 'pro')
            """
        )
    )
