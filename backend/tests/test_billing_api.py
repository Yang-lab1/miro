from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.billing import BillingAccount, BillingPlan, Payment
from app.models.user import User


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_user(db_session, *, user_id: str, email: str) -> User:
    user = User(id=user_id, email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def _build_authenticated_client(make_client, supabase_jwks_server, *, user_id: str, email: str):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](sub=user_id, email=email)
    return client, token


def _get_plan(db_session, plan_key: str) -> BillingPlan:
    plan = db_session.scalar(select(BillingPlan).where(BillingPlan.plan_key == plan_key))
    assert plan is not None
    return plan


def test_list_plans_returns_active_catalog_in_stable_order(
    make_client,
    supabase_jwks_server,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="plans@miro.local",
    )

    response = client.get("/api/v1/billing/plans", headers=_auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert [item["planKey"] for item in payload] == ["free", "go", "plus", "pro"]
    assert [item["displayName"] for item in payload] == ["Free", "Go", "Plus", "Pro"]
    assert [item["amountValue"] for item in payload] == [0.0, 8.0, 20.0, 200.0]
    assert all(item["billingCycle"] == "monthly" for item in payload)
    assert all(item["currencyCode"] == "USD" for item in payload)


def test_summary_auto_creates_default_demo_billing_account(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="summary@miro.local",
    )

    response = client.get("/api/v1/billing/summary", headers=_auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"]["currentPlanKey"] == "free"
    assert payload["account"]["creditBalance"] == 0
    assert payload["account"]["renewalAt"] is None
    assert payload["account"]["currencyCode"] == "USD"
    assert payload["currentPlan"]["planKey"] == "free"
    assert payload["allowedTopUpAmounts"] == [500, 1500, 3000]

    account = db_session.scalar(select(BillingAccount).where(BillingAccount.user_id == user_id))
    assert account is not None
    assert account.credit_balance == 0
    assert account.currency_code == "USD"


def test_billing_requires_auth_when_demo_fallback_disabled(make_client, supabase_jwks_server):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )

    response = client.get("/api/v1/billing/summary")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_required"


def test_summary_is_actor_scoped(
    make_client,
    supabase_jwks_server,
):
    first_user_id = str(uuid4())
    second_user_id = str(uuid4())
    first_client, first_token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=first_user_id,
        email="billing-one@miro.local",
    )
    second_client, second_token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=second_user_id,
        email="billing-two@miro.local",
    )

    select_response = first_client.post(
        "/api/v1/billing/select-plan",
        headers=_auth_headers(first_token),
        json={"planKey": "plus"},
    )
    assert select_response.status_code == 200

    top_up_response = first_client.post(
        "/api/v1/billing/top-up",
        headers=_auth_headers(first_token),
        json={"amount": 1500},
    )
    assert top_up_response.status_code == 200

    first_summary = first_client.get("/api/v1/billing/summary", headers=_auth_headers(first_token))
    second_summary = second_client.get(
        "/api/v1/billing/summary",
        headers=_auth_headers(second_token),
    )

    assert first_summary.status_code == 200
    assert second_summary.status_code == 200
    assert first_summary.json()["account"]["currentPlanKey"] == "plus"
    assert first_summary.json()["account"]["creditBalance"] == 1500
    assert second_summary.json()["account"]["currentPlanKey"] == "free"
    assert second_summary.json()["account"]["creditBalance"] == 0


def test_select_plan_updates_current_plan_and_sets_paid_renewal(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="select-plan@miro.local",
    )

    response = client.post(
        "/api/v1/billing/select-plan",
        headers=_auth_headers(token),
        json={"planKey": "pro"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"]["currentPlanKey"] == "pro"
    assert payload["account"]["renewalAt"] is not None
    assert payload["currentPlan"]["planKey"] == "pro"
    assert payload["currentPlan"]["amountValue"] == 200.0

    account = db_session.scalar(select(BillingAccount).where(BillingAccount.user_id == user_id))
    assert account is not None
    assert account.current_plan_id == _get_plan(db_session, "pro").id
    assert account.renewal_at is not None


def test_select_plan_rejects_unknown_or_inactive_plan(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="inactive-plan@miro.local")
    inactive_plan = _get_plan(db_session, "go")
    inactive_plan.is_active = False
    db_session.commit()

    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="inactive-plan@miro.local",
    )

    unknown = client.post(
        "/api/v1/billing/select-plan",
        headers=_auth_headers(token),
        json={"planKey": "enterprise"},
    )
    inactive = client.post(
        "/api/v1/billing/select-plan",
        headers=_auth_headers(token),
        json={"planKey": "go"},
    )

    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "billing_plan_not_found"
    assert inactive.status_code == 404
    assert inactive.json()["error"]["code"] == "billing_plan_not_found"


def test_top_up_increases_balance_and_records_payment_event(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="topup@miro.local",
    )

    response = client.post(
        "/api/v1/billing/top-up",
        headers=_auth_headers(token),
        json={"amount": 3000},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["account"]["creditBalance"] == 3000
    assert payload["payment"]["eventType"] == "top_up"
    assert payload["payment"]["amountValue"] == 3000
    assert payload["payment"]["paymentStatus"] == "demo_completed"
    assert payload["payment"]["currencyCode"] == "CREDIT"

    account = db_session.scalar(select(BillingAccount).where(BillingAccount.user_id == user_id))
    assert account is not None
    assert account.credit_balance == 3000

    payments = list(db_session.scalars(select(Payment).where(Payment.user_id == user_id)))
    assert len(payments) == 1
    assert payments[0].event_type == "top_up"
    assert Decimal(payments[0].amount_value) == Decimal("3000")
    assert payments[0].payment_status == "demo_completed"


def test_top_up_only_allows_whitelisted_amounts(
    make_client,
    supabase_jwks_server,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="topup-invalid@miro.local",
    )

    response = client.post(
        "/api/v1/billing/top-up",
        headers=_auth_headers(token),
        json={"amount": 600},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "billing_top_up_amount_not_allowed"


def test_summary_persists_after_select_plan_and_top_up(
    make_client,
    supabase_jwks_server,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="billing-refresh@miro.local",
    )

    select_response = client.post(
        "/api/v1/billing/select-plan",
        headers=_auth_headers(token),
        json={"planKey": "go"},
    )
    assert select_response.status_code == 200

    top_up_response = client.post(
        "/api/v1/billing/top-up",
        headers=_auth_headers(token),
        json={"amount": 500},
    )
    assert top_up_response.status_code == 200

    first = client.get("/api/v1/billing/summary", headers=_auth_headers(token))
    second = client.get("/api/v1/billing/summary", headers=_auth_headers(token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["account"]["currentPlanKey"] == "go"
    assert first.json()["account"]["creditBalance"] == 500
