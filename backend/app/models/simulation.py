from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class VoiceProfileCatalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "voice_profile_catalog"
    __table_args__ = (
        UniqueConstraint("voice_profile_id"),
        UniqueConstraint("provider_voice_id"),
    )

    voice_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_voice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Simulation(Base, IdMixin, TimestampMixin):
    __tablename__ = "simulations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
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
    constraints_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    setup_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    strategy_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategy_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    strategy_for_setup_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SimulationUploadedFile(Base, IdMixin, TimestampMixin):
    __tablename__ = "simulation_uploaded_files"

    simulation_id: Mapped[str] = mapped_column(
        ForeignKey("simulations.id"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_status: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parse_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_excerpt_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class RealtimeSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "realtime_sessions"

    simulation_id: Mapped[str] = mapped_column(
        ForeignKey("simulations.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    country_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meeting_type_key: Mapped[str] = mapped_column(String(64), nullable=False)
    goal_key: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    voice_style_key: Mapped[str] = mapped_column(String(64), nullable=False)
    voice_profile_catalog_id: Mapped[str] = mapped_column(
        ForeignKey("voice_profile_catalog.id"),
        nullable=False,
        index=True,
    )
    setup_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy_for_setup_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    transport: Mapped[str] = mapped_column(String(32), nullable=False)
    session_status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    launch_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    launch_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_user_turn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_assistant_turn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_alert_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RealtimeSessionTurn(Base, IdMixin, TimestampMixin):
    __tablename__ = "realtime_session_turns"
    __table_args__ = (UniqueConstraint("session_id", "turn_index"),)

    session_id: Mapped[str] = mapped_column(
        ForeignKey("realtime_sessions.id"),
        nullable=False,
        index=True,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_turn_id: Mapped[str | None] = mapped_column(
        ForeignKey("realtime_session_turns.id"),
        nullable=True,
        index=True,
    )
    speaker: Mapped[str] = mapped_column(String(32), nullable=False)
    input_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RealtimeSessionAlert(Base, IdMixin, TimestampMixin):
    __tablename__ = "realtime_session_alerts"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("realtime_sessions.id"),
        nullable=False,
        index=True,
    )
    turn_id: Mapped[str | None] = mapped_column(
        ForeignKey("realtime_session_turns.id"),
        nullable=True,
        index=True,
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title_text: Mapped[str] = mapped_column(Text, nullable=False)
    detail_text: Mapped[str | None] = mapped_column(Text, nullable=True)
