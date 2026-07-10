from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.history import (
    HistoryRecordsResponse,
    HistoryRecordStatusFilter,
    HistoryRecordType,
)
from app.db.session import get_db
from app.modules.history import service as history_service

router = APIRouter(prefix="/history", tags=["history"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.get("/records", response_model=HistoryRecordsResponse)
def list_history_records(
    db: DbSession,
    actor: ActorDep,
    countryKey: Annotated[str | None, Query(max_length=64)] = None,
    type: HistoryRecordType | None = None,  # noqa: A002
    status: HistoryRecordStatusFilter | None = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
) -> HistoryRecordsResponse:
    return history_service.list_history_records(
        db,
        actor,
        country_key=countryKey,
        record_type=type,
        status=status,
        query_text=query,
    )
