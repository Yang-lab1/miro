"""Demo hardware state models.

These tables currently support a simulated hardware surface for UI/demo flows.
They do not imply real device transport, firmware, or physical-world ingestion.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class Device(Base, IdMixin, TimestampMixin):
    __tablename__ = "devices"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False)
    transfer_state: Mapped[str] = mapped_column(String(32), nullable=False)
    battery_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceSyncEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "device_sync_events"

    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    review_id: Mapped[str | None] = mapped_column(
        ForeignKey("reviews.id"),
        nullable=True,
        index=True,
    )
    health_status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "device_logs"

    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    review_id: Mapped[str | None] = mapped_column(
        ForeignKey("reviews.id"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title_text: Mapped[str] = mapped_column(Text, nullable=False)
    detail_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
