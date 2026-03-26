from fastapi import Request
from sqlalchemy.orm import Session

from app.api.schemas.auth import (
    AuthMembershipResponse,
    AuthOrganizationResponse,
    AuthSessionResponse,
    AuthStatusResponse,
    AuthUserResponse,
)
from app.core.errors import AppError
from app.services.current_actor import resolve_actor_context


def raise_auth_managed_by_supabase() -> None:
    raise AppError(
        status_code=501,
        code="auth_managed_by_supabase",
        message="Authentication is managed by Supabase. Use the Supabase client flow.",
        details={"provider": "supabase"},
    )


def get_auth_session(session: Session, request: Request) -> AuthSessionResponse:
    context = resolve_actor_context(session, request)

    membership = None
    if context.membership is not None:
        membership = AuthMembershipResponse(
            organizationId=context.membership.organization_id,
            roleKey=context.membership.role_key,
            membershipStatus=context.membership.membership_status,
        )

    organization = None
    if context.organization is not None:
        organization = AuthOrganizationResponse(
            id=context.organization.id,
            name=context.organization.name,
            countryKey=context.organization.country_key,
        )

    return AuthSessionResponse(
        user=AuthUserResponse(
            id=context.user.id,
            email=context.user.email,
            fullName=context.user.full_name,
            companyName=context.user.company_name,
            roleTitle=context.user.role_title,
            preferredLanguage=context.user.preferred_language,
            status=context.user.status,
        ),
        membership=membership,
        organization=organization,
        auth=AuthStatusResponse(
            source=context.actor.auth_source,
            subject=context.auth_subject,
            expiresAt=context.auth_expires_at,
            role=context.auth_role,
        ),
    )
