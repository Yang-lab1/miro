import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.hardware import (
    HardwareDeviceLogResponse,
    HardwareDeviceSummaryResponse,
    HardwareDeviceSyncRecordResponse,
    HardwareSyncRequest,
    HardwareSyncResponse,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.hardware import Device, DeviceLog, DeviceSyncEvent
from app.models.review import Review, ReviewLine
from app.services.current_actor import CurrentActor

DEFAULT_DEMO_DEVICE_NAME = "Miro Pin 01"
DEFAULT_FIRMWARE_VERSION = "1.4.2"
DEFAULT_BATTERY_PERCENT = 84
DEFAULT_CONNECTION_STATE = "disconnected"
DEFAULT_TRANSFER_STATE = "idle"

SYNC_TITLE_BY_KIND = {
    "upload": "Demo upload completed",
    "download": "Demo download completed",
    "sync_complete": "Demo sync completed",
}

SYNC_DETAIL_BY_KIND = {
    "upload": "Demo device upload finished for UI playback.",
    "download": "Demo device download finished for UI playback.",
    "sync_complete": "Demo device sync finished for UI playback.",
}


def _hardware_provider_mode() -> str:
    return get_settings().hardware_provider_mode.strip().lower()


def _dispatch_hardware_provider(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    mode = settings.hardware_provider_mode.strip().lower()
    url = settings.hardware_provider_url.strip()
    is_production = settings.app_env.strip().lower() == "production"

    if mode == "demo" and not is_production:
        return {}
    if mode != "webhook" or not url or (is_production and not url.startswith("https://")):
        raise AppError(
            status_code=503,
            code="hardware_provider_not_configured",
            message="A real hardware transport is required before syncing.",
            details={
                "hint": (
                    "Configure HARDWARE_PROVIDER_MODE=webhook and an HTTPS "
                    "HARDWARE_PROVIDER_URL for the device bridge."
                ),
            },
        )

    headers = {
        "Content-Type": "application/json",
        "X-Miro-Protocol": "miro.hardware.sync.v1",
    }
    if settings.hardware_provider_api_key.strip():
        headers["Authorization"] = f"Bearer {settings.hardware_provider_api_key.strip()}"

    try:
        response = httpx.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.hardware_provider_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppError(
            status_code=502,
            code="hardware_provider_sync_failed",
            message="The hardware bridge did not accept the sync packet.",
            details={"provider": "webhook", "reason": str(exc)[:240]},
        ) from exc

    try:
        provider_response = response.json()
    except ValueError:
        return {}
    return provider_response if isinstance(provider_response, dict) else {}


def _raise_device_not_found(device_id: str) -> None:
    raise AppError(
        status_code=404,
        code="hardware_device_not_found",
        message="Demo device could not be found.",
        details={"deviceId": device_id},
    )


def _get_actor_device(session: Session, actor: CurrentActor, device_id: str) -> Device:
    device = session.scalar(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == actor.user_id,
        )
    )
    if device is None:
        _raise_device_not_found(device_id)
    return device


def _validate_review_for_actor(session: Session, actor: CurrentActor, review_id: str) -> Review:
    review = session.scalar(
        select(Review).where(
            Review.id == review_id,
            Review.user_id == actor.user_id,
        )
    )
    if review is None:
        raise AppError(
            status_code=404,
            code="hardware_review_not_found",
            message="Review could not be found for the current actor.",
            details={"reviewId": review_id},
        )
    return review


def _create_default_demo_device(session: Session, actor: CurrentActor) -> Device:
    device = Device(
        user_id=actor.user_id,
        device_name=DEFAULT_DEMO_DEVICE_NAME,
        firmware_version=DEFAULT_FIRMWARE_VERSION,
        connection_state=DEFAULT_CONNECTION_STATE,
        transfer_state=DEFAULT_TRANSFER_STATE,
        battery_percent=DEFAULT_BATTERY_PERCENT,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def _list_actor_devices(session: Session, actor: CurrentActor) -> list[Device]:
    devices = list(
        session.scalars(
            select(Device)
            .where(Device.user_id == actor.user_id)
            .order_by(Device.updated_at.desc(), Device.id.desc())
        )
    )
    if devices:
        return devices

    return [_create_default_demo_device(session, actor)]


def _get_latest_sync_event(session: Session, device_id: str) -> DeviceSyncEvent | None:
    return session.scalar(
        select(DeviceSyncEvent)
        .where(DeviceSyncEvent.device_id == device_id)
        .order_by(DeviceSyncEvent.created_at.desc(), DeviceSyncEvent.id.desc())
    )


def _build_version_path(session: Session, device_id: str) -> str | None:
    latest_event = _get_latest_sync_event(session, device_id)
    if latest_event is None:
        return None

    payload = latest_event.payload_json or {}
    before = payload.get("firmwareBefore")
    after = payload.get("firmwareAfter")
    if before and after and before != after:
        return f"{before} -> {after}"
    return None


def _count_sync_records(session: Session, device_id: str) -> int:
    result = session.scalar(
        select(func.count())
        .select_from(DeviceSyncEvent)
        .where(DeviceSyncEvent.device_id == device_id)
    )
    return int(result or 0)


def _count_vibration_events(session: Session, device_id: str) -> int:
    result = session.scalar(
        select(func.count())
        .select_from(DeviceLog)
        .where(
            DeviceLog.device_id == device_id,
            DeviceLog.event_type == "vibration",
        )
    )
    return int(result or 0)


def _build_device_summary(session: Session, device: Device) -> HardwareDeviceSummaryResponse:
    return HardwareDeviceSummaryResponse(
        deviceId=device.id,
        deviceName=device.device_name,
        connected=device.connection_state == "connected",
        connectionState=device.connection_state,
        transferState=device.transfer_state,
        firmwareVersion=device.firmware_version,
        versionPath=_build_version_path(session, device.id),
        batteryPercent=device.battery_percent,
        lastSyncAt=device.last_sync_at,
        capturedSessions=_count_sync_records(session, device.id),
        vibrationEvents=_count_vibration_events(session, device.id),
    )


def _build_log_response(log: DeviceLog) -> HardwareDeviceLogResponse:
    return HardwareDeviceLogResponse(
        logId=log.id,
        eventType=log.event_type,
        severity=log.severity,
        title=log.title_text,
        detail=log.detail_text,
        reviewId=log.review_id,
        createdAt=log.created_at,
    )


def _build_sync_record_response(event: DeviceSyncEvent) -> HardwareDeviceSyncRecordResponse:
    payload = event.payload_json or {}
    sync_kind = payload.get("syncKind", "sync_complete")
    title = event.summary_text or SYNC_TITLE_BY_KIND.get(sync_kind, "Demo sync completed")
    detail = payload.get("detailText") or SYNC_DETAIL_BY_KIND.get(sync_kind)
    return HardwareDeviceSyncRecordResponse(
        syncRecordId=event.id,
        syncKind=sync_kind,
        status=event.health_status,
        title=title,
        detail=detail,
        reviewId=event.review_id,
        createdAt=event.created_at,
    )


def _create_log(
    session: Session,
    *,
    device_id: str,
    event_type: str,
    severity: str,
    title_text: str,
    detail_text: str | None,
    review_id: str | None = None,
    payload_json: dict | None = None,
) -> DeviceLog:
    log = DeviceLog(
        device_id=device_id,
        review_id=review_id,
        event_type=event_type,
        severity=severity,
        title_text=title_text,
        detail_text=detail_text,
        payload_json=payload_json,
    )
    session.add(log)
    session.flush()
    return log


def _severity_for_health_status(health_status: str) -> str:
    if health_status == "healthy":
        return "info"
    if health_status == "failed":
        return "error"
    return "warning"


def list_devices(session: Session, actor: CurrentActor) -> list[HardwareDeviceSummaryResponse]:
    devices = _list_actor_devices(session, actor)
    return [_build_device_summary(session, device) for device in devices]


def connect_device(
    session: Session,
    actor: CurrentActor,
    device_id: str,
) -> HardwareDeviceSummaryResponse:
    device = _get_actor_device(session, actor, device_id)

    if device.connection_state != "connected":
        device.connection_state = "connected"
        _create_log(
            session,
            device_id=device.id,
            event_type="connection",
            severity="info",
            title_text="Demo device connected",
            detail_text="Demo hardware state changed to connected.",
            payload_json={"source": "hardware-demo"},
        )
        session.commit()
        session.refresh(device)

    return _build_device_summary(session, device)


def disconnect_device(
    session: Session,
    actor: CurrentActor,
    device_id: str,
) -> HardwareDeviceSummaryResponse:
    device = _get_actor_device(session, actor, device_id)

    if device.connection_state != "disconnected" or device.transfer_state != "idle":
        device.connection_state = "disconnected"
        device.transfer_state = "idle"
        _create_log(
            session,
            device_id=device.id,
            event_type="connection",
            severity="info",
            title_text="Demo device disconnected",
            detail_text="Demo hardware state changed to disconnected.",
            payload_json={"source": "hardware-demo"},
        )
        session.commit()
        session.refresh(device)

    return _build_device_summary(session, device)


def sync_device(
    session: Session,
    actor: CurrentActor,
    device_id: str,
    payload: HardwareSyncRequest,
) -> HardwareSyncResponse:
    device = _get_actor_device(session, actor, device_id)
    review_id = None
    if payload.reviewId is not None:
        review_id = _validate_review_for_actor(session, actor, payload.reviewId).id

    now = datetime.now(tz=UTC)
    previous_firmware = device.firmware_version
    next_firmware = payload.firmwareVersion or previous_firmware

    provider_response = _dispatch_hardware_provider(
        {
            "schemaVersion": "miro.hardware.sync.v1",
            "deviceId": device.id,
            "reviewId": review_id,
            "syncKind": payload.syncKind,
            "healthStatus": payload.healthStatus,
            "summaryText": payload.summaryText,
            "detailText": payload.detailText,
            "firmwareBefore": previous_firmware,
            "firmwareAfter": next_firmware,
            "batteryPercent": payload.batteryPercent,
            "payload": payload.payload or {},
        }
    )
    provider_mode = _hardware_provider_mode()
    is_demo = provider_mode == "demo"
    summary_text = payload.summaryText or (
        SYNC_TITLE_BY_KIND[payload.syncKind]
        if is_demo
        else "Hardware sync completed"
    )
    detail_text = payload.detailText or (
        SYNC_DETAIL_BY_KIND[payload.syncKind]
        if is_demo
        else "The hardware bridge accepted the sync packet."
    )

    device.connection_state = "connected"
    device.transfer_state = payload.healthStatus
    if payload.firmwareVersion is not None:
        device.firmware_version = payload.firmwareVersion
    if payload.batteryPercent is not None:
        device.battery_percent = payload.batteryPercent
    device.last_sync_at = now

    sync_payload = dict(payload.payload or {})
    sync_payload.update(
        {
            "syncKind": payload.syncKind,
            "detailText": payload.detailText,
            "vibrationEventCount": payload.vibrationEventCount,
            "firmwareBefore": previous_firmware,
            "firmwareAfter": next_firmware,
            "provider": provider_mode,
            "providerResponse": provider_response,
        }
    )

    sync_event = DeviceSyncEvent(
        device_id=device.id,
        review_id=review_id,
        health_status=payload.healthStatus,
        summary_text=summary_text,
        payload_json=sync_payload,
    )
    session.add(sync_event)
    session.flush()

    sync_log = _create_log(
        session,
        device_id=device.id,
        review_id=review_id,
        event_type="sync",
        severity=_severity_for_health_status(payload.healthStatus),
        title_text=summary_text,
        detail_text=detail_text,
        payload_json={"syncRecordId": sync_event.id, "source": f"hardware-{provider_mode}"},
    )

    if is_demo:
        for index in range(payload.vibrationEventCount):
            _create_log(
                session,
                device_id=device.id,
                review_id=review_id,
                event_type="vibration",
                severity="warning",
                title_text=f"Demo vibration event {index + 1}",
                detail_text="Simulated vibration event captured for UI playback.",
                payload_json={"syncRecordId": sync_event.id, "sequence": index + 1},
            )

    session.commit()
    session.refresh(device)
    session.refresh(sync_event)
    session.refresh(sync_log)

    return HardwareSyncResponse(
        device=_build_device_summary(session, device),
        syncRecord=_build_sync_record_response(sync_event),
        log=_build_log_response(sync_log),
    )


def _build_review_sync_text(review: Review) -> tuple[str, str]:
    summary_payload = review.summary_json or {}
    headline = str(summary_payload.get("headline") or review.title_text)
    coach_summary = str(summary_payload.get("coachSummary") or "")
    next_step = str(summary_payload.get("nextStep") or "")
    detail_parts = [
        coach_summary,
        f"Next: {next_step}" if next_step else "",
    ]
    details = " ".join(part for part in detail_parts if part)
    if not details:
        details = f"Review {review.id} is ready to continue on device."
    return headline[:500], details[:2000]


def _build_review_packet(session: Session, review: Review) -> tuple[dict, str]:
    summary = review.summary_json or {}
    metrics = review.metrics_json or {}
    lines = session.scalars(
        select(ReviewLine)
        .where(ReviewLine.review_id == review.id)
        .order_by(ReviewLine.line_index.asc(), ReviewLine.created_at.asc(), ReviewLine.id.asc())
        .limit(12)
    ).all()
    packet = {
        "schemaVersion": "miro.review.packet.v1",
        "reviewId": review.id,
        "countryKey": review.country_key,
        "meetingType": review.meeting_type_key,
        "goal": review.goal_key,
        "overallAssessment": review.overall_assessment,
        "score": review.score_total,
        "summary": {
            "headline": summary.get("headline") or review.title_text,
            "coachSummary": summary.get("coachSummary") or "",
            "nextStep": summary.get("nextStep") or "",
        },
        "metrics": {
            "turnCount": metrics.get("turnCount", 0),
            "alertCount": metrics.get("alertCount", 0),
            "topIssueKeys": review.repeated_issues_json or [],
        },
        "lines": [
            {
                "speaker": line.speaker,
                "turnIndex": line.turn_index,
                "text": line.text or line.source_text,
            }
            for line in lines
        ],
    }
    serialized = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return packet, sha256(serialized.encode("utf-8")).hexdigest()


def get_review_packet(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> dict:
    review = _validate_review_for_actor(session, actor, review_id)
    packet, packet_hash = _build_review_packet(session, review)
    return {
        "reviewId": review.id,
        "schemaVersion": "miro.review.packet.v1",
        "packetHash": packet_hash,
        "packet": packet,
    }


def sync_review_to_default_device(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> HardwareSyncResponse:
    review = _validate_review_for_actor(session, actor, review_id)
    devices = _list_actor_devices(session, actor)
    device = next((item for item in devices if item.connection_state == "connected"), devices[0])
    review.device_id = device.id
    summary_text, detail_text = _build_review_sync_text(review)
    packet, packet_hash = _build_review_packet(session, review)

    return sync_device(
        session,
        actor,
        device.id,
        HardwareSyncRequest(
            syncKind="download",
            healthStatus="healthy",
            summaryText=summary_text,
            detailText=detail_text,
            batteryPercent=device.battery_percent,
            reviewId=review.id,
            vibrationEventCount=1,
            payload={
                "source": "review_auto_sync",
                "schemaVersion": "miro.review.packet.v1",
                "packetHash": packet_hash,
                "reviewPacket": packet,
                "overallAssessment": review.overall_assessment,
                "topIssueKeys": review.repeated_issues_json or [],
            },
        ),
    )


def get_device_logs(
    session: Session,
    actor: CurrentActor,
    device_id: str,
) -> list[HardwareDeviceLogResponse]:
    device = _get_actor_device(session, actor, device_id)
    logs = session.scalars(
        select(DeviceLog)
        .where(DeviceLog.device_id == device.id)
        .order_by(DeviceLog.created_at.desc(), DeviceLog.id.desc())
    )
    return [_build_log_response(log) for log in logs]


def get_device_sync_records(
    session: Session,
    actor: CurrentActor,
    device_id: str,
) -> list[HardwareDeviceSyncRecordResponse]:
    device = _get_actor_device(session, actor, device_id)
    events = session.scalars(
        select(DeviceSyncEvent)
        .where(DeviceSyncEvent.device_id == device.id)
        .order_by(DeviceSyncEvent.created_at.desc(), DeviceSyncEvent.id.desc())
    )
    return [_build_sync_record_response(event) for event in events]
