from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.review import ReviewDetailResponse, ReviewListItemResponse
from app.db.session import get_db
from app.modules.review import service as review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.post("/from-realtime/{sessionId}", response_model=ReviewDetailResponse)
def create_review_from_realtime_session(
    sessionId: str,
    db: DbSession,
    actor: ActorDep,
) -> ReviewDetailResponse:
    return review_service.create_review_from_realtime_session(db, actor, sessionId)


@router.get("", response_model=list[ReviewListItemResponse])
def list_reviews(
    db: DbSession,
    actor: ActorDep,
) -> list[ReviewListItemResponse]:
    return review_service.list_reviews(db, actor)


@router.get("/{reviewId}", response_model=ReviewDetailResponse)
def get_review(
    reviewId: str,
    db: DbSession,
    actor: ActorDep,
) -> ReviewDetailResponse:
    return review_service.get_review_detail(db, actor, reviewId)
