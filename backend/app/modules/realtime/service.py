import re
from datetime import UTC, datetime

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.api.schemas.realtime import (
    RealtimeAlertResponse,
    RealtimeLaunchResponse,
    RealtimeSessionCreateRequest,
    RealtimeSessionResponse,
    RealtimeSessionSummaryResponse,
    RealtimeTurnExchangeResponse,
    RealtimeTurnRespondRequest,
    RealtimeTurnResponse,
)
from app.core.errors import AppError
from app.models.simulation import (
    RealtimeSession,
    RealtimeSessionAlert,
    RealtimeSessionTurn,
    Simulation,
    VoiceProfileCatalog,
)
from app.modules.realtime.alerts import RuleBasedRealtimeAlertAnalyzer
from app.modules.realtime.grounding import build_realtime_grounding_context
from app.modules.realtime.observability import RealtimeObservabilityTracker
from app.modules.realtime.providers import get_realtime_provider
from app.modules.realtime.providers.base import (
    RealtimeAlertExtractionContext,
    RealtimeLaunchContext,
    RealtimeProviderSyncContext,
    RealtimeTurnGenerationContext,
)
from app.modules.realtime.turn_engine import RuleBasedRealtimeTurnGenerator
from app.modules.simulation import service as simulation_service
from app.services.current_actor import CurrentActor

STATUS_REASON_LAUNCH_EXPIRED = "launch_expired"
STATUS_REASON_SUPERSEDED_TRANSPORT = "superseded_transport"
STATUS_REASON_SUPERSEDED_SETUP_REVISION = "superseded_setup_revision"
STATUS_REASON_SUPERSEDED_STRATEGY_REVISION = "superseded_strategy_revision"
STATUS_REASON_MANUALLY_ENDED = "manually_ended"

turn_generator = RuleBasedRealtimeTurnGenerator()
alert_analyzer = RuleBasedRealtimeAlertAnalyzer()


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _get_voice_profile_by_internal_id(
    session: Session,
    voice_profile_catalog_id: str,
) -> VoiceProfileCatalog | None:
    return session.scalar(
        select(VoiceProfileCatalog)
        .where(VoiceProfileCatalog.id == voice_profile_catalog_id)
        .limit(1)
    )


