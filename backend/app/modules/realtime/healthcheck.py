from __future__ import annotations

import asyncio
import base64
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.realtime import RealtimeSessionCreateRequest
from app.api.schemas.simulation import SimulationCreateRequest
from app.db.session import get_session_factory
from app.models.simulation import RealtimeSession, RealtimeSessionTurn
from app.models.user import User
from app.modules.realtime.doubao_proxy import BrowserSocket, run_doubao_voice_bridge
from app.modules.realtime.observability import (
    FINAL_STATUS_DIAGNOSTIC_INCOMPLETE,
    ROOT_EVIDENCE_INVALID,
    RealtimeObservabilityTracker,
)
from app.modules.realtime import service as realtime_service
from app.modules.simulation import service as simulation_service
from app.services.current_actor import CurrentActor

DEFAULT_AUDIO_FIXTURE = (
    Path(__file__).resolve().parents[3] / "scripts" / "fixtures" / "hello_can_you_hear_me.wav"
)


@dataclass(slots=True)
class SyntheticHealthCheckResult:
    realtime_session_id: str
    report: dict[str, Any]
    db_session: dict[str, Any] | None
    db_turns: list[dict[str, Any]]


class SyntheticBrowserSocket(BrowserSocket):
    def __init__(self) -> None:
        self._incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._closed = False
        self._done = asyncio.Event()
        self.sent_messages: list[dict[str, Any]] = []

    async def receive(self) -> dict[str, Any]:
        while True:
            if self._closed:
                return {"type": "websocket.disconnect"}
            if self._done.is_set() and self._incoming.empty():
                self._closed = True
                return {"type": "websocket.disconnect"}
            try:
                return await asyncio.wait_for(self._incoming.get(), timeout=0.1)
            except TimeoutError:
                continue

    async def send_text(self, data: str) -> None:
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            parsed = {"type": "text", "raw": data}
        await self.send_json(parsed)

    async def send_json(self, data: Any) -> None:
        message = data if isinstance(data, dict) else {"raw": data}
        self.sent_messages.append(message)
        if message.get("type") in {"assistant_turn_end", "error", "session_finished"}:
            self._done.set()

    async def receive_text(self) -> str:
        message = await self.receive()
        return str(message.get("text") or "")

    async def receive_bytes(self) -> bytes:
        message = await self.receive()
        return bytes(message.get("bytes") or b"")

    async def close(self, code: int = 1000) -> None:  # noqa: ARG002
        self._closed = True
        self._done.set()

    async def enqueue_text_message(self, payload: dict[str, Any]) -> None:
        await self._incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})

    async def mark_done(self) -> None:
        self._done.set()


def _resolve_healthcheck_actor(session: Session, user_email: str | None = None) -> CurrentActor:
    stmt = select(User).where(User.status == "active").order_by(User.created_at.asc())
    if user_email:
        stmt = select(User).where(User.email == user_email).limit(1)

    user = session.scalar(stmt.limit(1))
    if user is None and user_email:
        user = session.scalar(select(User).where(User.status == "active").order_by(User.created_at.asc()).limit(1))
    if user is None:
        raise RuntimeError("No active user is available for the realtime voice health check.")

    return CurrentActor(
        user_id=user.id,
        email=user.email,
        organization_id=None,
        auth_source="healthcheck",
    )


