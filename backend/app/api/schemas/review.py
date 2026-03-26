from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel

ReviewStatus = Literal["ready"]
ReviewAssessment = Literal["needs_work", "mixed", "promising"]


class ReviewSummaryResponse(StrictModel):
    headline: str
    coachSummary: str
    nextStep: str


class ReviewMetricsResponse(StrictModel):
    turnCount: int
    alertCount: int
    highSeverityCount: int
    mediumSeverityCount: int
    topIssueKeys: list[str]


class ReviewLineResponse(StrictModel):
    lineIndex: int
    speaker: str
    turnIndex: int
    text: str
    alertIssueKeys: list[str]
    createdAt: datetime


class ReviewListItemResponse(StrictModel):
    reviewId: str
    sourceType: str
    sourceSessionId: str
    status: ReviewStatus
    countryKey: str
    meetingType: str
    goal: str
    overallAssessment: ReviewAssessment
    topIssueKeys: list[str]
    createdAt: datetime
    endedAt: datetime | None


class ReviewDetailResponse(StrictModel):
    reviewId: str
    sourceType: str
    sourceSessionId: str
    status: ReviewStatus
    countryKey: str
    meetingType: str
    goal: str
    durationMinutes: int
    voiceStyle: str
    voiceProfileId: str
    setupRevision: int
    strategyForSetupRevision: int
    overallAssessment: ReviewAssessment
    summary: ReviewSummaryResponse
    metrics: ReviewMetricsResponse
    lines: list[ReviewLineResponse]
    createdAt: datetime
    endedAt: datetime | None
