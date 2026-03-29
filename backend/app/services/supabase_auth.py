from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Request
from jwt import PyJWKClient
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWKClientError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.audit import AuditLog
from app.models.billing import BillingAccount, Payment
from app.models.hardware import Device
from app.models.learning import UserLearningProgress
from app.models.review import Review
from app.models.simulation import RealtimeSession, Simulation
from app.models.user import Membership, User, UserTwinMemory

ASYMMETRIC_SIGNING_ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512")


@dataclass(slots=True)
class VerifiedSupabaseClaims:
    subject: str
    email: str
    role: str
    expires_at: datetime
    full_name: str | None


def extract_bearer_token(request: Request | None) -> str | None:
    if request is None:
        return None

    authorization = request.headers.get("Authorization")
    if authorization is None:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Authorization header must use Bearer token.",
        )

    return credentials.strip()


def is_demo_actor_fallback_enabled() -> bool:
    settings = get_settings()
    return settings.app_env == "development" and settings.allow_demo_actor_fallback


def _resolve_supabase_issuer() -> str:
    settings = get_settings()
    if settings.resolved_supabase_jwt_issuer:
        return settings.resolved_supabase_jwt_issuer

    raise AppError(
        status_code=503,
        code="auth_configuration_error",
        message="Supabase authentication is not configured.",
    )


def _resolve_supabase_jwks_url() -> str:
    settings = get_settings()
    if settings.resolved_supabase_jwks_url:
        return settings.resolved_supabase_jwks_url

    raise AppError(
        status_code=503,
        code="auth_configuration_error",
        message="Supabase authentication is not configured.",
    )


def _extract_full_name(payload: dict[str, Any]) -> str | None:
    user_metadata = payload.get("user_metadata")
    if isinstance(user_metadata, dict):
        for key in ("full_name", "name"):
            value = user_metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    full_name = payload.get("full_name")
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()

    return None


@lru_cache(maxsize=16)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def verify_supabase_token(token: str) -> VerifiedSupabaseClaims:
    settings = get_settings()
    issuer = _resolve_supabase_issuer()
    jwks_url = _resolve_supabase_jwks_url()

    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        ) from exc

    algorithm = header.get("alg")
    if algorithm not in ASYMMETRIC_SIGNING_ALGORITHMS:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )

    try:
        signing_key = _get_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=settings.supabase_jwt_audience,
            issuer=issuer,
            options={"require": ["sub", "exp", "iss", "aud"]},
        )
    except ExpiredSignatureError as exc:
        raise AppError(
            status_code=401,
            code="auth_token_expired",
            message="Bearer token has expired.",
        ) from exc
    except PyJWKClientError as exc:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        ) from exc
    except InvalidTokenError as exc:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        ) from exc

    subject = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")
    expires_at = payload.get("exp")

    if not isinstance(subject, str) or not subject:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )
    if not isinstance(email, str) or not email:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )
    if role != "authenticated":
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )
    if payload.get("is_anonymous") is True:
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )
    if not isinstance(expires_at, (int, float)):
        raise AppError(
            status_code=401,
            code="auth_token_invalid",
            message="Bearer token is invalid.",
        )

    return VerifiedSupabaseClaims(
        subject=subject,
        email=email,
        role=role,
        expires_at=datetime.fromtimestamp(expires_at, tz=UTC),
        full_name=_extract_full_name(payload),
    )


def _reassign_user_foreign_keys(
    session: Session,
    *,
    from_user_id: str,
    to_user_id: str,
) -> None:
    reassignments = (
        (AuditLog, AuditLog.actor_user_id),
        (BillingAccount, BillingAccount.user_id),
        (Payment, Payment.user_id),
        (Device, Device.user_id),
        (UserLearningProgress, UserLearningProgress.user_id),
        (Review, Review.user_id),
        (Simulation, Simulation.user_id),
        (RealtimeSession, RealtimeSession.user_id),
        (Membership, Membership.user_id),
        (UserTwinMemory, UserTwinMemory.user_id),
    )

    for model, column in reassignments:
        session.execute(
            update(model)
            .where(column == from_user_id)
            .values({column.key: to_user_id})
        )


def _migrate_legacy_user_to_supabase_subject(
    session: Session,
    *,
    legacy_user: User,
    claims: VerifiedSupabaseClaims,
) -> User:
    legacy_user.email = f"migrated+{legacy_user.id}@miro.local"
    session.flush()

    migrated_user = User(
        id=claims.subject,
        email=claims.email,
        full_name=claims.full_name or legacy_user.full_name,
        company_name=legacy_user.company_name,
        role_title=legacy_user.role_title,
        preferred_language=legacy_user.preferred_language,
        status=legacy_user.status,
        created_at=legacy_user.created_at,
        updated_at=legacy_user.updated_at,
    )
    session.add(migrated_user)
    session.flush()

    _reassign_user_foreign_keys(
        session,
        from_user_id=legacy_user.id,
        to_user_id=migrated_user.id,
    )
    session.delete(legacy_user)
    session.flush()

    return migrated_user


def sync_supabase_user(session: Session, claims: VerifiedSupabaseClaims) -> User:
    existing_conflict = session.scalar(
        select(User)
        .where(
            User.email == claims.email,
            User.id != claims.subject,
        )
        .limit(1)
    )

    user = session.scalar(select(User).where(User.id == claims.subject).limit(1))
    has_changes = False

    if user is None and existing_conflict is not None:
        user = _migrate_legacy_user_to_supabase_subject(
            session,
            legacy_user=existing_conflict,
            claims=claims,
        )
        has_changes = True
    elif user is None:
        user = User(
            id=claims.subject,
            email=claims.email,
            full_name=claims.full_name,
            status="active",
        )
        session.add(user)
        has_changes = True
    else:
        if user.email != claims.email:
            user.email = claims.email
            has_changes = True
        if claims.full_name and user.full_name != claims.full_name:
            user.full_name = claims.full_name
            has_changes = True

    try:
        if has_changes:
            session.commit()
            session.refresh(user)
    except IntegrityError as exc:
        session.rollback()
        raise AppError(
            status_code=409,
            code="auth_user_sync_failed",
            message="Authenticated user could not be synchronized locally.",
        ) from exc

    return user
