from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class RealtimeSessionObservability(Base, IdMixin, TimestampMixin):
    __tablename__ = "realtime_session_observability"
    __table_args__ = (UniqueConstraint("realtime_session_id"),)

    realtime_session_id: Mapped[str] = mapped_column(
        ForeignKey("realtime_sessions.id"),
        nullable=False,
        index=True,
    )
    doubao_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    session_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voice_ws_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    client_audio_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    client_audio_total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    server_received_audio_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    server_received_audio_total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    server_forwarded_audio_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    server_forwarded_audio_total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_transcript_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assistant_text_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assistant_audio_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assistant_turn_end_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_user_turn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_assistant_turn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_status: Mapped[str] = mapped_column(String(64), nullable=False, default="diagnostic_incomplete")
    root_block_point: Mapped[str] = mapped_column(String(64), nullable=False, default="NONE")


class RealtimeSessionEvent(Base, IdMixin):
    __tablename__ = "realtime_session_events"
    __table_args__ = (UniqueConstraint("realtime_session_id", "sequence_no"),)

    realtime_session_id: Mapped[str] = mapped_column(
        ForeignKey("realtime_sessions.id"),
        nullable=False,
        index=True,
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
