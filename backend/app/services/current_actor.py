from dataclasses import dataclass
from datetime import datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.user import Membership, Organization, User
from app.services.supabase_auth import (
    extract_bearer_token,
    is_demo_actor_fallback_enabled,
    sync_supabase_user,
    verify_supabase_token,
)


@dataclass(slots=True)
class CurrentActor:
    user_id: str
    email: str
    organization_id: str | None
    auth_source: str = "supabase"


@dataclass(slots=True)
class ActorContext:
    actor: CurrentActor
    user: User
    membership: Membership | None
    organization: Organization | None
    auth_subject: str
    auth_role: str | None
    auth_expires_at: datetime | None


def _build_actor_context(
    session: Session,
    *,
    user_id: str,
    auth_source: str,
    auth_subject: str,
    auth_role: str | None,
    auth_expires_at: datetime | None,
) -> ActorContext:
    row = session.execute(
        select(User, Membership, Organization)
        .outerjoin(Membership, Membership.user_id == User.id)
        .outerjoin(Organization, Organization.id == Membership.organization_id)
        .where(User.id == user_id)
        .order_by(Membership.created_at.asc())
    ).first()

    if row is None:
        raise AppError(
            status_code=503,
            code="actor_unavailable",
            message="Current actor could not be resolved.",
            details={"userId": user_id},
        )

    user, membership, organization = row
    actor = CurrentActor(
        user_id=user.id,
        email=user.email,
        organization_id=membership.organization_id if membership else None,
        auth_source=auth_source,
    )
    return ActorContext(
        actor=actor,
        user=user,
        membership=membership,
        organization=organization,
        auth_subject=auth_subject,
        auth_role=auth_role,
        auth_expires_at=auth_expires_at,
    )


def _resolve_demo_actor_context(session: Session) -> ActorContext:
    settings = get_settings()

    stmt = (
        select(User.id)
        .outerjoin(Membership, Membership.user_id == User.id)
        .where(User.email == settings.demo_user_email)
        .order_by(Membership.created_at.asc())
    )
    row = session.execute(stmt).first()

    if row is None:
        raise AppError(
            status_code=503,
            code="actor_unavailable",
            message="Current actor could not be resolved.",
            details={"email": settings.demo_user_email},
        )

    return _build_actor_context(
        session,
        user_id=row.id,
        auth_source="demo_fallback",
        auth_subject=row.id,
        auth_role=None,
        auth_expires_at=None,
    )


def resolve_actor_context(
    session: Session,
    request: Request | None = None,
) -> ActorContext:
    token = extract_bearer_token(request)

    if token is not None:
        claims = verify_supabase_token(token)
        user = sync_supabase_user(session, claims)
        return _build_actor_context(
            session,
            user_id=user.id,
            auth_source="supabase",
            auth_subject=claims.subject,
            auth_role=claims.role,
            auth_expires_at=claims.expires_at,
        )

    if is_demo_actor_fallback_enabled():
        return _resolve_demo_actor_context(session)

    raise AppError(
        status_code=401,
        code="auth_token_required",
        message="Bearer access token is required.",
    )


def resolve_current_actor(
    session: Session,
    request: Request | None = None,
) -> CurrentActor:
    return resolve_actor_context(session, request).actor
