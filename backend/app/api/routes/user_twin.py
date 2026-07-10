from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.user_twin import UserTwinResponse
from app.db.session import get_db
from app.modules.user_twin import service as user_twin_service

router = APIRouter(prefix="/user-twin", tags=["user-twin"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.get("", response_model=UserTwinResponse)
def get_user_twin(
    db: DbSession,
    actor: ActorDep,
    countryKey: str | None = Query(default=None),
) -> UserTwinResponse:
    return user_twin_service.list_memories(db, actor, country_key=countryKey)


@router.post("/refresh-from-review/{reviewId}", response_model=UserTwinResponse)
def refresh_user_twin_from_review(
    reviewId: str,
    db: DbSession,
    actor: ActorDep,
) -> UserTwinResponse:
    return user_twin_service.refresh_from_review(db, actor, reviewId)
