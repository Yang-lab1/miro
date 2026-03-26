from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.billing import (
    BillingPlanResponse,
    BillingSelectPlanRequest,
    BillingSummaryResponse,
    BillingTopUpRequest,
    BillingTopUpResponse,
)
from app.db.session import get_db
from app.modules.billing import service as billing_service

router = APIRouter(prefix="/billing", tags=["billing"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.get("/plans", response_model=list[BillingPlanResponse])
def list_plans(
    db: DbSession,
    actor: ActorDep,
) -> list[BillingPlanResponse]:
    return billing_service.list_plans(db, actor)


@router.get("/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    db: DbSession,
    actor: ActorDep,
) -> BillingSummaryResponse:
    return billing_service.get_summary(db, actor)


@router.post("/select-plan", response_model=BillingSummaryResponse)
def select_plan(
    payload: BillingSelectPlanRequest,
    db: DbSession,
    actor: ActorDep,
) -> BillingSummaryResponse:
    return billing_service.select_plan(db, actor, payload)


@router.post("/top-up", response_model=BillingTopUpResponse)
def top_up(
    payload: BillingTopUpRequest,
    db: DbSession,
    actor: ActorDep,
) -> BillingTopUpResponse:
    return billing_service.top_up(db, actor, payload)
