from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.voice_profiles import VoiceProfileResponseItem
from app.db.session import get_db
from app.modules.simulation import service as simulation_service

router = APIRouter(tags=["voice-profiles"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/voice-profiles", response_model=list[VoiceProfileResponseItem])
def list_voice_profiles(
    countryKey: Annotated[str, Query(...)],
    db: DbSession,
) -> list[VoiceProfileResponseItem]:
    return simulation_service.list_voice_profiles(db, countryKey)
