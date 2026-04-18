"""FastAPI WebSocket endpoint that proxies browser voice → Doubao realtime."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_session_factory
from app.models.simulation import RealtimeSession
from app.modules.realtime.doubao_proxy import run_doubao_voice_bridge
from app.modules.realtime.observability import RealtimeObservabilityTracker
from app.services.current_actor import resolve_current_actor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["realtime-voice"])


class _WebSocketRequestShim:
    """Lets `resolve_current_actor` (which expects a `Request`) read headers and query params.

    Supabase JWT can ride either the `Authorization` header (preferred) or the
    `?access_token=` query param (convenient for browsers that can't set custom
    headers on `WebSocket`). This shim exposes both in a FastAPI-Request-like shape.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self.headers = dict(websocket.headers)
        token = websocket.query_params.get("access_token")
        has_authorization = "authorization" in self.headers or "Authorization" in self.headers
        if token and not has_authorization:
            bearer = f"Bearer {token}"
            self.headers["authorization"] = bearer
            self.headers["Authorization"] = bearer
        self.query_params = dict(websocket.query_params)


@router.websocket("/sessions/{session_id}/voice")
async def realtime_voice_ws(websocket: WebSocket, session_id: str) -> None:
    # Accept first so we can cleanly send an error frame before closing.
    await websocket.accept()

    db: Session = get_session_factory()()
    tracker = RealtimeObservabilityTracker(session_id)
    try:
        try:
            actor = resolve_current_actor(db, _WebSocketRequestShim(websocket))  # type: ignore[arg-type]
        except AppError as exc:
            logger.info(
                "realtime_voice.auth_rejected code=%s session=%s",
                exc.code,
                session_id,
            )
            tracker.record_event(
                source="backend",
                event_type="error",
                payload_summary={"stage": "auth"},
                error_code=exc.code,
                error_message=exc.message,
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": exc.code,
                    "message": exc.message,
                }
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        realtime_session = db.get(RealtimeSession, session_id)
        if realtime_session is None or realtime_session.user_id != actor.user_id:
            tracker.record_event(
                source="backend",
                event_type="error",
                payload_summary={"stage": "session_lookup"},
                error_code="realtime_session_not_found",
                error_message=f"Realtime session '{session_id}' was not found.",
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "realtime_session_not_found",
                    "message": f"Realtime session '{session_id}' was not found.",
                }
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        tracker.record_event(
            source="frontend",
            event_type="voice_ws_open",
            payload_summary={
                "userId": actor.user_id,
                "sessionStatus": realtime_session.session_status,
            },
            set_values={
                "client_connected": True,
                "session_status": realtime_session.session_status,
                "started_at": realtime_session.started_at or datetime.now(tz=UTC),
            },
        )

        try:
            await run_doubao_voice_bridge(
                db=db,
                actor=actor,
                realtime_session=realtime_session,
                browser_ws=websocket,  # type: ignore[arg-type]
            )
        except WebSocketDisconnect:
            logger.info("realtime_voice.browser_disconnect session=%s", session_id)
        except AppError as exc:
            logger.warning(
                "realtime_voice.app_error session=%s code=%s",
                session_id,
                exc.code,
            )
            tracker.record_event(
                source="backend",
                event_type="error",
                payload_summary={"stage": "bridge_app_error"},
                error_code=exc.code,
                error_message=exc.message,
            )
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    }
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("realtime_voice.bridge_failed session=%s error=%s", session_id, exc)
            tracker.record_event(
                source="backend",
                event_type="error",
                payload_summary={"stage": "bridge_unexpected"},
                error_code="doubao_bridge_failed",
                error_message=str(exc),
            )
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "doubao_bridge_failed",
                        "message": "The Doubao bridge encountered an unexpected error.",
                    }
                )
            except Exception:  # noqa: BLE001
                pass
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
