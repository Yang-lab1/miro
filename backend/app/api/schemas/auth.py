from datetime import datetime
from typing import Literal

from app.api.schemas.common import StrictModel


class AuthUserResponse(StrictModel):
    id: str
    email: str
    fullName: str | None
    companyName: str | None
    roleTitle: str | None
    preferredLanguage: str
    status: str


class AuthMembershipResponse(StrictModel):
    organizationId: str
    roleKey: str
    membershipStatus: str


class AuthOrganizationResponse(StrictModel):
    id: str
    name: str
    countryKey: str | None


class AuthStatusResponse(StrictModel):
    source: Literal["supabase", "demo_fallback"]
    subject: str
    expiresAt: datetime | None
    role: str | None


class AuthSessionResponse(StrictModel):
    user: AuthUserResponse
    membership: AuthMembershipResponse | None
    organization: AuthOrganizationResponse | None
    auth: AuthStatusResponse
