from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel

RealtimeTransport = Literal["webrtc", "websocket"]
RealtimeSessionStatus = Literal["pending", "active", "ended", "failed"]


class RealtimeSessionCreateRequest(StrictModel):
    simulationId: str
    transport: RealtimeTransport | None = None
    skipLearningPrecheck: bool = False
    seedOpeningTurn: bool = False


class RealtimeTurnRespondRequest(StrictModel):
    inputMode: Literal["text", "speech", "speech_stub"]
    sourceText: str | None = None
    language: str | None = None
    audioBase64: str | None = None
    audioMimeType: str | None = None
    audioFileName: str | None = None


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
    inputMode: Literal["text", "speech", "speech_stub"] | None
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
    assistantAudioBase64: str | None = None
    assistantAudioMimeType: str | None = None
    assistantVoice: str | None = None


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
    openingTurn: RealtimeTurnResponse | None = None
    createdAt: datetime
    updatedAt: datetime
    startedAt: datetime | None
    endedAt: datetime | None
