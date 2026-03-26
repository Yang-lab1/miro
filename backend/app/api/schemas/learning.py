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
