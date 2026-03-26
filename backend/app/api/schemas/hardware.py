from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.api.schemas.common import StrictModel


class HardwareDeviceSummaryResponse(StrictModel):
    deviceId: str
    deviceName: str
    connected: bool
    connectionState: Literal["connected", "disconnected"]
    transferState: Literal["idle", "healthy", "warning", "failed"]
    firmwareVersion: str | None
    versionPath: str | None
    batteryPercent: int | None
    lastSyncAt: datetime | None
    capturedSessions: int
    vibrationEvents: int


class HardwareSyncRequest(StrictModel):
    syncKind: Literal["upload", "download", "sync_complete"]
    healthStatus: Literal["healthy", "warning", "failed"]
    summaryText: str | None = Field(default=None, max_length=500)
    detailText: str | None = Field(default=None, max_length=2000)
    firmwareVersion: str | None = Field(default=None, max_length=64)
    batteryPercent: int | None = Field(default=None, ge=0, le=100)
    reviewId: str | None = None
    vibrationEventCount: int = Field(default=0, ge=0, le=100)
    payload: dict[str, Any] | None = None


class HardwareDeviceLogResponse(StrictModel):
    logId: str
    eventType: Literal["connection", "sync", "vibration"]
    severity: Literal["info", "warning", "error"]
    title: str
    detail: str | None
    reviewId: str | None
    createdAt: datetime


class HardwareDeviceSyncRecordResponse(StrictModel):
    syncRecordId: str
    syncKind: Literal["upload", "download", "sync_complete"]
    status: Literal["healthy", "warning", "failed"]
    title: str
    detail: str | None
    reviewId: str | None
    createdAt: datetime


class HardwareSyncResponse(StrictModel):
    device: HardwareDeviceSummaryResponse
    syncRecord: HardwareDeviceSyncRecordResponse
    log: HardwareDeviceLogResponse
