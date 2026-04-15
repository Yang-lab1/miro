from datetime import datetime
from typing import Literal

from pydantic import Field

from app.api.schemas.common import LocalizedText, StrictModel

SimulationSetupStatus = Literal["draft", "ready_for_strategy", "strategy_ready"]


class SimulationPrecheckRequest(StrictModel):
    countryKey: str


class SimulationPrecheckLearningState(StrictModel):
    status: Literal["missing", "completed"]
    contentVersion: str | None
    completedVersion: str | None
    isUpToDate: bool


class SimulationPrecheckResponse(StrictModel):
    ready: bool
    countryKey: str
    countryName: LocalizedText
    reason: Literal["ready", "learning_required", "learning_outdated", "country_not_supported"]
    learning: SimulationPrecheckLearningState
    recommendedAction: str | None = None
    skipLearningAllowed: bool | None = None
    warningMode: str | None = None


class SimulationSetupDefaultsResponse(StrictModel):
    countryKey: str
    meetingType: str
    goal: str
    durationMinutes: int = Field(ge=1)
    voiceStyle: str
    voiceProfileId: str


class SimulationCreateRequest(StrictModel):
    countryKey: str
    meetingType: str | None = None
    goal: str | None = None
    durationMinutes: int | None = Field(default=None, ge=1)
    voiceStyle: str | None = None
    voiceProfileId: str | None = None
    constraints: str | None = None


class SimulationPatchRequest(StrictModel):
    countryKey: str | None = None
    meetingType: str | None = None
    goal: str | None = None
    durationMinutes: int | None = Field(default=None, ge=1)
    voiceStyle: str | None = None
    voiceProfileId: str | None = None
    constraints: str | None = None


class SimulationFileCreateRequest(StrictModel):
    fileName: str
    contentType: str
    sizeBytes: int = Field(ge=0)
    sourceType: str | None = None
    textContent: str | None = None
    fileDataBase64: str | None = None


class SimulationFilesRequest(StrictModel):
    files: list[SimulationFileCreateRequest] = Field(min_length=1)


class SimulationUploadedFileResponse(StrictModel):
    fileId: str
    fileName: str
    contentType: str
    sizeBytes: int
    sourceType: str | None
    storageKey: str | None
    parseStatus: str | None
    status: str
    createdAt: datetime


class SimulationStrategyGeneratedFrom(StrictModel):
    countryKey: str
    meetingType: str
    goal: str
    voiceStyle: str
    voiceProfileId: str
    learningContentVersion: str
    setupRevision: int


class SimulationStrategyBullets(StrictModel):
    en: list[str]
    zh: list[str]


class SimulationStrategyItem(StrictModel):
    id: str
    tag: LocalizedText
    title: LocalizedText
    bullets: SimulationStrategyBullets


class SimulationStrategyResponse(StrictModel):
    templateKey: str
    generatedAt: datetime
    generatedFrom: SimulationStrategyGeneratedFrom
    summary: LocalizedText
    items: list[SimulationStrategyItem]


class SimulationResponse(StrictModel):
    simulationId: str
    status: SimulationSetupStatus
    setupRevision: int
    countryKey: str
    meetingType: str | None
    goal: str | None
    durationMinutes: int | None
    voiceStyle: str | None
    voiceProfileId: str | None
    constraints: str | None
    uploadedFiles: list[SimulationUploadedFileResponse]
    strategy: SimulationStrategyResponse | None
    createdAt: datetime
    updatedAt: datetime
