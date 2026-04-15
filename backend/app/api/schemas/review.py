from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel

ReviewStatus = Literal["ready"]
ReviewAssessment = Literal["needs_work", "mixed", "promising"]
ReviewAnalysisDimensionKey = Literal[
    "goalFit",
    "cultureFit",
    "pacing",
    "clarity",
    "grounding",
    "objection",
]


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


class ReviewAnalysisDimensionResponse(StrictModel):
    dimensionKey: ReviewAnalysisDimensionKey
    label: str
    score: int
    status: Literal["strong", "watch", "weak"]
    reason: str


class ReviewAnalysisTrendPointResponse(StrictModel):
    turnIndex: int
    minuteLabel: str
    score: int
    issueKeys: list[str]


class ReviewAnalysisFocusItemResponse(StrictModel):
    title: str
    detail: str
    dimensionKey: ReviewAnalysisDimensionKey
    relatedIssueKeys: list[str]


class ReviewAnalysisEvidenceMomentResponse(StrictModel):
    minuteLabel: str
    text: str
    relatedIssueKeys: list[str]


class ReviewAnalysisDerivedInsightsResponse(StrictModel):
    strongest: ReviewAnalysisDimensionKey
    weakest: ReviewAnalysisDimensionKey
    spread: int


class ReviewAnalysisResponse(StrictModel):
    overallScore: int
    dimensions: list[ReviewAnalysisDimensionResponse]
    trend: list[ReviewAnalysisTrendPointResponse]
    focusItems: list[ReviewAnalysisFocusItemResponse]
    evidenceMoments: list[ReviewAnalysisEvidenceMomentResponse]
    derivedInsights: ReviewAnalysisDerivedInsightsResponse


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
    analysis: ReviewAnalysisResponse | None = None
    lines: list[ReviewLineResponse]
    createdAt: datetime
    endedAt: datetime | None
