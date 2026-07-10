from datetime import datetime

from app.api.schemas.common import StrictModel


class UserTwinMemoryResponse(StrictModel):
    memoryId: str
    issueKey: str
    countryKey: str
    riskLevel: str
    issueCount: int
    lastContext: str | None
    lastReviewId: str | None
    lastSeenAt: datetime | None
    createdAt: datetime
    updatedAt: datetime


class UserTwinResponse(StrictModel):
    items: list[UserTwinMemoryResponse]
