from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class CountryCatalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "country_catalog"

    country_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    country_name_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    default_meeting_type_key: Mapped[str] = mapped_column(String(64), nullable=False)
    default_goal_key: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CountryLearningContent(Base, IdMixin, TimestampMixin):
    __tablename__ = "country_learning_contents"
    __table_args__ = (UniqueConstraint("country_key", "content_version"),)

    country_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    content_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    sections_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    checklist_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserLearningProgress(Base, IdMixin, TimestampMixin):
    __tablename__ = "user_learning_progress"
    __table_args__ = (UniqueConstraint("user_id", "country_key", "content_version"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    country_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    progress_status: Mapped[str] = mapped_column(String(32), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
