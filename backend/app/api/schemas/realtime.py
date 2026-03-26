from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel

RealtimeTransport = Literal["webrtc", "websocket"]
RealtimeSessionStatus = Literal["pending", "active", "ended", "failed"]


class RealtimeSessionCreateRequest(StrictModel):
    simulationId: str
    transport: RealtimeTransport | None = None


class RealtimeTurnRespondRequest(StrictModel):
    inputMode: Literal["text", "speech_stub"]
    sourceText: str
    language: str | None = None


class RealtimeLaunchResponse(StrictModel):
    mode: str
    transport: RealtimeTransport
    sessionToken: str
    connectUrl: str | None
    fallbackTransport: RealtimeTransport | None
    expiresAt: datetime


class RealtimeTurnResponse(StrictModel):
    turnId: str
    turnIndex: int
    speaker: str
    inputMode: Literal["text", "speech_stub"] | None
    sourceText: str
    normalizedText: str
    language: str
    parentTurnId: str | None
    createdAt: datetime


class RealtimeAlertResponse(StrictModel):
    alertId: str
    turnId: str
    severity: str
    issueKey: str
    title: str
    detail: str | None
    createdAt: datetime


class RealtimeTurnExchangeResponse(StrictModel):
    sessionId: str
    userTurn: RealtimeTurnResponse
    assistantTurn: RealtimeTurnResponse
    alerts: list[RealtimeAlertResponse]
    turnCount: int


class RealtimeSessionSummaryResponse(StrictModel):
    sessionId: str
    status: RealtimeSessionStatus
    transport: RealtimeTransport
    countryKey: str
    meetingType: str
    goal: str
    durationMinutes: int
    voiceStyle: str
    voiceProfileId: str
    setupRevision: int
    strategyForSetupRevision: int
    turnCount: int
    alertCount: int
    lastAlertSeverity: str | None
    lastUserTurnAt: datetime | None
    lastAssistantTurnAt: datetime | None
    startedAt: datetime | None
    endedAt: datetime | None
    createdAt: datetime
    updatedAt: datetime


class RealtimeSessionResponse(StrictModel):
    sessionId: str
    simulationId: str
    status: RealtimeSessionStatus
    transport: RealtimeTransport
    countryKey: str
    meetingType: str
    goal: str
    durationMinutes: int
    voiceStyle: str
    voiceProfileId: str
    setupRevision: int
    strategyForSetupRevision: int
    launch: RealtimeLaunchResponse
    createdAt: datetime
    updatedAt: datetime
    startedAt: datetime | None
    endedAt: datetime | None