def _load_audio_chunks(audio_path: Path, frame_ms: int = 20) -> list[bytes]:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio fixture was not found: {audio_path}")

    with wave.open(str(audio_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        if sample_rate != 16000 or sample_width != 2 or channels != 1:
            raise RuntimeError(
                "Synthetic health check fixture must be mono PCM16 at 16kHz. "
                f"Got rate={sample_rate}, width={sample_width}, channels={channels}."
            )
        frame_count = int(sample_rate * frame_ms / 1000)
        chunks: list[bytes] = []
        while True:
            data = wav_file.readframes(frame_count)
            if not data:
                break
            chunks.append(data)
        return chunks


async def _stream_audio_fixture(
    browser_ws: SyntheticBrowserSocket,
    audio_chunks: list[bytes],
    *,
    frame_ms: int = 20,
) -> None:
    for chunk in audio_chunks:
        await browser_ws.enqueue_text_message(
            {
                "type": "audio",
                "data": base64.b64encode(chunk).decode("ascii"),
            }
        )
        await asyncio.sleep(frame_ms / 1000)
    await browser_ws.enqueue_text_message({"type": "end_segment"})


def _load_db_snapshot(session: Session, realtime_session_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    realtime_session = session.get(RealtimeSession, realtime_session_id)
    turns = session.scalars(
        select(RealtimeSessionTurn)
        .where(RealtimeSessionTurn.session_id == realtime_session_id)
        .order_by(RealtimeSessionTurn.turn_index.asc(), RealtimeSessionTurn.created_at.asc())
    ).all()
    session_payload = None
    if realtime_session is not None:
        session_payload = {
            "id": realtime_session.id,
            "session_status": realtime_session.session_status,
            "turn_count": realtime_session.turn_count,
            "last_user_turn_at": (
                realtime_session.last_user_turn_at.isoformat()
                if realtime_session.last_user_turn_at
                else None
            ),
            "last_assistant_turn_at": (
                realtime_session.last_assistant_turn_at.isoformat()
                if realtime_session.last_assistant_turn_at
                else None
            ),
            "started_at": realtime_session.started_at.isoformat() if realtime_session.started_at else None,
            "ended_at": realtime_session.ended_at.isoformat() if realtime_session.ended_at else None,
        }
    turn_payload = [
        {
            "id": turn.id,
            "turn_index": turn.turn_index,
            "speaker": turn.speaker,
            "input_mode": turn.input_mode,
            "source_text": turn.source_text,
            "created_at": turn.created_at.isoformat(),
        }
        for turn in turns
    ]
    return session_payload, turn_payload


async def run_synthetic_realtime_voice_healthcheck(
    *,
    user_email: str | None = None,
    country_key: str = "Japan",
    audio_fixture_path: Path = DEFAULT_AUDIO_FIXTURE,
    timeout_seconds: float = 20.0,
) -> SyntheticHealthCheckResult:
    session = get_session_factory()()
    realtime_session_id = ""
    tracker: RealtimeObservabilityTracker | None = None

    try:
        actor = _resolve_healthcheck_actor(session, user_email=user_email)
        defaults = simulation_service.get_setup_defaults(session, country_key)
        simulation = simulation_service.create_simulation(
            session,
            actor,
            SimulationCreateRequest(
                countryKey=defaults.countryKey,
                meetingType=defaults.meetingType,
                goal=defaults.goal,
                durationMinutes=defaults.durationMinutes,
                voiceStyle=defaults.voiceStyle,
                voiceProfileId=defaults.voiceProfileId,
            ),
        )
        simulation = simulation_service.generate_simulation_strategy(session, actor, simulation.simulationId)
        realtime_session = realtime_service.create_realtime_session(
            session,
            actor,
            RealtimeSessionCreateRequest(
                simulationId=simulation.simulationId,
                transport="websocket",
                skipLearningPrecheck=True,
            ),
        )
        realtime_session = realtime_service.start_realtime_session(session, actor, realtime_session.sessionId)
        realtime_session_id = realtime_session.sessionId
        tracker = RealtimeObservabilityTracker(realtime_session_id)
        tracker.record_event(
            source="system",
            event_type="healthcheck_started",
            payload_summary={
                "countryKey": country_key,
                "audioFixturePath": str(audio_fixture_path),
            },
            set_values={
                "session_status": realtime_session.status,
                "started_at": realtime_session.startedAt,
            },
        )
        tracker.record_event(
            source="frontend",
            event_type="voice_ws_open",
            payload_summary={"mode": "synthetic_healthcheck"},
            set_values={
                "client_connected": True,
                "session_status": realtime_session.status,
                "started_at": realtime_session.startedAt,
            },
        )

        audio_chunks = _load_audio_chunks(audio_fixture_path)
        browser_ws = SyntheticBrowserSocket()
        producer = asyncio.create_task(
            _stream_audio_fixture(browser_ws, audio_chunks),
            name="synthetic_healthcheck.audio_stream",
        )
        try:
            await asyncio.wait_for(
                run_doubao_voice_bridge(
                    db=session,
                    actor=actor,
                    realtime_session=session.get(RealtimeSession, realtime_session_id),
                    browser_ws=browser_ws,
                ),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            if tracker is not None:
                tracker.record_event(
                    source="system",
                    event_type="error",
                    payload_summary={"stage": "healthcheck_timeout"},
                    error_code="synthetic_timeout",
                    error_message=f"Health check timed out after {timeout_seconds} seconds.",
                )
            await browser_ws.mark_done()
        finally:
            producer.cancel()
            try:
                await producer
            except asyncio.CancelledError:
                pass
            await browser_ws.close()

        ended_session = realtime_service.end_realtime_session(session, actor, realtime_session_id)
        tracker.finalize(
            session_status=ended_session.status,
            ended_at=ended_session.endedAt,
            payload_summary={
                "sentMessageCount": len(browser_ws.sent_messages),
                "audioChunkCount": len(audio_chunks),
            },
        )
        db_session, db_turns = _load_db_snapshot(session, realtime_session_id)
        return SyntheticHealthCheckResult(
            realtime_session_id=realtime_session_id,
            report=tracker.build_report(),
            db_session=db_session,
            db_turns=db_turns,
        )
    except Exception as exc:  # noqa: BLE001
        if tracker is not None:
            tracker.finalize(
                final_status=FINAL_STATUS_DIAGNOSTIC_INCOMPLETE,
                root_block_point=ROOT_EVIDENCE_INVALID,
                payload_summary={"exception": str(exc)},
            )
        raise
    finally:
        session.close()
