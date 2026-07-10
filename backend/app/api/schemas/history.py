from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel

HistoryRecordType = Literal["review", "hardware_sync"]
HistoryRecordStatusFilter = Literal["ready", "healthy", "warning", "failed"]


class HistoryRecordResponse(StrictModel):
    recordId: str
    recordType: HistoryRecordType
    title: str
    summary: str | None
    detail: str | None
    countryKey: str | None
    status: str
    createdAt: datetime
    reviewId: str | None
    sourceSessionId: str | None
    overallAssessment: str | None
    score: int | None
    canContinue: bool
    canOpenReview: bool
    canReplay: bool


class HistoryRecordsResponse(StrictModel):
    items: list[HistoryRecordResponse]
