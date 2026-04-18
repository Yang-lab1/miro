"""Per-session bridge between a frontend WebSocket and a Doubao WebSocket.

The frontend talks JSON + base64 PCM16 frames. The Doubao side talks binary
frames encoded by `doubao_protocol`. This module:

1. Opens a Doubao WebSocket using configured credentials.
2. Fans browser messages → Doubao frames (audio + control).
3. Fans Doubao events → browser JSON (user_transcript, assistant_text,
   assistant_audio_chunk, assistant_turn_end, error).
4. Persists recognised user turn + assistant turn to `realtime_session_turns`
   so the rest of the app (history, review, metrics) can observe real data.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.simulation import RealtimeSession, RealtimeSessionTurn
from app.modules.realtime.doubao_client import (
    DoubaoClient,
    DoubaoClientError,
    DoubaoCredentials,
    DoubaoSessionConfig,
)
from app.modules.realtime.observability import RealtimeObservabilityTracker
from app.modules.realtime.doubao_protocol import (
    MSG_TYPE_ERROR,
    DoubaoFrame,
    ServerEvent,
)
from app.services.current_actor import CurrentActor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Browser-facing protocol helpers
# ---------------------------------------------------------------------------


class BrowserSocket:
    """Thin protocol for the frontend side of the bridge.

    Both FastAPI's `WebSocket` and a test fake can satisfy this shape. We only
    use `receive_text` / `receive_bytes` / `send_text` / `send_bytes` / `close`.
    """

    async def receive_text(self) -> str: ...  # pragma: no cover
    async def receive_bytes(self) -> bytes: ...  # pragma: no cover
    async def send_text(self, data: str) -> None: ...  # pragma: no cover
    async def send_json(self, data: Any) -> None: ...  # pragma: no cover
    async def receive(self) -> dict: ...  # pragma: no cover
    async def close(self, code: int = 1000) -> None: ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Proxy state
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _TurnAccumulator:
    """Accumulates ASR/Chat text fragments into per-turn buffers."""

    user_text: str = ""
    assistant_text: str = ""
    user_recorded: bool = False
    assistant_recorded: bool = False
    # Pre-reserved turn indices. Filled lazily when the first ASR final arrives.
    user_turn_index: int | None = None
    assistant_turn_index: int | None = None
    # Which turns we've already written to the DB this cycle.
    user_turn_started_at: datetime | None = None
    user_turn_ended_at: datetime | None = None
    assistant_turn_started_at: datetime | None = None
    assistant_turn_ended_at: datetime | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.user_text = ""
        self.assistant_text = ""
        self.user_recorded = False
        self.assistant_recorded = False
        self.user_turn_index = None
        self.assistant_turn_index = None
        self.user_turn_started_at = None
        self.user_turn_ended_at = None
        self.assistant_turn_started_at = None
        self.assistant_turn_ended_at = None
        self.extras = {}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_doubao_credentials_from_settings() -> DoubaoCredentials:
    settings = get_settings()
    if not settings.doubao_app_id or not settings.doubao_access_token:
        raise AppError(
            status_code=503,
            code="doubao_not_configured",
            message="Doubao credentials are not configured on the backend.",
            details={
                "hint": (
                    "Set DOUBAO_APP_ID and DOUBAO_ACCESS_TOKEN in backend/.env, "
                    "then restart uvicorn."
                )
            },
        )
    return DoubaoCredentials(
        app_id=settings.doubao_app_id,
        access_token=settings.doubao_access_token,
        secret_key=settings.doubao_secret_key or "",
        resource_id=settings.doubao_resource_id,
        app_key=settings.doubao_app_key,
    )


async def run_doubao_voice_bridge(
    *,
    db: Session,
    actor: CurrentActor,
    realtime_session: RealtimeSession,
    browser_ws: BrowserSocket,
) -> None:
    """Run the voice bridge until either side closes."""

    settings = get_settings()
    credentials = build_doubao_credentials_from_settings()
    tracker = RealtimeObservabilityTracker(realtime_session.id)
    session_cfg = DoubaoSessionConfig(
        speaker=settings.doubao_speaker,
        model=settings.doubao_model,
        input_mod="push_to_talk",
    )

    client = DoubaoClient(credentials=credentials)

    try:
        await client.connect()
    except DoubaoClientError as exc:
        logger.warning("doubao_proxy.connect_failed error=%s", exc)
        tracker.record_event(
            source="backend",
            event_type="error",
            payload_summary={"stage": "connect"},
            error_code="doubao_connect_failed",
            error_message=str(exc),
        )
        await _send_browser_json(
            browser_ws,
            {"type": "error", "code": "doubao_connect_failed", "message": str(exc)},
        )
        await browser_ws.close(code=1011)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao_proxy.connect_unexpected error=%s", exc)
        tracker.record_event(
            source="backend",
            event_type="error",
            payload_summary={"stage": "connect_unexpected"},
            error_code="doubao_connect_unexpected",
            error_message=str(exc),
        )
        await _send_browser_json(
            browser_ws,
            {
                "type": "error",
                "code": "doubao_connect_unexpected",
                "message": "Failed to open the Doubao WebSocket.",
            },
        )
        await browser_ws.close(code=1011)
        return

    try:
        await client.start_connection()
        doubao_session_id = await client.start_session(config=session_cfg)
        await _send_browser_json(
            browser_ws,
            {
                "type": "ready",
                "doubaoSessionId": doubao_session_id,
                "realtimeSessionId": realtime_session.id,
                "tts": {
                    "format": session_cfg.tts_format,
                    "sampleRate": session_cfg.tts_sample_rate,
                    "channels": 1,
                },
                "input": {
                    "format": "pcm_s16le",
                    "sampleRate": 16000,
                    "channels": 1,
                },
            },
        )
        tracker.record_event(
            source="backend",
            event_type="voice_ws_ready",
            payload_summary={
                "doubaoSessionId": doubao_session_id,
                "inputSampleRate": 16000,
                "ttsSampleRate": session_cfg.tts_sample_rate,
            },
            set_values={
                "voice_ws_ready": True,
                "doubao_session_id": doubao_session_id,
                "session_status": realtime_session.session_status,
            },
        )

        accumulator = _TurnAccumulator()

        browser_task = asyncio.create_task(
            _pump_browser_to_doubao(browser_ws, client, tracker=tracker),
            name="doubao_proxy.browser_to_doubao",
        )
        doubao_task = asyncio.create_task(
            _pump_doubao_to_browser(
                client=client,
                browser_ws=browser_ws,
                db=db,
                actor=actor,
                realtime_session=realtime_session,
                accumulator=accumulator,
                tracker=tracker,
            ),
            name="doubao_proxy.doubao_to_browser",
        )

        done, pending = await asyncio.wait(
            {browser_task, doubao_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done | pending:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("doubao_proxy.task_failed name=%s error=%s", task.get_name(), exc)

    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Browser → Doubao
# ---------------------------------------------------------------------------


async def _pump_browser_to_doubao(
    browser_ws: BrowserSocket,
    client: DoubaoClient,
    *,
    tracker: RealtimeObservabilityTracker,
) -> None:
    while True:
        try:
            message = await browser_ws.receive()
        except Exception as exc:  # noqa: BLE001
            logger.info("doubao_proxy.browser_disconnect error=%s", exc)
            return

        if message.get("type") == "websocket.disconnect":
            return

        text_payload = message.get("text")
        bytes_payload = message.get("bytes")

        if bytes_payload:
            frame_bytes = bytes(bytes_payload)
            frame_size = len(frame_bytes)
            tracker.record_event(
                source="frontend",
                event_type="client_audio_frame",
                payload_summary={"bytes": frame_size, "format": "pcm_s16le"},
                payload_size=frame_size,
                increments={
                    "client_audio_frame_count": 1,
                    "client_audio_total_bytes": frame_size,
                },
            )
            tracker.record_event(
                source="backend",
                event_type="server_audio_received",
                payload_summary={"bytes": frame_size, "transport": "binary"},
                payload_size=frame_size,
                increments={
                    "server_received_audio_frame_count": 1,
                    "server_received_audio_total_bytes": frame_size,
                },
            )
            # Raw binary frame from the browser — assume PCM16 LE.
            try:
                await client.send_audio_chunk(frame_bytes)
                tracker.record_event(
                    source="backend",
                    event_type="server_audio_forwarded",
                    payload_summary={"bytes": frame_size, "transport": "binary"},
                    payload_size=frame_size,
                    increments={
                        "server_forwarded_audio_frame_count": 1,
                        "server_forwarded_audio_total_bytes": frame_size,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("doubao_proxy.audio_forward_failed error=%s", exc)
                tracker.record_event(
                    source="backend",
                    event_type="error",
                    payload_summary={"stage": "audio_forward_binary", "bytes": frame_size},
                    error_code="audio_forward_failed",
                    error_message=str(exc),
                )
            continue

        if not text_payload:
            continue

        try:
            parsed = json.loads(text_payload)
        except json.JSONDecodeError:
            logger.debug("doubao_proxy.non_json_text message=%s", text_payload[:200])
            continue

        msg_type = parsed.get("type")
        if msg_type == "audio":
            b64 = parsed.get("data") or parsed.get("audioBase64") or ""
            try:
                raw = base64.b64decode(b64)
            except Exception as exc:  # noqa: BLE001
                logger.warning("doubao_proxy.b64_decode_failed error=%s", exc)
                tracker.record_event(
                    source="backend",
                    event_type="error",
                    payload_summary={"stage": "b64_decode", "chars": len(b64)},
                    error_code="browser_audio_decode_failed",
                    error_message=str(exc),
                )
                continue
            if raw:
                frame_size = len(raw)
                tracker.record_event(
                    source="frontend",
                    event_type="client_audio_frame",
                    payload_summary={"bytes": frame_size, "format": "pcm_s16le"},
                    payload_size=frame_size,
                    increments={
                        "client_audio_frame_count": 1,
                        "client_audio_total_bytes": frame_size,
                    },
                )
                tracker.record_event(
                    source="backend",
                    event_type="server_audio_received",
                    payload_summary={"bytes": frame_size, "transport": "json_base64"},
                    payload_size=frame_size,
                    increments={
                        "server_received_audio_frame_count": 1,
                        "server_received_audio_total_bytes": frame_size,
                    },
                )
                try:
                    await client.send_audio_chunk(raw)
                    tracker.record_event(
                        source="backend",
                        event_type="server_audio_forwarded",
                        payload_summary={"bytes": frame_size, "transport": "json_base64"},
                        payload_size=frame_size,
                        increments={
                            "server_forwarded_audio_frame_count": 1,
                            "server_forwarded_audio_total_bytes": frame_size,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("doubao_proxy.audio_forward_failed error=%s", exc)
                    tracker.record_event(
                        source="backend",
                        event_type="error",
                        payload_summary={"stage": "audio_forward_json", "bytes": frame_size},
                        error_code="audio_forward_failed",
                        error_message=str(exc),
                    )
        elif msg_type == "end_segment":
            # Explicitly declare the end of the current utterance so upstream
            # can leave ASR and enter assistant response generation.
            try:
                await client.end_asr()
            except Exception as exc:  # noqa: BLE001
                logger.warning("doubao_proxy.end_asr_failed error=%s", exc)
                tracker.record_event(
                    source="backend",
                    event_type="error",
                    payload_summary={"stage": "end_asr"},
                    error_code="end_asr_failed",
                    error_message=str(exc),
                )
        elif msg_type == "interrupt":
            await client.send_client_interrupt()
        elif msg_type == "hello":
            text = str(parsed.get("text", "")).strip()
            if text:
                await client.say_hello(text)
        elif msg_type == "finish":
            await client.finish_session()
            return
        else:
            logger.debug("doubao_proxy.unhandled_browser_message type=%s", msg_type)


# ---------------------------------------------------------------------------
# Doubao → Browser
# ---------------------------------------------------------------------------


async def _pump_doubao_to_browser(
    *,
    client: DoubaoClient,
    browser_ws: BrowserSocket,
    db: Session,
    actor: CurrentActor,
    realtime_session: RealtimeSession,
    accumulator: _TurnAccumulator,
    tracker: RealtimeObservabilityTracker,
) -> None:
    from app.modules.realtime import service as realtime_service  # local import to dodge cycles

    async for frame in client.frames():
        try:
            await _handle_doubao_frame(
                frame=frame,
                browser_ws=browser_ws,
                db=db,
                actor=actor,
                realtime_session=realtime_session,
                accumulator=accumulator,
                tracker=tracker,
                realtime_service=realtime_service,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("doubao_proxy.frame_handler_failed error=%s", exc)


async def _handle_doubao_frame(
    *,
    frame: DoubaoFrame,
    browser_ws: BrowserSocket,
    db: Session,
    actor: CurrentActor,
    realtime_session: RealtimeSession,
    accumulator: _TurnAccumulator,
    tracker: RealtimeObservabilityTracker,
    realtime_service: Any,
) -> None:
    if frame.is_error or frame.message_type == MSG_TYPE_ERROR:
        payload_text = _decode_payload_text(frame.payload)
        error_code = frame.extras.get("error_code")
        logger.warning(
            "doubao_proxy.error_frame event=%s code=%s payload=%s",
            frame.event_id,
            error_code,
            payload_text[:200],
        )
        await _send_browser_json(
            browser_ws,
            {
                "type": "error",
                "code": str(error_code) if error_code is not None else "doubao_error",
                "message": payload_text or "Doubao returned an error frame.",
            },
        )
        tracker.record_event(
            source="upstream",
            event_type="error",
            payload_summary={"eventId": frame.event_id, "payload": payload_text[:200]},
            error_code=str(error_code) if error_code is not None else "doubao_error",
            error_message=payload_text or "Doubao returned an error frame.",
        )
        return

    event = frame.event_id
    if event is None:
        return

    if event == int(ServerEvent.CONNECTION_STARTED):
        logger.info("doubao_proxy.connection_started")
        return
    if event == int(ServerEvent.CONNECTION_FAILED):
        payload_text = _decode_payload_text(frame.payload)
        logger.warning("doubao_proxy.connection_failed payload=%s", payload_text)
        await _send_browser_json(
            browser_ws,
            {
                "type": "error",
                "code": "doubao_connection_failed",
                "message": payload_text or "Doubao connection failed.",
            },
        )
        tracker.record_event(
            source="upstream",
            event_type="error",
            payload_summary={"eventId": event, "payload": payload_text[:200]},
            error_code="doubao_connection_failed",
            error_message=payload_text or "Doubao connection failed.",
        )
        return

    if event == int(ServerEvent.SESSION_STARTED):
        logger.info("doubao_proxy.session_started session=%s", frame.session_id)
        tracker.sync_session_state(
            doubao_session_id=frame.session_id,
            session_status=realtime_session.session_status,
        )
        return
    if event == int(ServerEvent.SESSION_FAILED):
        payload_text = _decode_payload_text(frame.payload)
        logger.warning("doubao_proxy.session_failed payload=%s", payload_text)
        await _send_browser_json(
            browser_ws,
            {
                "type": "error",
                "code": "doubao_session_failed",
                "message": payload_text or "Doubao session failed.",
            },
        )
        tracker.record_event(
            source="upstream",
            event_type="error",
            payload_summary={"eventId": event, "payload": payload_text[:200]},
            error_code="doubao_session_failed",
            error_message=payload_text or "Doubao session failed.",
        )
        return
    if event == int(ServerEvent.SESSION_FINISHED):
        logger.info("doubao_proxy.session_finished")
        await _send_browser_json(browser_ws, {"type": "session_finished"})
        return

    if event in (int(ServerEvent.ASR_INFO), int(ServerEvent.ASR_RESPONSE)):
        payload = _decode_payload_json(frame.payload)
        text = _extract_asr_text(payload)
        is_final = bool(payload.get("is_final") or payload.get("isFinal"))
        if text:
            accumulator.user_text = text
            if accumulator.user_turn_started_at is None:
                accumulator.user_turn_started_at = _utcnow()
            await _send_browser_json(
                browser_ws,
                {
                    "type": "user_transcript",
                    "text": text,
                    "isFinal": is_final,
                },
            )
            tracker.record_event(
                source="upstream",
                event_type="user_transcript",
                payload_summary={"text": text[:200], "isFinal": is_final},
                payload_size=len(text.encode("utf-8", errors="ignore")),
                increments={"user_transcript_event_count": 1},
                set_values={"last_user_turn_at": _utcnow() if is_final else None},
            )
        if is_final:
            accumulator.user_turn_ended_at = _utcnow()
            await _persist_user_turn_if_needed(
                db=db,
                actor=actor,
                realtime_session=realtime_session,
                accumulator=accumulator,
                tracker=tracker,
                realtime_service=realtime_service,
            )
        return

    if event == int(ServerEvent.ASR_ENDED):
        accumulator.user_turn_ended_at = _utcnow()
        return

    if event in (int(ServerEvent.CHAT_RESPONSE), int(ServerEvent.TTS_SENTENCE_START)):
        payload = _decode_payload_json(frame.payload)
        text_fragment = _extract_chat_text(payload)
        if text_fragment:
            if accumulator.assistant_turn_started_at is None:
                accumulator.assistant_turn_started_at = _utcnow()
            accumulator.assistant_text += text_fragment
            await _send_browser_json(
                browser_ws,
                {
                    "type": "assistant_text",
                    "text": accumulator.assistant_text,
                    "delta": text_fragment,
                    "isFinal": False,
                },
            )
            tracker.record_event(
                source="upstream",
                event_type="assistant_text",
                payload_summary={
                    "delta": text_fragment[:200],
                    "text": accumulator.assistant_text[:200],
                    "isFinal": False,
                },
                payload_size=len(text_fragment.encode("utf-8", errors="ignore")),
                increments={"assistant_text_event_count": 1},
            )
        return

    if event == int(ServerEvent.CHAT_ENDED):
        await _send_browser_json(
            browser_ws,
            {
                "type": "assistant_text",
                "text": accumulator.assistant_text,
                "delta": "",
                "isFinal": True,
            },
        )
        tracker.record_event(
            source="upstream",
            event_type="assistant_text",
            payload_summary={"text": accumulator.assistant_text[:200], "isFinal": True},
            payload_size=len(accumulator.assistant_text.encode("utf-8", errors="ignore")),
            increments={"assistant_text_event_count": 1},
        )
        return

    if event == int(ServerEvent.TTS_RESPONSE):
        if frame.is_audio and frame.payload:
            await _send_browser_json(
                browser_ws,
                {
                    "type": "assistant_audio_chunk",
                    "data": base64.b64encode(frame.payload).decode("ascii"),
                    "format": "pcm_s16le",
                    "sampleRate": 24000,
                },
            )
            tracker.record_event(
                source="upstream",
                event_type="assistant_audio_chunk",
                payload_summary={"bytes": len(frame.payload), "sampleRate": 24000},
                payload_size=len(frame.payload),
                increments={"assistant_audio_chunk_count": 1},
            )
        return

    if event == int(ServerEvent.TTS_SENTENCE_END):
        return

    if event == int(ServerEvent.TTS_ENDED):
        accumulator.assistant_turn_ended_at = _utcnow()
        await _persist_assistant_turn_if_needed(
            db=db,
            actor=actor,
            realtime_session=realtime_session,
            accumulator=accumulator,
            tracker=tracker,
            realtime_service=realtime_service,
        )
        await _send_browser_json(browser_ws, {"type": "assistant_turn_end"})
        tracker.record_event(
            source="upstream",
            event_type="assistant_turn_end",
            payload_summary={"text": accumulator.assistant_text[:200]},
            increments={"assistant_turn_end_count": 1},
            set_values={"last_assistant_turn_at": _utcnow()},
        )
        return

    if event == int(ServerEvent.DIALOG_COMMON_ERROR):
        payload_text = _decode_payload_text(frame.payload)
        logger.warning("doubao_proxy.dialog_common_error payload=%s", payload_text)
        await _send_browser_json(
            browser_ws,
            {
                "type": "error",
                "code": "dialog_common_error",
                "message": payload_text,
            },
        )
        tracker.record_event(
            source="upstream",
            event_type="error",
            payload_summary={"eventId": event, "payload": payload_text[:200]},
            error_code="dialog_common_error",
            error_message=payload_text,
        )
        return

    logger.debug("doubao_proxy.unhandled_event event=%s", event)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def _persist_user_turn_if_needed(
    *,
    db: Session,
    actor: CurrentActor,
    realtime_session: RealtimeSession,
    accumulator: _TurnAccumulator,
    tracker: RealtimeObservabilityTracker,
    realtime_service: Any,
) -> None:
    if accumulator.user_recorded:
        return
    if not accumulator.user_text.strip():
        return

    try:
        user_idx, assistant_idx = realtime_service._reserve_turn_index_pair(  # type: ignore[attr-defined]
            db, realtime_session
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("doubao_proxy.reserve_turn_failed error=%s", exc)
        tracker.record_event(
            source="backend",
            event_type="error",
            payload_summary={"stage": "reserve_user_turn_pair"},
            error_code="reserve_turn_failed",
            error_message=str(exc),
        )
        return

    accumulator.user_turn_index = user_idx
    accumulator.assistant_turn_index = assistant_idx

    user_turn = RealtimeSessionTurn(
        session_id=realtime_session.id,
        turn_index=user_idx,
        speaker="user",
        input_mode="voice",
        source_text=accumulator.user_text,
        normalized_text=_normalize(accumulator.user_text),
        language=None,
        started_at=accumulator.user_turn_started_at,
        ended_at=accumulator.user_turn_ended_at or _utcnow(),
    )
    db.add(user_turn)

    realtime_session.last_user_turn_at = user_turn.ended_at
    realtime_session.turn_count = int(realtime_session.turn_count or 0) + 1

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("doubao_proxy.persist_user_turn_failed error=%s", exc)
        tracker.record_event(
            source="db",
            event_type="error",
            payload_summary={"stage": "persist_user_turn"},
            error_code="persist_user_turn_failed",
            error_message=str(exc),
        )
        return

    accumulator.user_recorded = True
    tracker.record_event(
        source="db",
        event_type="db_turn_persisted",
        payload_summary={
            "speaker": "user",
            "turnIndex": user_turn.turn_index,
            "text": accumulator.user_text[:200],
        },
        increments={"persisted_turn_count": 1},
        set_values={"last_user_turn_at": user_turn.ended_at},
    )


async def _persist_assistant_turn_if_needed(
    *,
    db: Session,
    actor: CurrentActor,
    realtime_session: RealtimeSession,
    accumulator: _TurnAccumulator,
    tracker: RealtimeObservabilityTracker,
    realtime_service: Any,
) -> None:
    if accumulator.assistant_recorded:
        return
    if not accumulator.assistant_text.strip():
        return
    # If user turn was never persisted (no ASR final), reserve a standalone pair now.
    if accumulator.assistant_turn_index is None:
        try:
            _, assistant_idx = realtime_service._reserve_turn_index_pair(  # type: ignore[attr-defined]
                db, realtime_session
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("doubao_proxy.reserve_assistant_turn_failed error=%s", exc)
            tracker.record_event(
                source="backend",
                event_type="error",
                payload_summary={"stage": "reserve_assistant_turn_pair"},
                error_code="reserve_assistant_turn_failed",
                error_message=str(exc),
            )
            return
        accumulator.assistant_turn_index = assistant_idx

    assistant_turn = RealtimeSessionTurn(
        session_id=realtime_session.id,
        turn_index=accumulator.assistant_turn_index,
        speaker="assistant",
        input_mode="voice",
        source_text=accumulator.assistant_text,
        normalized_text=_normalize(accumulator.assistant_text),
        language=None,
        started_at=accumulator.assistant_turn_started_at,
        ended_at=accumulator.assistant_turn_ended_at or _utcnow(),
    )
    db.add(assistant_turn)

    realtime_session.last_assistant_turn_at = assistant_turn.ended_at
    realtime_session.turn_count = int(realtime_session.turn_count or 0) + 1

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("doubao_proxy.persist_assistant_turn_failed error=%s", exc)
        tracker.record_event(
            source="db",
            event_type="error",
            payload_summary={"stage": "persist_assistant_turn"},
            error_code="persist_assistant_turn_failed",
            error_message=str(exc),
        )
        return

    accumulator.assistant_recorded = True
    tracker.record_event(
        source="db",
        event_type="db_turn_persisted",
        payload_summary={
            "speaker": "assistant",
            "turnIndex": assistant_turn.turn_index,
            "text": accumulator.assistant_text[:200],
        },
        increments={"persisted_turn_count": 1},
        set_values={"last_assistant_turn_at": assistant_turn.ended_at},
    )

    # Prepare for the next turn cycle — keep the accumulator alive but reset.
    accumulator.reset()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _decode_payload_text(payload: bytes) -> str:
    if not payload:
        return ""
    try:
        return payload.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _decode_payload_json(payload: bytes) -> dict[str, Any]:
    text = _decode_payload_text(payload)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _extract_asr_text(payload: dict) -> str:
    """Doubao ASR responses place transcript text under a few shapes; normalise."""

    if not payload:
        return ""
    direct = payload.get("text")
    if isinstance(direct, str) and direct:
        return direct
    results = payload.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            text = first.get("text") or first.get("sentence")
            if isinstance(text, str):
                return text
    result = payload.get("result")
    if isinstance(result, dict):
        text = result.get("text") or result.get("sentence")
        if isinstance(text, str):
            return text
    return ""


def _extract_chat_text(payload: dict) -> str:
    if not payload:
        return ""
    for key in ("text", "content", "delta", "response_text"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    content = payload.get("message")
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        if isinstance(text, str):
            return text
    return ""


async def _send_browser_json(browser_ws: BrowserSocket, data: Any) -> None:
    try:
        await browser_ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.debug("doubao_proxy.browser_send_failed error=%s", exc)
