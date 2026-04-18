from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.db.session import get_session_factory
from app.models.realtime_observability import RealtimeSessionEvent, RealtimeSessionObservability

logger = logging.getLogger(__name__)

FINAL_STATUS_FULL_SUCCESS = "full_success"
FINAL_STATUS_NO_CLIENT_AUDIO = "no_client_audio"
FINAL_STATUS_CLIENT_AUDIO_NOT_RECEIVED = "client_audio_sent_but_backend_not_received"
FINAL_STATUS_BACKEND_NOT_FORWARDED = "backend_received_but_not_forwarded"
FINAL_STATUS_NO_UPSTREAM_RESPONSE = "forwarded_but_no_upstream_response"
FINAL_STATUS_ASR_ONLY = "asr_only"
FINAL_STATUS_TEXT_ONLY = "text_only"
FINAL_STATUS_AUDIO_ONLY = "audio_only"
FINAL_STATUS_FRONTEND_RENDER_UNKNOWN = "frontend_render_unknown"
FINAL_STATUS_ERROR = "error"
FINAL_STATUS_DIAGNOSTIC_INCOMPLETE = "diagnostic_incomplete"

ROOT_NONE = "NONE"
ROOT_BROWSER_NO_AUDIO = "A_browser_no_audio"
ROOT_BACKEND_NO_AUDIO = "B_backend_no_audio"
ROOT_UPSTREAM_NO_RESPONSE = "C_upstream_no_asr_chat_tts"
ROOT_FRONTEND_RENDER_MISSING = "D_frontend_render_missing"
ROOT_EVIDENCE_INVALID = "E_evidence_invalid"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _json_summary(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text[:1000] if text else None
    try:
        return json.dumps(value, ensure_ascii=False)[:1000]
    except Exception:  # noqa: BLE001
        return str(value)[:1000]


def _derive_status(row: RealtimeSessionObservability) -> tuple[str, str]:
    if (
        row.user_transcript_event_count > 0
        and row.assistant_text_event_count > 0
        and row.assistant_audio_chunk_count > 0
        and row.assistant_turn_end_count > 0
        and row.persisted_turn_count > 0
    ):
        return FINAL_STATUS_FULL_SUCCESS, ROOT_NONE

    if row.client_connected and row.client_audio_frame_count <= 0:
        return FINAL_STATUS_NO_CLIENT_AUDIO, ROOT_BROWSER_NO_AUDIO

    if row.client_audio_frame_count > 0 and row.server_received_audio_frame_count <= 0:
        return FINAL_STATUS_CLIENT_AUDIO_NOT_RECEIVED, ROOT_BACKEND_NO_AUDIO

    if row.server_received_audio_frame_count > 0 and row.server_forwarded_audio_frame_count <= 0:
        return FINAL_STATUS_BACKEND_NOT_FORWARDED, ROOT_BACKEND_NO_AUDIO

    if (
        row.server_forwarded_audio_frame_count > 0
        and row.user_transcript_event_count <= 0
        and row.assistant_text_event_count <= 0
        and row.assistant_audio_chunk_count <= 0
    ):
        return FINAL_STATUS_NO_UPSTREAM_RESPONSE, ROOT_UPSTREAM_NO_RESPONSE

    if (
        row.user_transcript_event_count > 0
        and row.assistant_text_event_count <= 0
        and row.assistant_audio_chunk_count <= 0
    ):
        return FINAL_STATUS_ASR_ONLY, ROOT_UPSTREAM_NO_RESPONSE

    if row.assistant_text_event_count > 0 and row.assistant_audio_chunk_count <= 0:
        return FINAL_STATUS_TEXT_ONLY, ROOT_UPSTREAM_NO_RESPONSE

    if row.assistant_audio_chunk_count > 0 and row.assistant_text_event_count <= 0:
        return FINAL_STATUS_AUDIO_ONLY, ROOT_UPSTREAM_NO_RESPONSE

    if (
        row.user_transcript_event_count > 0
        and row.assistant_text_event_count > 0
        and row.assistant_audio_chunk_count > 0
        and row.persisted_turn_count <= 0
    ):
        return FINAL_STATUS_FRONTEND_RENDER_UNKNOWN, ROOT_FRONTEND_RENDER_MISSING

    if row.error_count > 0:
        if row.client_audio_frame_count <= 0:
            return FINAL_STATUS_ERROR, ROOT_BROWSER_NO_AUDIO
        if row.server_forwarded_audio_frame_count <= 0:
            return FINAL_STATUS_ERROR, ROOT_BACKEND_NO_AUDIO
        return FINAL_STATUS_ERROR, ROOT_UPSTREAM_NO_RESPONSE

    return FINAL_STATUS_DIAGNOSTIC_INCOMPLETE, ROOT_NONE


@dataclass(slots=True)
class _ObservationUpdate:
    set_values: dict[str, Any] = field(default_factory=dict)
    increments: dict[str, int] = field(default_factory=dict)
    payload_summary: str | None = None
    payload_size: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class RealtimeObservabilityTracker:
    def __init__(self, realtime_session_id: str) -> None:
        self.realtime_session_id = realtime_session_id

    def sync_session_state(
        self,
        *,
        session_status: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        doubao_session_id: str | None = None,
    ) -> None:
        update = _ObservationUpdate(
            set_values={
                "session_status": session_status,
                "started_at": started_at,
                "ended_at": ended_at,
                "doubao_session_id": doubao_session_id,
            }
        )
        self._write_observation(None, None, update)

    def record_event(
        self,
        *,
        source: str,
        event_type: str,
        payload_summary: Any = None,
        payload_size: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        set_values: dict[str, Any] | None = None,
        increments: dict[str, int] | None = None,
    ) -> None:
        update = _ObservationUpdate(
            set_values=set_values or {},
            increments=increments or {},
            payload_summary=_json_summary(payload_summary),
            payload_size=payload_size,
            error_code=error_code,
            error_message=error_message,
        )
        self._write_observation(source, event_type, update)

    def finalize(
        self,
        *,
        session_status: str | None = None,
        ended_at: datetime | None = None,
        final_status: str | None = None,
        root_block_point: str | None = None,
        payload_summary: Any = None,
    ) -> None:
        update = _ObservationUpdate(
            set_values={
                "session_status": session_status,
                "ended_at": ended_at or _utcnow(),
                "final_status": final_status,
                "root_block_point": root_block_point,
            },
            payload_summary=_json_summary(payload_summary),
        )
        self._write_observation("system", "healthcheck_finished", update)

    def build_report(self) -> dict[str, Any]:
        session = get_session_factory()()
        try:
            summary = session.scalar(
                select(RealtimeSessionObservability)
                .where(RealtimeSessionObservability.realtime_session_id == self.realtime_session_id)
                .limit(1)
            )
            events = session.scalars(
                select(RealtimeSessionEvent)
                .where(RealtimeSessionEvent.realtime_session_id == self.realtime_session_id)
                .order_by(RealtimeSessionEvent.sequence_no.asc(), RealtimeSessionEvent.event_time.asc())
            ).all()
            if summary is None:
                return {}
            return {
                "realtime_session_id": summary.realtime_session_id,
                "doubao_session_id": summary.doubao_session_id,
                "session_status": summary.session_status,
                "started_at": summary.started_at.isoformat() if summary.started_at else None,
                "ended_at": summary.ended_at.isoformat() if summary.ended_at else None,
                "client_connected": summary.client_connected,
                "voice_ws_ready": summary.voice_ws_ready,
                "client_audio_frame_count": summary.client_audio_frame_count,
                "client_audio_total_bytes": summary.client_audio_total_bytes,
                "server_received_audio_frame_count": summary.server_received_audio_frame_count,
                "server_received_audio_total_bytes": summary.server_received_audio_total_bytes,
                "server_forwarded_audio_frame_count": summary.server_forwarded_audio_frame_count,
                "server_forwarded_audio_total_bytes": summary.server_forwarded_audio_total_bytes,
                "user_transcript_event_count": summary.user_transcript_event_count,
                "assistant_text_event_count": summary.assistant_text_event_count,
                "assistant_audio_chunk_count": summary.assistant_audio_chunk_count,
                "assistant_turn_end_count": summary.assistant_turn_end_count,
                "persisted_turn_count": summary.persisted_turn_count,
                "last_user_turn_at": (
                    summary.last_user_turn_at.isoformat() if summary.last_user_turn_at else None
                ),
                "last_assistant_turn_at": (
                    summary.last_assistant_turn_at.isoformat()
                    if summary.last_assistant_turn_at
                    else None
                ),
                "error_count": summary.error_count,
                "last_error_code": summary.last_error_code,
                "last_error_message": summary.last_error_message,
                "final_status": summary.final_status,
                "root_block_point": summary.root_block_point,
                "event_timeline": [
                    {
                        "sequence_no": event.sequence_no,
                        "event_time": event.event_time.isoformat(),
                        "source": event.source,
                        "event_type": event.event_type,
                        "payload_summary": event.payload_summary,
                        "payload_size": event.payload_size,
                        "error_code": event.error_code,
                        "error_message": event.error_message,
                    }
                    for event in events
                ],
            }
        finally:
            session.close()

    def _write_observation(
        self,
        source: str | None,
        event_type: str | None,
        update: _ObservationUpdate,
    ) -> None:
        session = get_session_factory()()
        try:
            row = session.scalar(
                select(RealtimeSessionObservability)
                .where(RealtimeSessionObservability.realtime_session_id == self.realtime_session_id)
                .limit(1)
            )
            if row is None:
                row = RealtimeSessionObservability(
                    realtime_session_id=self.realtime_session_id,
                    final_status=FINAL_STATUS_DIAGNOSTIC_INCOMPLETE,
                    root_block_point=ROOT_NONE,
                )
                session.add(row)
                session.flush()

            for key, value in update.set_values.items():
                if value is not None:
                    setattr(row, key, value)

            for key, value in update.increments.items():
                current = int(getattr(row, key) or 0)
                setattr(row, key, current + int(value))

            if update.error_code or update.error_message:
                row.error_count = int(row.error_count or 0) + 1
                row.last_error_code = update.error_code or row.last_error_code
                row.last_error_message = update.error_message or row.last_error_message

            if "final_status" not in update.set_values or "root_block_point" not in update.set_values:
                final_status, root_block_point = _derive_status(row)
                row.final_status = final_status
                row.root_block_point = root_block_point

            if source and event_type:
                current_max_sequence = session.scalar(
                    select(func.max(RealtimeSessionEvent.sequence_no)).where(
                        RealtimeSessionEvent.realtime_session_id == self.realtime_session_id
                    )
                )
                next_sequence_no = int(current_max_sequence or 0) + 1
                session.add(
                    RealtimeSessionEvent(
                        realtime_session_id=self.realtime_session_id,
                        event_time=_utcnow(),
                        source=source,
                        event_type=event_type,
                        sequence_no=next_sequence_no,
                        payload_summary=update.payload_summary,
                        payload_size=update.payload_size,
                        error_code=update.error_code,
                        error_message=update.error_message,
                    )
                )

            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.warning(
                "realtime_observability.write_failed session=%s source=%s event=%s error=%s",
                self.realtime_session_id,
                source,
                event_type,
                exc,
            )
        finally:
            session.close()
