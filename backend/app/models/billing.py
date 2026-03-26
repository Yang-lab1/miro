"""Demo billing models.

These tables support the product's simulated billing layer only.
They do not represent real payment-provider state, invoicing, or accounting.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class BillingPlan(Base, IdMixin, TimestampMixin):
    __tablename__ = "billing_plans"

    plan_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class BillingAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "billing_accounts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    current_plan_id: Mapped[str] = mapped_column(
        ForeignKey("billing_plans.id"),
        nullable=False,
        index=True,
    )
    credit_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    renewal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)


class Payment(Base, IdMixin, TimestampMixin):
    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("billing_plans.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
