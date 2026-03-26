from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.learning import (
    LearningCountryResponse,
    LearningCountrySummaryResponse,
    LearningProgressCompleteRequest,
    LearningProgressResponse,
)
from app.db.session import get_db
from app.modules.learning import service as learning_service

router = APIRouter(prefix="/learning", tags=["learning"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.get("/countries", response_model=list[LearningCountrySummaryResponse])
def list_learning_countries(db: DbSession) -> list[LearningCountrySummaryResponse]:
    return learning_service.list_learning_countries(db)


@router.get("/countries/{countryKey}", response_model=LearningCountryResponse)
def get_country_learning(
    countryKey: str,
    db: DbSession,
) -> LearningCountryResponse:
    return learning_service.get_country_learning(db, countryKey)


@router.get("/progress/{countryKey}", response_model=LearningProgressResponse)
def get_learning_progress(
    countryKey: str,
    db: DbSession,
    actor: ActorDep,
) -> LearningProgressResponse:
    return learning_service.get_learning_progress(db, actor, countryKey)


@router.post("/progress/{countryKey}/complete", response_model=LearningProgressResponse)
def complete_learning(
    countryKey: str,
    payload: LearningProgressCompleteRequest,
    db: DbSession,
    actor: ActorDep,
) -> LearningProgressResponse:
    return learning_service.complete_learning_progress(
        db,
        actor,
        countryKey,
        payload.contentVersion,
    )
