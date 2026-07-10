from datetime import datetime
from typing import Any, Literal

from app.api.schemas.common import LocalizedText, StrictModel


class LearningCountrySummaryResponse(StrictModel):
    countryKey: str
    countryName: LocalizedText
    hasContent: bool
    latestContentVersion: str | None
    defaultMeetingType: str
    defaultGoal: str


class LearningCountryResponse(StrictModel):
    countryKey: str
    countryName: LocalizedText
    contentVersion: str
    defaultMeetingType: str
    defaultGoal: str
    sections: list[dict[str, Any]]
    checklist: list[dict[str, Any]]


class LearningProgressResponse(StrictModel):
    countryKey: str
    countryName: LocalizedText
    status: Literal["missing", "completed"]
    contentVersion: str | None
    latestContentVersion: str | None
    completedAt: datetime | None
    expiresAt: datetime | None
    isUpToDate: bool


class LearningProgressCompleteRequest(StrictModel):
    contentVersion: str


LearningModuleStatus = Literal["new", "saved", "open", "completed"]
LearningModuleTab = Literal["all", "recommended", "new", "saved", "open", "completed"]
LearningModuleAction = Literal["start", "save", "unsave", "complete"]


class LearningModuleItemResponse(StrictModel):
    moduleId: str
    countryKey: str
    title: str
    summary: str
    theme: str
    scene: str
    status: LearningModuleStatus
    stateLabel: str
    saved: bool
    recommended: bool
    sortOrder: int


class LearningModuleSnapshotCountsResponse(StrictModel):
    open: int
    new: int
    saved: int


class LearningModulesResponse(StrictModel):
    recommendedModule: LearningModuleItemResponse | None
    snapshotCounts: LearningModuleSnapshotCountsResponse
    items: list[LearningModuleItemResponse]


class LearningModuleStateRequest(StrictModel):
    action: LearningModuleAction


class LearningModuleStateResponse(StrictModel):
    item: LearningModuleItemResponse
    recommendedModule: LearningModuleItemResponse | None
    snapshotCounts: LearningModuleSnapshotCountsResponse
