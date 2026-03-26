from datetime import datetime

from pydantic import Field

from app.api.schemas.common import StrictModel


class BillingPlanResponse(StrictModel):
    planId: str
    planKey: str
    displayName: str
    billingCycle: str
    currencyCode: str
    amountValue: float
    isCurrent: bool


class BillingAccountResponse(StrictModel):
    currentPlanKey: str
    creditBalance: int
    renewalAt: datetime | None
    currencyCode: str


class BillingSummaryResponse(StrictModel):
    account: BillingAccountResponse
    currentPlan: BillingPlanResponse
    allowedTopUpAmounts: list[int]


class BillingSelectPlanRequest(StrictModel):
    planKey: str = Field(min_length=1, max_length=64)


class BillingTopUpRequest(StrictModel):
    amount: int


class BillingPaymentResponse(StrictModel):
    paymentId: str
    eventType: str
    amountValue: int
    currencyCode: str
    paymentStatus: str
    createdAt: datetime


class BillingTopUpResponse(StrictModel):
    summary: BillingSummaryResponse
    payment: BillingPaymentResponse
