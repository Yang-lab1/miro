from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.schemas.auth import AuthSessionResponse
from app.db.session import get_db
from app.modules.auth import service as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register() -> None:
    auth_service.raise_auth_managed_by_supabase()


@router.post("/login")
def login() -> None:
    auth_service.raise_auth_managed_by_supabase()


@router.post("/logout")
def logout() -> None:
    auth_service.raise_auth_managed_by_supabase()


@router.get("/session", response_model=AuthSessionResponse)
def get_session(
    request: Request,
    db: DbSession,
) -> AuthSessionResponse:
    return auth_service.get_auth_session(db, request)
