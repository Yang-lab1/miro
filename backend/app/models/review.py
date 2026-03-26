from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class Review(Base, IdMixin, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "review_source",
            "realtime_session_id",
            name="uq_reviews_review_source_realtime_session_id",
        ),
    )

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    realtime_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("realtime_sessions.id"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id"),
        nullable=True,
        index=True,
    )
    review_source: Mapped[str] = mapped_column(String(32), nullable=False)
    country_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meeting_type_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_style_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voice_profile_catalog_id: Mapped[str | None] = mapped_column(
        ForeignKey("voice_profile_catalog.id"),
        nullable=True,
        index=True,
    )
    setup_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strategy_for_setup_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    overall_assessment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title_text: Mapped[str] = mapped_column(String(255), nullable=False)
    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    repeated_issues_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewLine(Base, IdMixin, TimestampMixin):
    __tablename__ = "review_lines"

    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), nullable=False, index=True)
    line_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaker: Mapped[str] = mapped_column(String(32), nullable=False)
    turn_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    issue_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    advice_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alert_issue_keys_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
