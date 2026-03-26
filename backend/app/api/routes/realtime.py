from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.realtime import (
    RealtimeAlertResponse,
    RealtimeSessionCreateRequest,
    RealtimeSessionResponse,
    RealtimeSessionSummaryResponse,
    RealtimeTurnExchangeResponse,
    RealtimeTurnRespondRequest,
    RealtimeTurnResponse,
)
from app.db.session import get_db
from app.modules.realtime import service as realtime_service

router = APIRouter(prefix="/realtime", tags=["realtime"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.post("/sessions", response_model=RealtimeSessionResponse)
def create_realtime_session(
    payload: RealtimeSessionCreateRequest,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionResponse:
    return realtime_service.create_realtime_session(db, actor, payload)


@router.get("/sessions/{sessionId}", response_model=RealtimeSessionResponse)
def get_realtime_session(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionResponse:
    return realtime_service.get_realtime_session(db, actor, sessionId)


@router.get("/sessions/{sessionId}/summary", response_model=RealtimeSessionSummaryResponse)
def get_realtime_session_summary(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionSummaryResponse:
    return realtime_service.get_realtime_session_summary(db, actor, sessionId)


@router.post("/sessions/{sessionId}/start", response_model=RealtimeSessionResponse)
def start_realtime_session(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionResponse:
    return realtime_service.start_realtime_session(db, actor, sessionId)


@router.post("/sessions/{sessionId}/end", response_model=RealtimeSessionResponse)
def end_realtime_session(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionResponse:
    return realtime_service.end_realtime_session(db, actor, sessionId)


@router.post("/sessions/{sessionId}/sync", response_model=RealtimeSessionResponse)
def sync_realtime_session(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeSessionResponse:
    return realtime_service.sync_realtime_session(db, actor, sessionId)


@router.post(
    "/sessions/{sessionId}/turns/respond",
    response_model=RealtimeTurnExchangeResponse,
)
def respond_realtime_turn(
    sessionId: str,
    payload: RealtimeTurnRespondRequest,
    db: DbSession,
    actor: ActorDep,
) -> RealtimeTurnExchangeResponse:
    return realtime_service.respond_realtime_turn(db, actor, sessionId, payload)


@router.get("/sessions/{sessionId}/turns", response_model=list[RealtimeTurnResponse])
def list_realtime_turns(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> list[RealtimeTurnResponse]:
    return realtime_service.list_realtime_turns(db, actor, sessionId)


@router.get("/sessions/{sessionId}/alerts", response_model=list[RealtimeAlertResponse])
def list_realtime_alerts(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> list[RealtimeAlertResponse]:
    return realtime_service.list_realtime_alerts(db, actor, sessionId)