def _get_realtime_session_for_actor(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSession:
    realtime_session = session.scalar(
        select(RealtimeSession)
        .where(
            RealtimeSession.id == session_id,
            RealtimeSession.user_id == actor.user_id,
        )
        .limit(1)
    )

    if realtime_session is None:
        raise AppError(
            status_code=404,
            code="realtime_session_not_found",
            message=f"Realtime session '{session_id}' was not found.",
        )

    return realtime_session


def load_realtime_session_for_actor(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSession:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)
    return realtime_session


def _get_candidate_launch_session(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
) -> RealtimeSession | None:
    return session.scalar(
        select(RealtimeSession)
        .where(
            RealtimeSession.user_id == actor.user_id,
            RealtimeSession.simulation_id == simulation_id,
            RealtimeSession.session_status.in_(("pending", "active")),
        )
        .order_by(
            case((RealtimeSession.session_status == "active", 0), else_=1),
            RealtimeSession.created_at.desc(),
        )
        .limit(1)
    )


def _parse_launch_payload(payload: dict | None) -> RealtimeLaunchResponse:
    if payload is None:
        raise AppError(
            status_code=500,
            code="realtime_launch_missing",
            message="Realtime launch payload is missing.",
        )
    return RealtimeLaunchResponse.model_validate(payload)


def _build_realtime_response(
    session: Session,
    realtime_session: RealtimeSession,
) -> RealtimeSessionResponse:
    voice_profile = _get_voice_profile_by_internal_id(
        session,
        realtime_session.voice_profile_catalog_id,
    )
    if voice_profile is None:
        raise AppError(
            status_code=500,
            code="voice_profile_not_found",
            message="Voice profile catalog entry for realtime session is missing.",
            details={"sessionId": realtime_session.id},
        )

    return RealtimeSessionResponse(
        sessionId=realtime_session.id,
        simulationId=realtime_session.simulation_id,
        status=realtime_session.session_status,
        transport=realtime_session.transport,
        countryKey=realtime_session.country_key,
        meetingType=realtime_session.meeting_type_key,
        goal=realtime_session.goal_key,
        durationMinutes=realtime_session.duration_minutes,
        voiceStyle=realtime_session.voice_style_key,
        voiceProfileId=voice_profile.voice_profile_id,
        setupRevision=realtime_session.setup_revision,
        strategyForSetupRevision=realtime_session.strategy_for_setup_revision,
        launch=_parse_launch_payload(realtime_session.launch_payload_json),
        createdAt=realtime_session.created_at,
        updatedAt=realtime_session.updated_at,
        startedAt=realtime_session.started_at,
        endedAt=realtime_session.ended_at,
    )


def _build_realtime_summary_response(
    session: Session,
    realtime_session: RealtimeSession,
) -> RealtimeSessionSummaryResponse:
    voice_profile = _get_voice_profile_by_internal_id(
        session,
        realtime_session.voice_profile_catalog_id,
    )
    if voice_profile is None:
        raise AppError(
            status_code=500,
            code="voice_profile_not_found",
            message="Voice profile catalog entry for realtime session is missing.",
            details={"sessionId": realtime_session.id},
        )

    return RealtimeSessionSummaryResponse(
        sessionId=realtime_session.id,
        status=realtime_session.session_status,
        transport=realtime_session.transport,
        countryKey=realtime_session.country_key,
        meetingType=realtime_session.meeting_type_key,
        goal=realtime_session.goal_key,
        durationMinutes=realtime_session.duration_minutes,
        voiceStyle=realtime_session.voice_style_key,
        voiceProfileId=voice_profile.voice_profile_id,
        setupRevision=realtime_session.setup_revision,
        strategyForSetupRevision=realtime_session.strategy_for_setup_revision,
        turnCount=realtime_session.turn_count,
        alertCount=realtime_session.alert_count,
        lastAlertSeverity=realtime_session.last_alert_severity,
        lastUserTurnAt=realtime_session.last_user_turn_at,
        lastAssistantTurnAt=realtime_session.last_assistant_turn_at,
        startedAt=realtime_session.started_at,
        endedAt=realtime_session.ended_at,
        createdAt=realtime_session.created_at,
        updatedAt=realtime_session.updated_at,
    )


def _build_turn_response(turn: RealtimeSessionTurn) -> RealtimeTurnResponse:
    return RealtimeTurnResponse(
        turnId=turn.id,
        turnIndex=turn.turn_index,
        speaker=turn.speaker,
        inputMode=turn.input_mode,
        sourceText=turn.source_text or "",
        normalizedText=turn.normalized_text or "",
        language=turn.language or "en",
        parentTurnId=turn.parent_turn_id,
        createdAt=turn.created_at,
    )


def _build_alert_response(alert: RealtimeSessionAlert) -> RealtimeAlertResponse:
    return RealtimeAlertResponse(
        alertId=alert.id,
        turnId=alert.turn_id,
        severity=alert.severity,
        issueKey=alert.issue_key,
        title=alert.title_text,
        detail=alert.detail_text,
        createdAt=alert.created_at,
    )


def _is_launch_expired(
    realtime_session: RealtimeSession,
    now: datetime,
) -> bool:
    if realtime_session.launch_expires_at is None:
        return True
    return _ensure_utc(realtime_session.launch_expires_at) <= now


def _mark_realtime_session_failed(
    realtime_session: RealtimeSession,
    *,
    reason: str | None,
    now: datetime,
) -> None:
    realtime_session.session_status = "failed"
    realtime_session.status_reason = reason
    if realtime_session.ended_at is None:
        realtime_session.ended_at = now


def _mark_realtime_session_ended(
    realtime_session: RealtimeSession,
    *,
    reason: str | None,
    now: datetime,
) -> None:
    realtime_session.session_status = "ended"
    realtime_session.status_reason = reason
    if realtime_session.ended_at is None:
        realtime_session.ended_at = now


def _apply_provider_sync(
    realtime_session: RealtimeSession,
) -> bool:
    provider = get_realtime_provider(realtime_session.provider_mode)
    sync_result = provider.sync_runtime_state(
        RealtimeProviderSyncContext(
            session_id=realtime_session.id,
            transport=realtime_session.transport,
            provider_mode=realtime_session.provider_mode,
            provider_session_id=realtime_session.provider_session_id,
            provider_status=realtime_session.provider_status,
            provider_payload_json=realtime_session.provider_payload_json,
        )
    )
    changed = False

    if sync_result.provider_status != realtime_session.provider_status:
        realtime_session.provider_status = sync_result.provider_status
        changed = True

    if sync_result.provider_payload_json != realtime_session.provider_payload_json:
        realtime_session.provider_payload_json = sync_result.provider_payload_json
        changed = True

    return changed


def _sync_realtime_session_runtime_state(
    realtime_session: RealtimeSession,
    *,
    now: datetime,
) -> bool:
    changed = _apply_provider_sync(realtime_session)

    if realtime_session.session_status == "pending" and _is_launch_expired(realtime_session, now):
        _mark_realtime_session_failed(
            realtime_session,
            reason=STATUS_REASON_LAUNCH_EXPIRED,
            now=now,
        )
        if realtime_session.provider_status is not None:
            realtime_session.provider_status = "failed"
        return True

    if realtime_session.provider_status == "closed":
        if realtime_session.session_status != "ended":
            _mark_realtime_session_ended(
                realtime_session,
                reason=realtime_session.status_reason,
                now=now,
            )
            changed = True
        elif realtime_session.ended_at is None:
            realtime_session.ended_at = now
            changed = True

    if realtime_session.provider_status == "failed":
        if realtime_session.session_status != "failed":
            _mark_realtime_session_failed(
                realtime_session,
                reason=realtime_session.status_reason,
                now=now,
            )
            changed = True
        elif realtime_session.ended_at is None:
            realtime_session.ended_at = now
            changed = True

    return changed


def _sync_and_refresh_if_needed(
    session: Session,
    realtime_session: RealtimeSession,
) -> RealtimeSession:
    changed = _sync_realtime_session_runtime_state(realtime_session, now=_utcnow())
    if changed:
        session.commit()
        session.refresh(realtime_session)
    return realtime_session


def _get_pending_stale_reason(
    realtime_session: RealtimeSession,
    *,
    simulation: Simulation,
    transport: str,
    now: datetime,
) -> str | None:
    if _is_launch_expired(realtime_session, now):
        return STATUS_REASON_LAUNCH_EXPIRED
    if realtime_session.transport != transport:
        return STATUS_REASON_SUPERSEDED_TRANSPORT
    if realtime_session.setup_revision != simulation.setup_revision:
        return STATUS_REASON_SUPERSEDED_SETUP_REVISION
    if realtime_session.strategy_for_setup_revision != simulation.strategy_for_setup_revision:
        return STATUS_REASON_SUPERSEDED_STRATEGY_REVISION
    return None


def _raise_not_startable_error(realtime_session: RealtimeSession) -> None:
    if (
        realtime_session.session_status == "failed"
        and realtime_session.status_reason == STATUS_REASON_LAUNCH_EXPIRED
    ):
        raise AppError(
            status_code=400,
            code="realtime_launch_expired",
            message="Realtime launch payload has expired.",
            details={"sessionId": realtime_session.id},
        )

    raise AppError(
        status_code=400,
        code="realtime_session_not_startable",
        message="Realtime session can no longer be started.",
        details={
            "sessionId": realtime_session.id,
            "status": realtime_session.session_status,
        },
    )


def _raise_not_active_error(realtime_session: RealtimeSession) -> None:
    raise AppError(
        status_code=400,
        code="realtime_session_not_active",
        message="Realtime session is not active.",
        details={
            "sessionId": realtime_session.id,
            "status": realtime_session.session_status,
        },
    )


def _try_advance_next_turn_index(
    session: Session,
    session_id: str,
    *,
    expected_next_turn_index: int,
    ) -> bool:
    result = session.execute(
        update(RealtimeSession)
        .where(
            RealtimeSession.id == session_id,
            RealtimeSession.next_turn_index == expected_next_turn_index,
        )
        .values(next_turn_index=expected_next_turn_index + 2)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _reserve_turn_index_pair(
    session: Session,
    realtime_session: RealtimeSession,
) -> tuple[int, int]:
    for _ in range(5):
        session.refresh(realtime_session, attribute_names=["next_turn_index"])
        next_turn_index = int(realtime_session.next_turn_index or 1)

        if _try_advance_next_turn_index(
            session,
            realtime_session.id,
            expected_next_turn_index=next_turn_index,
        ):
            realtime_session.next_turn_index = next_turn_index + 2
            return next_turn_index, next_turn_index + 1

        session.expire(realtime_session, ["next_turn_index"])

    raise AppError(
        status_code=409,
        code="realtime_turn_index_conflict",
        message="Realtime turn order could not be allocated safely.",
        details={"sessionId": realtime_session.id},
    )


def _load_recent_transcript_lines(
    session: Session,
    session_id: str,
    *,
    limit: int = 4,
) -> list[str]:
    turns = session.scalars(
        select(RealtimeSessionTurn)
        .where(RealtimeSessionTurn.session_id == session_id)
        .order_by(
            RealtimeSessionTurn.turn_index.desc(),
            RealtimeSessionTurn.created_at.desc(),
            RealtimeSessionTurn.id.desc(),
        )
        .limit(limit)
    ).all()
    ordered_turns = list(reversed(turns))
    transcript_lines: list[str] = []
    for turn in ordered_turns:
        text = turn.normalized_text or turn.source_text or ""
        if not text:
            continue
        transcript_lines.append(f"{turn.speaker}: {text}")
    return transcript_lines


def create_realtime_session(
    session: Session,
    actor: CurrentActor,
    payload: RealtimeSessionCreateRequest,
) -> RealtimeSessionResponse:
    prerequisites = simulation_service.validate_realtime_launch_prerequisites(
        session,
        actor,
        payload.simulationId,
        skip_learning_precheck=payload.skipLearningPrecheck,
    )
    simulation = prerequisites.simulation
    voice_profile_catalog_id = simulation.voice_profile_catalog_id
    if voice_profile_catalog_id is None:
        raise AppError(
            status_code=400,
            code="voice_profile_not_selected",
            message="voiceProfileId is required before realtime launch.",
            details={"simulationId": payload.simulationId},
        )

    transport = payload.transport or "webrtc"
    now = _utcnow()
    existing_session = _get_candidate_launch_session(session, actor, payload.simulationId)
    if existing_session is not None:
        _sync_realtime_session_runtime_state(existing_session, now=now)

        if existing_session.session_status == "active":
            session.commit()
            session.refresh(existing_session)
            return _build_realtime_response(session, existing_session)

        if existing_session.session_status == "pending":
            stale_reason = _get_pending_stale_reason(
                existing_session,
                simulation=simulation,
                transport=transport,
                now=now,
            )
            if stale_reason is None:
                session.commit()
                session.refresh(existing_session)
                return _build_realtime_response(session, existing_session)

            _mark_realtime_session_failed(
                existing_session,
                reason=stale_reason,
                now=now,
            )
            if existing_session.provider_status is not None:
                existing_session.provider_status = "failed"

    provider = get_realtime_provider()
    launch_result = provider.create_launch(
        RealtimeLaunchContext(
            actor_user_id=actor.user_id,
            simulation_id=simulation.id,
            transport=transport,
        )
    )
    realtime_session = RealtimeSession(
        simulation_id=simulation.id,
        user_id=actor.user_id,
        country_key=simulation.country_key,
        meeting_type_key=simulation.meeting_type_key or "",
        goal_key=simulation.goal_key or "",
        duration_minutes=simulation.duration_minutes or 0,
        voice_style_key=simulation.voice_style_key or "",
        voice_profile_catalog_id=voice_profile_catalog_id,
        setup_revision=simulation.setup_revision,
        strategy_for_setup_revision=simulation.strategy_for_setup_revision
        or prerequisites.setup_revision,
        transport=transport,
        session_status="pending",
        status_reason=None,
        provider_mode=launch_result.provider_mode,
        provider_session_id=launch_result.provider_session_id,
        provider_status=launch_result.provider_status,
        provider_payload_json=launch_result.provider_payload_json,
        launch_payload_json=launch_result.launch.model_dump(mode="json"),
        launch_expires_at=launch_result.launch.expiresAt,
        next_turn_index=1,
        last_user_turn_at=None,
        last_assistant_turn_at=None,
        turn_count=0,
        alert_count=0,
        last_alert_severity=None,
    )
    session.add(realtime_session)
    session.commit()
    session.refresh(realtime_session)
    RealtimeObservabilityTracker(realtime_session.id).sync_session_state(
        session_status=realtime_session.session_status,
        started_at=realtime_session.started_at,
        ended_at=realtime_session.ended_at,
        doubao_session_id=realtime_session.provider_session_id,
    )
    return _build_realtime_response(session, realtime_session)


def get_realtime_session(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSessionResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)
    return _build_realtime_response(session, realtime_session)


def get_realtime_session_summary(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSessionSummaryResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)
    return _build_realtime_summary_response(session, realtime_session)


def start_realtime_session(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSessionResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)

    if realtime_session.session_status == "active":
        return _build_realtime_response(session, realtime_session)

    if realtime_session.provider_status == "closed":
        _mark_realtime_session_ended(
            realtime_session,
            reason=realtime_session.status_reason,
            now=_utcnow(),
        )
        session.commit()
        session.refresh(realtime_session)

    if realtime_session.session_status in {"ended", "failed"}:
        _raise_not_startable_error(realtime_session)

    realtime_session.session_status = "active"
    realtime_session.provider_status = "connected"
    if realtime_session.started_at is None:
        realtime_session.started_at = _utcnow()

    session.commit()
    session.refresh(realtime_session)
    RealtimeObservabilityTracker(realtime_session.id).sync_session_state(
        session_status=realtime_session.session_status,
        started_at=realtime_session.started_at,
        ended_at=realtime_session.ended_at,
        doubao_session_id=realtime_session.provider_session_id,
    )
    return _build_realtime_response(session, realtime_session)


def end_realtime_session(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSessionResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)

    if realtime_session.session_status == "failed":
        return _build_realtime_response(session, realtime_session)

    if realtime_session.session_status == "ended":
        return _build_realtime_response(session, realtime_session)

    _mark_realtime_session_ended(
        realtime_session,
        reason=STATUS_REASON_MANUALLY_ENDED,
        now=_utcnow(),
    )
    realtime_session.provider_status = "closed"
    session.commit()
    session.refresh(realtime_session)
    RealtimeObservabilityTracker(realtime_session.id).sync_session_state(
        session_status=realtime_session.session_status,
        started_at=realtime_session.started_at,
        ended_at=realtime_session.ended_at,
        doubao_session_id=realtime_session.provider_session_id,
    )
    return _build_realtime_response(session, realtime_session)


def sync_realtime_session(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> RealtimeSessionResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)
    return _build_realtime_response(session, realtime_session)


def respond_realtime_turn(
    session: Session,
    actor: CurrentActor,
    session_id: str,
    payload: RealtimeTurnRespondRequest,
) -> RealtimeTurnExchangeResponse:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)

    if realtime_session.session_status != "active":
        _raise_not_active_error(realtime_session)

    language = payload.language or "en"
    grounding = build_realtime_grounding_context(session, realtime_session)
    user_turn_index, assistant_turn_index = _reserve_turn_index_pair(session, realtime_session)
    user_turn_created_at = _utcnow()
    assistant_audio_base64: str | None = None
    assistant_audio_mime_type: str | None = None
    assistant_voice: str | None = None

    if payload.inputMode == "speech":
        raise AppError(
            status_code=400,
            code="realtime_voice_socket_required",
            message="Speech turns must use /realtime/sessions/{id}/voice.",
            details={
                "sessionId": realtime_session.id,
                "hint": "Use the Doubao voice WebSocket bridge from the Live stage.",
            },
        )

    normalized_text = _normalize_text(payload.sourceText or "")
    if not normalized_text:
        raise AppError(
            status_code=400,
            code="validation_error",
            message="Request validation failed.",
            details={
                "errors": [
                    {
                        "loc": ["body", "sourceText"],
                        "msg": "sourceText must not be empty after trimming.",
                        "type": "value_error",
                    }
                ]
            },
        )
    transcript_text = payload.sourceText or normalized_text

    user_turn = RealtimeSessionTurn(
        session_id=realtime_session.id,
        turn_index=user_turn_index,
        parent_turn_id=None,
        speaker="user",
        input_mode=payload.inputMode,
        source_text=transcript_text,
        normalized_text=normalized_text,
        language=language,
        created_at=user_turn_created_at,
    )
    session.add(user_turn)
    session.flush()
    recent_transcript_lines = _load_recent_transcript_lines(
        session,
        realtime_session.id,
    )

    generated_turn = turn_generator.generate_turn(
        RealtimeTurnGenerationContext(
            session_id=realtime_session.id,
            provider_mode=realtime_session.provider_mode,
            language=language,
            normalized_text=normalized_text,
            grounding=grounding,
            recent_transcript_lines=recent_transcript_lines,
        )
    )
    assistant_text = generated_turn.assistant_text

    assistant_turn_created_at = _utcnow()
    assistant_turn = RealtimeSessionTurn(
        session_id=realtime_session.id,
        turn_index=assistant_turn_index,
        parent_turn_id=user_turn.id,
        speaker="assistant",
        input_mode=None,
        source_text=assistant_text,
        normalized_text=assistant_text,
        language=language,
        created_at=assistant_turn_created_at,
    )
    session.add(assistant_turn)
    session.flush()

    created_alerts: list[RealtimeSessionAlert] = []
    extracted_alerts = alert_analyzer.extract_alerts(
        RealtimeAlertExtractionContext(
            session_id=realtime_session.id,
            normalized_text=normalized_text,
            grounding=grounding,
        )
    )
    for alert_spec in extracted_alerts:
        alert = RealtimeSessionAlert(
            session_id=realtime_session.id,
            turn_id=user_turn.id,
            severity=alert_spec.severity,
            issue_key=alert_spec.issue_key,
            title_text=alert_spec.title_text,
            detail_text=alert_spec.detail_text,
            created_at=_utcnow(),
        )
        session.add(alert)
        created_alerts.append(alert)

    realtime_session.turn_count += 2
    realtime_session.last_user_turn_at = user_turn_created_at
    realtime_session.last_assistant_turn_at = assistant_turn_created_at
    if created_alerts:
        realtime_session.alert_count += len(created_alerts)
        realtime_session.last_alert_severity = created_alerts[-1].severity

    session.commit()
    session.refresh(realtime_session)
    session.refresh(user_turn)
    session.refresh(assistant_turn)
    for alert in created_alerts:
        session.refresh(alert)

    return RealtimeTurnExchangeResponse(
        sessionId=realtime_session.id,
        userTurn=_build_turn_response(user_turn),
        assistantTurn=_build_turn_response(assistant_turn),
        alerts=[_build_alert_response(alert) for alert in created_alerts],
        turnCount=realtime_session.turn_count,
        assistantAudioBase64=assistant_audio_base64,
        assistantAudioMimeType=assistant_audio_mime_type,
        assistantVoice=assistant_voice,
    )


def list_realtime_turns(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> list[RealtimeTurnResponse]:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)

    turns = session.scalars(
        select(RealtimeSessionTurn)
        .where(RealtimeSessionTurn.session_id == realtime_session.id)
        .order_by(
            RealtimeSessionTurn.turn_index.asc(),
            RealtimeSessionTurn.created_at.asc(),
            RealtimeSessionTurn.id.asc(),
        )
    ).all()
    return [_build_turn_response(turn) for turn in turns]


def list_realtime_alerts(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> list[RealtimeAlertResponse]:
    realtime_session = _get_realtime_session_for_actor(session, actor, session_id)
    _sync_and_refresh_if_needed(session, realtime_session)

    alerts = session.scalars(
        select(RealtimeSessionAlert)
        .where(RealtimeSessionAlert.session_id == realtime_session.id)
        .order_by(
            RealtimeSessionAlert.created_at.desc(),
            RealtimeSessionAlert.id.desc(),
        )
    ).all()
    return [_build_alert_response(alert) for alert in alerts]
