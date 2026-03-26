from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.user import Membership, Organization, User


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_session_creates_local_user_from_valid_supabase_token(
    make_client,
    supabase_jwks_server,
    db_session,
):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    user_id = str(uuid4())
    token = supabase_jwks_server["issue_token"](
        sub=user_id,
        email="new-user@miro.local",
        extra_claims={"user_metadata": {"full_name": "New User"}},
    )

    response = client.get("/api/v1/auth/session", headers=_auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] == user_id
    assert payload["user"]["email"] == "new-user@miro.local"
    assert payload["user"]["fullName"] == "New User"
    assert payload["membership"] is None
    assert payload["organization"] is None
    assert payload["auth"]["source"] == "supabase"
    assert payload["auth"]["subject"] == user_id
    assert payload["auth"]["role"] == "authenticated"
    assert payload["auth"]["expiresAt"] is not None

    user = db_session.scalar(select(User).where(User.id == user_id))
    assert user is not None
    assert user.email == "new-user@miro.local"
    assert user.full_name == "New User"


def test_auth_session_returns_existing_membership_and_organization(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    user = User(id=user_id, email="member@miro.local", full_name="Existing Member", status="active")
    organization = Organization(name="Miro Japan Org", country_key="Japan", is_active=True)
    db_session.add_all([user, organization])
    db_session.flush()
    membership = Membership(
        user_id=user.id,
        organization_id=organization.id,
        role_key="member",
        membership_status="active",
    )
    db_session.add(membership)
    db_session.commit()

    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](sub=user_id, email="member@miro.local")

    response = client.get("/api/v1/auth/session", headers=_auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["membership"] == {
        "organizationId": organization.id,
        "roleKey": "member",
        "membershipStatus": "active",
    }
    assert payload["organization"] == {
        "id": organization.id,
        "name": "Miro Japan Org",
        "countryKey": "Japan",
    }


def test_missing_bearer_token_returns_auth_token_required(make_client):
    client = make_client(ALLOW_DEMO_ACTOR_FALLBACK="false", SUPABASE_URL="http://127.0.0.1:9999")

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_required"


def test_invalid_signature_returns_auth_token_invalid(make_client, supabase_jwks_server):
    from cryptography.hazmat.primitives.asymmetric import rsa

    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    wrong_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = supabase_jwks_server["issue_token"](
        email="wrong-signature@miro.local",
        private_key_override=wrong_private_key,
    )

    response = client.get("/api/v1/auth/session", headers=_auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_invalid"


def test_expired_token_returns_auth_token_expired(make_client, supabase_jwks_server):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](
        email="expired@miro.local",
        expires_in_seconds=-60,
    )

    response = client.get("/api/v1/auth/session", headers=_auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_expired"


@pytest.mark.parametrize(
    ("token_kwargs", "label"),
    [
        ({"issuer_override": "https://malicious.example.com/auth/v1"}, "wrong issuer"),
        ({"audience": "other-audience"}, "wrong audience"),
        ({"role": "service_role"}, "wrong role"),
        ({"email": None}, "missing email"),
        ({"is_anonymous": True}, "anonymous user"),
        ({"extra_claims": {"sub": None}}, "missing sub"),
    ],
)
def test_invalid_claims_return_auth_token_invalid(
    make_client,
    supabase_jwks_server,
    token_kwargs,
    label,
):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](**token_kwargs)

    response = client.get("/api/v1/auth/session", headers=_auth_headers(token))

    assert response.status_code == 401, label
    assert response.json()["error"]["code"] == "auth_token_invalid"


def test_protected_endpoint_prefers_valid_token_over_demo_fallback(
    make_client,
    supabase_jwks_server,
):
    client = make_client(
        APP_ENV="development",
        ALLOW_DEMO_ACTOR_FALLBACK="true",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](email="fresh-user@miro.local")

    response = client.get(
        "/api/v1/learning/progress/Japan",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "missing"
    assert payload["contentVersion"] is None


def test_invalid_token_does_not_fallback_to_demo_actor(make_client, supabase_jwks_server):
    from cryptography.hazmat.primitives.asymmetric import rsa

    client = make_client(
        APP_ENV="development",
        ALLOW_DEMO_ACTOR_FALLBACK="true",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    wrong_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = supabase_jwks_server["issue_token"](
        email="wrong-signature@miro.local",
        private_key_override=wrong_private_key,
    )

    response = client.get("/api/v1/learning/progress/Japan", headers=_auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_invalid"


def test_demo_fallback_allows_session_only_in_explicit_development_mode(make_client):
    client = make_client(
        APP_ENV="development",
        ALLOW_DEMO_ACTOR_FALLBACK="true",
        SUPABASE_URL=None,
    )

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "demo@miro.local"
    assert payload["auth"]["source"] == "demo_fallback"
    assert payload["auth"]["subject"] == payload["user"]["id"]


@pytest.mark.parametrize(
    ("app_env", "allow_demo"),
    [
        ("development", "false"),
        ("production", "true"),
    ],
)
def test_demo_fallback_rejects_when_not_explicitly_allowed(
    make_client,
    app_env,
    allow_demo,
):
    client = make_client(
        APP_ENV=app_env,
        ALLOW_DEMO_ACTOR_FALLBACK=allow_demo,
        SUPABASE_URL=None,
    )

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_required"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/logout"],
)
def test_supabase_managed_routes_return_explicit_placeholder(make_client, path):
    client = make_client()

    response = client.post(path)

    assert response.status_code == 501
    payload = response.json()
    assert payload["error"]["code"] == "auth_managed_by_supabase"
