from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.billing import (
    BillingAccountResponse,
    BillingPaymentResponse,
    BillingPlanResponse,
    BillingSelectPlanRequest,
    BillingSummaryResponse,
    BillingTopUpRequest,
    BillingTopUpResponse,
)
from app.core.errors import AppError
from app.models.billing import BillingAccount, BillingPlan, Payment
from app.services.current_actor import CurrentActor

DEMO_PLAN_ORDER = ("free", "go", "plus", "pro")
DEMO_ALLOWED_TOP_UP_AMOUNTS = (500, 1500, 3000)
DEFAULT_CURRENCY_CODE = "USD"
DEMO_PAYMENT_CURRENCY_CODE = "CREDIT"
DEMO_TOP_UP_STATUS = "demo_completed"
DEMO_TOP_UP_EVENT = "top_up"


def _raise_plan_not_found(plan_key: str) -> None:
    raise AppError(
        status_code=404,
        code="billing_plan_not_found",
        message="Billing plan could not be found.",
        details={"planKey": plan_key},
    )


def _raise_top_up_amount_not_allowed(amount: int) -> None:
    raise AppError(
        status_code=400,
        code="billing_top_up_amount_not_allowed",
        message="Top-up amount is not allowed for the demo billing flow.",
        details={"allowedAmounts": list(DEMO_ALLOWED_TOP_UP_AMOUNTS), "amount": amount},
    )


def _get_default_plan(session: Session) -> BillingPlan:
    plan = session.scalar(select(BillingPlan).where(BillingPlan.plan_key == "free"))
    if plan is None:
        raise AppError(
            status_code=500,
            code="billing_plan_catalog_unavailable",
            message="Billing plan catalog is unavailable.",
        )
    return plan


def _get_billing_account(session: Session, actor: CurrentActor) -> BillingAccount | None:
    return session.scalar(select(BillingAccount).where(BillingAccount.user_id == actor.user_id))


def _ensure_billing_account(session: Session, actor: CurrentActor) -> BillingAccount:
    account = _get_billing_account(session, actor)
    if account is not None:
        return account

    default_plan = _get_default_plan(session)
    account = BillingAccount(
        user_id=actor.user_id,
        current_plan_id=default_plan.id,
        credit_balance=0,
        renewal_at=None,
        currency_code=default_plan.currency_code,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _get_active_plan_by_key(session: Session, plan_key: str) -> BillingPlan:
    plan = session.scalar(
        select(BillingPlan).where(
            BillingPlan.plan_key == plan_key,
            BillingPlan.is_active.is_(True),
        )
    )
    if plan is None:
        _raise_plan_not_found(plan_key)
    return plan


def _get_plans_by_order(session: Session) -> list[BillingPlan]:
    plans = list(session.scalars(select(BillingPlan).where(BillingPlan.is_active.is_(True))))
    order_map = {plan_key: index for index, plan_key in enumerate(DEMO_PLAN_ORDER)}
    return sorted(
        plans,
        key=lambda plan: (order_map.get(plan.plan_key, len(order_map)), plan.display_name),
    )


def _build_plan_response(plan: BillingPlan, *, current_plan_id: str | None) -> BillingPlanResponse:
    return BillingPlanResponse(
        planId=plan.id,
        planKey=plan.plan_key,
        displayName=plan.display_name,
        billingCycle=plan.billing_cycle,
        currencyCode=plan.currency_code,
        amountValue=float(plan.amount_value),
        isCurrent=plan.id == current_plan_id,
    )


def _build_summary_response(session: Session, account: BillingAccount) -> BillingSummaryResponse:
    plan = session.scalar(select(BillingPlan).where(BillingPlan.id == account.current_plan_id))
    if plan is None:
        raise AppError(
            status_code=500,
            code="billing_plan_catalog_unavailable",
            message="Current billing plan is unavailable.",
        )

    return BillingSummaryResponse(
        account=BillingAccountResponse(
            currentPlanKey=plan.plan_key,
            creditBalance=account.credit_balance,
            renewalAt=account.renewal_at,
            currencyCode=account.currency_code,
        ),
        currentPlan=_build_plan_response(plan, current_plan_id=plan.id),
        allowedTopUpAmounts=list(DEMO_ALLOWED_TOP_UP_AMOUNTS),
    )


def list_plans(session: Session, actor: CurrentActor) -> list[BillingPlanResponse]:
    account = _get_billing_account(session, actor)
    current_plan_id = account.current_plan_id if account is not None else None
    return [
        _build_plan_response(plan, current_plan_id=current_plan_id)
        for plan in _get_plans_by_order(session)
    ]


def get_summary(session: Session, actor: CurrentActor) -> BillingSummaryResponse:
    account = _ensure_billing_account(session, actor)
    return _build_summary_response(session, account)


def select_plan(
    session: Session,
    actor: CurrentActor,
    payload: BillingSelectPlanRequest,
) -> BillingSummaryResponse:
    account = _ensure_billing_account(session, actor)
    plan = _get_active_plan_by_key(session, payload.planKey)

    account.current_plan_id = plan.id
    account.currency_code = plan.currency_code
    if plan.plan_key == "free":
        account.renewal_at = None
    else:
        account.renewal_at = datetime.now(tz=UTC) + timedelta(days=30)

    session.commit()
    session.refresh(account)
    return _build_summary_response(session, account)


def top_up(
    session: Session,
    actor: CurrentActor,
    payload: BillingTopUpRequest,
) -> BillingTopUpResponse:
    if payload.amount not in DEMO_ALLOWED_TOP_UP_AMOUNTS:
        _raise_top_up_amount_not_allowed(payload.amount)

    account = _ensure_billing_account(session, actor)
    account.credit_balance += payload.amount

    payment = Payment(
        user_id=actor.user_id,
        plan_id=account.current_plan_id,
        event_type=DEMO_TOP_UP_EVENT,
        amount_value=payload.amount,
        currency_code=DEMO_PAYMENT_CURRENCY_CODE,
        payment_status=DEMO_TOP_UP_STATUS,
    )
    session.add(payment)
    session.flush()
    payment.external_reference = f"demo_topup_{payment.id}"
    session.commit()
    session.refresh(account)
    session.refresh(payment)

    return BillingTopUpResponse(
        summary=_build_summary_response(session, account),
        payment=BillingPaymentResponse(
            paymentId=payment.id,
            eventType=payment.event_type,
            amountValue=int(payment.amount_value),
            currencyCode=payment.currency_code,
            paymentStatus=payment.payment_status,
            createdAt=payment.created_at,
        ),
    )
