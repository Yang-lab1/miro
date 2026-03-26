from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class Organization(Base, IdMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    country_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Membership(Base, IdMixin, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    membership_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class UserTwinMemory(Base, IdMixin, TimestampMixin):
    __tablename__ = "user_twin_memories"
    __table_args__ = (UniqueConstraint("user_id", "issue_key", "country_key"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False)
    country_key: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
